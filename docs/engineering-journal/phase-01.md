# Phase 1 engineering journal

This journal records Phase 1 planning and implementation. Entries distinguish
historical planning evidence from subsequent approved work.

## P1-001 - Planning after the Phase 0 merge

- **Date/time + timezone:** 2026-10-18 IST; original message time unavailable. Recorded on 2026-10-18.
- **Phase / branch / starting SHA:** Phase 1 / `feat/phase-1-ingestion` / `310c3146af9b7dcded5e85dbcd91a149324cb871`.
- **Actor/tool/category:** Human to Codex / planning.
- **Goal:** Plan dataset/provenance work from merged Phase 0 without starting implementation.

### Original prompt

> Merged, now we are good to move further with the planning for phase 1. GO in planning mode.

### Context, proposal, and human review

- The human confirmed Phase 0 was merged. The local Phase 1 branch was created from updated `main`, not an unmerged feature branch.
- Codex inspected existing contracts, source schema/counts, extraction options, and dependency/documentation availability. Proposed work is limited to manifests, extraction/cache, benchmark preparation, frozen IDs, and audit documentation.
- Read-only planning confirmed 53 canonical PDFs, 9,504 pages, and 52 selected questions. No embeddings, provider calls, or Phase 1 evaluation ran.
- The twelve-page layout probe and Windows dependency resolution were preliminary diagnostics, not full-corpus extraction or a successful project parser installation.
- **Human review:** Overall Phase 1 implementation pending. Split decision is recorded separately below. No reasoning beyond the human's supplied instructions is inferred.

### Evidence and remaining risk

- Local branch was clean at the start of the plan-file request (`git status --short --branch`).
- Base includes the Phase 0 code and CI fixes; a later Phase 0 evidence-only commit was not included in the human's merge. Reconcile factual documentation during approved Phase 1 work.
- No Phase 1 commit, push, PR, merge, or implementation verification has occurred.

## P1-002 - Company-stratified split decision

- **Date/time + timezone:** 2026-10-18 IST; original message time unavailable.
- **Actor/tool/category:** Human to Codex / decision and planning constraints.
- **Goal:** Select the split and protect evaluation integrity.

### Original prompt

> Choose Option 1: Company-stratified split (36 development / 16 holdout).
> Freeze the split with a fixed random seed and persist the 52 question IDs in separate development and holdout manifests.
> Requirements:
> 1. Ensure all six companies are represented in both splits.
> 2. Stratify by company and, where feasible, question reasoning type.
> 3. Use the original PDFs as the only RAG knowledge corpus.
> 4. Use FinanceBench JSON for benchmark questions, split construction, gold answers and offline evaluation only.
> 5. Never expose reference answers, gold evidence passages, page annotations or justifications to the RAG retriever or generation prompt.
> 6. Tune retrieval parameters and prompts only on the development set.
> 7. Evaluate the holdout once after configurations are frozen.
> 8. Run all four RAG configurations on identical question sets.
> 9. Record in the evaluation report that the same filings may appear in both splits; this evaluates unseen questions, not unseen documents.
> 10. Confirm each company's question count permits both splits, and report the final split distribution.
> Do not generate embeddings from FinanceBench question-answer JSON. Embed only extracted financial-document content.

### Agent proposal and diagnostics

- Proposed seed: 42. Proposed allocation: AMD 5/3, American Express 5/2, PepsiCo 8/3, Boeing 6/2, Amcor 6/3, Johnson & Johnson 6/3 (development/holdout).
- Read-only standard-library diagnostics constructed candidate allocations in memory and verified exact 36/16 counts, disjoint/exhaustive string IDs, and all companies in both splits. No IDs were persisted.
- The initial hierarchical allocation put all 13 repeated company/reasoning strata in both splits but left some globally repeated compound labels out of holdout. A second constrained allocation verified all seven globally repeated labels can appear in both, while retaining 12/13 repeated company/reasoning strata in both. The plan uses this latter policy.
- Twenty-two reasoning labels are missing; three raw categories are singletons. Preserve the source labels and disclose limits instead of assigning guessed labels.
- Dataset SHA-256 observed: `a5a2aa673e573e55675fc3c0f9aa38c1cf59d2abc91edb077534f71f10a71877`.
- **Human review:** Company-stratified choice and listed integrity requirements received. Seed/algorithm details and overall implementation remain proposed for plan review.
- **Verification limitation:** These were planning calculations, not executed project split tests, frozen manifests, or holdout model measurements.

## P1-003 - Save the plan for human review

- **Date/time + timezone:** 2026-10-18 IST; file preparation began after clock observation 14:21:01 IST (08:51:01 UTC). Exact prompt time unavailable.
- **Actor/tool/category:** Human to Codex / documentation and planning review.
- **Goal:** Make the Phase 1 implementation plan reviewable as a repository file.

### Original prompt

> show me plan 1 file i will review it

### Proposal and documentation changes

- Created [the Phase 1 plan](../superpowers/plans/2026-10-18-phase-1-ingestion.md), this planning journal, and prompt-registry entries; linked Phase 1 from the journal index.
- The plan names proposed files/interfaces, test cycles, source/hash checks, split policy, isolation boundaries, commands, risks, and approval gates. Tasks remain unchecked.
- Added a parser licensing decision after checking the [official PyMuPDF notice](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright): AGPL/commercial terms require a considered choice for the currently MIT-licensed repository. No dependency or license was changed.
- Superpowers used: `using-superpowers`, `brainstorming`, and `writing-plans` during this planning workflow. Native implementation is recommended; execution has not begun.
- **Human review:** PENDING for the plan and parser choice. This request authorizes saving planning documentation, not Phase 1 code or publication.
- **Commit / PR:** None for Phase 1.

### Verification

Checked on 2026-10-18 at approximately 14:24 IST (clock observation 08:54:23 UTC).

| Command / check | Result | Evidence |
|---|---|---|
| `python -B -` with inline documentation integrity checks | PASSED | Four documentation files; eight local Markdown links; eleven unique CSV registry entries; three Phase 1 anchors; four pending task sections; limited secret-pattern and size checks. |
| `git -c safe.directory=E:/maai-projects/finsight-ai diff --check` | PASSED | Exit 0. Git noted normal LF-to-CRLF conversion for the journal index. |
| `git -c safe.directory=E:/maai-projects/finsight-ai status --short --branch` | PASSED | Phase 1 branch; two new documentation files and two modified documentation files only. |
| Application tests, parser installation, source extraction, and evaluation | NOT RUN | Documentation-only request; no Phase 1 implementation or test pass is claimed. |

Remaining step: human review of the plan and parser choice. No commit or push was
performed for this documentation request.

## P1-004 - Approved Phase 1 implementation

- **Date/time + timezone:** 2026-10-18 IST; exact prompt time unavailable.
- **Phase / branch / base:** Phase 1 / `feat/phase-1-ingestion` / `310c3146af9b7dcded5e85dbcd91a149324cb871`.
- **Actor/tool/category:** Human to Codex / implementation approval.

### Original prompt

> PyMUPDF is open source and we cn use it for our project. use official documentation covering 1.28.2
>
> I have reviewed the phase 1 plan and approving it. Please develop the code as per plan.

### Review and execution

- **Human review: REVIEWED.** Phase 1 plan and PyMuPDF use explicitly approved. Use official 1.28.2 documentation rather than the older ContextHub guide for implementation behavior.
- Native execution uses Superpowers executing-plans, TDD, verification-before-completion, and a fresh final code review. Existing feature branch/workspace preference retained.
- Baseline command: `uv run --locked pytest -m "not integration" --basetemp=.pytest-tmp -q` with writable temporary uv cache: **65 passed in 2.06s**.
- Keep original FinanceBench files immutable and benchmark labels evaluation-only. No Phase 2 implementation, paid calls, push, merge, or deployment is authorized.
- Third-party PyMuPDF license remains documented separately; the repository license is unchanged.
- Implementation evidence follows as tests and corpus checks actually run.

### Task 1 - Source manifest and dependency verification

- Installed pinned PyMuPDF 1.28.2 with `uv lock` then `uv sync --locked --group dev`; isolated environment reports Python 3.12.15 / PyMuPDF 1.28.2 / MuPDF 1.28.2.
- RED: `uv run --locked pytest tests/test_manifest.py tests/test_ingestion_contracts.py --basetemp=.pytest-tmp -q` failed with two expected missing-module errors before implementation.
- First implementation test run: 18 passed / 1 failed / 1 skipped. Diagnosis: the outside-conflict synthetic fixture used 2022 twice; corrected it to 2023/2022. Loader behavior was not changed to satisfy the faulty fixture.
- Ruff initially found long lines/import ordering; formatting and import corrections applied. `uv run --locked ruff format .` and `uv run --locked ruff check .` then passed.
- GREEN: `uv run --locked pytest -m "not integration" --basetemp=.pytest-tmp -q`: **84 passed, 1 skipped in 2.50s**. Skip: this Windows host cannot create the symlink used by the real-link escape test; direct traversal/absolute/Windows-drive tests pass.
- Fresh environment via `UV_PROJECT_ENVIRONMENT=.superpowers/sdd/2026-10-18-phase-1-ingestion/fresh-env` plus `uv sync --locked --group dev`: 16 distributions installed. Version probe and `finsight-smoke` passed; smoke cost remains `unknown`.
- Real read-only loader check: **53 canonical PDFs / 9,504 pages**, two excluded Amcor aliases, one outside-scope Foot Locker metadata conflict. Selected source snapshot saved only in ignored execution scratch.
- Canonical 53-source fingerprint: `7376d03d8183077b92ed98b8c4e3a584fefd02202b75feba82cdc13b2519fad3`. The original 55-PDF aggregate remains `7d8ca4d2d901038058ac345778ecb5898f20e04e6f5a0c97ffd344db41a776fe`; both JSONL hashes equal the planning baseline.
- Contracts remain Pydantic/standard-library only. The offline manifest loader accepts document-information fields, not benchmark question/answer fields. No raw source files were staged.
