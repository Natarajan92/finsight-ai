# Engineering journal conventions

Use the [iteration template](../templates/engineering-iteration.md) for material
human prompts, engineering decisions, failures, reviews and verification.
The [prompt registry](../prompt-registry.csv) indexes entries; [Phase 0](phase-00.md)
contains the initial planning session and implementation approval.

[Phase 1](phase-01.md) records the post-merge plan, company-stratified split
requirements, the plan-file review request, and subsequent implementation approval/evidence.

[Phase 2](phase-02.md) records provider access, the shared testing budget,
framework-led architecture review, written-spec approval, and implementation-plan
preparation/review status.

[AMD application](amd-application.md) records the authorized single-filing RAG
delivery, Streamlit interface, live answer, free replay, review fixes and checks.

- Stable IDs: P0-001, P0-002, then P1-001, etc. Record timezone and branch/base SHA.
- Capture verbatim material prompts or label excerpts. Separate human words,
  assistant proposals and observed evidence. Record unavailable times as unavailable.
- Human reasoning/review stays pending or not supplied unless actually received.
- Record exact commands, outcomes, counts, failed attempts and fixes as they happen.
- Associate entries with commits through Git history; a commit cannot contain its
  own final hash. A journal entry's containing commit is its implementation link.
- Keep credentials, private documents, benchmark gold and raw chat exports out of
  Git. Sanitized aggregate counts/hashes are acceptable; no automatic capture claim.
- Preserve unsuccessful attempts in the bug log. Evaluation results require source,
  split and configuration fingerprints; missing metrics are unknown, not zero.
- Update documentation before each phase commit and request review afterward.
