package example;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import java.io.IOException;
import java.net.*;
import java.time.LocalDate;
import java.util.*;

@RestController
public class Api {
    private final ObjectMapper mapper;
    private final String pythonUrl;
    private final int timeout;
    static final Map<String, Map<String,String>> CALLERS = Map.of(
        "atlas-employee-01", Map.of("tenant","Atlas","role","employee"),
        "atlas-contractor-01", Map.of("tenant","Atlas","role","contractor"),
        "boreal-employee-01", Map.of("tenant","Boreal","role","employee"));

    public Api(ObjectMapper mapper, @Value("${python.url}") String pythonUrl, @Value("${python.timeout-ms}") int timeout) {
        this.mapper=mapper; this.pythonUrl=pythonUrl; this.timeout=timeout;
    }
    static class Problem extends RuntimeException {
        final int status; final String code;
        Problem(int status, String code, String message) { super(message); this.status=status; this.code=code; }
    }
    private Map<String,String> caller(String id) {
        if (id==null || !CALLERS.containsKey(id)) throw new Problem(401,"UNKNOWN_CALLER","A known X-Caller-Id is required.");
        return CALLERS.get(id);
    }
    private String required(JsonNode body, String field) {
        if (body==null || !body.isObject() || !body.path(field).isTextual() || body.path(field).asText().isBlank())
            throw new Problem(400,"INVALID_REQUEST",field+" must be a non-empty string.");
        return body.get(field).asText();
    }
    private String asOf(JsonNode body) {
        String value=required(body,"as_of");
        try { if (!value.matches("\\d{4}-\\d{2}-\\d{2}") || LocalDate.parse(value).getYear()<1) throw new IllegalArgumentException(); }
        catch (Exception e) { throw new Problem(400,"INVALID_DATE","as_of must be a valid YYYY-MM-DD date."); }
        return value;
    }
    @PostMapping(value="/answer", consumes="application/json")
    public JsonNode answer(@RequestHeader(value="X-Caller-Id",required=false) String id, @RequestBody JsonNode body) {
        var context=caller(id);
        return call("/answer",Map.of("context",context,"as_of",asOf(body),"question",required(body,"question")));
    }
    @PostMapping(value="/batches", consumes="multipart/form-data")
    public JsonNode batch(@RequestHeader(value="X-Caller-Id",required=false) String id,
                          @RequestPart("metadata") String metadata, @RequestPart("files") List<MultipartFile> files) {
        var context=caller(id);
        JsonNode body;
        try { body=mapper.readTree(metadata); } catch (Exception e) { throw new Problem(400,"INVALID_METADATA","metadata must be JSON."); }
        String batchId=required(body,"batch_id"), day=asOf(body);
        if (batchId.length()>100 || !batchId.matches("[A-Za-z0-9._-]+")) throw new Problem(400,"INVALID_METADATA","batch_id must be 1-100 safe identifier characters.");
        JsonNode docs=body.path("documents");
        if (!docs.isArray() || docs.isEmpty() || docs.size()>8) throw new Problem(400,"INVALID_METADATA","Provide 1-8 manifest entries.");
        Set<String> ids=new HashSet<>(), names=new HashSet<>();
        for (JsonNode doc:docs) {
            String docId=required(doc,"document_id"), name=required(doc,"filename");
            if (docId.length()>100 || !docId.matches("[A-Za-z0-9._-]+") || name.length()>200 || name.contains("/") || name.contains("\\"))
                throw new Problem(400,"INVALID_METADATA","Invalid document identifier or filename.");
            if (!ids.add(docId) || !names.add(name)) throw new Problem(400,"DUPLICATE_MANIFEST","Manifest IDs and filenames must be unique.");
        }
        Map<String,MultipartFile> uploaded=new HashMap<>();
        for (MultipartFile file:files) {
            String name=file.getOriginalFilename();
            if (!names.contains(name) || uploaded.putIfAbsent(name,file)!=null) throw new Problem(400,"FILE_MISMATCH","Uploaded files must match the manifest exactly.");
        }
        if (!uploaded.keySet().equals(names)) throw new Problem(400,"FILE_MISMATCH","Uploaded files must match the manifest exactly.");
        List<Map<String,String>> documents=new ArrayList<>();
        for (JsonNode doc:docs) {
            String name=doc.get("filename").asText();
            try { documents.add(Map.of("document_id",doc.get("document_id").asText(),"filename",name,"content",Base64.getEncoder().encodeToString(uploaded.get(name).getBytes()))); }
            catch (IOException e) { throw new Problem(400,"UPLOAD_FAILURE","An upload could not be read."); }
        }
        return call("/batch",Map.of("context",context,"as_of",day,"batch_id",batchId,"documents",documents));
    }
    private JsonNode call(String path,Object payload) {
        HttpURLConnection connection=null;
        try {
            connection=(HttpURLConnection) URI.create(pythonUrl+path).toURL().openConnection();
            connection.setConnectTimeout(2000); connection.setReadTimeout(timeout); connection.setInstanceFollowRedirects(false);
            connection.setRequestMethod("POST"); connection.setDoOutput(true); connection.setRequestProperty("Content-Type","application/json");
            byte[] bytes=mapper.writeValueAsBytes(payload);
            connection.setFixedLengthStreamingMode(bytes.length);
            try (var output=connection.getOutputStream()) { output.write(bytes); }
            int status=connection.getResponseCode();
            if (status>=400) {
                try (var stream=connection.getErrorStream()) {
                    JsonNode error=mapper.readTree(stream).path("error");
                    throw new Problem(status==504?504:502,error.path("code").asText("DEPENDENCY_FAILURE"),error.path("message").asText("Processing service failed."));
                }
            }
            if (status!=200) throw new Problem(502,"DEPENDENCY_FAILURE","Unexpected processing response.");
            try (var stream=connection.getInputStream()) {
                JsonNode response=mapper.readTree(stream);
                if (response==null || !response.isObject() || (path.equals("/answer") && !Set.of("ANSWERED","CONFLICT","INSUFFICIENT_EVIDENCE").contains(response.path("status").asText())) || (path.equals("/batch") && !response.path("results").isArray()))
                    throw new Problem(502,"DEPENDENCY_MALFORMED","Invalid processing response.");
                return response;
            }
        } catch (SocketTimeoutException e) { throw new Problem(504,"DEPENDENCY_TIMEOUT","Processing service timed out."); }
        catch (IOException e) { throw new Problem(502,"DEPENDENCY_UNAVAILABLE","Processing service is unavailable or returned invalid JSON."); }
        finally { if (connection!=null) connection.disconnect(); }
    }
    @ExceptionHandler(Problem.class)
    public ResponseEntity<?> problem(Problem error) {
        return ResponseEntity.status(error.status).body(Map.of("error",Map.of("code",error.code,"message",error.getMessage())));
    }
    @ExceptionHandler(Exception.class)
    public ResponseEntity<?> invalid(Exception error) {
        return ResponseEntity.badRequest().body(Map.of("error",Map.of("code","INVALID_REQUEST","message","Invalid request body or multipart upload.")));
    }
}
