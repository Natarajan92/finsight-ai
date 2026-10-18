# Phase 1 Dataset and Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` for native implementation, or `superpowers:subagent-driven-development` if the human explicitly selects delegated execution. Implement and verify one task at a time. No implementation is authorized by this planning document alone.

**Goal:** Produce a verified 53-filing source manifest, reproducible page extraction/cache, and frozen 36-development/16-holdout question manifests with benchmark annotations isolated from RAG inputs.

**Architecture:** Keep the modular Python monolith. `ingestion` consumes approved PDF provenance and PDF bytes; `evaluation` owns benchmark questions, annotations, split construction, and offline diagnostics. Shared runtime contracts depend only on Pydantic and the standard library.

**Tech stack:** Python 3.12.15, uv 0.12.23, existing pinned Pydantic v2/pytest/Ruff, and approved PyMuPDF 1.28.2. No embedding, vector-store, model-provider, OCR, or UI dependency in Phase 1.

**Spec:** [project.md](../../../project.md), [Phase 0 audit](../../phase-0-audit.md), and the human's split requirements recorded in [P1-002](../../engineering-journal/phase-01.md#p1-002---company-stratified-split-decision).

**Status:** APPROVED FOR LOCAL IMPLEMENTATION on 2026-10-18; see [P1-004](../../engineering-journal/phase-01.md#p1-004---approved-phase-1-implementation). The human explicitly approved PyMuPDF 1.28.2. Task completion and measurements are recorded separately; approval is not evidence of completed work.

**Workspace:** Existing checkout, branch `feat/phase-1-ingestion`, based on merged `main` at `310c3146af9b7dcded5e85dbcd91a149324cb871`. No Phase 1 push, PR, merge, or deployment is authorized.

## Global constraints

- Preserve every original FinanceBench PDF and JSONL byte-for-byte.
- Use all 53 approved canonical filings as the common retrieval corpus. Exclude the two duplicate Amcor aliases without deleting them.
- Embed only extracted financial-document content in later phases. Never embed FinanceBench question-answer JSON.
- Keep reference answers, gold evidence passages, evidence-page annotations, full-page annotations, and justifications outside the runtime index, prompts, answer cache, and app API.
- Use FinanceBench question/annotation JSON only for benchmark preparation, split construction, and offline evaluation. Document-information JSON may support the offline provenance join; its contents are not RAG knowledge text.
- Tune retrieval parameters, prompts, and any annotation-guided parser adjustments only on development questions.
- Evaluate holdout once, after all four configurations are frozen, in a later approved phase. Phase 1 does not execute a RAG evaluation.
- All four arms use identical question sets and the same 53-filing corpus. Primary retrieval must not filter using gold document/page annotations.
- Preserve source text and zero-based PDF page indices. Missing metadata remains explicit; do not infer periods or filing types from filenames.
- Unit/CI checks require no original PDFs, credentials, paid calls, model downloads, or application network access. Actual-source checks are opt-in and local.
- Retain the existing application-service protocol and later-phase package boundaries. No chunking, indexing, retrieval, generation, reranking, or UI implementation here.
- Record exact commands and actual outcomes. Missing cost/usage/latency remains unknown. Push and merge require separate explicit approval.

## Review focus

1. Ambiguous joins, conflicting metadata, or a source path escaping the PDF root must fail visibly; Task 1 owns these tests.
2. A damaged, encrypted, or unexpectedly changed PDF must not produce a successful manifest/extraction result; Tasks 1 and 2 own these tests.
3. Table columns, year/unit headings, negatives, Unicode, and block offsets must survive extraction or receive explicit diagnostics; Task 2 owns these tests.
4. Corrupt/stale caches and interrupted writes must never silently reuse wrong pages; Task 2 owns these tests.
5. Rare/missing reasoning labels, source-order changes, split rerolls, and annotation injection must not undermine reproducibility or isolation; Task 3 owns these tests.

## Observed baseline and proposed split

These counts were established during read-only planning. The approved allocation is now persisted in `configs/evaluation/`; execution evidence is in P1-004.

| Company | Canonical filings | Questions | Development | Holdout |
|---|---:|---:|---:|---:|
| AMD | 9 | 8 | 5 | 3 |
| American Express | 1 | 7 | 5 | 2 |
| PepsiCo | 13 | 11 | 8 | 3 |
| Boeing | 8 | 8 | 6 | 2 |
| Amcor | 9 | 9 | 6 | 3 |
| Johnson & Johnson | 13 | 9 | 6 | 3 |
| **Total** | **53** | **52** | **36** | **16** |

- The 53 canonical filings contain 9,504 pages; all required question-linked filings exist. There are 55 local selected-company PDFs including two byte-identical Amcor aliases.
- The 52 questions refer to 19 filings, with 59 evidence references across 49 distinct pages. Previous normalized exact-quote matches were 23/59: an extraction diagnostic, not an answer-quality score or proof that other annotations are wrong.
- Twenty-two questions have no reasoning label. Preserve them as missing; do not invent labels or split compound labels into guessed classes.
- Seven reasoning categories, including missing, have multiple questions and can appear in both splits. Three categories contain one question each and cannot appear in both.
- The in-memory allocation can cover all seven repeated categories in both splits while covering 12 of 13 repeated company/reasoning strata in both. Report the remaining imbalance explicitly.
- The full metadata JSONL has a conflicting duplicate Foot Locker record outside the approved companies. Detect/report it; fail on unresolved conflicts within the selected corpus.

### Deterministic split policy

1. Fix seed **42**, algorithm version **`company-reasoning-v1`**, and question JSONL SHA-256 **`a5a2aa673e573e55675fc3c0f9aa38c1cf59d2abc91edb077534f71f10a71877`**.
2. Allocate 16 holdout places by largest remainder from `company_count * 16 / 52`; break equal remainders by case-folded approved company display name. This yields the table above.
3. Preserve exact raw `question_reasoning` values, including `None` and malformed/compound labels. Constrain every globally repeated reasoning label to have at least one question in each split.
4. Subject to those constraints, maximize the number of repeated company/reasoning strata represented in both splits, then minimize the sum of squared deviations from each company's proportional reasoning allocation. Use exact rational arithmetic.
5. Resolve remaining allocation ties with SHA-256 over canonical JSON containing seed, company, and the ordered raw-label/count allocation. Select holdout IDs within each company/reasoning stratum by seeded SHA-256 order, with the original string ID as collision tie-breaker. Never use Python's process-randomized `hash()`.
6. A small standard-library dynamic program over per-company allocations is sufficient for this fixed dataset; no scikit-learn/scipy dependency. Fail clearly if requested constraints become infeasible on a changed dataset.
7. Persist **all 52 original string IDs**, sorted within separate `development.json` and `holdout.json` manifests. Each records membership, seed, algorithm version, dataset/source fingerprints, and a shared split fingerprint; no question text or gold fields.
8. Fingerprint canonical UTF-8 JSON with sorted object keys, compact separators, and `ensure_ascii=False`. Pin the algorithm and serialization in tests. Refuse to overwrite a different existing frozen split; a new dataset/split requires a separately reviewed version.

The report must state: **The same filings may appear in both splits. This evaluates unseen questions, not unseen documents.** All four arms use the same 36 development IDs and, after freezing, the same 16 holdout IDs.

## Task 1: Canonical source manifest and provenance

**Files:**
- Create `src/finsight/contracts/ingestion.py` for `CorpusManifest` and `ExtractionConfig`.
- Create `src/finsight/ingestion/fingerprints.py`, `manifest.py`, and the PDF inspection boundary in `pdf.py`.
- Modify `pyproject.toml` and `uv.lock` for the approved parser dependency.
- Modify `src/finsight/contracts/__init__.py` only to export runtime ingestion contracts.
- Create `tests/test_manifest.py` and `tests/test_ingestion_contracts.py`.
- Later generate `data/manifests/financebench-selected.json`; it contains provenance, not extracted text or annotations.

**Interfaces:**
- `build_manifest(metadata_path: Path, pdf_root: Path, companies: tuple[str, ...], ingestion_version: str) -> CorpusManifest`.
- `inspect_pdf(pdf_path: Path) -> int` verifies that a PDF opens without encryption and returns its positive page count; source hashing remains in the manifest builder.
- `CorpusManifest`: schema version, ordered `DocumentManifest` entries, metadata-file hash, source fingerprint, and typed audit diagnostics for aliases/out-of-scope conflicts.
- `ExtractionConfig`: schema/extractor version, original-order extraction, and explicit text flags; its canonical JSON produces the config fingerprint used by Task 2.
- The manifest builder is an offline preparation boundary. Runtime page extraction accepts a validated manifest and never reads benchmark question JSON.

- [x] Resolve the parser licensing decision before dependency installation. If approved, pin **PyMuPDF 1.28.2**, regenerate the lockfile, and verify a locked isolated installation; otherwise revise and approve the parser-specific parts of Tasks 1 and 2 before coding.
- [x] Write failing synthetic tests for exact metadata joins, nullable metadata, duplicate/conflicting records, alias handling, stable IDs/hashes, portable paths, and unreadable/encrypted PDFs.
- [x] Run `uv run --locked pytest tests/test_manifest.py tests/test_ingestion_contracts.py --basetemp=.pytest-tmp`; confirm failures arise from missing behavior.
- [x] Implement the smallest manifest loader. Match metadata `doc_name` to PDF stems, verify PDF SHA/page count, and map actual fields (`doc_period`, `doc_type`, `doc_link`) explicitly. Reject selected ambiguous/missing joins; report the outside-scope conflict.
- [x] Resolve candidate paths under the configured root and reject traversal/escaping links. Store relative POSIX paths. Derive `document_id` as `doc_` plus SHA-256 of canonical JSON `[doc_name, pdf_sha256]`; source fingerprint hashes sorted `[doc_name, pdf_sha256]` pairs for the 53 canonical documents.
- [x] Treat the two unmatched Amcor PDFs as excluded aliases only after hash equality to a unique metadata-matched filing. Do not silently collapse distinct canonical metadata records by hash.
- [x] Verify schema generation/round trips and reject incorrect supplied fingerprints, duplicate IDs/names, invalid hashes/counts, and escaping paths. Run focused tests and the existing contract suite.
- [x] Record results in the journal and make an explicit-allowlist local commit after all applicable pre-commit checks pass.

## Task 2: Page extraction, layout provenance, and cache

**Files:**
- Modify `pyproject.toml` for the ingestion CLI entry point; preserve the Task 1 parser pin.
- Modify `src/finsight/contracts/documents.py` to add `TextBlock` and backward-compatible `Page.text_blocks = ()`.
- Extend `src/finsight/ingestion/pdf.py`; create `cache.py`, `qa.py`, and `cli.py`.
- Create `tests/test_pdf_extraction.py`, `test_page_cache.py`, and synthetic PDF fixtures generated locally during tests.
- Update `tests/test_contracts.py` for the additive page/block contract.

**Interfaces:**
- `extract_pages(pdf_path: Path, document: DocumentManifest, config: ExtractionConfig) -> tuple[Page, ...]`.
- `extract_cached(pdf_root: Path, document: DocumentManifest, config: ExtractionConfig, cache_root: Path) -> tuple[Page, ...]`.
- `TextBlock`: original block index, finite ordered bounding box, exact block text, and a `SourceSpan` into the unchanged `Page.text`. Validate page identity, offsets, and exact substring agreement on the containing `Page`.
- `finsight-ingest manifest` builds the Task 1 manifest; `finsight-ingest extract` accepts only manifest/PDF/config/cache inputs, never benchmark questions or annotations.

- [x] Verify the Task 1 parser installation and record its exact PyMuPDF/MuPDF backend versions before defining cache keys.
- [x] Write failing tests using small generated financial PDFs: page zero, blank pages, multiple years, units, parentheses/minus signs, Unicode supported by the fixture font, multi-column text, and ordered source offsets.
- [x] Run `uv run --locked pytest tests/test_pdf_extraction.py tests/test_page_cache.py --basetemp=.pytest-tmp`; verify the expected failures.
- [x] Extract original-order text with explicit `TEXTFLAGS_TEXT`, `sort=False`; obtain text blocks using the same configuration. Preserve raw page text without whitespace, sign, or numeric normalization. Store only text blocks whose offsets can be proven against raw text; retain raw text and report layout-mapping failure rather than fabricating spans.
- [x] Preserve `ok`, `empty`, and `error` page outcomes and page indices. Fail the command on unreadable/encrypted sources, source hash/page-count changes, or extraction errors; do not silently drop pages. Blank pages receive explicit diagnostics.
- [x] Cache validated per-document pages under ignored `data/cache/pages/`, keyed by PDF SHA, extraction config, PyMuPDF/MuPDF versions, and cache schema. Validate identity, page completeness/order, and payload integrity before reuse; rebuild corrupt/stale caches from the verified PDF. Write via same-directory temporary file and atomic replacement.
- [x] Test cache hits without parser calls, each invalidation input, truncated/wrong-document cache data, interrupted writes, and block/source mismatches. Test that annotation changes cannot affect extraction/cache output.
- [x] Run focused tests, unchanged Phase 0 tests, schema checks, and synthetic CLI smoke. Record actual outcomes and commit only this verified scope.

## Task 3: Evaluation-only benchmark preparation and frozen IDs

**Files:**
- Create `src/finsight/evaluation/benchmark.py`, `splits.py`, `audit.py`, and `cli.py`.
- Create `configs/evaluation/split-policy.json`, `development.json`, and `holdout.json` during approved implementation.
- Create `tests/test_benchmark_loader.py`, `test_benchmark_splits.py`, and `test_annotation_isolation.py` with synthetic records.
- Modify `pyproject.toml` for `finsight-benchmark-audit`; clarify the local-PDF integration marker description if needed.

**Interfaces:**
- Evaluation-private `BenchmarkCase`, `BenchmarkEvidence`, `SplitPolicy`, and `SplitManifest` models remain under `evaluation`, never exported through runtime contracts.
- `load_benchmark(path: Path, corpus: CorpusManifest) -> tuple[BenchmarkCase, ...]` validates the actual schema and selects the approved companies; unknown IDs, conflicting duplicates, or unresolved selected references fail visibly.
- `freeze_splits(cases: tuple[BenchmarkCase, ...], policy: SplitPolicy, dataset_sha256: str, source_fingerprint: str) -> tuple[SplitManifest, SplitManifest]` produces development then holdout.
- `finsight-benchmark-audit split` creates the ID manifests; `finsight-benchmark-audit validate` checks joins/references and reports aggregates. Annotation-guided extraction diagnostics require `--split development`.

- [x] Write failing tests for string IDs, nullable fields, mixed reasoning labels, actual evidence `doc_name`/zero-based `evidence_page_num`, duplicate IDs, and missing filings.
- [x] Write split tests asserting **36/16**, the exact six-company table, disjoint/exhaustive IDs, all seven repeated reasoning categories in both splits, optimal feasible company/reasoning coverage, and input-order independence. Use synthetic data with the audited count/label pattern, not copied gold content.
- [x] Run the focused tests and verify expected failures; implement the policy above with deterministic canonical fingerprints and overwrite protection.
- [x] Add subprocess/import tests proving that contracts, ingestion, application, and smoke do not import evaluation. Runtime models and ingestion commands reject gold-answer/justification/annotated-evidence inputs. Altering synthetic annotations must not alter PDF-derived pages, blocks, or source fingerprints.
- [x] Keep full gold cases and detailed annotation diagnostics only in ignored `data/evaluation/`. Public manifests contain membership and reproducibility metadata only. Do not print holdout answers, evidence, or per-case extraction feedback for tuning.
- [x] Verify the real 52-ID split and structural reference checks locally after implementation. Freeze IDs before annotation-guided extraction review, which uses development cases only. Run no holdout answer/retrieval evaluation.
- [x] Record the selected policy separately from pending overall implementation review; commit the verified evaluator preparation and ID manifests.

## Task 4: Real-corpus acceptance, documentation, and checkpoint

**Files:**
- Create `tests/test_corpus_integration.py` (opt-in local-data checks).
- Create `docs/data_audit.md` and `docs/decisions/0002-dataset-provenance.md`.
- Update `README.md`, `docs/experiments.md`, `docs/engineering-journal/phase-01.md`, `docs/prompt-registry.csv`, and `docs/bug-log.md` when actual defects occur.
- Update CI only where required for new synthetic checks; retain pinned actions, Python 3.12.15, and Windows/Ubuntu coverage.

- [x] Add integration assertions for 53 canonical filings, 9,504 ordered page records, 52 questions, 19 question-linked filings, complete split membership, and valid zero-based evidence references. Run these only when local source paths are explicitly supplied.
- [x] Compare original JSONL and all 55 selected PDF hashes before and after ingestion. Label the original 55-file audit fingerprint separately from the new 53-file corpus fingerprint.
- [x] Review at least one development evidence page and one financial-table example per company. Verify years, row labels, units, negatives, headings, and PDF-page provenance against the original page. Record each observed mismatch and parser limitation; avoid claiming complete table reconstruction from a spot check.
- [x] Report per-company/filing-type/year counts, extraction successes/empty/error pages, layout/cache diagnostics, aliases/conflicts, split distributions, and previous/new diagnostic differences in `docs/data_audit.md`. A quote normalization match is not faithfulness or benchmark accuracy.
- [x] Document the holdout protocol: tune only on the 36 development IDs; freeze model/prompt/retrieval/chunking/reranking/context/corpus/index revisions before one final A/B/C/D holdout campaign on the same 16 IDs. Preserve identical pre-rank pools within paired rerank arms. Implement the runner only in its later phase.
- [x] Reconcile the existing Phase 0 journal/CI evidence with the successful published run, without pulling unrelated code or inventing PR authorization. The merged base contains the code/CI fix; one later Phase 0 evidence-only commit was not part of the merge.
- [x] Run the commands below; inspect all results, staged contents, secret patterns, ignored artifacts, and large files. Record exact failures/corrections and final outcomes before each commit. Source PDFs, annotations, caches, and private environment files must stay untracked.
- [x] Repeat locked installation and the synthetic smoke from a fresh temporary project environment; record interpreter/parser versions and wheel-build results. Keep its environment/cache outside committed artifacts.
- [x] Return the eight-part checkpoint required by `project.md`, with actual commit SHA, journal links, test counts, fingerprints, limitations, and next recommendation. Stop for human review; do not push or start Phase 2.

## Verification commands

Use a writable temporary uv cache and `UV_LINK_MODE=copy` where required. The current managed Python environment is authoritative; do not install into the conflicted global Python 3.10 environment.

```text
uv lock --check
uv sync --locked --group dev
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest -m "not integration" --basetemp=.pytest-tmp
uv run --locked finsight-smoke
uv build
```

Additional proposed local commands after the CLI/tests exist:

```text
uv run --locked finsight-ingest manifest --metadata source-data/data/financebench_document_information.jsonl --pdf-root source-data/pdfs --output data/manifests/financebench-selected.json
uv run --locked finsight-ingest extract --manifest data/manifests/financebench-selected.json --pdf-root source-data/pdfs --cache-root data/cache/pages
uv run --locked finsight-benchmark-audit split --questions source-data/data/financebench_open_source.jsonl --manifest data/manifests/financebench-selected.json --policy configs/evaluation/split-policy.json --output-dir configs/evaluation
uv run --locked finsight-benchmark-audit validate --questions source-data/data/financebench_open_source.jsonl --manifest data/manifests/financebench-selected.json --split-dir configs/evaluation --split development --cache-root data/cache/pages
uv run --locked pytest -m integration tests/test_corpus_integration.py --basetemp=.pytest-tmp
```

The integration test reads `FINSIGHT_SOURCE_PDF_DIR=source-data/pdfs` and `FINSIGHT_BENCHMARK_DIR=source-data/data`; it must explicitly skip with a reason when local inputs are absent. Standard CI runs synthetic tests only. CI for Phase 1 is unexecuted until an approved push actually triggers it.

The earlier Phase 0 checkpoint had 65 passing tests. Local Phase 1 verification reached 133 passing unit tests (one explicit Windows symlink skip; four integration checks deselected), four passing real-corpus checks, fresh installation/isolated wheel smoke, and full-corpus extraction/cache verification. Extractor `phase1-v2` explicitly flags nine scanned appendix pages as text-coverage gaps without OCR. Phase 1 remote CI is **not executed** until an approved push. Final independent review is the next gate; its findings and corrections will be recorded in the journal.

## Decisions, risks, and approval boundary

1. **Selected:** company-stratified 36/16, seed 42, reasoning balance where feasible, all six companies in both splits, original PDFs as the only RAG knowledge corpus, development-only tuning, once-only frozen holdout, and identical question sets across A/B/C/D.
2. **Resolved for this implementation by P1-004:** The human explicitly approved PyMuPDF 1.28.2. Its AGPL/commercial terms remain documented separately from this repository's MIT license; no license change or commercial purchase is authorized. See the [official license notice](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright).
3. **Extraction risk:** original PDF order can differ from visual reading order. Preserve text and block geometry; report financial-table problems. OCR, new parser backends, and structured table reconstruction require a scoped follow-up decision if they become blockers. See [official text extraction documentation](https://pymupdf.readthedocs.io/en/latest/app1.html).
4. **Small benchmark:** 52 questions and shared filings limit conclusions. Report missing/singleton reasoning labels and unseen-question scope. Never choose a seed by answer/retrieval performance.
5. **Preliminary documentation evidence:** ContextHub `pymupdf/package` material consulted during planning covered 1.27.2; official documentation covering 1.28.2 was checked for extraction behavior. Record both versions rather than calling the older guide current for every API.
6. **GitHub:** a local Phase 1 branch exists. The previous PR connector returned 403; public read access and git push worked for Phase 0, and the human merged PR #1. Reverify publication permissions only after Phase 1 push approval.
7. **Time box:** target 2-2.5 hours for approved implementation/verification, subject to corpus extraction findings. This is an estimate, not a passed quality gate or deadline guarantee.

**Approval and checkpoint:** The human approved this plan and PyMuPDF in P1-004. Native task-by-task local implementation proceeds through a final independent review. Phase 1 publication and later phases remain separate approval boundaries.
