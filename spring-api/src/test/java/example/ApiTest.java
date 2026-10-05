package example;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.*;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.atomic.AtomicReference;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;
import static org.junit.jupiter.api.Assertions.*;

class ApiTest {
    HttpServer server; MockMvc mvc;
    AtomicReference<String> received=new AtomicReference<>();
    String response="{\"status\":\"INSUFFICIENT_EVIDENCE\",\"answer\":null,\"citations\":[]}";
    int status=200; long delay=0;
    @BeforeEach void setup() throws Exception {
        server=HttpServer.create(new InetSocketAddress("127.0.0.1",0),0);
        server.createContext("/",exchange->{
            received.set(new String(exchange.getRequestBody().readAllBytes(),StandardCharsets.UTF_8));
            try { Thread.sleep(delay); byte[] bytes=response.getBytes(StandardCharsets.UTF_8); exchange.sendResponseHeaders(status,bytes.length); exchange.getResponseBody().write(bytes); }
            catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            finally { exchange.close(); }
        });
        server.start();
        mvc=MockMvcBuilders.standaloneSetup(new Api(new ObjectMapper(),"http://127.0.0.1:"+server.getAddress().getPort(),100)).build();
    }
    @AfterEach void cleanup() { server.stop(0); }
    @Test void identityAndValidation() throws Exception {
        for(String id:new String[]{"", "unknown"}) mvc.perform(post("/answer").header("X-Caller-Id",id).contentType("application/json").content("{\"question\":\"certification\",\"as_of\":\"2026-09-21\"}")).andExpect(status().isUnauthorized());
        mvc.perform(post("/answer").contentType("application/json").content("{}")).andExpect(status().isUnauthorized());
        for(String body:new String[]{"{}","{\"question\":\"\",\"as_of\":\"2026-09-21\"}","{\"question\":42,\"as_of\":\"2026-09-21\"}","{\"question\":\"q\",\"as_of\":\"2026-02-30\"}","{\"question\":\"q\",\"as_of\":\"2026-9-21\"}"})
            mvc.perform(post("/answer").header("X-Caller-Id","atlas-employee-01").contentType("application/json").content(body)).andExpect(status().isBadRequest());
        mvc.perform(post("/answer").header("X-Caller-Id","atlas-employee-01").contentType("application/json").content("{\"question\":\"q\",\"as_of\":\"2026-09-21\",\"tenant\":\"Boreal\",\"role\":\"contractor\"}")).andExpect(status().isOk());
        assertEquals("Atlas",new ObjectMapper().readTree(received.get()).path("context").path("tenant").asText());
        assertEquals("employee",new ObjectMapper().readTree(received.get()).path("context").path("role").asText());
    }
    MockMultipartFile metadata(String docs) {
        return new MockMultipartFile("metadata","", "application/json",("{\"batch_id\":\"test\",\"as_of\":\"2026-09-21\",\"documents\":"+docs+"}").getBytes(StandardCharsets.UTF_8));
    }
    @Test void multipartContract() throws Exception {
        String doc="{\"document_id\":\"one\",\"filename\":\"a.txt\"}";
        MockMultipartFile file=new MockMultipartFile("files","a.txt","text/plain",new byte[0]);
        mvc.perform(multipart("/batches").file(metadata("["+doc+","+doc+"]")).file(file).header("X-Caller-Id","atlas-employee-01")).andExpect(status().isBadRequest());
        mvc.perform(multipart("/batches").file(metadata("["+doc+"]")).file(new MockMultipartFile("files","b.txt","text/plain",new byte[0])).header("X-Caller-Id","atlas-employee-01")).andExpect(status().isBadRequest());
        mvc.perform(multipart("/batches").file(metadata("["+doc+",{\"document_id\":\"two\",\"filename\":\"b.txt\"}]")).file(file).header("X-Caller-Id","atlas-employee-01")).andExpect(status().isBadRequest());
        mvc.perform(multipart("/batches").file(metadata("["+doc+"]")).file(file).file(file).header("X-Caller-Id","atlas-employee-01")).andExpect(status().isBadRequest());
        response="{\"batch_id\":\"test\",\"summary\":{},\"results\":[]}";
        mvc.perform(multipart("/batches").file(metadata("["+doc+"]")).file(file).header("X-Caller-Id","atlas-employee-01")).andExpect(status().isOk());
        assertTrue(received.get().contains("\"content\":\"\""));
    }
    @Test void dependencyFailures() throws Exception {
        response="{\"error\":{\"code\":\"MODEL_MALFORMED\",\"message\":\"Unsupported output.\"}}"; status=502;
        mvc.perform(post("/answer").header("X-Caller-Id","atlas-employee-01").contentType("application/json").content("{\"question\":\"q\",\"as_of\":\"2026-09-21\"}")).andExpect(status().isBadGateway()).andExpect(jsonPath("$.error.code").value("MODEL_MALFORMED"));
        status=200;response="not JSON";
        mvc.perform(post("/answer").header("X-Caller-Id","atlas-employee-01").contentType("application/json").content("{\"question\":\"q\",\"as_of\":\"2026-09-21\"}")).andExpect(status().isBadGateway());
        response="{}"; delay=250;
        mvc.perform(post("/answer").header("X-Caller-Id","atlas-employee-01").contentType("application/json").content("{\"question\":\"q\",\"as_of\":\"2026-09-21\"}")).andExpect(status().isGatewayTimeout());
        server.stop(0);
        mvc.perform(post("/answer").header("X-Caller-Id","atlas-employee-01").contentType("application/json").content("{\"question\":\"q\",\"as_of\":\"2026-09-21\"}")).andExpect(status().isBadGateway());
    }
}
