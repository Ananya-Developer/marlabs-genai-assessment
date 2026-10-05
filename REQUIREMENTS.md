# Assessment checklist

| Requirement | Implementation / verification |
| --- | --- |
| Spring public API and Python processing | `spring-api/`, `python-service/`; public demo exercises both |
| Caller required; tenant/role from lookup | `Api.CALLERS`, validation tests and forged body identity test |
| Strict date and effective interval | `Api.asOf`, `Engine.answer`; start/end boundary tests |
| Approved, relevant, accessible evidence only | Metadata filtering before `policy_fact` and generation; spy model test |
| Answered / insufficient / conflict | `Engine.answer`, public saved response examples |
| Policy IDs and exact source quotations | Original JSON records; citation equality assertions |
| Supplied policy records separate and unchanged | `data/policies.json`, 12 supplied records |
| Reorder, duplicate, add/change records | Mutation tests; no hardcoded policy IDs in application logic |
| TXT and text PDF | `extract_text`; supplied request 02 and corrupt-file tests |
| Extract fields with source quotations | `extract_fields`; source substring assertions |
| Missing/ambiguous inputs distinct from failure/conflict | Request 03 amount null, request 07 amount absent; both completed |
| Annual limit does not prove payability | Every completed item includes explicit limitations and human review |
| Untrusted submissions/policies/model | Caller context from Java; conservative fact parser; exact output validation |
| Preserve duplicate and failed entries | `Engine.batch`; request 06 and empty request 08 |
| Batch metadata and one-to-one file validation | `Api.batch`; Java tests and public demo missing/extra/duplicate parts |
| No automatic retries; bounded generation and HTTP | `generate_once`, Java timeouts and streaming POST; failure tests |
| Timeout, unavailable, malformed doubles | `test_core.py`, `test_server.py`, `ApiTest.java` |
| Traceable batch/document diagnostics | Sanitized IDs and per-item status/error logging |
| Runnable calls and saved real responses | `examples/demo.py`, curl calls in README, `examples/responses/` |
| Dependencies, startup/config and error shapes | Manifests and README |
| Decision, limitations, AI/time disclosure | `DECISIONS.md`; candidate must fill actual personal time |
| Production design at most 400 words | `PRODUCTION.md` |
| Public GitHub URL and full reviewed SHA | Submission commands in README; candidate publication/submission pending |
| Explain and predict without AI in follow-up | `WALKTHROUGH.md`; candidate must practice independently |
