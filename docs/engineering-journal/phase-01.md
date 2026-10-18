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

### Task 2 - Source extraction and validated cache

- Task 1 local commit: `4c69d41`; its 15-file staged allowlist passed limited secret-pattern, size, artifact, ignore, and whitespace checks. Lock check, formatting check, synthetic smoke, and focused task-done test passed (19 passed / 1 explicit Windows symlink skip).
- RED: extraction/cache tests failed on missing `TextBlock` and cache module. Implemented original-order PyMuPDF text/blocks, unchanged raw text, proven block spans, explicit empty/error pages, and atomic validated cache envelopes.
- Added read-only `load_cached(document, config, cache_root)` so offline audit can validate frozen pages without reading private envelopes or re-extracting based on annotations. Its added test failed on missing function before implementation, then passed.
- Cache tests cover hits without parser calls; changed source hashes; config/parser revisions; truncated, wrong-document, incomplete, modified-text, and old-schema cache data; interrupted atomic replacement. Synthetic table/text tests cover years, units, negatives, Latin Unicode, original multi-column order, and layout/extraction failures.
- Focused initial GREEN: 23 tests passed. Final `uv run --locked pytest -m "not integration" --basetemp=.pytest-tmp -q`: **108 passed, 1 skipped in 3.12s**. Ruff formatting/lint passed.
- `uv run --locked finsight-ingest manifest --metadata source-data/data/financebench_document_information.jsonl --pdf-root source-data/pdfs --output data/manifests/financebench-selected.json`: **53 documents**, expected aliases/conflict, unchanged 53-source fingerprint. This generated provenance artifact contains no benchmark questions or labels.
- No claim of full-corpus extraction or real table QA yet; those checks follow frozen-ID preparation.

### Task 3 - Offline benchmark preparation and frozen IDs

- Task 2 local commit: `ce330c1`; 12 staged files passed limited secret/artifact/size/ignore and whitespace checks. Lock, formatting, synthetic smoke, and focused task-done check passed (24 tests).
- Full source-only extraction command completed: **53 filings, 9,504 pages, 9,486 nonempty, 18 empty, 0 parser errors, 0 block-mapping failures**. This does not certify financial table semantics.
- RED: benchmark loader/split tests failed with two missing-module errors; audit tests separately failed on the missing audit module. GREEN focused suites: 21 tests and 3 tests respectively.
- Implemented actual-schema evaluation-private models, exact question/document/page joins, constrained seeded allocation, ID-only manifests, shared fingerprints, idempotent writes, and refusal to replace a different frozen pair.
- Runtime subprocess/import checks confirm no evaluation imports; source cache output is independent of changed synthetic gold annotations. Runtime request/page/CLI and metadata-loader tests reject annotation inputs.
- `uv run --locked pytest -m "not integration" --basetemp=.pytest-tmp -q`: **132 passed, 1 explicit Windows symlink skip in 6.99s**. Ruff lint/format checks passed after correcting one long diagnostic string.
- Real `finsight-benchmark-audit split` command: **36 development / 16 holdout**, all six companies represented. Shared split fingerprint: `e6ec481633654b779721f1d94c7aa05a65e43c9f37deae177819658d2b665431`.
- Real `finsight-benchmark-audit validate --split development` command: **52 questions / 19 question-linked filings / 59 structurally valid references / 49 distinct annotated pages**. Development-only normalized exact matching: **17/41**, with 24 nonmatches retained as mechanical diagnostics. No new holdout quote feedback or answer/retrieval evaluation is produced.
- Detailed development annotations/IDs/page diagnostics are written only to ignored `data/evaluation/`; public split artifacts contain original IDs and reproducibility metadata only.

### Task 4 - Real-source checks, visual review, and packaging

- Task 3 local commit: `c3eb7ac`; its 14-file allowlist passed limited staged secret/artifact/size/ignore checks, lock check, synthetic smoke, and focused task-done tests (24 passed in 4.26s).
- Added four opt-in local-source integration tests. Initial run passed 4/4 in 5.89s, verifying 53 source joins, all cached pages without parser calls, 52 cases and split reproduction, and original PDF/JSONL hashes.
- Visually inspected six development financial-table pages against original PyMuPDF renders, one per company. Raw headings, years, row labels, scales, parentheses, sampled amounts, and footnotes are preserved. Table relationships remain flattened text with bounding boxes; no structured-cell or global table correctness claim.
- Inspected all 18 text-empty page renders. Nine are blank; nine are scanned Amcor 2020 deferred-compensation appendix pages. None is an annotated evidence page. Added source-only image diagnostics, not OCR, under the approved scope; extraction coverage remains explicitly incomplete for those nine pages.
- Regression RED: `uv run --locked pytest tests/test_pdf_extraction.py::test_image_without_text_is_an_explicit_coverage_gap --basetemp=.pytest-tmp -q` failed on absent diagnostic. GREEN after minimal detection: 1 passed in 0.39s. Extractor version bumped to `phase1-v2` to invalidate stale envelopes.
- Full v2 extraction: **9,504 pages, 9,486 nonempty, 18 empty, 9 image-content-without-text diagnostics, 0 errors, 0 layout-mapping failures**. Per-document source-text checksums confirm all 9,504 raw page texts are identical between v1 and v2; only version/diagnostics changed.
- A suspected Unicode parser defect was ruled out: all cached pages contain zero U+FFFD characters. NBSP/em/en dashes/curly punctuation survive; Windows preview decoding was the issue (ENV-003). No speculative parser fix was made.
- Final implementation unit command: `uv run --locked pytest -m "not integration" --basetemp=.pytest-tmp -q`: **133 passed, 1 skipped, 4 deselected in 7.09s**. Skip is the unavailable Windows symlink privilege; integration checks are explicitly opt-in.
- Final v2 local command with `FINSIGHT_SOURCE_PDF_DIR=source-data/pdfs` and `FINSIGHT_BENCHMARK_DIR=source-data/data`: `uv run --locked pytest -m integration tests/test_corpus_integration.py --basetemp=.pytest-tmp -q`: **4 passed in 7.48s**, including all 59 references pointing to nonempty extracted pages, with no holdout quote/answer scoring.
- Before/after snapshot comparison passed for all 55 selected PDFs and both JSONL files. A separate v1/v2 text-fingerprint comparison passed across all 53 canonical filings.
- `uv lock --check`, `uv sync --locked --group dev`, both Ruff checks, and `uv build` passed. Wheel and source distribution built successfully.
- Installed the final wheel into a separate runtime-only environment (nine distributions). From an empty cwd with Python `-I`: all **19 exported contract schemas** generated, extractor is `phase1-v2`, synthetic smoke passed, and both installed CLI help commands passed. `uv pip check --python <wheel-env>/Scripts/python.exe`: all nine packages compatible.
- Development QA renders/selections and empty-page renders are retained only in ignored `data/evaluation/phase1-visual-qa/`; detailed development extraction diagnostics remain ignored. Public documentation contains sanitized aggregates and limitations.
- GitHub connector reverified historical Phase 0 run 39111532667: both Windows/Ubuntu jobs and all gates succeeded. Reconciled the unmerged evidence-only Phase 0 documentation in its journal; this is not a Phase 1 CI result.
- Phase 1 CI has not run; its workflow retains pinned actions/keyless Windows+Ubuntu checks and adds installed CLI help checks. No Phase 1 push, remote PR, merge, model call, embedding, or holdout RAG run has occurred.

## P1-005 - Independent branch review

- **Actor/category:** Fresh-context Codex review agent (`gpt-6-astra`, high reasoning) / code review under Superpowers executing-plans.
- **Range:** `310c3146af9b7dcded5e85dbcd91a149324cb871..68ca6dab9d8fe55e86af236d4d8e9fc3f8955d91`.
- **Critical:** None. **Important:** silent MuPDF repairs/native syntax warnings accepted as success; owner-encrypted empty-user-password PDFs not detected by `needs_pass`; validation accepted checksum-consistent swapped split IDs without recomputing the declared policy.
- Reviewer reproduced all three with generated PDFs/synthetic cases only and reran unit tests: 133 passed / 1 Windows symlink skip / 4 integrations deselected. No original data, tracked files, frozen IDs, Git index, or branch state was modified by the reviewer.
- **Minor deferred:** Unmatched nonalias PDFs are omitted without a diagnostic. Preserve metadata-controlled scope; a broader unmatched-source audit is a follow-up, not an automatic corpus expansion.
- Parent verification found nine actual approved originals with owner encryption, no password required, and copy/accessibility permissions granted. This conflicts with blanket encryption rejection; requested a concrete exception decision while the other fixes proceed.
- Review findings are engineering feedback, not human approval of implementation results. Corrections and final verification follow; no second independent review is claimed.

## P1-006 - Exact-source encryption exception approved

- **Date/time + timezone:** 2026-10-18 IST; exact message time unavailable.
- **Actor/category:** Human / scoped policy clarification.
- **Question context:** The approved plan rejects encrypted files, but American Express 2022 and Boeing 2015-2022 are owner-encrypted, open without a password, and permit copying. Proposed read-only processing of those exact hash-verified files with visible diagnostics; all password-required files still rejected.

### Original answer

> Allow these nine files with diagnostics (Recommended)

- **Human review: REVIEWED.** Limit the exception to these nine original SHA-256 values; do not decrypt/rewrite originals, attempt passwords, change permissions, or allow arbitrary encrypted uploads.
- Record encryption in manifest/page diagnostics and require copy permission. Unknown encrypted files or any file requiring a password remain failures. The canonical source identities and frozen question memberships must remain unchanged.

### P1-005/P1-006 corrective implementation and verification

- **Correction context:** one pass after review of `68ca6da`, on the existing
  `feat/phase-1-ingestion` branch. No second independent review is claimed.
  All three Important severities stand: wrong source acceptance or incorrect
  development membership would violate the approved ingestion/evaluation boundary.
- **RED:** `uv run --locked pytest tests/test_pdf_integrity.py tests/test_benchmark_audit.py tests/test_benchmark_splits.py::test_synthetic_policy_fingerprint_is_pinned_across_platforms --basetemp=.pytest-tmp -q`
  returned **8 failed, 3 passed in 2.25s**. Repaired xref and syntax-warning pages
  were accepted/cached; unknown/readable encryption bypassed policy and diagnostics;
  a checksum-consistent within-stratum swap was accepted by direct audit and CLI.
- **Fix:** reject repair/open warnings, detect encryption using metadata, enforce
  the exact nine-source SHA-256 allowlist and copy permission, and disclose the
  approved exception. Recompute the fixed split policy before accessing development
  page annotations/caches. Never persist failed extraction; keep prior diagnostics
  unchanged when membership validation fails. Synthetic cross-platform split hash
  is pinned; real IDs/algorithm stay unchanged.
- **First GREEN:** same focused command returned **11 passed in 2.24s**. Whole
  unit suite reached 141 passed / 1 Windows symlink skip / 4 integrations deselected.
  Ruff initially reported two style errors (line length/import order); both were
  corrected and subsequent lint/format checks pass.
- **Failed broad-warning hypothesis:** strict rejection of every native page warning
  made full extraction return **618 errors**, CLI exit 1; failed documents were not
  cached. Source-only probes (no benchmark labels) showed the exact warning
  `ActualText with no position. Text may be lost or mispositioned.` across nine
  filings. This is text-quality uncertainty and must be visible, not silently lost
  or misrepresented as a syntax error. No extraction flags/text were changed.
- **Additional RED:** `uv run --locked pytest tests/test_pdf_integrity.py::test_actualtext_position_warning_preserves_available_text_with_visible_gap --basetemp=.pytest-tmp -q`
  returned **1 failed in 0.65s** on a generated marked-content PDF. The narrow
  classification preserves available text and records `actualtext_position_warning`;
  all syntax/unknown warnings still fail. The focused correction command then
  returned **12 passed in 2.12s**. See BUG-005 through BUG-007 and ADR 0002.
- **P1-006 manifest migration:** rebuilt into a candidate, asserted all 53
  `DocumentManifest` entries, metadata/source hashes, and previous alias/conflict
  diagnostics equal the existing artifact, then added nine approved-encryption
  diagnostics only. No general overwrite/force option was added.
- **Full v3 extraction command:**
  `uv run --locked finsight-ingest extract --manifest data/manifests/financebench-selected.json --pdf-root source-data/pdfs --cache-root data/cache/pages`
  returned **9,504 pages; 9,486 nonempty; 18 empty; 0 fatal errors; 0 layout failures;
  9 image-only diagnostics; 618 ActualText-position diagnostics; 1,607 readable
  encrypted-page diagnostics**. Process-global warnings are handled serially.
- Warning distribution by filing: Amcor 2019 73; American Express 2022 1;
  Johnson & Johnson 2015 98, 2016 100, 2017 105, 2018 115, 2019 123, 2022 2;
  PepsiCo 2022 1. This is corpus-wide source QA, not holdout performance feedback.
- Per-document canonical text fingerprints assert that **all 9,504 raw page texts
  remain identical to v1**. The exact source/split fingerprints in the data audit
  remain unchanged. Explicit integration verifies the 55 originals and both JSONL
  hashes, all cached pages without reparsing, and split replay.
- **Final unit command:** `uv run --locked pytest -m "not integration" --basetemp=.pytest-tmp -q`
  returned **142 passed, 1 skipped, 4 deselected in 7.48s**. The sole skip is host
  symlink privilege, explicitly reported. No paid/network tests were substituted.
- **Final local integration:** set `FINSIGHT_SOURCE_PDF_DIR=source-data/pdfs` and
  `FINSIGHT_BENCHMARK_DIR=source-data/data`, then
  `uv run --locked pytest -m integration tests/test_corpus_integration.py --basetemp=.pytest-tmp -q`:
  **4 passed in 5.74s**.
- **Development audit:** the documented `finsight-benchmark-audit validate` command
  passed with **17/41** normalized exact quote matches. No new holdout quote feedback,
  retrieval/generation evaluation, embeddings, provider/model calls, cost or latency
  measurements. Unknown economics remain unknown.
- **Environment/build:** `uv lock --check`, `uv sync --locked --group dev`,
  `uv run --locked ruff check .`, `uv run --locked ruff format --check .`,
  `uv run --locked finsight-smoke`, and `uv build` passed. Smoke output remains
  `synthetic_contract_roundtrip`, status `passed`, page zero, cost `unknown`.
- Reinstalled the built wheel into the separate runtime-only environment using
  `uv pip install --python <wheel-env>/Scripts/python.exe --reinstall-package finsight-ai dist/finsight_ai-0.1.0-py3-none-any.whl`.
  `uv pip check --python <wheel-env>/Scripts/python.exe` found **9 compatible
  distributions**. From an empty cwd, isolated Python `-I` imported site-packages,
  generated **19 schemas**, checked parser versions **1.28.2**, extractor **v3**,
  nine allowlisted hashes, runtime/evaluation import isolation, synthetic smoke,
  and both CLI help entry points successfully.
- **Human implementation-result review: PENDING.** P1-004/P1-006 approve the design
  and scoped exception, not a completed-code review. No Phase 1 publication,
  merge, deployment, Phase 2 implementation, or remote CI run was authorized.

### Execution rulings and review scope

The following preserves the execution ledger before its plan-specific scratch
workspace is removed. These are agent rulings, not invented human reasoning.

1. Use the human-approved PyMuPDF 1.28.2; retain repository MIT and document
   third-party terms separately. Cost if wrong: reassess terms for a different use
   or distribution; no purchase/relicensing is authorized.
2. Expose source-only `load_cached` for read-only offline QA instead of parsing
   private envelopes or re-extracting based on annotations. Cost if wrong: wider API
   maintenance.
3. Flag image-only pages and version caches; defer OCR. Cost if wrong: nine scanned
   pages remain unavailable to text retrieval.
4. Preserve the exact ActualText-position warning as visible quality uncertainty;
   reject syntax/unknown warnings. Cost if wrong: affected text may be incomplete
   or misplaced; 618 pages require that limitation to remain visible.
5. Reviewer did not certify OCR/table-cell semantics. Keep those follow-ups outside
   Phase 1 rather than infer coverage from spot checks. Cost: incomplete text/table
   relationships remain.
6. Reviewer did not judge later RAG or four-arm quality. Keep implementation within
   Phase 1. Cost: retrieval/answer performance remains unmeasured.
7. Reviewer did not judge holdout quality. Preserve development-only feedback and
   the once-only later holdout gate. Cost: holdout quality remains unknown now.
8. Reviewer did not run remote CI. Report local Windows evidence only until an
   approved push. Cost: remote Windows/Linux compatibility remains unverified.
9. Reviewer did not provide legal judgment. Human dependency approval is recorded
   without calling it a legal finding. Cost: different distribution/use may require
   separate license review.
10. Reviewer did not judge general-purpose allocation scalability/concurrent writers.
    Keep the fixed 52-case, serial local scope. Cost: larger/parallel workloads need
    separate engineering.

**Minor (deferred):** unmatched nonalias PDFs lack an explicit diagnostic. Metadata
continues to control membership; report rather than automatically expand corpus.
The final corrective commit contains these records and corresponding regressions;
the final checkpoint supplies its exact SHA.

### Final local commit gates

- Repeated real `manifest` and `split` commands passed idempotently: 53 sources,
  nine approved encryption diagnostics, expected aliases/conflict, identical
  source and 36/16 split fingerprints. No general overwrite option exists.
- Checked **30 local documentation link targets**, **14 unique prompt-registry
  rows**, and all **four public JSON artifacts** for forbidden gold/annotation
  fields. Built wheel/source artifacts contain the packaged source policy and
  exclude PDFs, JSONL, renders, bytecode, private environment and source-data.
- `git diff --check` and `git diff --cached --check` passed. Diff against merged
  base confirms later-phase package boundaries unchanged.
- Explicitly staged **20 allowlisted correction/documentation files**. The limited
  staged secret-pattern, sub-1-MB file-size, source/generated-artifact, and ignored
  path scan passed for all 20. Raw PDFs/JSONL, caches, local QA, `.env`, environments,
  build output and plan scratch remain ignored/untracked. This is a targeted scan,
  not a claim that every possible secret format has been detected.
- Staged correction before this gate-record addition: 698 insertions / 38 deletions;
  native PDF policy, split replay, nine added unit regressions, diagnostics, and
  documentation only. The local corrective commit includes the final gate record.
- Plan scratch is disposable only after this correction is committed; retain local
  source caches and ignored QA evidence, and leave sibling plan workspaces alone.

## P1-007 - Phase 1 publication authorized

- **Recorded:** 2026-10-18 15:40:43 IST (10:10:43 UTC clock); exact human message
  time unavailable. Actor: human; category: publication/workflow.
- **Exact human prompt:** "push the code for phase 1".
- **Context:** local implementation `500cd4622ec2d5e109c8bea36806fae9547245ad`,
  clean `feat/phase-1-ingestion`; original five implementation commits are local.
- **Authorization:** push only this Phase 1 branch and open its review PR under
  `project.md`. No merge, deployment, force push, branch deletion, or Phase 2 work.
  This message authorizes publication; no independent human technical diagnosis or
  explicit final implementation-review rationale was supplied.
- Reverified `origin` as `https://github.com/Natarajan92/finsight-ai.git`;
  `gh repo view` reports ADMIN permission and default branch `main`. `gh pr list`
  found no existing Phase 1 PR; `git ls-remote --heads origin main feat/phase-1-ingestion`
  confirms remote main remains `310c3146af9b7dcded5e85dbcd91a149324cb871` and no
  remote Phase 1 branch exists before publication.
- **Fresh pre-publication gates:** `uv lock --check`,
  `uv sync --locked --group dev`, `uv run --locked ruff check .`,
  `uv run --locked ruff format --check .`, `uv run --locked finsight-smoke`,
  and `uv build` passed. Synthetic smoke: status passed, page index zero,
  cost unknown. Wheel/source distribution built successfully.
- `uv run --locked pytest -m "not integration" --basetemp=.pytest-tmp -q`:
  **142 passed, 1 Windows symlink-privilege skip, 4 integration deselections
  in 7.89s**.
- With the documented explicit local source paths,
  `uv run --locked pytest -m integration tests/test_corpus_integration.py --basetemp=.pytest-tmp -q`:
  **4 passed in 6.20s**; source hashes, complete caches, and split replay verified.
- Add this publication record and prompt-registry row as one documentation-only
  local commit; then inspect the outgoing tree/history, ignored artifacts, limited
  secret patterns, file sizes, and exact refspec before pushing. No runtime code,
  source data, frozen IDs, or extraction configuration changes in this iteration.
- At preparation time the push, PR, and remote CI are **pending**, not claimed
  successful. The final user response will report verified remote commit/PR/CI
  evidence. Keep the feature branch and workspace for human review afterward.
- Pre-commit outgoing scan passed for **45 changed/current Phase 1 files** and
  outgoing Git objects: limited secret patterns, sub-1-MB sizes, forbidden raw/
  generated suffixes, ignored source/cache/evaluation/private paths, and 15 unique
  prompt rows. `git diff --check` passed; only the two journal/registry files change.
