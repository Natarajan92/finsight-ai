# Phase 1 local review checkpoint

Status: implementation verification completed; independent whole-branch review pending.

## Scope

Branch `feat/phase-1-ingestion`, from merged `main` at `310c3146af9b7dcded5e85dbcd91a149324cb871`.
Source manifests, page/block provenance and cache, evaluation-private benchmark
preparation, frozen IDs, synthetic/local-source tests, and documentation only.
No Phase 1 push/PR, merge, deployment, embedding, model call, or Phase 2 work.

## Review evidence

- Unit tests: 133 passed, one Windows symlink privilege skip, four local integration
  checks deselected by default. Explicit local integration: four passed.
- Ruff lint/format, lock check/sync, synthetic smoke, wheel/source build: passed.
- Separate runtime wheel environment: nine compatible distributions, 19 contract
  schemas, extractor `phase1-v2`, smoke and both CLI entry points checked from an
  empty cwd with isolated Python import mode.
- 53 canonical filings, 9,504 cached pages, 52 selected questions, frozen 36/16
  split. All 55 original selected PDFs and both JSONL hashes unchanged.
- Source fingerprint: `7376d03d8183077b92ed98b8c4e3a584fefd02202b75feba82cdc13b2519fad3`.
- Split fingerprint: `e6ec481633654b779721f1d94c7aa05a65e43c9f37deae177819658d2b665431`.
- Development quote diagnostics: 17/41 normalized exact matches. No holdout
  generation/retrieval or new holdout quote feedback.
- Phase 1 Windows/Ubuntu Actions results are unexecuted until push approval.

## Decisions and limitations

PyMuPDF 1.28.2 was explicitly approved. Shared contracts remain Pydantic/stdlib;
runtime imports do not load evaluation. Source-only cache loading supports offline
audit without annotation-guided extraction. Corpus selection, original text,
zero-based page indices, and seed 42 are preserved.

Nine scanned Amcor appendix pages are text-coverage gaps requiring a future OCR
decision. Nine other text-empty pages are blank. No parser error or block-mapping
failure occurred; that does not establish complete table semantics. Six development
financial pages were visually reviewed, and the full audit discloses flattened
column relationships and small-sample/shared-filing limitations.

## Independent findings

Pending the required fresh-context review. Findings, severity decisions, any
RED-to-GREEN corrections, and deferred minor items will be recorded here before
the final human checkpoint.

See [data audit](../data_audit.md), [ADR 0002](../decisions/0002-dataset-provenance.md),
and [P1-004](../engineering-journal/phase-01.md#p1-004---approved-phase-1-implementation).
