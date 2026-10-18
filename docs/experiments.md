# Experiment record conventions

No retrieval/generation experiment has run. The Phase 1 split is selected and frozen;
there is no index, provider, measured accuracy, faithfulness, latency, token usage or model cost yet.
The synthetic smoke verifies contracts only and reports cost as unknown.

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
- PyMuPDF/MuPDF 1.28.2, extractor `phase1-v2`, original-order text/blocks. Nine
  scanned appendix pages have explicit image-only coverage gaps; no OCR is run.
- Development annotation check: 17/41 normalized exact quote matches. This is an
  extraction diagnostic, not retrieval correctness, faithfulness, or an experiment arm.
- Eight question-linked filings appear in both splits. This evaluates unseen
  questions, not unseen documents. All 53 filings remain the common retrieval corpus.
- Freeze all four configurations and prompts using development only, then evaluate
  holdout once on the same 16 IDs. No holdout generation/retrieval run has occurred.

See [the data audit](data_audit.md) and [Phase 1 journal](engineering-journal/phase-01.md).
