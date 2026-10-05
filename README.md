# Employee support desk: small, offline, evidence-first

Spring Boot owns the public API, validates requests, and resolves the synthetic caller identity. A loopback-only Python service extracts TXT/PDF submissions, filters policies, and generates supported answers with a deterministic offline model double. No API key, database, frontend, OCR, or paid provider is needed.

## Prerequisites and startup

Use Java 17+, Maven 3.9+, and Python 3.10+. Initial dependency installation requires internet access; installed dependencies and the application work offline. Run these commands from the repository root (PowerShell, macOS, or Linux):

```sh
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux instead: source .venv/bin/activate
python -m pip install -r python-service/requirements.txt
mvn -f spring-api/pom.xml clean verify
```

Open two terminals, both at the repository root with the Python environment activated:

```sh
# Terminal 1
python python-service/server.py
# Terminal 2
java -jar spring-api/target/support-desk-1.0.0.jar
```

The public API is `http://127.0.0.1:8080`; Python is internal at `http://127.0.0.1:8001`. The internal service assumes a trusted local machine and must not be exposed publicly. The caller header only simulates authentication, as specified by the exercise.

## Tests and reproducible demonstration

```sh
python -m unittest discover -s python-service -v
mvn -f spring-api/pom.xml test
# With both services running:
python examples/demo.py
```

The demonstration calls the public Spring API, checks business outcomes, caller rejection, date validation, and missing/extra/duplicate multipart uploads. It writes real public responses to `examples/responses/`. The supplied batch has 8 results in manifest order: 7 completed and 1 failed. Request 02 is a text-based PDF, request 06 is an exact byte duplicate of request 01, and request 08 is empty.

See `VALIDATION.md` for the checks actually run here and the desktop environment's Java build limitation. The tests and live API demonstration passed; a clean Maven build and executable-JAR packaging still need independent local verification.

Python tests cover access filtering, both date boundaries, verbatim evidence, conflicts, unavailable evidence, forged instructions, policy reordering/duplication/addition/change, ambiguous fields, duplicates, mixed results, corrupt files, and timeout/unavailable/malformed model doubles with one attempt. Spring tests cover caller/body validation, metadata/file matching, forged body identity, dependency errors and timeouts. One uncovered behavior is resource exhaustion from a deliberately complex, compressed PDF: this local version has upload size limits but does not isolate PDF parsing in a killable worker process.

## Public requests

Use `curl.exe` on Windows (avoids PowerShell's historical curl alias); `curl` on Linux/macOS.

```sh
curl.exe -X POST http://127.0.0.1:8080/answer -H "X-Caller-Id: atlas-employee-01" -H "Content-Type: application/json" --data-binary "@examples/answer.json"
```

```sh
curl.exe -X POST http://127.0.0.1:8080/batches -H "X-Caller-Id: atlas-employee-01" -F "metadata=@examples/manifest.json;type=application/json" -F "files=@examples/requests/request-01.txt" -F "files=@examples/requests/request-02.pdf" -F "files=@examples/requests/request-03.txt" -F "files=@examples/requests/request-04.txt" -F "files=@examples/requests/request-05.txt" -F "files=@examples/requests/request-06.txt" -F "files=@examples/requests/request-07.txt" -F "files=@examples/requests/request-08.txt"
```

Callers: `atlas-employee-01`, `atlas-contractor-01`, `boreal-employee-01`. Every request requires a valid `as_of` in exact `YYYY-MM-DD` form. Effective dates are start-inclusive and end-exclusive. Only Approved records matching the resolved tenant and role are eligible. Submission text and extra request body fields cannot set tenant or role.

## Response shapes and errors

`/answer` returns `{status, answer, citations}`. `ANSWERED` contains a supported string and citations; `CONFLICT` contains null answer and conflicting citations; `INSUFFICIENT_EVIDENCE` contains null answer and an empty citation list. Each citation is `{chunk_id, quote}` with the original policy ID and verbatim passage.

`/batches` returns `{batch_id, summary: {total, completed, failed}, results: [...]}`. Each result contains:

| Field | Shape / meaning |
| --- | --- |
| `document_id` | Manifest identifier |
| `processing_status` | `COMPLETED` or `FAILED`; readable missing information is completed |
| `extracted` | `{benefit, amount, currency, reference}`; each string or null. Amount is a decimal string, never a payable amount |
| `field_evidence` | Same four keys, each an array of verbatim extracted source quotations. Competing amount quotations remain visible when amount is null |
| `policy` | `/answer` shape, or null on failure/unidentified benefit |
| `review_required` | Always true |
| `issues` | Array of readable review reasons: unresolved fields, policy gaps/conflicts, policy conditions, no claims history, and no determination of eligibility/balance/payability |
| `duplicate_of` | Earliest earlier document ID with identical file bytes; otherwise null. Duplicates still get an independently processed result |
| `error` | Null when completed; `{code, message}` when failed |

Request-level errors have `{error: {code, message}}`. HTTP 401: `UNKNOWN_CALLER`. HTTP 400: `INVALID_REQUEST`, `INVALID_DATE`, `INVALID_METADATA`, `DUPLICATE_MANIFEST`, `FILE_MISMATCH`, `UPLOAD_FAILURE`. Multipart files over Spring's configured limits are rejected before processing. HTTP 502/504: `DEPENDENCY_UNAVAILABLE`, `DEPENDENCY_FAILURE`, `DEPENDENCY_MALFORMED`, `DEPENDENCY_TIMEOUT`, `INTERNAL_FAILURE`, or a propagated model failure. Item error codes: `EMPTY_FILE`, `UNREADABLE_FILE`, `UNSUPPORTED_FILE`, `ITEM_FAILURE`, `MODEL_TIMEOUT`, `MODEL_UNAVAILABLE`, `MODEL_MALFORMED`. Python's private request validation also uses `INVALID_INTERNAL_REQUEST` and `NOT_FOUND`.

No automatic retries are enabled. Generation is attempted at most once per question/item, only when a supported, nonconflicting fact exists. A timeout or unsupported model output is a failure, never a business outcome of insufficient evidence. Model doubles are injected in tests; there is no production failure-switch endpoint.

## Configuration and limits

| Environment variable | Default | Meaning |
| --- | --- | --- |
| `PORT` | `8080` | Spring port |
| `PYTHON_PORT` | `8001` | Python port |
| `PYTHON_URL` | `http://127.0.0.1:8001` | Spring's processing service URL |
| `PYTHON_TIMEOUT_MS` | `15000` | Read timeout per Python HTTP call; connect timeout is 2 seconds |
| `MODEL_TIMEOUT_SECONDS` | `1` | Generation deadline; increase Spring timeout if changed substantially |
| `API_URL` | `http://127.0.0.1:8080` | Demonstration target |

Each batch supports 1-8 files, at most 1 MB per file and 12 MB per multipart request. IDs are 1-100 letters/digits/dot/underscore/hyphen to prevent log injection. The manifest has unique document IDs and filenames, and uploaded files must match it one-to-one. UTF-8 TXT and text-based PDF are supported; encrypted/image-only/corrupt PDFs fail individually. Diagnostic logs contain batch/document identifiers, processing status and error code, not full text or credentials. Nothing approves claims, pays money, or sends employee messages.

Policies live only in `data/policies.json`. There are no special-case policy IDs in application logic. Exact duplicate records do not create false conflicts; simultaneously applicable different facts do. Conservative grammar supports the supplied annual-limit and travel/training policy forms. Unsupported prose and broad or multiple-benefit questions return insufficient evidence rather than guessing; add explicit tested grammars to support more language. There is no real model integration.

## Submission and ownership

Read `DECISIONS.md`, `PRODUCTION.md`, and `REQUIREMENTS.md`. Learn the flow in `WALKTHROUGH.md` so you can explain and modify it yourself. Replace the candidate-owned time/unfinished-work disclosure in `DECISIONS.md` with your actual information before submission.

Create your own public GitHub repository and push these files, excluding `.venv`, build folders and credentials. Then record the reviewed commit:

```sh
git init
git add .
git commit -m "Implement offline employee policy and reimbursement triage"
git branch -M main
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git
git push -u origin main
git rev-parse HEAD
```

Reply to the recruitment email with the repository URL and full final SHA. This local deliverable has not been published or emailed. Keep the reviewed commit available and commit only synthetic data.
