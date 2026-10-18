# Phase 2 Baseline Evidence-First RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a fixed-chunk financial-document RAG service and CLI that return validated cited answers or explicit abstentions within the approved shared testing budget.

**Architecture:** Preserve the modular Python application and existing `ApplicationService.answer(QueryRequest) -> Answer` boundary. Compose retrieval, context, structured generation and validation with LangChain runnables. Keep source provenance, cache/index integrity, persistent spending authorization, citation validation and evaluation isolation under FinSight control.

**Tech Stack:** Python 3.12.15; uv 0.12.23; existing pinned Pydantic/PyMuPDF/pytest/Ruff; pinned LangChain core/Anthropic/Chroma integrations; local Chroma; tokenizers; HTTPX; SQLite/Decimal from the standard library. Hosted embeddings: Nebius `Qwen/Qwen3-Embedding-8B`; generation: `claude-sonnet-5`.

**Spec:** [2026-10-18-phase-2-baseline-rag-design.md](../specs/2026-10-18-phase-2-baseline-rag-design.md), approved in P2-006.

**Status:** Reviewed and approved for native execution in P2-008. Task checkboxes record verified implementation progress; paid acceptance remains a separate gated step.

## Global Constraints

- Source of truth: `project.md`; phase branch: `feat/phase-2-baseline-rag`, currently containing documentation commit `f8c29d3` over merged Phase 1 `6db76b2`.
- "Common corpus: 53 canonical filings, 9,504 pages; keep original files unchanged."
- "Frozen questions: 36 development, 16 holdout; seed 42 and existing membership."
- Source fingerprint: `7376d03d8183077b92ed98b8c4e3a584fefd02202b75feba82cdc13b2519fad3`.
- Split fingerprint: `e6ec481633654b779721f1d94c7aa05a65e43c9f37deae177819658d2b665431`.
- "The fixed baseline uses page-local windows with a hard maximum of 400 source-text tokens and a target overlap of 60."
- Dense retrieval: 15 candidates; default selection: 5; 3,500 evidence tokens; 512 question tokens; 6,000 estimated full input tokens; 1,024 maximum billable output/reasoning tokens.
- "Use an explicit 20-second timeout per provider attempt and a 45-second application deadline."
- "The approved testing ceiling is USD 5.00 shared by both providers. The working allowance is USD 4.00; USD 1.00 remains untouched. Phase 2 has a sub-allowance of USD 0.75 for indexing and real smoke runs, included in the shared allowance."
- "SDK/framework automatic retries are disabled." At most one application-controlled retry for an explicit 429/502/503/504 response, with a new reservation and remaining deadline. Uncertain timeouts retain reservations and do not automatically retry.
- "The public service still returns `Answer`, not a tuple or a framework message." Emit correlated `RunTrace` through an injected recorder.
- Preserve zero-based pages, exact source substrings, extraction diagnostics, the nine source-specific encryption exceptions, and existing immutable split/source policy.
- Runtime/contracts cannot import evaluation; no gold answers, rationale, evidence quotes or annotated pages enter runtime inputs, indexes, prompts, caches or normal CLI output.
- Only fixed/dense/no-rerank runs in Phase 2. Semantic/reranking selections fail explicitly. Later phases, OCR, new companies, agents, UI and cloud deployment remain outside implementation scope.
- Standard CI and synthetic smoke must work without API keys, original PDFs, model downloads or network requests. Real checks remain opt-in integration tests.
- Push, PR publication and merge require separate explicit approval. Record actual RED/GREEN evidence and commands in the Phase 2 journal before commits.

## Review Focus

1. A request times out after dispatch or the process restarts: retained reservations must prevent spend reuse; duplicate request IDs must not cause a second dispatch. Task 2.
2. Repeated text, non-ASCII financial symbols and adjacent token windows: spans must point to the correct original occurrence without missing source characters or changing signs/units. Task 3.
3. A locally modified catalog/index has plausible metadata or a partial build: refuse inconsistent sources, filters, dimensions and incomplete indexes before paid generation. Task 5.
4. Financial source text contains instructions, or benchmark labels are poisoned: text stays data, no tool executes, and annotations cannot change runtime prompts or source-derived artifacts. Task 9.
5. A quote is real but belongs to another supplied span/year, or a calculation invents an operand: reject the mapping/operand; semantic claim support remains separately reviewed. Task 8 and real smoke inspection in Task 10.

## Planning evidence and dependency decisions

Public PyPI JSON metadata and published wheel source were inspected on 2026-10-18. A metadata-only, wheel-only `uv pip compile` resolution for Python 3.12 succeeded for both `x86_64-pc-windows-msvc` and `x86_64-unknown-linux-gnu`: **104 packages per platform**. This is dependency-resolution evidence, not an installation, runtime compatibility test or remote-CI result.

Keep existing pins unchanged and add these direct pins in Task 1:

| Package | Exact pin | Responsibility |
|---|---|---|
| [langchain-core](https://pypi.org/pypi/langchain-core/1.6.12/json) | `1.6.12` | Runnable/document/embedding interfaces |
| [langchain-anthropic](https://pypi.org/pypi/langchain-anthropic/1.7.6/json) | `1.7.6` | Native structured Claude generation |
| [langchain-chroma](https://pypi.org/pypi/langchain-chroma/1.1.0/json) | `1.1.0` | Persistent vector-store integration |
| [chromadb](https://pypi.org/pypi/chromadb/1.5.9/json) | `1.5.9` | Local database and explicit collection settings |
| [tokenizers](https://pypi.org/pypi/tokenizers/0.23.3/json) | `0.23.3` | Local source-token offsets/counts |
| [httpx](https://pypi.org/pypi/httpx/0.28.1/json) | `0.28.1` | Nebius API and public tokenizer downloads |
| [anthropic](https://pypi.org/pypi/anthropic/1.15.0/json) | `1.15.0` | Explicit Claude counting/client configuration |
| [langsmith](https://pypi.org/pypi/langsmith/0.14.11/json) | `0.14.11` | Explicitly disable inherited hosted tracing |

The resolution includes `httpx2==2.13.1` transitively. Anthropic 1.15 uses HTTPX2, while the Nebius adapter uses HTTPX. Published LangChain Anthropic source contains compatibility wrappers subclassing the SDK's `DefaultHttpxClient`; do not inject an HTTPX client into an HTTPX2 SDK. Add a keyless constructor regression rather than relying on declared bounds alone. Retain exact transitive versions/hashes in `uv.lock` after approved installation.

Chroma and tokenizers publish compatible Windows AMD64 and Linux wheels. If installation or constructor tests disagree, stop that dependency task and review replacement pins; do not replace Chroma or a model silently. Disable Chroma telemetry and hosted LangSmith tracing explicitly. Framework contracts remain Pydantic/stdlib-only.

Tokenizer source is `Qwen/Qwen3-Embedding-8B` at Hugging Face revision `1d8ad4ca9b3dd8059ad90a75d4983776a23d44af`. Fetch only `tokenizer.json`, `tokenizer_config.json` and `config.json`; never model weights. Task 3 records file SHA-256s after download. This is a tokenizer revision, not proof of Nebius's hosted weight revision.

Anthropic documents token counting as free but approximate. Use the configured Claude model's counting endpoint; no counting network request runs in CI. Full-input admission uses the returned estimate plus `max(512, ceil(0.10 * estimate))` overhead tokens, capped at 6,000. Count any schema text serialized into the request and retain the native schema in the request identity. If the counter cannot establish a bounded estimate, stop before generation. The USD 1 reserve remains untouched; estimated costs do not certify final invoices.

Do not commit guessed/live-unverified prices. A paid run requires an ignored, validated `RateBook` with both model IDs, current official rate sources, verification time and rate fingerprint. Verification must be no older than 24 hours when a paid campaign starts. Pure tests use synthetic rate cards. No paid operation uses an unknown rate or automatically switches service tiers.

## File structure and shared interface vocabulary

Existing files are extended only where needed. The numbered tasks own these units:

| Task | Product files created or changed | Tests |
|---|---|---|
| 1 | `contracts/runtime.py`, `contracts/tracing.py`, `runtime/errors.py`, `runtime/ports.py`, `runtime/__init__.py`; modify `config.py`, `contracts/__init__.py`, `observability/logging.py`, `pyproject.toml`, `uv.lock`, `.env.example`; add baseline JSON config | `tests/rag/conftest.py`, `test_runtime_config.py` |
| 2 | `contracts/budget.py`, `observability/budget.py`, `observability/dispatch.py` | `test_budget.py`, `test_dispatch.py` |
| 3 | `chunking/tokenizer.py`, `chunking/fixed.py`, `chunking/diagnostics.py` | `test_tokenizer.py`, `test_fixed_chunking.py` |
| 4 | `indexing/embedding_cache.py`, `indexing/nebius.py` | `test_embedding_cache.py`, `test_nebius.py` |
| 5 | `contracts/indexing.py`, `indexing/catalog.py`, `indexing/store.py`, `indexing/builder.py`, `retrieval/dense.py`, `ingestion/pages.py` | `test_index_lifecycle.py`, `test_dense_retrieval.py` |
| 6 | `contracts/context.py`, `generation/counting.py`, `context/packing.py` | `test_token_counting.py`, `test_context_packing.py` |
| 7 | `contracts/generation.py`, `generation/prompts.py`, `generation/claude.py` | `test_generation.py` |
| 8 | `citations/validation.py`, `citations/calculation.py` | `test_citation_validation.py`, `test_calculation.py` |
| 9 | modify `application.py`; create `runtime/factory.py`, `observability/tracing.py`, `cli.py`, `rag_smoke.py`; extend installed CLI/CI settings | `test_application.py`, `test_rag_cli.py`; extend existing isolation/runtime tests |
| 10 | `evaluation/smoke.py`, `tests/test_rag_integration.py`, ADR/review/report/docs updates | Opt-in acceptance checks and full existing suites |

All abbreviated test filenames in the table live under `tests/rag/`. Existing tests outside that subtree remain in place. The `tests/rag/conftest.py` builders provide synthetic canonical manifests/pages, an offset-aware character tokenizer, a tiny locally trained tokenizer, deterministic fake embeddings, fake clocks/transports, a recording trace sink and draft factories. No public test fixture contains real benchmark IDs/answers.

Task 1 establishes these shared ports/types; owning tasks define implementation details without changing the names:

- `CallContext(run_id: str, phase: int, deadline: float)`: immutable per-invocation context; monotonic deadline, no implicit shared current-run state.
- `FinsightError(code: str, message: str, retryable: bool = False)`: safe application exception mapped to public `AppError`.
- `OffsetTokenizer.count(text: str) -> int` and `.offsets(text: str) -> tuple[tuple[int, int], ...]`: Unicode-character offsets; no import-time downloads.
- `EmbeddingBackend.for_run(context: CallContext) -> EmbeddingBackend`, `.embed_documents(texts: list[str]) -> list[list[float]]`, `.embed_query(text: str) -> list[float]`: match LangChain embedding semantics.
- `PageRepository.get(document_id: str, page_index: int) -> Page`: validated source/cache reads; source-only dependencies.
- `TokenCounter.count_text(text: str, context: CallContext) -> int` and `.count_prompt(system: str, user: str, schema: dict[str, object], context: CallContext) -> int`.
- `TraceRecorder.record(trace: RunTrace) -> None`: one correlated terminal trace per admitted invocation, including failures.
- `ProviderUsage`: provider/model, input/output/cache token categories as optional nonnegative integers, optional USD Decimal, `cost_basis` (`provider_reported`, `usage_priced`, `unknown`), and a usage-known flag. Never reinterpret absent counts as zero; usage-priced cost is an estimate, not an invoice.
- `RunTrace`: run/config/source/index/prompt identities, canonical question/request fingerprint, request filters, ordered `RetrievalCandidate`s, packed-evidence IDs/spans, stage timings, provider-attempt records, final typed `Answer`, status/error and cache/replay flags. This preserves the answer for exact artifact validation/replay. Types introduced later extend the trace model without importing framework/providers.

## Task 1: Runtime contracts, configuration and verified dependency installation

**Files:** Table row 1; create `configs/runtime/phase-2-baseline.json`; extend `tests/test_runtime.py` for two-provider redaction.

**Interfaces:** Produce `BaselineConfig`, `CallContext`, `ProviderUsage`, `RunTrace`, the ports above, and `load_baseline_config(path: Path) -> BaselineConfig`. Extend `Settings` with `nebius_api_key` and `anthropic_api_key` as optional `SecretStr`; retain the legacy `api_key` and its existing tests. Do not instantiate provider clients at import time.

`BaselineConfig` serializes schema/scenario version; source fingerprint; size/overlap; tokenizer name/revision; embedding provider/model/revision/dimension/instructions/normalization; generation model/prompt version/effort; execution limits; score metric; budget identity/caps. Default scenario is `fixed_dense_v1`, dimension 4096, cosine distance, prompt `grounded-v1`, effort `low`; use the global limits verbatim. Configuration cannot increase approved budget/output bounds. All material settings participate in a canonical fingerprint.

- [x] **Step 1 - Add failing configuration/constructor tests.** Include assertions:

```python
assert config.chunk_tokens == 400 and config.overlap_tokens == 60
assert (config.candidate_count, config.top_k, config.context_tokens) == (15, 5, 3500)
assert (config.question_tokens, config.input_tokens, config.output_tokens) == (512, 6000, 1024)
assert config.working_usd == Decimal("4.00")
assert config.phase2_usd == Decimal("0.75")
assert config.fingerprint() != changed_prompt.fingerprint()
```

Also reject nonfinite rates/limits, semantic/rerank baseline configuration, unbounded budgets, credentials inside serialized config, and contracts importing LangChain/provider modules. Fake-key `ChatAnthropic` client construction and a local Chroma instance with default embedding disabled must perform no network request.
- [x] **Step 2 - Run RED:** `uv run --locked pytest tests/rag/test_runtime_config.py tests/test_runtime.py --basetemp=.pytest-tmp/p2 -q`. Expect missing new types/imports before dependency changes; record the actual failure.
- [x] **Step 3 - Add the exact pins above, regenerate `uv.lock`, then `uv sync --locked --group dev`.** Do not upgrade existing direct pins. Capture actual installation and constructor compatibility. Create the typed configuration/ports, config JSON and credential placeholders; redact both provider keys plus the legacy key.
- [x] **Step 4 - Run GREEN:** the RED command plus `uv lock --check`, Ruff and existing contract/isolation tests. Expect keyless constructors and serialization/import boundaries to pass. No model/tokenizer download occurs.
- [x] **Step 5 - Run the common pre-commit gate; commit only Task 1 files and updated journal:** `feat: define baseline RAG runtime configuration`.

## Task 2: Durable spending ledger and guarded dispatch

**Files:** Table row 2; extend `tests/rag/conftest.py` with initialized temporary ledgers, synthetic rates and scripted attempts.

**Interfaces:** `RateBook` binds rates to provider/model/service tier/source URL/UTC verification time and canonical fingerprint. `BudgetLedger.initialize(path: Path, budget_id: str) -> BudgetLedger`, `.open(path: Path, budget_id: str) -> BudgetLedger`, `.reserve(request_id: str, provider: str, model: str, maximum_usd: Decimal, phase: int) -> Reservation`, `.mark_dispatched(reservation_id: str) -> None`, `.settle(reservation_id: str, observed_usd: Decimal | None) -> None`, `.snapshot() -> BudgetSnapshot`. `GuardedDispatcher.execute(estimate: CallEstimate, send: Callable[[], T], usage_of: Callable[[T], ProviderUsage | None], context: CallContext) -> T`.

`CallEstimate` fields are `request_id`, `provider`, `model`, `rate_fingerprint`, `input_tokens`, `max_output_tokens`, `maximum_usd`, and `service_tier`. `Reservation` exposes `reservation_id`, `request_id`, `maximum_usd` and state. `BudgetSnapshot` exposes accounted/reserved totals and available global/phase USD. Here `settle`'s `observed_usd` is provider-reported cost if available, otherwise an explicitly labeled estimate priced from observed token usage; it is `None` when neither can be established. Store that cost basis with the attempt.

Use integer USD micro-units with upward rounding for reservations and Decimal input/output; never binary-float money. SQLite uses `BEGIN IMMEDIATE`, unique request IDs, integrity/schema checks and explicit states `reserved`, `dispatched`, `settled`, `unknown`. Keep an adjacent budget-identity marker and write the budget ID into run/index records. Missing DB after marker/records, mismatched IDs or corruption blocks dispatch. Initial bootstrap is an explicit command; no automatic reset. An already-dispatched request ID cannot dispatch twice.

- [x] **Step 1 - Write failing budget/dispatch tests**, including:

```python
ledger.reserve("one", "anthropic", "claude-sonnet-5", Decimal("0.74"), 2)
with pytest.raises(FinsightError, match="budget_exceeded"):
    ledger.reserve("two", "anthropic", "claude-sonnet-5", Decimal("0.02"), 2)
assert BudgetLedger.open(path, budget_id).snapshot().reserved_usd == Decimal("0.74")
```

Add named tests `test_timeout_retains_full_reservation_after_restart`, `test_two_connections_cannot_overreserve`, `test_duplicate_request_cannot_dispatch_twice`, `test_missing_or_corrupt_ledger_blocks_send`, `test_actual_cost_over_reservation_is_recorded_not_clamped`, `test_expired_or_missing_rate_blocks_send`, `test_retry_reserves_again_and_stops_at_two_attempts`, and `test_deadline_prevents_next_dispatch`. Assert transport call counts, retained totals and budget/error codes; uncertain failure keeps `usage=None` and the whole reservation.
- [x] **Step 2 - Run RED:** `uv run --locked pytest tests/rag/test_budget.py tests/rag/test_dispatch.py --basetemp=.pytest-tmp/p2 -q`; expect missing ledger/dispatcher.
- [x] **Step 3 - Implement transactional authorization and per-attempt execution.** Include maximum input/output/overhead in estimates. Pass `min(20, remaining_deadline)` into each transport attempt. Allow one new attempt only for explicit eligible status responses; a timeout/disconnect is uncertain and does not retry. Reconcile usage before parsing/generation validation can discard it. Unknown usage retains reserved money. Record actual overrun honestly and block subsequent calls if limits are exhausted.
- [x] **Step 4 - Run GREEN:** same focused tests, including both phase/global limits, repeat-open, concurrency and retry assertions. Verify a denied call never executes `send`.
- [x] **Step 5 - Common gate and commit:** `feat: enforce persistent provider spending limits`.

## Task 3: Pinned tokenizer and exact-span fixed chunking

**Files:** Table row 3; tokenizer preparation function is later exposed by Task 9 CLI. No parser/cache policy rewrite.

**Interfaces:** `prepare_tokenizer(destination: Path, revision: str) -> TokenizerArtifact`; `LocalOffsetTokenizer(artifact: TokenizerArtifact)` implements Task 1's tokenizer port; `chunk_pages(document: DocumentManifest, pages: tuple[Page, ...], config: BaselineConfig, tokenizer: OffsetTokenizer) -> tuple[Chunk, ...]`; `chunk_diagnostics(chunk: Chunk, page: Page) -> tuple[str, ...]`.

The artifact manifest records the exact three source URLs at the pinned revision, SHA-256s, tokenizer library/version and special-token settings. Use `add_special_tokens=False` for source chunk counts. Download explicitly to an ignored staging directory, validate JSON/hashes and atomically publish; offline loading never downloads. Use source character offsets, re-count candidate substrings after choosing boundaries, retain coverage/progress, and derive overlap from valid character boundaries. Warn on a financial-looking page when a cut is inside a line/table block or separates an available header; diagnostics are conservative heuristics, not table reconstruction.

- [ ] **Step 1 - Write failing tokenizer/chunker tests.** With `char_tokenizer` and an 800-character synthetic page:

```python
assert [(s.char_start, s.char_end) for c in chunks for s in c.source_spans] == [
    (0, 400),
    (340, 740),
    (680, 800),
]
assert all(tokenizer.count(c.content) <= 400 for c in chunks)
assert all(
    c.content == page.text[c.source_spans[0].char_start : c.source_spans[0].char_end]
    for c in chunks
)
```

Test `test_unicode_and_repeated_rows_keep_correct_occurrence`, `test_all_source_characters_covered`, `test_page_boundaries_never_overlap`, `test_empty_pages_emit_no_chunks_but_keep_diagnostics`, `test_wrong_document_or_error_page_rejected`, `test_table_boundary_risk_is_visible`, `test_artifact_tamper_rejected_without_download`, and stable IDs under repeat runs/config changes. The local tiny tokenizer fixture must exercise genuine tokenizer offset/re-encoding behavior without a remote download.
- [ ] **Step 2 - Run RED:** `uv run --locked pytest tests/rag/test_tokenizer.py tests/rag/test_fixed_chunking.py --basetemp=.pytest-tmp/p2 -q`.
- [ ] **Step 3 - Implement source-preserving windows, artifact validation and diagnostics.** Expose `tokenizer_unavailable`, `tokenizer_integrity` and `invalid_source_span` errors rather than character-count fallbacks. Keep hosted model revision unknown unless the provider exposes it; keep the pinned tokenizer revision distinct.
- [ ] **Step 4 - Run GREEN:** same tests plus existing provenance/extraction tests; source numbers, signs, years and units remain byte-for-byte equivalent as Unicode strings.
- [ ] **Step 5 - Common gate and commit:** `feat: chunk financial pages with exact token provenance`.

## Task 4: Guarded Nebius embeddings with durable role-aware caching

**Files:** Table row 4.

**Interfaces:** `EmbeddingCache.key(text: str, role: Literal['document', 'query']) -> str`, `.get(key: str) -> EmbeddingRecord | None`, `.put(record: EmbeddingRecord) -> None`; the cache is bound to the frozen embedding configuration. `EmbeddingRecord` contains key, provider/model/role, config fingerprint, submitted-text hash, vector and payload hash. `CachedNebiusEmbeddings(EmbeddingBackend)` implements the standard LangChain `Embeddings` interface and immutable `.for_run(context)` binding. Inject `httpx.Client`, tokenizer, cache, config and dispatcher. `estimate_embedding_batch(texts: list[str], role: Literal['document', 'query'], rates: RateBook) -> CallEstimate` reserves each submitted input's counted tokens plus 64 overhead tokens as a conservative special-token allowance; any observed overrun remains visible and halts later dispatch if allowances are exhausted.

Call only `https://api.tokenfactory.nebius.com/v1/embeddings`, with automatic transport retries/redirects disabled, `encoding_format='float'`, the configured model, dimension 4096 and explicit `service_tier='default'`. Never select surge/over-limit billing. Batch at most 16 documents; count all submitted inputs. Documents have no retrieval instruction. Freeze query format as `Instruct: Given a financial question, retrieve passages from company filings that answer the question.\nQuery:{question}`. Confirm provider prefix handling during preflight before accepting a live config; do not silently double-prefix.

- [ ] **Step 1 - Write failing mocked-transport tests**, with fake live dimension 4096 and smaller explicitly injected synthetic test profiles:

```python
assert first_vectors == second_vectors
assert transport.calls == 1  # second identical request is a cache hit
assert cache.key("same text", role="query") != cache.key("same text", role="document")
assert ledger.snapshot().reserved_usd == Decimal("0")  # known usage settled
```

Assert request body/endpoint/tier/prefix, indices reordered correctly, no automatic redirects or retries, missing/duplicate result indices rejected, NaN/Inf/zero/wrong-dimension vectors rejected, tampered cache rejection, normalization to unit length, successful-batch persistence after later failure, and no second request when budget authorization fails. Preserve raw returned usage even for malformed vectors; cache no malformed vectors.
- [ ] **Step 2 - Run RED:** `uv run --locked pytest tests/rag/test_embedding_cache.py tests/rag/test_nebius.py --basetemp=.pytest-tmp/p2 -q`.
- [ ] **Step 3 - Implement the HTTP adapter/cache.** Cache key hashes exact submitted text, role, instructions, provider/model/revision, dimension and normalization. Validate count/index/model/vector correspondence before use. Use atomic writes with payload fingerprints; retain usage via the dispatcher before shape validation. No generic OpenAI endpoint/key defaults.
- [ ] **Step 4 - Run GREEN:** same tests with sockets blocked and exact call/reservation assertions. Repeat a simulated interrupted embedding job and verify only uncached batches dispatch.
- [ ] **Step 5 - Common gate and commit:** `feat: cache budgeted Nebius embeddings`.

## Task 5: Complete persistent indexes and provenance-checked filtered retrieval

**Files:** Table row 5. `ingestion/pages.py` wraps existing cache/source APIs rather than altering them.

**Interfaces:** `ChunkCatalog` binds manifest/source/extraction/config identity, typed chunks, diagnostics and payload hashes. `IndexManifest` binds catalog/source/config fingerprints, expected chunk IDs/count, vector dimension, metric, provider/model/tokenizer/software identities and completion status. `build_index(corpus: CorpusManifest, pages: PageRepository, config: BaselineConfig, embeddings: EmbeddingBackend, root: Path, context: CallContext) -> IndexManifest`; `open_index(root: Path, expected: BaselineConfig, corpus: CorpusManifest) -> DenseRetriever`; `DenseRetriever.retrieve(request: QueryRequest, context: CallContext) -> tuple[RetrievalCandidate, ...]`.

Use validated source PDFs/cache records and manifest metadata, stable insertion order, single-threaded HNSW construction and explicit cosine configuration. The published Chroma wrapper accepts `collection_configuration={'hnsw': {'space': 'cosine'}}`; inspect/verify further HNSW options against pinned APIs before setting them. All embedding calls go through the guarded cached adapter. Disable default embedding downloads and telemetry. Query by an already obtained query vector; verify the chosen wrapper method returns raw distance, and label it `cosine_distance/lower_is_better`. Preserve returned pre-rank pool; sort equal distances by stable chunk ID. Persist the exact observed pool for later paired-arm reuse.

- [ ] **Step 1 - Write failing synthetic PDF/index/retrieval tests**, including:

```python
assert len(results) <= 15
assert all(r.source.company == "AMD" and r.source.fiscal_period == "2022" for r in results)
assert [r.rank for r in results] == list(range(1, len(results) + 1))
assert all(
    r.score.kind == "cosine_distance" and r.score.direction == "lower_is_better" for r in results
)
```

Test combined company/document/period filters, unknown/conflicting filters, unfiltered corpus scope, equal-score ties, catalog/manifest/source mismatch, a forged document ID, stale vector dimension, incomplete build, interrupted/resumed build and `test_second_complete_build_makes_zero_embedding_calls`. Reject altered stored text or filter metadata against the catalog. Missing/replaced original PDFs or altered page caches must fail before generation.
- [ ] **Step 2 - Run RED:** `uv run --locked pytest tests/rag/test_index_lifecycle.py tests/rag/test_dense_retrieval.py --basetemp=.pytest-tmp/p2 -q`.
- [ ] **Step 3 - Implement staged index/catalog lifecycle and retrieval.** Publish a completion manifest atomically only after validating expected IDs/count, text/metadata joins and dimensions. Resume an incomplete compatible build; never expose it to queries or overwrite a different complete fingerprint. Reopen validation checks completion/catalog integrity. Confirm candidate content/provenance against the catalog and selected original sources before generation.
- [ ] **Step 4 - Run GREEN:** the same tests on local temporary Chroma, with socket blocking and default embeddings disabled. Re-run existing source/cache/isolation tests. Approximate search repeatability is measured, not inferred solely from a seed; persisted candidate pools provide exact replay.
- [ ] **Step 5 - Common gate and commit:** `feat: persist and query provenance-validated baseline indexes`.

## Task 6: Claude-aware token counting and bounded source packing

**Files:** Table row 6.

**Interfaces:** `EvidenceSlice(evidence_id, chunk_id, document_id, page_index, source_spans, text, source, score, diagnostics)`; `EvidencePacket(slices, token_count, dropped_ids, limitations)`; `pack_evidence(candidates: tuple[RetrievalCandidate, ...], pages: PageRepository, request: QueryRequest, counter: TokenCounter, context: CallContext, config: BaselineConfig) -> EvidencePacket`; `ClaudeTokenCounter` implements the Task 1 port using a configured Anthropic counting client with `max_retries=0`.

Counting is a traced, known-free network operation in live mode and a fake in CI. Cache counts by model and exact counted payload. Count labels/headings/separators; trim only already-covered source intervals, retaining novel rows/years and mapping every remaining fragment to its original page. Evidence IDs hash chunk ID plus retained spans. A quote cannot cross an inserted separator. Retain headings already present in selected evidence; expose missing-heading/table-boundary risks instead of reconstructing columns. Respect `request.top_k`, capped by 15, with default 5; the token ceiling always applies.

- [ ] **Step 1 - Write failing packing/counting tests**, including:

```python
assert packet.token_count <= 3500
assert len({s.chunk_id for s in packet.slices}) <= request.top_k
assert packet.slices[0].page_index == 0
assert "2021" in packed_text and "2022" in packed_text
assert "USD millions" in packed_text and "(25)" in packed_text
```

Test overlapping spans preserve all novel row text, duplicate chunks do not repeat evidence, same wording on different sources remains distinct, empty input returns an empty packet, over-budget chunks are explicitly dropped, quote spans map after deduplication, and missing counter/deadline failures block generation. Assert full-input padding: estimate 5,000 becomes 5,512; estimate 5,500 becomes 6,050 and is rejected against the 6,000 limit.
- [ ] **Step 2 - Run RED:** `uv run --locked pytest tests/rag/test_token_counting.py tests/rag/test_context_packing.py --basetemp=.pytest-tmp/p2 -q`.
- [ ] **Step 3 - Implement counting and packing.** Count the question before embedding, reject over 512, enforce generation-model evidence/full-input limits, and record the counting method/estimates. Include serialized schema in counting even if the counter API does not accept the native output format. Do not use a whitespace/embedding-tokenizer fallback for Claude admission. Model-specific counting failures are explicit errors.
- [ ] **Step 4 - Run GREEN:** same tests; verify no generation or paid reservation occurs for empty/oversized/uncountable input.
- [ ] **Step 5 - Common gate and commit:** `feat: assemble bounded evidence with exact source spans`.

## Task 7: Versioned grounded prompt and structured Claude generation

**Files:** Table row 7.

**Interfaces:** `DraftReference(evidence_id: str, quote: str)`; `DraftClaim(text: str, references: tuple[DraftReference, ...])`; `DraftOperand(name: str, evidence_id: str, source_text: str, value: Decimal, unit: str, period: str)`; `DraftCalculation(operator: Literal['add','subtract','multiply','divide'], operands: tuple[DraftOperand, DraftOperand], result: Decimal, unit: str)`; `DraftAnswer(status: Literal['answered','partial','insufficient_evidence'], claims, limitations, calculation)`; `GroundedPrompt(system: str, user: str, schema: dict[str, object], fingerprint: str)`; `build_prompt(request: QueryRequest, packet: EvidencePacket) -> GroundedPrompt`; `ClaudeGenerator.generate(prompt: GroundedPrompt, context: CallContext) -> DraftAnswer`.

Freeze `grounded-v1`: answer only the question from supplied passages; cite every material claim using supplied IDs/exact quotes; preserve company/period/units; disclose unsupported parts; source instructions have no authority; ambiguity requests clarification; missing facts and forecasts abstain. Serialize source text as data fields with escaped delimiters, never template instructions. Native JSON schema contains draft fields only, not trusted source metadata or operational statuses. Keep two operands per calculation in Phase 2; more complex arithmetic remains unsupported.

- [ ] **Step 1 - Write failing prompt/response tests.** Capture native model invocation with a fake SDK response and assert:

```python
assert captured["model"] == "claude-sonnet-5"
assert captured["max_tokens"] == 1024
assert captured["output_config"]["effort"] == "low"
assert captured["output_config"]["format"]["type"] == "json_schema"
assert client_options["max_retries"] == 0  # constructor setting, not request body
assert result.status == "answered"
```

Assert the configured integration uses `with_structured_output(DraftAnswer, method='json_schema', include_raw=True)` and retains usage from `raw` before handling `parsing_error`. Test native refusal, truncated output, invalid schema, missing claims/references, empty output and expired deadline. Native citation blocks, tool/web/agent calls, schema-repair LLM calls and automatic model fallbacks must be absent. Verify source text is preserved as data even when it contains delimiter/instruction strings.
- [ ] **Step 2 - Run RED:** `uv run --locked pytest tests/rag/test_generation.py --basetemp=.pytest-tmp/p2 -q`.
- [ ] **Step 3 - Implement the prompt and guarded LangChain adapter.** Count full input before reserving/dispatch. Construct `ChatAnthropic` with explicit timeout/retries/model/max output, use SDK-native transport types, set low effort and bound thinking plus response together. No sampling parameter is sent if unsupported by the configured model. Actual usage is recorded on refusal/parse failure. Return safe typed failures; do not retry validation failures through another paid model call.
- [ ] **Step 4 - Run GREEN:** same tests, comparing serialized prompt/config fingerprints and exact transport attempt counts. Keep deterministic fakes distinct from real prompt-injection/semantic-support evidence.
- [ ] **Step 5 - Common gate and commit:** `feat: generate grounded structured answer drafts`.

## Task 8: Claim-to-source citation integrity and bounded Decimal calculations

**Files:** Table row 8.

**Interfaces:** `validate_draft(draft: DraftAnswer, packet: EvidencePacket, pages: PageRepository, usage: UsageMetrics) -> Answer`; `validate_calculation(calculation: DraftCalculation, packet: EvidencePacket, pages: PageRepository) -> Calculation`. Build public `Evidence` only from packet/catalog/manifest fields. Render `answer_text` by joining validated claim text with inline citation labels; do not append uncited model prose.

Every quoted reference must match a supplied evidence ID and lie wholly within one supplied exact source span and its unchanged cached page. Resolve metadata on the server. A real quote elsewhere in the filing, another year, another page, or an omitted portion of an overlapping chunk is invalid. Preserve extraction warnings as relevant limitations. Integrity checks do not certify semantic support.

- [ ] **Step 1 - Write failing validation/calculation tests**, including:

```python
assert answer.status == "answered"
assert answer.citations[0].page_index == 0
assert answer.citations[0].source == original_manifest_source
assert calculation.result == Decimal("-25")
with pytest.raises(FinsightError, match="citation_validation_failed"):
    validate_draft(wrong_span_draft, packet, pages, usage)
```

Add `test_real_quote_on_wrong_year_span_rejected`, `test_every_claim_requires_reference`, `test_unsupplied_id_never_resolves`, `test_invalid_citation_does_not_leave_success_text`, `test_partial_requires_missing_part_limitations`, and `test_abstention_carries_no_fact_citations_or_calculation`. Arithmetic tests assert exact supplied operand text/value, preserved scale/year, parentheses negatives and grouping commas; reject scientific/code expressions, division by zero, incompatible units/unsupported periods, invented operands and mismatched finite results. `test_explicit_cross_period_subtraction_keeps_each_cited_year` proves an expressly requested year-over-year comparison is supported rather than requiring all operands to share a year.
- [ ] **Step 2 - Run RED:** `uv run --locked pytest tests/rag/test_citation_validation.py tests/rag/test_calculation.py --basetemp=.pytest-tmp/p2 -q`.
- [ ] **Step 3 - Implement deterministic mapping and arithmetic.** Parse only explicit financial numeric literals (`1,000`, `-25`, `(25)`, decimal forms); scales must come from supplied evidence and match declared units. Addition/subtraction require identical units; explicitly requested comparisons may use different individually verified periods. Multiplication/division allow one dimensionless operand, or same-unit division to a dimensionless ratio. Reject other dimensional combinations. Use Decimal precision 28, no Python expression execution, no silent rounding or percent/percentage-point conversions. Recompute supported operations and populate the existing public `Calculation` with a server-rendered expression.
- [ ] **Step 4 - Run GREEN:** same tests plus existing `tests/test_contracts.py`. Preserve actual usage when a draft fails; map validation failures to explicit codes in Task 9.
- [ ] **Step 5 - Common gate and commit:** `feat: validate claim citations and financial calculations`.

## Task 9: Shared LangChain service, traces and keyless CLI smoke

**Files:** Table row 9; add `finsight-rag = 'finsight.cli:main'` to `pyproject.toml`; extend `.github/workflows/ci.yml` with CLI help and synthetic RAG smoke. Keep existing smoke/ingestion/audit commands.

**Interfaces:** `BaselineApplicationService.answer(request: QueryRequest) -> Answer` implements the existing protocol. Constructor injects config, retriever, counter, generator, page repository, trace recorder and a monotonic clock. `create_application(settings: Settings, config: BaselineConfig, *, allow_paid: bool = False) -> BaselineApplicationService`; `JsonlTraceRecorder(root: Path)` implements `TraceRecorder`; `cli.main(argv: list[str] | None = None) -> int`; `run_rag_smoke() -> dict[str, object]`.

Compose `validate -> embed/retrieve -> pack -> grounded generation -> validate draft -> Answer` as LangChain runnables/branches. Empty evidence and explicit unsupported-scope requests exit without generation. Map known errors to safe `Answer(status='error', error=AppError(...))`; unexpected errors use `internal_error` and safe messages, retain trace/usage, and never reveal credentials. All admitted success/error/abstention paths produce one terminal trace. The recorder atomically writes one JSONL file per run ID, refuses conflicting overwrites, and records final `Answer` plus immutable input/config identity. A trace write failure returns `trace_write_failed` with retained usage/ledger evidence and never repeats generation. Invoke with explicit callbacks and `langsmith.tracing_context(enabled=False)` even if the parent process enables tracing; disable Chroma telemetry.

- [ ] **Step 1 - Write failing service/CLI/isolation tests**, including:

```python
assert isinstance(service.answer(request), Answer)
assert len(recorder.records) == 1
assert recorder.records[0].run_id == recorded_run_id
assert generator.calls == 0  # empty evidence fixture
assert result["check"] == "synthetic_rag_roundtrip"
assert result["provider_network_calls"] == 0
```

Test `test_source_prompt_injection_never_executes_or_changes_control_fields`, `test_poisoned_gold_cannot_change_index_or_prompt`, `test_contract_runtime_imports_exclude_evaluation`, `test_trace_write_failure_does_not_retry_model`, wrong-scope clarification, unsupported semantic/rerank, timeout/budget/citation failures with usage retained, forced inherited tracing with no socket activity, both-key redaction, and installed CLI operation from an empty cwd with absolute input paths. Verify baseline dispatch passes question/fair filters only; candidate ordering and selected spans survive tracing.
- [ ] **Step 2 - Run RED:** `uv run --locked pytest tests/rag/test_application.py tests/rag/test_rag_cli.py tests/test_annotation_isolation.py tests/test_runtime.py --basetemp=.pytest-tmp/p2 -q`.
- [ ] **Step 3 - Implement factory, composition, trace sink and CLI.** CLI commands are `prepare-tokenizer`, `preflight`, `budget-init`, `build-index`, `ask`, and `smoke --synthetic`. `budget-init` creates only the approved fixed budget identity/caps and refuses reset/overwrite. `preflight` performs no paid embedding/generation. `build-index`/`ask` require explicit `--allow-paid`, both rate/ledger validation and relevant credentials; synthetic smoke uses injected local fakes and requires neither. CLI output is a JSON envelope with `answer` and `trace_id`; service return remains `Answer`. Exit 0 for answered/partial/abstention, 1 for operational errors, 2 for command/argument errors. Use ignored local paths and sanitized summaries.
- [ ] **Step 4 - Run GREEN:** the focused suite, all existing unit tests, installed `finsight-rag --help`, `finsight-rag smoke --synthetic`, existing CLIs and isolated wheel smoke. Injection fixtures establish data/control separation and validation behavior, not immunity of a real model to all injections.
- [ ] **Step 5 - Common gate and commit:** `feat: expose the traced baseline RAG application and CLI`.

## Task 10: Real-source acceptance, budgeted development smoke and review evidence

**Files:** Table row 10; add `docs/decisions/0003-baseline-rag.md`, `docs/reviews/phase-2.md`, `results/phase-2-baseline-smoke.md`; update `README.md`, `docs/experiments.md`, `docs/engineering-journal/phase-02.md`, `docs/prompt-registry.csv` and `.env.example` where needed. No holdout campaign or Phase 4 scoring implementation.

**Interfaces:** `evaluation.smoke.select_development_cases(questions: Path, corpus: CorpusManifest, split_dir: Path, count: int = 3) -> tuple[SmokeCase, ...]` uses the existing benchmark loader and split-policy replay internally and selects first stable IDs from three distinct companies in frozen development membership. `SmokeCase(question_id: str, request: QueryRequest)` lives only in `evaluation.smoke`; its request contains question text only, with no benchmark-derived filter. The harness records IDs privately and dispatches only `case.request` to the service. Never pass source labels/pages/answers to the service. Synthetic safety negatives are identified separately from official cases. Add keyless selector tests in `tests/test_rag_smoke_selection.py`.

- [ ] **Step 1 - Write opt-in acceptance tests before paid execution.** `tests/test_rag_integration.py` has explicit `integration` markers and separates local-source checks from provider checks. Assert all 53 source hashes/cache identities unchanged, complete expected index membership, vectors/config/source identities, runtime-gold isolation and unchanged split files. Missing paid opt-in explicitly skips provider tests with a reason. Once paid opt-in is requested, missing credentials/rates or a source/budget/model/config failure fails rather than silently skips.
- [ ] **Step 2 - Run RED/GREEN for the smoke selector using synthetic benchmark fixtures:** `uv run --locked pytest tests/test_rag_smoke_selection.py --basetemp=.pytest-tmp/p2 -q`. Assert exactly three distinct-company development IDs, no holdout membership, no annotation fields in returned `QueryRequest`, and deterministic repeated membership. Record missing-selector RED before implementing it and passing GREEN afterward. Run the keyless whole-suite gate before any paid operation.
- [ ] **Step 3 - Perform public artifact/provider preflight.** Use `finsight-rag prepare-tokenizer --config configs/runtime/phase-2-baseline.json`. Verify the three artifact hashes/revision and actual native tokenizer behavior. Validate account model access/current rates and provider prefix behavior from metadata first; record rate source/time/snapshot and do not commit credentials. Initialize the ledger once with `finsight-rag budget-init --ledger data/cache/budget/testing.sqlite3`. Perform no paid capability probe at this step; validate actual dimensions/usage on the first authorized embedding batch after Step 4.
- [ ] **Step 4 - Preflight the full corpus and smoke allowance before indexing.** `finsight-rag preflight --config configs/runtime/phase-2-baseline.json --manifest data/manifests/financebench-selected.json --pdf-root source-data/pdfs --page-cache data/cache/pages --rates data/cache/budget/rates.json --ledger data/cache/budget/testing.sqlite3`. Report actual token/chunk counts and conservative cost of all uncached embeddings plus four question runs with eligible retries. Confirm it fits both remaining allowances; if not, stop and report the conflict without shrinking the corpus, changing models or increasing caps.
- [ ] **Step 5 - Build once, then smoke.** `finsight-rag build-index` uses the same explicit paths plus `--index-root data/indexes --allow-paid`. Use the opted-in acceptance harness as the single campaign executor for the three selected development questions and one clearly out-of-corpus/future-prediction negative through the shared service; do not repeat them manually with `ask`. Primary smoke uses full-corpus scope without gold filters. All actual attempts, including refusals and failures, count against the ledger. Matching completed campaign records may be validated/replayed without new paid calls and must be labeled replay; new runs must pass a fresh full estimate. Do not buy extra answers just to obtain a success. Optionally inspect a synthetic document-injection provider case only if its separate estimate fits; keep it separate from official corpus/benchmark results.
- [ ] **Step 6 - Inspect and report actual results.** Verify original PDF/page/quote mappings, reported company/year/units and any calculation for each answered claim; document unsupported/incorrect claims rather than declaring semantic faithfulness from citation validity. Record source/index/config/prompt/rate fingerprints, selected IDs, paid/cached call counts, latency, usage availability, reserved/estimated spend, unknown costs, abstentions and limitations. Sanitized summary may include public benchmark IDs but no gold answers/evidence/page annotations. Keep raw question/answer/source traces ignored. No aggregate accuracy/95% claim from this smoke.
- [ ] **Step 7 - Run final gates and review.** Execute the commands below; record actual counts and skips. Build/install a runtime wheel into an isolated temporary environment, exercise CLI help/synthetic smoke from an empty cwd, and confirm runtime imports never load evaluation. Run one independent whole-branch review if authorized by the selected execution workflow; correct findings with regression evidence. Update ADR/journal/review evidence. The real-source/provider smoke is an exit gate: if blocked or not run, report Phase 2 incomplete.
- [ ] **Step 8 - Commit reviewed acceptance/docs only after their gates:** `docs: record baseline RAG acceptance and limitations`. Stop for human phase-result review; do not push/open PR/merge without explicit publication authorization.

## Common commit gate and final verification

For every task commit: inspect `git status`, stage only that task's intended paths, run lint/format/unit checks and relevant smoke checks, update the journal/registry with actual RED/GREEN results, and inspect staged diffs for credentials/generated artifacts. No commit changes raw PDFs, benchmark annotations, frozen splits, original caches or unrelated modules. Artifacts created by new code remain under ignored paths.

```powershell
uv lock --check
uv sync --locked --group dev
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest -m 'not integration' --basetemp=.pytest-tmp/p2 -q
uv run --locked finsight-smoke
uv run --locked finsight-ingest --help
uv run --locked finsight-benchmark-audit --help
# Add after Task 9:
uv run --locked finsight-rag --help
uv run --locked finsight-rag smoke --synthetic
uv build
git diff --check
```

Only execute opted-in real checks with explicit source paths and the paid gate configured:

```powershell
uv run --locked pytest -m integration tests/test_corpus_integration.py --basetemp=.pytest-tmp/p2-corpus -q
uv run --locked pytest -m integration tests/test_rag_integration.py --basetemp=.pytest-tmp/p2-real -q
```

Credentials are configured locally as `FINSIGHT_NEBIUS_API_KEY` and `FINSIGHT_ANTHROPIC_API_KEY`; never paste them into chat or CLI arguments. `FINSIGHT_RAG_PAID_TESTS=1` is the additional provider-test opt-in; integration selection alone cannot spend. The ledger, current verified rates and phase/global allowance checks still apply. Test reports distinguish no-key synthetic tests, local-corpus checks, free metadata/counting calls, paid model calls and explicit skips.

Before declaring Phase 2 complete: baseline and error/abstention flows work end to end; all source mappings and isolation tests pass; original data/splits remain unchanged; an actual real-source/provider smoke has evidence; all available calls/costs are accounted for; accepted limitations and review findings are recorded. Remote CI is unknown until an approved publication actually runs it.

## Self-review coverage and execution handoff

Spec coverage: intent/bounds/contracts -> Task 1; money/retry/restart safety -> Task 2; source/token/table boundaries -> Task 3; provider/cache integrity -> Task 4; full-source/index/filter/score lifecycle -> Task 5; token/dedupe/context control -> Task 6; prompt/structured drafts -> Task 7; citations/arithmetic/status rules -> Task 8; same-service/trace/CLI/injection/leakage/CI -> Task 9; source/provider acceptance, honest reporting and phase delivery -> Task 10. Later-phase diagrams remain extension points, not executable tasks.

Inline self-review checked matching port/type names across task consumers/producers, named tests for all five Review Focus conditions, spec coverage, and dispatch through Task 2 for paid operations. It clarified cache-key signatures, final-answer trace persistence, cross-period arithmetic and one campaign executor. The structural audit confirms ten tasks, 53 unchecked steps and nine syntax-valid future test examples. Preserve `answer(...) -> Answer`, raw usage before parsing, score direction, source span identity and all three budget ceilings. Test fragments define assertions; they are not claims of implemented/passing tests. Dependency resolution does not replace installation/constructor/Windows CI checks.

Recommended execution: **Native**, implementing these tightly related tasks sequentially in this checkout, with the independent final review prescribed by the chosen workflow. This keeps producer/consumer interface changes in one context and avoids fresh implementation-agent contexts per task. **Subagent-driven** execution is an available alternative with per-task implementer/reviewer handoffs. Neither method has been selected yet. Request plan review and execution-method selection before implementation.

References checked for version-specific planning: versioned PyPI metadata linked in the pin table; published `langchain-anthropic==1.7.6`/`langchain-chroma==1.1.0` wheel source; [Qwen model/tokenizer card](https://huggingface.co/Qwen/Qwen3-Embedding-8B); [Nebius embedding request/usage fields](https://docs.tokenfactory.nebius.com/api-reference/inference/create-embeddings); [Claude counting estimates/pricing](https://platform.claude.com/docs/en/build-with-claude/token-counting); [Claude output/thinking cost bounds](https://platform.claude.com/docs/en/build-with-claude/thinking-steering-and-cost). ContextHub remains unavailable; no claim of ContextHub validation is made.
