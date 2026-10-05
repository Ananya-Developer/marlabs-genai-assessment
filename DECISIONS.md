# Decision note

The consequential choice is evidence-first deterministic retrieval and generation. Metadata eligibility is checked before any policy text reaches generation. A conservative fact grammar then establishes relevance; conflicting simultaneous facts produce CONFLICT without inventing precedence. The offline model sees only selected eligible facts. Its output must exactly match a supported answer or processing fails. Citations are assembled by the application from original records, never trusted from model output.

I rejected asking a general-purpose model to choose policies from the full corpus and return its own citations. That would make access control and correctness depend on following prose instructions, especially with the supplied injection passage. I also rejected embeddings, a database and a frontend: the 12-record local exercise does not need that infrastructure.

Main limitation: conservative language support. Five benefit categories and a few policy sentence forms are supported. An unfamiliar policy wording may yield insufficient evidence even when a human could interpret it. Currency codes accompanying numeric amounts are accepted, but spelled-out amounts, currency symbols and date/receipt semantics are not inferred. The whole question must resolve to one benefit. PDF parsing runs in-process; a hostile PDF could consume resources, and the timeout thread cannot kill an arbitrary stuck provider. The shipped offline double terminates promptly. Production would need killable isolated workers and real provider cancellation.

No live model is integrated; that is optional. No production authentication, approval integration or OCR is built; those are out of scope. All supplied sample cases are implemented. GitHub publication and recruitment email submission remain candidate-owned tasks.

AI assistance: Codex generated the implementation, tests, synthetic files, documentation and demonstration. The candidate must review, understand and verify all of it. Do not claim unaided authorship. The assessment explicitly requires an explanation and prediction without AI assistance during follow-up.

Time spent: this generated implementation was prepared in this chat on 2026-10-05. Candidate's own total time has not been supplied and cannot be truthfully invented. Before submitting, replace this paragraph with the actual total time (including review and independent testing) and update unfinished work accurately.
