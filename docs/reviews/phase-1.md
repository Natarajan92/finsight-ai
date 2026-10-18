# Phase 1 local review checkpoint

Status: one independent whole-branch review completed; three Important findings
corrected and verified in one correction pass. Final human result review pending.

## Scope

Branch `feat/phase-1-ingestion`, from merged `main` at `310c3146af9b7dcded5e85dbcd91a149324cb871`.
Source manifests, page/block provenance and cache, evaluation-private benchmark
preparation, frozen IDs, synthetic/local-source tests, and documentation only.
No Phase 1 push/PR, merge, deployment, embedding, model call, or Phase 2 work.

## Review evidence

- Unit tests: 142 passed, one Windows symlink privilege skip, four local integration
  checks deselected by default. Explicit local integration: four passed.
- Ruff lint/format, lock check/sync, synthetic smoke, wheel/source build: passed.
- Separate runtime wheel environment: nine compatible distributions, 19 contract
  schemas, extractor `phase1-v3`, nine approved encrypted-source hashes, smoke and
  both CLI entry points checked from an
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

P1-006 explicitly approves nine hash-verified owner-encrypted originals with no
password required and copy permission. Manifest diagnostics identify all nine,
and their 1,607 page records disclose encryption. Password-required, unknown
encrypted, repaired, syntax-error, or unknown-warning sources fail. An additional
618 pages have visible ActualText-position warnings: available text is preserved,
but may omit/misposition text. All 9,504 raw texts match v1 fingerprints.

## Independent findings

Fresh-context review covered base `310c3146af9b7dcded5e85dbcd91a149324cb871` through
`68ca6dab9d8fe55e86af236d4d8e9fc3f8955d91`. The reviewer modified no tracked files,
originals, index, or branch state and independently reproduced the findings with
synthetic inputs. No Critical findings; Important severity upheld for all three:

1. Silent MuPDF repairs/native syntax warnings accepted as success. Fixed with
   explicit repair/warning checks; failed extraction cannot be cached. Broadly
   rejecting every warning first caused 618 real-data failures; investigation
   narrowed one recognized ActualText quality warning to an explicit diagnostic.
2. `needs_pass` missed owner-encrypted sources with empty user passwords. Fixed
   metadata detection plus P1-006 exact-hash/copy-permission policy and diagnostics.
3. Internally consistent hashes allowed altered development membership. Fixed
   deterministic policy replay before cache/annotation feedback; no frozen IDs change.

RED: focused regressions returned eight failures/three passes. GREEN: eleven
passes. Additional generated ActualText regression failed before classification;
expanded focused suite then passed all twelve. Final full unit and local-source
integration gates pass as recorded above. No second independent review is claimed.

**Minor (deferred):** unmatched nonalias PDFs are omitted without a diagnostic.
Metadata-controlled membership stays in scope; do not automatically add sources.

The reviewer did not certify OCR/table semantics, future RAG/four-arm quality,
holdout quality, remote CI, legal suitability, or general-purpose allocation and
concurrent-writer scalability. Agent rulings and their costs are preserved in
[P1-005](../engineering-journal/phase-01.md#p1-005---independent-branch-review).

See [data audit](../data_audit.md), [ADR 0002](../decisions/0002-dataset-provenance.md),
and [P1-004](../engineering-journal/phase-01.md#p1-004---approved-phase-1-implementation).
