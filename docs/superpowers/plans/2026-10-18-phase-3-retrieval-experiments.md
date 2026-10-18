# Phase 3 Retrieval Experiments Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans, native execution with
> one fresh whole-branch review. The human explicitly approved this plan's scope.

**Goal:** Four reproducible retrieval arms with an interactive AMD pilot and gated
36-question development expansion.

**Architecture:** Reuse guarded Nebius embeddings, exact page/chunk contracts,
Chroma integrity checks and the shared answer pipeline. Prepare semantic evidence
before cache-only catalogs; share indexes/pools across paired arms; rank locally.

**Tech Stack:** Python 3.12, Pydantic, LangChain, Chroma, tokenizers, ONNX Runtime.

**Spec:** `docs/superpowers/specs/2026-10-18-phase-3-retrieval-experiments-design.md`.

## Global Constraints

- Existing $5/$4/$1 authority; atomic Phase 3 cap $0.75; no reset or increased cap.
- Nebius semantic and retrieval embeddings; local pinned CPU reranker; no PyTorch.
- Four-input batches, 20-second attempts, 45-second requests, existing retry policy.
- Preserve baseline identities/indexes, original data/splits and executed notebook.
- 15 candidates, five selections, 3500 context tokens; no holdout or bulk generation.
- No push/merge. All notebook network steps off and delivered notebook outputless.

## Review Focus

- Recomputed semantic preparation must bind real cached vectors to exact source units.
- Two concurrent Phase 3 calls must include prior reservations in the same transaction.
- A changed dense pool or model artifact must invalidate replay before any dispatch.
- Long reranker passages must cover every source token including overflow tails.
- Dirty local notebook outputs must never enter commits or invalidate shipped checks.

### Task 1: Experiment identities and shared spending

**Files:** contracts/retrieval_experiments.py; observability/budget.py and dispatch.py;
tests/rag/test_retrieval_experiments.py and test_budget.py.
**Interfaces:** RetrievalExperimentConfig provides arm, baseline-compatible limits,
index_config/index_fingerprint and full experiment fingerprint. Ledger reserve gains
an independently bounded phase3_usd and phase_available(phase); dispatcher forwards it.

- [ ] Write and run RED tests for shared paired identities, independent fingerprints,
  atomic Phase 3/global bounds and retained unknown Phase 2 reservations.
- [ ] Implement validated contracts and backward-compatible ledger/dispatch changes.
- [ ] Run focused checks and baseline budget/config tests; commit and ledger evidence.

### Task 2: Cached semantic preparation and exact chunks

**Files:** chunking/semantic.py and semantic_cache.py; indexing/catalog.py and builder.py;
tests/rag/test_semantic_chunking.py.
**Interfaces:** semantic_units(document,pages,config,tokenizer), prepare_semantics(...),
load_preparation(...), semantic_chunk_pages(...). Catalog/build/open accept a pure
chunker injection, retaining legacy defaults. Generated index config is arm-independent.

- [ ] RED tests for vector-sensitive boundaries, exact coverage/Unicode/overlap/caps,
  corruption/missing-cache failure and rebuild with zero embedding calls.
- [ ] Implement source-unit preparation, one-batch guarded embedding, persisted
  distances and pure validated reconstruction. Keep preparation in ignored cache.
- [ ] Test catalog/index reopen and baseline compatibility; commit and ledger evidence.

### Task 3: Offline CPU cross-encoder reranker

**Files:** retrieval/reranking.py and reranker_artifacts.py; runtime/ports.py;
tests/rag/test_reranking.py. Pin the already installed ONNX Runtime directly.
**Interfaces:** Reranker.rerank(question,candidates,context)->RerankResult; explicit
prepare_reranker and offline artifact loader. Pure window construction is inspectable.

- [ ] RED tests for rank-15 promotion, original-score preservation, ties, complete
  overflow coverage, long-query rejection, finite logits and artifact corruption.
- [ ] Implement pinned artifact preparation and local ONNX inference with cached
  query/text/model/window identities; never fall back after errors.
- [ ] Run focused/baseline checks; commit and ledger evidence.

### Task 4: Four-arm pipeline, receipts and development comparison

**Files:** retrieval/experiments.py; runtime/experiment_factory.py; evaluation/retrieval.py;
application.py and cli.py; tests/rag/test_experiment_runner.py.
**Interfaces:** ExperimentRetriever.retrieve preserves the current retriever contract;
run_arms returns typed traces with shared pool fingerprints. Shared service gets an
optional phase/scenario capability while baseline defaults remain unchanged. CLI
exposes explicit preparation, cache-only index, retrieval, comparison and pilot ask.

- [ ] RED tests for equal paired pools, failure isolation, no-repurchase replay,
  question-only runtime input and scorer metrics/development-only membership.
- [ ] Implement arm-aware factories, staged preflight, durable start/complete receipts,
  separate offline scoring and fail-closed full-corpus baseline prerequisite.
- [ ] Run real synthetic Chroma integration and baseline service/CLI tests; commit.

### Task 5: Interactive AMD notebook and documentation

**Files:** notebooks/02_retrieval_experiments.ipynb; tests/rag/test_experiment_notebook.py;
README, docs/experiments.md and the Phase 3 journal/results summary.
**Interfaces:** Notebook uses the same experiment facade as CLI, manual network gates,
fresh stage contexts and read-only inspections; optional four-answer pilot is off.

- [ ] RED test shipped notebook cells against synthetic source/PDF/provider boundary.
- [ ] Build guided stage cells, explicit preparation/batches and comparison inspectors.
- [ ] Run notebook tests and a real network-blocked Jupyter kernel on AMD source.
  Commit outputless notebook/docs and preserve the original notebook hash.

### Task 6: Acceptance, conditional expansion and final review

- [ ] Run full shipped-tree unit suite, Ruff, lock/build and synthetic smokes; inspect
  exact outgoing paths and secret patterns. Record actual failures/skips truthfully.
- [ ] Validate pinned real CPU model and AMD preparation/pilot where safely permitted.
  Keep optional generation manual. Full expansion requires complete baseline and
  passing spending estimates; record blocked gates without weakening them.
- [ ] Obtain one fresh whole-branch review, re-grade findings, perform one RED/GREEN
  fix pass, verify suite and record rulings. Keep commits local for human review.
