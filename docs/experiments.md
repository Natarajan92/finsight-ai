# Experiment record conventions

The Phase 1 split is frozen. Phase 2 implementation is verified; its guarded
full-corpus index stopped on an uncertain provider timeout. Acceptance is blocked;
actual status is recorded below and in the
linked result summary. No aggregate accuracy or faithfulness is established.
The synthetic smoke reports provider cost as unknown.

Future approved experiments must compare A fixed/no-rerank, B semantic/no-rerank,
C fixed/rerank, D semantic/rerank. Freeze corpus, embedding model/revision/dimension,
question IDs, prompts, generation model, explicit filters, candidate count and
context budget. Paired rerank arms reuse the identical pre-rank candidate pool.

Record source/dataset/split/config fingerprints, dev/holdout IDs, seeds,
configuration, software/model revisions, retrieval order and typed scores,
per-case and aggregate metrics, timing, tokens/calls/cost (unknown if unavailable),
failures and qualitative review. Never tune on holdout or silently scope retrieval
with gold doc names. Gold annotations stay in the offline evaluator and ignored
artifacts. Track page-hit proxies separately from semantic citation support.

Version only sanitized summaries under `results/`; raw traces/caches stay ignored.
Provider smoke tests require separate credential/spend approval. Targets in
`project.md` remain targets, not achieved performance.

## Phase 1 frozen benchmark inputs

- Seed 42; algorithm `company-reasoning-v1`; 36 development / 16 holdout, all six
  companies represented in both. Manifests are in `configs/evaluation/`.
- Shared split fingerprint: `e6ec481633654b779721f1d94c7aa05a65e43c9f37deae177819658d2b665431`.
- Full 53-filing corpus fingerprint: `7376d03d8183077b92ed98b8c4e3a584fefd02202b75feba82cdc13b2519fad3`.
- PyMuPDF/MuPDF 1.28.2, extractor `phase1-v3`, original-order text/blocks. Nine
  scanned appendix pages have explicit image-only coverage gaps; no OCR is run.
- P1-006 permits nine exact readable owner-encrypted source hashes with copying
  permission and diagnostics. Strict repair/native-warning checks invalidate old
  caches; neither source identities nor frozen question IDs change.
- 618 pages have explicit ActualText-position uncertainty; available raw text is
  retained unchanged. These diagnostics do not establish complete extraction.
- Development annotation check: 17/41 normalized exact quote matches. This is an
  extraction diagnostic, not retrieval correctness, faithfulness, or an experiment arm.
- Eight question-linked filings appear in both splits. This evaluates unseen
  questions, not unseen documents. All 53 filings remain the common retrieval corpus.
- Freeze all four configurations and prompts using development only, then evaluate
  holdout once on the same 16 IDs. No holdout generation/retrieval run has occurred.

See [the data audit](data_audit.md) and [Phase 1 journal](engineering-journal/phase-01.md).

## Phase 2 baseline

The approved fixed/dense baseline is implemented through the same typed service
used by future UI/experiments. Real acceptance uses exactly three deterministic
frozen-development cases from distinct companies and a separate forecast negative;
it does not run holdout or implement Phase 4 scoring. Requests contain only
question text, never gold-derived document filters. Completed campaigns replay
validated local traces; interrupted started campaigns fail closed against repurchase.

See [ADR 0003](decisions/0003-baseline-rag.md), the
[Phase 2 journal](engineering-journal/phase-02.md) and
[baseline acceptance](../results/phase-2-baseline-smoke.md) for actual execution
and known limitations. Synthetic/model-metadata checks do not establish live answer
quality. All paid attempts share the $5/$4/$0.75 ledger limits and an untouched $1 reserve.

Current real checkpoint: 1,792/22,070 chunk vectors, 113 Nebius attempts (112
settled, one unknown), $0.006045 accounted plus $0.000065 retained reservation.
No Claude inference or development/holdout answer run occurred. The five real
source/cache/split checks pass; complete-index and campaign gates fail closed.
No query latency, answer correctness or citation-support result is available yet.
