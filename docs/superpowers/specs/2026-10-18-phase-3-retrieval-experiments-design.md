# Phase 3 controlled retrieval experiments — approved design

Approved in the human's "PLEASE IMPLEMENT THIS PLAN" message on 2026-10-18.
Primary authority: `project.md`. Implementation method: native, continuing the
session preference. No push/merge or later-phase work is included.

## Goal and arms

Validate four arms on AMD_2022_10K, then the same 36 frozen development questions
over the same 53 filings, after full-corpus baseline acceptance and budget checks.

| Arm | Chunking | Retrieval | Reranking |
|---|---|---|---|
| A | Fixed | Dense | None |
| B | Semantic | Dense | None |
| C | Fixed | Dense | Local cross-encoder |
| D | Semantic | Dense | Local cross-encoder |

Keep Qwen/Qwen3-Embedding-8B, 4096 dimensions, Claude model/prompt, 15 candidates,
top five selection, 3500 context tokens, existing timeouts/retries and extraction
rules. A/C share one fixed index and identical pre-rank pools; B/D likewise share
one semantic index/pool. Experiment identity must not force duplicate indexes.
Preserve legacy baseline behavior, fingerprints and persisted index compatibility.

## Spending

Use the existing ledger/authority, total $5, working $4 and untouched $1 reserve.
Phase 3 has its own atomic $0.75 sublimit; prior spending and unknown reservations
remain included globally. Phase 3 requests carry phase=3. Estimate semantic
preparation before embedding, then actual indexing/comparison after preparation.
Stop on a budget conflict. Never initialize another allowance or raise limits.
Embedding invocations default to four inputs and one batch; timeouts stop and
retain their unknown reservation. No automatic timeout retry.

## Semantic preparation and chunking

Partition unchanged pages into contiguous sentence/paragraph units toward 64–128
Qwen tokens. Split oversized units using exact tokenizer offsets. Embed units with
the guarded Nebius adapter; cache computations and vector references. Compute
adjacent same-page cosine distances, with the document's 95th-percentile positive
distance as break threshold. At least 64 new tokens precede a semantic break;
chunks have at most 400 tokens and up to 60 tokens overlap. Short tails are valid.
Use deterministic source-preserving forced cuts when semantic breaks cannot meet
the maximum. Record units, distances, threshold, boundaries and forced-cut reasons.
Reconstruction is pure/cache-only and must not buy missing vectors.

Every chunk is a page-local exact source substring. Preserve Unicode, coverage,
table and extraction diagnostics. No table-cell reconstruction or OCR.

## Local reranker

Model: cross-encoder/ms-marco-MiniLM-L6-v2, immutable revision
`eeed17e3bfc6fa06a790f2d12a9501fec587fccf`, official `onnx/model.onnx` float32
artifact, CPUExecutionProvider. Download explicitly; pin/hash artifacts and load
offline. No GPU/PyTorch installation. The official ONNX model SHA-256 is
`5d3e70fd0c9ff14b9b5169a51e957b7a9c74897afd0a35ce4bd318150c1d4d4a`.

Score all 15 candidates, retain original dense ranks/scores and provenance, sort
descending logits with chunk-ID ties, then select five. Use overlapping passage
windows within the 512-token pair limit, maximum window score per chunk. Reject
unsupported query lengths and never silently truncate source text. Rerank failure
is a failed arm, never an unlabelled baseline fallback.

Official sources consulted during planning:
- https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2/tree/eeed17e3bfc6fa06a790f2d12a9501fec587fccf/onnx
- https://sbert.net/docs/cross_encoder/usage/efficiency.html

## Shared pipeline, runner and notebook

Retain `answer(QueryRequest) -> Answer`, existing context and citation stages.
Add typed experiment configuration, semantic preparation and rerank records.
Full development runs are retrieval-only. Gold joins/metrics live exclusively in
the offline evaluator; runtime receives question text without gold-derived scope.
Holdout remains unexecuted. Immutable pool receipts enable replay without buys.
Report page-hit@5, unique gold-page recall@5, MRR@15, candidate-pool coverage,
stage latency, API usage and failures. These are not semantic-faithfulness scores.

Add `notebooks/02_retrieval_experiments.ipynb`, exposing preparation batches,
boundaries/catalogs, paired pools, scores, selections and comparisons separately.
Network cells default off. Keep the existing notebook and its local execution
untouched; publish the new notebook outputless. Up to four optional manually
executed AMD answers use one human-written question across arms; no bulk answers.
Raw traces/caches stay ignored, summaries are sanitized.

## Acceptance

TDD covers semantic-vector-sensitive boundaries, exact spans/Unicode/caps/overlap,
cache invalidation and zero-dispatch rebuilds, concurrent spending bounds including
unknown prior billing, paired pool equality and promotion of candidate 15, full
long-passage window coverage, artifact/reranker errors, development membership and
gold isolation, no-repurchase replay and offline notebook execution. Existing
baseline, lint, packaging and synthetic smoke checks must stay green. Full-corpus
execution waits for its baseline prerequisite and successful preflight. Stop and
report partial execution if those gates cannot pass; do not silently shrink the
benchmark, raise the allowance or claim acceptance.
