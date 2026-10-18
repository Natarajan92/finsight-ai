# Experiment record conventions

No retrieval/generation experiment has run. There is no selected split, index,
provider, measured accuracy, faithfulness, latency, token usage or model cost yet.
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
