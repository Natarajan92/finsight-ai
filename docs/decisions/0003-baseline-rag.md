# ADR 0003: Framework-led fixed/dense RAG with durable spend authorization

- Status: design and native implementation approved in P2-006/P2-008; final Phase 2
  acceptance and human result review are recorded separately.
- Scope: the existing 53 canonical filings and frozen development membership.
  Original PDFs, page caches and holdout membership remain unchanged.

## Decision

Preserve the modular Python application and `answer(QueryRequest) -> Answer`
boundary. Use LangChain runnables/branches, its native Anthropic structured-output
integration and local Chroma. Keep source identity, chunk/citation provenance,
budget authorization and evaluation isolation under application control.

The fixed baseline uses page-local windows of at most 400 Qwen tokenizer tokens
with a target overlap of 60. Record exact Unicode character spans and stable IDs;
never normalize financial source text. Pin the tokenizer commit and three JSON
asset hashes, with no model-weight download or character-count fallback.

Use Nebius `Qwen/Qwen3-Embedding-8B`, 4096 normalized dimensions, explicit default
tier and cosine distance. Cache exact submitted-text/config hashes separately for
document and query roles. Documents remain raw; queries receive the frozen
retrieval instruction once in client code. Hosted embedding weight revision and
internal preprocessing are not exposed by the public model metadata.

Retrieve up to 15 candidates and select up to the requested top-k (default five).
Join every result back to the trusted source catalog. Subtract covered source
intervals rather than deduplicating repeated words. Pack labeled source data
within 3500 Claude tokens. Count the question before embedding (maximum 512),
then count the complete prompt/schema with the configured Claude endpoint.
Add `max(512, ceil(estimate * 0.10))` overhead and reject input above 6000.

Use `claude-sonnet-5`, low effort, adaptive thinking, standard-only tier and a
1024-token shared thinking/answer output cap. Native JSON-schema output contains
untrusted claims/references/calculations. No native citation blocks, tools, agents,
model fallback or paid schema-repair call is enabled. SDK conversion strips fixed
tuple item schemas, so operands use a homogeneous typed array with exactly two
values enforced by application validation.

Resolve citation IDs, source metadata and exact quote spans on the server. Every
claim needs a supplied reference. A quote cannot cross a removed interval or refer
to another page/year span. Arithmetic uses exact financial literals and bounded
Decimal precision 28, explicit units/periods and two operands; inexact operations
are refused. Cross-period calculations require an explicit comparison question.
These structural checks do not establish semantic faithfulness.

## Durable spending and failure handling

The approved testing ceiling is $5 across both providers: $4 working allowance,
$1 reserve left untouched, and a $0.75 Phase 2 sublimit. SQLite reserves integer
micro-USD atomically before each physical paid attempt. Current, provider/model/
tier-specific rates require official sources and UTC verification within 24 hours.
Lower configured caps also apply inside the reservation transaction.

An independent durable `results/testing-budget-identity.json` binds that identity
to one ledger location outside its cache directory. Every transaction checks this
authority; bootstrap also rejects surviving embedding/index/trace activity.
Recovery or moving a ledger requires explicit reconciliation rather than a new
zero-spend allowance.

Never recreate a missing/corrupt ledger automatically. Unique request IDs prevent
duplicate physical dispatch. Unknown billing retains the entire reservation;
known overrun is recorded honestly. SDK/transport retries are disabled. At most
one controlled retry is permitted for an explicit 429/502/503/504 response with a
new reservation and time remaining; uncertain timeouts are not automatically retried.

Answer invocations have a 45-second deadline and physical attempts at most 20
seconds. A resumable full-corpus build has a four-hour maximum job limit and separate
45-second batch contexts. Query embedding inputs are additionally bounded to
32768 local tokens; preflight reserves that conservative query allowance.
Copied-context daemon execution bounds elapsed client wait; transport timeouts
remain enabled. Unknown remote cancellation retains its entire reservation, and
late results cannot change accounting/caches/terminal traces. At most 16 unfinished
provider calls are admitted.

Publish an index completion manifest only after exact expected IDs, text,
metadata, vectors, dimensions and identities validate. Reopening regenerates the
source-derived windows; self-consistent local hashes alone cannot prove complete
membership. Persist hash-verified canonical little-endian float32 input references,
then require stored Chroma cosine vectors to remain within `1e-6` L2 of those
references; exact output-byte equality fails under legitimate renormalization.
Validate in batches of 128 and recheck selected vectors
and original sources before generation. Chroma uses one construction thread;
persist observed candidate pools for exact replay rather than assuming ANN order.

## Observability and acceptance

Record one terminal typed trace per admitted answer invocation, with request,
source/config/index/prompt/software identities, candidates, retained spans,
counting estimates, physical attempts, usage basis and final Answer. Trace write
failure returns an explicit error with retained accounting and never repeats the
model call. Raw traces and generated artifacts stay ignored. Disable inherited
LangSmith tracing and Chroma telemetry explicitly.

CI uses synthetic PDFs, genuine tiny local tokenizer tests, local Chroma and fake
providers under blocked sockets. Real acceptance verifies unchanged sources,
then runs three stable development cases from distinct companies plus a separate
future-prediction negative through the same service. Runtime receives question
text only, with no benchmark-derived filters or annotations. Completed campaign
receipts replay without new purchases; an interrupted started campaign blocks
automatic repurchase. No holdout campaign or Phase 4 scoring is implemented.
Replay rejoins chunks/source metadata/retained spans to the reopened catalog,
checks request filters/hashes, rebuilds the prompt and validates canonical trace
fingerprints before accepting saved results.

See the [approved design](../superpowers/specs/2026-10-18-phase-2-baseline-rag-design.md),
[implementation plan](../superpowers/plans/2026-10-18-phase-2-baseline-rag.md),
[review checkpoint](../reviews/phase-2.md) and
[acceptance summary](../../results/phase-2-baseline-smoke.md).
