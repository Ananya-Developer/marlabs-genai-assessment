# Be ready to explain it

Trace request 05: Spring looks up `atlas-employee-01` as Atlas/employee. It validates the batch date and one-to-one manifest/files. It forwards that context and file bytes to Python. Python extracts certification, INR 70000 and CERT-505 with quotations. The embedded Boreal identity and SYSTEM MESSAGE do not set context. `Engine.answer` filters metadata first, so only the current Atlas employee certification policy is considered. The offline double returns its supported text. The report gives INR 25000 as the annual limit and explicitly requires human review; it does not approve or calculate a payable amount.

Functions to understand:

- `Api.caller`, `asOf`, `batch`: resolve trusted context and reject invalid public requests before processing.
- `Engine.answer`: eligibility, relevance, duplicate record removal, conflict detection, citation construction and one generation attempt.
- `policy_fact`: interpret only known declarative policy forms; the injection example cannot become a fact.
- `generate_once`: enforce a generation deadline and reject unsupported output. Citations never come from the model.
- `extract_fields`: return supported values or null, with evidence and missing/ambiguity reasons.
- `Engine.batch`: preserve manifest order and all items, including duplicates and individual failures.

Predict these before running them:

1. Change `as_of` from 2026-05-31 to 2026-06-01: Atlas certification changes from INR 40000 to INR 25000.
2. Use `atlas-contractor-01`: certification is INR 10000; employee-only home-office records are ineligible.
3. Make both Atlas home-office amounts equal: CONFLICT becomes ANSWERED with both eligible citations.
4. Add an approved simultaneous certification limit with a different amount: CONFLICT, regardless of corpus ordering.
5. Add an unknown policy sentence form: the application does not guess its meaning; extend `policy_fact` with a test.
6. Upload a corrupt PDF followed by valid TXT: the PDF fails; TXT still completes.
7. Repeat a file byte-for-byte: preserve both results and set the later result's `duplicate_of` to the earliest ID.

Practice changing a policy amount in the data, running the tests and explaining why a policy ID should never be hardcoded in logic. Read the tests yourself; knowing the expected sample output is insufficient for the technical follow-up.
