# Verification performed on 2026-10-05

Swagger addition: the three Spring API tests passed again. A separate local Spring instance served `/swagger-ui/index.html` and `/openapi.json` successfully; `/v3/api-docs/swagger-config` correctly selected the supplied contract. The Swagger contract includes request examples, the caller header and multipart file inputs. Restart/rebuild your running JAR to use the addition.

- Python: 7 test methods passed, including multiple subcases and an actual internal HTTP server exercising model timeout, unavailable provider and malformed output.
- Spring: 3 test methods passed, with zero failures/errors/skips. Tests exercise synthetic caller lookup, forged body identity, dates and question validation, multipart manifests/file matching, unavailable dependency, malformed JSON, propagated model errors and read timeout.
- Live public API: `examples/demo.py` passed against both running services. Saved representative public JSON responses are in `examples/responses/`; they are actual HTTP outputs, not manually constructed examples. The supplied batch returned total 8, completed 7, failed 1. Every result requires human review.
- Sample PDF was rendered and visually checked; it is text-based and successfully processed by the live batch.

This desktop environment has a Java NIO permission problem: javac emitted the compiled classes, but failed while closing archive files with `AccessDeniedException`. Separate compilation of main/test sources and `mvn surefire:test` allowed the Spring tests to run successfully. The live Spring service was started with the resolved Maven dependency classpath. A clean Maven build and executable-JAR packaging have therefore **not been verified here**; run the README's `mvn -f spring-api/pom.xml clean verify` on your local machine before submitting. No tests were changed or disabled to produce the passing test result.

Port 8080 was already used by another application here, so the live demonstration used port 18080 and `API_URL=http://127.0.0.1:18080`. Default repository configuration remains port 8080. If that port is busy locally, set `PORT=18080` for Spring and `API_URL=http://127.0.0.1:18080` for the demo.

Candidate-owned final checks: fill in actual time spent, read and understand the implementation, independently run the tests and clean build, publish the public repository, and send its URL/full final commit SHA to recruitment. No repository was published and no email was sent from this chat.
