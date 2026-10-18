# Phase 2 baseline evidence-first RAG design

- Recorded: 2026-10-18, IST.
- Source of truth: [project.md](../../../project.md).
- Branch: `feat/phase-2-baseline-rag`.
- Base: merged Phase 1, `6db76b2c887e86aca6fa58ab08706443b0bd637b`.
- Status: conversational architecture approved by the human in P2-004. This
  written specification requires review before the implementation plan is written.
- Scope: design documentation only at this checkpoint. No product dependency,
  runtime implementation, paid request, push, PR, or merge is part of this change.

## 1. Intent and success criteria

FinSight helps junior financial analysts answer questions from the approved
financial-report PDFs. Phase 2 produces a fixed-chunk baseline that returns a
source-grounded answer, a supported partial answer, an explicit abstention, or a
structured operational error. The CLI, future evaluator, and future Streamlit UI
use the same typed application service.

The human selected a framework-led architecture to support future scenarios and
comparisons. LangChain composes the stages; FinSight retains financial provenance,
evidence packing, citation integrity, experiment controls, and spending policy.
The human has API keys and credits for both Nebius and Claude. The shared testing
budget is USD 5.00, with a USD 4.00 working allowance and USD 1.00 untouched reserve.
This allowance is cumulative across providers, processes, runs, and later testing
phases; it does not reset at a phase boundary.

Phase 2 succeeds when synthetic end-to-end checks pass and a small real,
development-only smoke campaign demonstrates grounded output and abstention with
verifiable source mappings and an honest usage/latency trace. The project targets
of 95% faithfulness and sub-eight-second median latency are not Phase 2 guarantees.

## 2. Scope and preserved foundations

Reuse the existing Python 3.12 modular monolith, Pydantic v2 contracts,
`ApplicationService.answer(QueryRequest) -> Answer`, validated manifests,
`ingestion.cache.load_cached`, source-policy decisions, and offline evaluation
isolation. Work from the merged base on the discrete Phase 2 branch.

- Common corpus: 53 canonical filings, 9,504 pages; keep original files unchanged.
- Source fingerprint:
  `7376d03d8183077b92ed98b8c4e3a584fefd02202b75feba82cdc13b2519fad3`.
- Frozen questions: 36 development, 16 holdout; seed 42 and existing membership.
- Split fingerprint:
  `e6ec481633654b779721f1d94c7aa05a65e43c9f37deae177819658d2b665431`.
- Nine scanned appendix pages have no extractable text. Preserve their coverage
  diagnostics; they produce no text chunks. Nine additional empty pages are blank.
- Carry forward the 618 ActualText-position warnings and the nine exact-source
  readable-encryption exceptions. Nonempty text is not certified complete.
- Existing flattened table text and geometry do not establish table-cell semantics.

Phase 2 includes fixed chunking, guarded embeddings, persistent indexing, dense
retrieval, bounded context, structured generation, citation checks, abstention,
usage traces, and a CLI. Semantic chunking and local reranking belong to Phase 3;
comprehensive scoring and failure analysis to Phase 4; Streamlit to Phase 5.
OCR, new companies, agent loops, automatic ingestion, cloud deployment, and
unrelated refactoring remain outside this phase.

## 3. System architecture

```text
CLI [P2]          Benchmark runner [P4]          Streamlit [P5]
    |                       |                        |
    +-----------------------+------------------------+
                            |
                     Typed QueryRequest
                            |
            +-----------------------------------+
            | ApplicationService.answer(request)|
            | LangChain runnable composition    |
            | + FinSight validation stages      |
            +-----------------+-----------------+
                              |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
 Retrieval/context    Guarded provider calls   Citation validation
          |                   |                   |
          v             +-----+------+            |
 Local Chroma           |            |            |
 + chunk catalog     Nebius        Claude         |
                     embeddings    generation     |
          |             |            |            |
          +-------------+------------+------------+
                              |
                     Typed Answer + RunTrace

Shared: versioned configuration, source/index fingerprints,
persistent spending ledger, local caches, redacted local traces.
```

LangChain runnable sequences and conditional branches compose explicit stages.
Use its standard embedding interface, Anthropic structured-output integration,
and Chroma integration behind application-owned boundaries. A guarded Nebius
adapter implements the embedding interface and preserves provider usage metadata.
Callbacks collect observations; the dispatch boundary enforces spending before
network requests. Callback logging alone is not a spending guard.

The public service still returns `Answer`, not a tuple or a framework message.
Inject a typed trace recorder into the service; every invocation emits a correlated
`RunTrace` to that recorder. CLI and benchmark callers can inspect the trace they
recorded. Diagrams showing answer plus trace describe those two outputs together,
without changing the established `answer(request) -> Answer` interface.

Keep contracts independent of framework/provider imports. Explicitly validate
conversions between Pydantic source/chunk models and framework documents. Chroma
stores searchable text, vectors, stable IDs, and filterable scalar metadata; a
validated local chunk catalog holds full spans and provenance. Search results are
joined to that catalog and manifest rather than trusting model-generated metadata.

Proposed providers are Nebius `Qwen/Qwen3-Embedding-8B` and Anthropic
`claude-sonnet-5`. Before the first paid request, check account model availability,
supported features, current pricing, and returned embedding dimension. Freeze the
configured identifiers, query/document instructions, tokenizer revision, dimension,
normalization, distance metric, prompt version, and software versions in run/index
metadata. Record any unavailable hosted revision as unknown; do not imply immutable
provider weights. An unavailable model or incompatible dependency requires a
reviewed configuration change, not a silent substitution.

Exact compatible dependency pins belong in the implementation plan after checking
Python/Windows compatibility. No dependency installation is authorized by this
documentation checkpoint.

## 4. Offline preparation and index lifecycle

```text
Original PDFs + source manifest [existing]
                 |
       Verify source/cache identities
                 |
       Validated page cache [existing]
                 |
       Fixed chunker: 400 / 60 [P2]
                 |
       Validated chunk catalog
                 |
       Embedding cache lookup
          |              |
         HIT            MISS
          |              |
          |       Spending reservation
          |              |
          |       Nebius embedding call
          |              |
          |       Validate + cache vectors
          |              |
          +-------+------+
                  |
         Staged local Chroma index
                  |
         Verify expected IDs/counts/config
                  |
         Publish complete index manifest

Same page cache --> Semantic chunker/index [P3]
```

The fixed baseline uses page-local windows with a hard maximum of 400 source-text
tokens and a target overlap of 60. Overlap may be smaller at page boundaries or
where required to preserve a valid character boundary. Measure chunks with the
pinned embedding tokenizer. Never decode partial token bytes into altered source
text: source spans use half-open Unicode character offsets into unchanged pages,
and the chunk content must reproduce those source substrings exactly.

Before building an index, verify the original PDFs against the manifest and use
only cache records validated for those identities. A source mismatch or missing
required source blocks preparation; the index must not certify unverified inputs.

Chunk identity includes document/source identity, page/span, strategy, and chunking
configuration. Validate token limits, span ordering, repeated-text offsets, IDs,
and deterministic repeatability. Empty/error pages and malformed spans cannot
silently produce chunks. Fail preparation on source/cache integrity errors.

Preserve years, units, signs, row labels, and footnotes in retained text. Record
boundary risks when splitting financial tables or separating headings/values.
Keep available headings within packed evidence, with their proven spans and token
costs. Do not infer table columns, rewrite values, or invent missing headers. If
selected evidence cannot establish the necessary value/year/unit relationship,
the answer must disclose the gap or abstain. Table semantic correctness remains a
review/evaluation concern, not a consequence of passing span checks.

Embedding cache keys cover the exact submitted text, provider/model identity,
document-versus-query role, instructions, and embedding configuration. Check vector
count, input/output correspondence, finite values, and dimension before persisting.
Successful batches are durable so interruption does not repeat completed calls.

Index identity additionally includes source/extraction/chunking/catalog fingerprints,
distance metric, and relevant software versions. Build in a distinct staged
directory; only a validated completion manifest makes it queryable. Incomplete
builds remain resumable and cannot serve as a complete-corpus index. Configuration
mismatches fail explicitly rather than mixing incompatible vectors. Generated
indexes, catalogs, and caches remain ignored.

## 5. Online flow and bounded execution

```text
QueryRequest
     |
Validate input + resolve scenario/index
     |
Query embedding cache --> guarded Nebius call on miss
     |
Apply explicit metadata filters; dense search up to 15
     |
Validate source joins; preserve original ranks/scores
     |
Ranking stage: dense order [P2] / optional local rerank [P3]
     |
Deduplicate spans; pack up to 5 chunks / 3,500 evidence tokens
     |
     +-- No usable evidence --> insufficient_evidence + trace
     |
Grounded prompt + structured draft schema
     |
Spending guard --> Claude generation
     |
Validate draft, claims, quotes, source mappings and calculations
     |
Assemble Answer + RunTrace

Operational/schema/integrity failure --> structured error + trace
```

Entry points validate question length and explicit company/document/period filters.
The proposed Phase 2 limits are 512 question tokens, 3,500 packed evidence tokens,
6,000 total estimated input tokens including instructions/schema, and 1,024 maximum
billable output/reasoning tokens. Evidence and full-prompt counting use a documented
generation-model counting method with a conservative overhead allowance. These
budgets are independent of the embedding tokenizer's chunk count. If the bounded
request cannot be formed safely, stop before calling the provider.

The primary benchmark searches the full 53-filing corpus. Only user-supplied or
fairly declared experiment filters can narrow it; gold document names and annotated
pages never supply filters. Validate filter combinations and apply them in search,
before selecting candidates. Preserve raw ordered candidates, score kind/direction,
the applied filters, and explicit tie-breaking policy. Similarity is not confidence.

Phase 2 accepts the fixed/dense/no-rerank scenario only. Requests selecting semantic
chunking or reranking fail as unsupported; they do not silently run the baseline.
Select at most `top_k` chunks, default 5 and bounded by the existing request
contract; enforce the evidence budget regardless of that selection limit.

Deduplicate exact chunks and overlapping source spans without erasing distinct
years or rows. Every packed passage has an evidence ID, chunk/document identity,
page index, exact source spans, source metadata, and relevant extraction diagnostics.
Count source labels and any retained heading text in the evidence allowance.

Use an explicit 20-second timeout per provider attempt and a 45-second application
deadline. Failures return typed error codes with retryability information, not
misleading abstentions. These are execution bounds, not latency achievements.

## 6. Generation, citations, calculations, and status semantics

The versioned prompt separates system instructions, the user's question, and
delimited source text. Documents are untrusted data. The generator has no tools,
network access, or authority to follow document instructions. It must use supplied
evidence, preserve units/periods, and disclose unsupported parts.

Generate an internal Pydantic draft rather than asking the model to populate the
public `Answer` with trusted metadata. The draft contains status, claim text,
evidence references with exact source quotes, limitations, and an optional bounded
calculation. Each material claim requires at least one evidence reference. The
application renders final answer text from validated claims and resolves public
citations from the manifest/catalog; unsupported free-form summary text is not
appended. Draft status cannot invent an operational error or bypass validators.

Use LangChain's native Anthropic JSON-schema structured-output mode, while retaining
raw usage and refusal/truncation information. Do not enable Anthropic native
citation blocks alongside JSON-schema output; they are incompatible. Quote and
page checking remains application-owned and provider-independent.

For every citation, require a supplied evidence ID, matching chunk/document/page,
and a nonempty exact quote inside a supplied source span and the corresponding
unchanged cached page. Citation checks must reject plausible but unsupplied IDs,
quotes elsewhere in the filing, wrong pages, and fabricated metadata. A valid
quote mapping does not prove semantic support for a claim. Semantic support is
reviewed separately in Phase 4 and development smoke inspection.

Optional arithmetic is limited to finite Decimal addition, subtraction,
multiplication, and division with explicit operands and units. Recompute supported
operations; never execute a model expression with Python evaluation. Require cited
operand text and consistent declared units/periods; reject division by zero and
nonfinite or inconsistent results. If the operands or required financial
relationships cannot be verified, do not return an answered calculation. Broad
numeric-answer normalization and correctness scoring remain Phase 4 work.

Statuses preserve the existing public contract:

- `answered`: validated claim text and citations; required evidence is present.
- `partial`: only supported claims, citations, and explicit missing-part limitations.
- `insufficient_evidence`: no factual answer, citations, or calculation. Ambiguous
  scope can return a clarification message here instead of guessing a company/year.
- `error`: a structured operational/schema/citation/calculation failure, with an
  error code and safe message. Do not strip invalid citations and return the same
  unsupported answer as successful.

Preserve returned usage even when answer validation fails. A source warning is
surfaced as a limitation where relevant; it is not automatically proof that every
claim on that page is wrong or unsupported.

## 7. Spending, caching, and observability

```text
Proposed paid request
        |
Read persistent ledger + outstanding reservations
        |
Estimate conservative maximum request cost
        |
Working allowance or Phase 2 allowance exceeded?
        |
        +-- YES --> budget_exceeded; no provider dispatch
        |
        +-- NO --> reserve allowance atomically
                         |
                    execute one request
                         |
                    reconcile returned usage
                         |
                    persist ledger + trace
```

The approved testing ceiling is USD 5.00 shared by both providers. The working
allowance is USD 4.00; USD 1.00 remains untouched. Phase 2 has a sub-allowance of
USD 0.75 for indexing and real smoke runs, included in the shared allowance. Do not
auto-expand either allowance or reset the ledger for a new process, run, or phase.
The Phase 2 limit is a ceiling, not a target spend or a prediction of index cost.

Use a local ignored SQLite ledger with transactional reservations. Initialize its
approved budget identity explicitly, preserve it across restarts, and fail on
corruption/inconsistent totals. A missing ledger after recorded activity requires
reconciliation, not a fresh zero-spend assumption. Initial paid work is serial.

Before every actual embedding/generation dispatch, reserve conservative maximum
cost using current configured rates, full submitted input, bounded billable output,
and pricing-specific overhead. The proposed call must fit both remaining Phase 2
and global working allowances. Missing pricing or an unbounded billable component
blocks execution. Reconcile returned tokens/cache categories and keep the rate
snapshot and cost-estimation method with the trace.

SDK/framework automatic retries are disabled. The application may retry once for
an explicit transient 429/502/503/504 response within the deadline, with a new
reservation. An uncertain timeout/disconnection retains its full reservation and
does not trigger an automatic retry. Unknown usage/cost is recorded as unknown,
not zero; unresolved reservations continue to count against the allowance.

Use cached document/query embeddings. Reuse persisted retrieval pools and completed
run records for explicit replay/resumption. Generation replays are labeled cached
and cannot count as new measured provider calls or fresh-call latency samples.
Never cache evaluation gold or reuse a response under a different prompt, context,
question, model, filter, or experiment identity.

Preflight the full proposed batch/campaign before starting it. A 52-question,
four-arm generation campaign would involve 208 answers before retries; do not
assume it fits this budget. Begin with a small representative development smoke
set, reuse deterministic retrieval for debugging, and preserve later evaluation
allowance. Any reduced campaign must declare its actual question IDs and incomplete
coverage; never silently report a partial campaign as a full comparison.

The ledger governs FinSight's calls, not unrelated account activity. Provider
invoices are authoritative; locally estimated spend is not certified billed cost.
The reserve protects against estimation uncertainty, not an absolute billing
guarantee. Review provider balances before paid campaigns without exposing keys.

Trace request/run IDs, source/index/config/prompt identities, filters, ordered
retrieval scores, packed evidence spans, stage timings, provider attempts, available
token usage, cache/replay flags, reservations, estimated cost, and failures. Keep
detailed traces ignored and local; commit sanitized summaries only. Redact both
providers' credentials and safe error paths. No hosted tracing service is required.

## 8. Experiment and evaluation extension

```text
                   Same corpus and embedding model
                              |
                   +----------+----------+
                   |                     |
               Fixed index          Semantic index [P3]
                   |                     |
              Candidate F           Candidate S
               /       \             /       \
          A: dense   C: rerank   B: dense   D: rerank
               \       /             \       /
                +-----+---------------+-----+
                              |
            Same context policy / prompt / generation model
                              |
                   Retrieval and answer records
                              |
                   Evaluation-private gold join [P4]
                              |
                Measured summaries and failure analysis
```

A/C reuse exactly the same fixed pre-rank pool; B/D reuse exactly the same semantic
pre-rank pool. Preserve the 15-candidate ceiling, final context allowance, question
IDs, explicit scope, prompt, and generation model for the primary comparison. The
semantic chunker uses actual boundary/similarity grouping with a hard size limit,
and caches its embedding computations. The cross-encoder is local. Neither is
implemented or installed in Phase 2.

Only the evaluator reads benchmark answers, justifications, evidence quotes, or
annotated pages. It passes question text and fair explicit filters to the shared
service, then joins completed outputs to gold internally. Runtime modules cannot
import evaluation. Development may guide tuning; holdout is evaluated in one final
campaign after four-arm configuration freeze. Report shared-filing/small-sample
limitations and distinguish citation validity from semantic citation support.

Future model changes are separately named experiments. Extend a component factory
and versioned scenario configuration rather than duplicating pipeline logic.

## 9. Module responsibilities

```text
src/finsight/
  application.py    Typed service and LangChain composition
  contracts/        Framework-independent domain and trace models
  ingestion/        Existing manifest/extractor/cache; preserve behavior
  chunking/         Fixed chunker; later semantic strategy
  indexing/         Guarded embeddings, caches and index lifecycle
  retrieval/        Filtered dense search; later local reranking
  context/          Evidence spans, deduplication and token budgets
  generation/       Versioned prompt, draft schema and Claude adapter
  citations/        Source/quote/page/calculation integrity
  observability/    Persistent budget ledger, timings and safe traces
  evaluation/       Isolated offline benchmark/scoring
  ui/               Later Streamlit presentation only

configs/            Versioned runtime/scenario settings
data/cache/         Ignored pages, embeddings and spending ledger
data/indexes/       Ignored staged/complete indexes and chunk catalogs
results/traces/     Ignored detailed run records
results/            Sanitized measured summaries
docs/               Decisions, journal and review evidence
```

The implementation plan will map these responsibilities to exact files and typed
interfaces and pin compatible dependencies. It must preserve the established
Pydantic/stdlib-only contract boundary and the locked, keyless CI workflow.

## 10. Verification and phase exit

Tests must exercise actual behaviors and failure modes with synthetic sources,
fake providers, and local temporary indexes. Routine CI blocks network access and
uses no credentials or private PDFs.

- Fixed boundaries/overlap/max tokens, Unicode/repeated-text source mapping,
  financial signs/units/years, empty pages, stable IDs, and source diagnostics.
- Cache role/config separation, finite vector/dimension validation, interruption
  recovery, incompatible/partial index refusal, and repeat-build cache reuse.
- Explicit company/document/period filters, candidate counts/rank/score direction,
  no hidden benchmark filters, unsupported scenario refusal, and deterministic ties.
- Deduplication and bounded evidence/full prompt; preserve distinct rows/years.
- Draft validation, every material claim referenced, exact quote/span/page checks,
  fabricated/unsupplied citation rejection, prompt-injection source fixtures,
  ambiguity/unsupported questions, and valid answer/partial/abstention/error states.
- Supported Decimal operations and cited operands; zero division, nonfinite,
  inconsistent units/results, and executable expression rejection.
- Budget reservation before every attempt, cache hits without dispatch, retry bounds,
  restart/concurrent reservation safety, unknown-usage retention, and exhausted or
  corrupt ledger refusal. No hidden retries or automatic budget reset.
- Runtime/evaluation isolation, poisoned-gold independence, credential redaction,
  and a fake-provider end-to-end CLI run from an empty working directory.

Real tests are explicit opt-in integration checks. First inspect expected corpus
token volume and current rates without embedding. Only dispatch a small development
campaign that fits its reserved allowance. Record actual question IDs and outcomes,
source/index/config identities, quote mappings, cache behavior, latency, calls,
available tokens, and estimated cost. A skipped/blocked real smoke remains a failed
phase exit gate, not a completed RAG demonstration. Do not tune on holdout.

Before delivery run lint, format, unit tests, relevant CLI/build checks, and
secret/ignored-artifact checks. Update the engineering journal and decision record,
record exact commands/results, and request phase-result review. No claim of
faithfulness attainment or remote CI is allowed without actual evidence. Push/PR
publication and human merge remain separate explicit permissions.

## 11. Design rationale and references

The initial assistant proposal used direct provider adapters. The human selected
framework-led composition for future scenarios; this design adopts LangChain's
standard boundaries while preserving FinSight's correctness and spending rules.
A hosted vector service, separate application services, and extra runtime model
calls would add operational/spending work without serving this baseline gate.

Official documentation consulted during the design discussion on 2026-10-18:

- [LangChain runnable composition](https://reference.langchain.com/python/langchain-core/runnables/base).
- [LangChain embedding interface](https://docs.langchain.com/oss/python/integrations/embeddings).
- [ChatAnthropic integration and native structured output](https://docs.langchain.com/oss/python/integrations/chat/anthropic).
- [LangChain Chroma persistence and filtered/scored search](https://docs.langchain.com/oss/python/integrations/vectorstores/chroma).
- [Nebius Qwen model catalog](https://nebius.com/services/token-factory/models/qwen-models-inference).
- [Nebius embeddings API](https://docs.tokenfactory.nebius.com/api-reference/examples/create-embeddings).
- [Claude model identifiers](https://platform.claude.com/docs/en/about-claude/models/overview).
- [Claude structured-output/citation compatibility](https://platform.claude.com/docs/en/build-with-claude/structured-outputs#feature-compatibility).

ContextHub tools were unavailable in this session; official sources were used.
Framework/provider package versions are not installed or claimed verified here.

## 12. Review boundary

P2-004 approves the architecture presented in chat, budget subdivision/reserve, and
continuation of planning. Review this written specification next. After that review,
write and self-review the implementation plan with exact interfaces, dependency
pins, test cycles, commands, and execution method. Product implementation starts
only after the plan review. These review stages follow the installed Superpowers
brainstorming workflow; they do not imply provider calls or publication occurred.
