# Phase 2 engineering journal

Planning and design evidence, recorded 2026-10-18, IST. Actual message times are
unavailable; entries are ordered from the visible conversation. The recording
clock was 16:25:53 IST before writing these files. No automatic chat capture is
claimed. Material human prompts are quoted verbatim below.

## P2-001 - Planning after merged Phase 1

- **Actor/category:** Human to Codex / planning.
- **Starting checkout:** `feat/phase-1-ingestion` at
  `45ffabe5fe2ac430feae4ba8da9a12e97182c3af`, clean.
- **Goal:** Discuss Phase 2 before implementation using `project.md` as primary
  reference and the requested Superpowers/GitHub capabilities.

### Original prompt

> As a Senior Software Developer use the  project.md file as your primary reference. So far Phase 0 and phase 1 has been completed reviewed and pushed to github. Branches also merged. Now start the planning for Phase 2. Lets discuss the plan and than after review we can start implementaing th phase 2

The original prompt also selected the Superpowers and GitHub plugins.

### Context, proposal, and evidence

- Read `project.md`, existing source/contracts/tests, data audit, ADRs, reviews,
  Phase 1 planning/journal evidence, and available Superpowers workflows.
- Used installed Superpowers `using-superpowers`, `brainstorming`, and
  `writing-plans` instructions for workflow context; no implementation plan was
  written before architecture/spec review. No subagents were dispatched.
- Git ownership checks initially blocked read-only status/log commands. Used the
  command-local `-c safe.directory=E:/maai-projects/finsight-ai` override; no global
  Git configuration change was made.
- GitHub connector `get_pr_info` confirmed PRs 1 and 3 merged. Phase 1 merge SHA:
  `6db76b2c887e86aca6fa58ab08706443b0bd637b`. Local main was behind that merge.
- Proposed fixed chunking, guarded embedding/index adapters, filtered dense
  retrieval, bounded context, structured generation, citation integrity, abstention,
  a shared CLI/service, and traces. Human review continued in later entries.
- Existing audit: 53 filings, 9,504 pages, 36 development / 16 holdout questions;
  retain extraction limitations and gold isolation. No source reprocessing or
  RAG/holdout scoring ran during planning.

## P2-002 - Provider access established

- **Actor/category:** Human / provider decision; message times unavailable.
- **Goal:** Select a feasible hosted setup without assuming OpenAI API billing.

### Original replies

> I dont have API billing for codex, chatgpt models. I have nebius, claude

After an API-access clarification, the human replied:

> API keys and credits for both Nebius and Claude

### Proposal and review

- Assistant proposed Nebius `Qwen/Qwen3-Embedding-8B` for embeddings, Claude
  `claude-sonnet-5` for generation, and local Chroma. Public official sources were
  checked; account-specific model access, rates, dimensions, and SDK compatibility
  have not been tested. No keys were requested in chat or read for this planning.
- Structured generation uses application-owned citation IDs; official Anthropic
  docs disclose native citation-block/strict-JSON incompatibility.
- ContextHub tools were unavailable; official provider/framework docs were used.
- Provider access is human-reported. No authentication or paid request occurred.

## P2-003 - Shared budget and framework-led design

- **Actor/category:** Human / architecture and spending constraints.
- **Goal:** Conserve credits and review the whole architecture before implementation.

### Original prompt

> Yes lets put the budget of $5 as total testing plan. Be careful on the credit usage, don't exhaust the plan. A framework-led architecture would be more reliable and in future we can try multiple scenarios and test the result. Now as a next step provide me entire architecture in ASCII, lets review one more time end to end architecture and flow. Desiging the system is more important.

### Agent proposal and human reasoning

- **Human reasoning supplied:** framework-led architecture would support reliability
  and future scenarios/comparisons; system design takes priority; preserve credits.
- Assistant revised the proposal to LangChain runnable composition and standard
  provider/vector interfaces, with FinSight-owned provenance, citation checks,
  bounded execution, experiment controls, and persistent spending enforcement.
- Presented ASCII offline preparation, online query, four-arm/evaluation isolation,
  budget reservation, and module diagrams. Phase 2 remains the fixed baseline;
  semantic/reranking/evaluation/UI paths were labeled later work.
- Proposed shared USD 5.00 ceiling, USD 4.00 working allowance, USD 1.00 untouched
  reserve, and USD 0.75 Phase 2 sub-allowance. Count indexing, queries, generation,
  retries, and unresolved billed attempts. Persist across process/run/phase changes.
- Explained that a full 52-question/four-arm generation campaign requires 208
  answers before retries and cannot be assumed to fit the budget. No paid campaign
  or provider performance estimate was represented as a measured result.

## P2-004 - Conversational architecture approval

- **Actor/category:** Human / architecture review.
- **Goal:** Approve the presented end-to-end design and continue planning.

### Original prompt

> yes aligned and good to go

### Decision and remaining review

- **Human review status: REVIEWED** for the ASCII architecture and budget controls
  presented immediately before this reply. Additional human reasoning was not
  supplied; do not invent it.
- The installed `superpowers:brainstorming` workflow says conversational design
  approval permits writing the spec; written-spec approval precedes the detailed
  implementation plan and its review. This approval is not recorded as review of
  a then-nonexistent written spec/plan or permission to publish/merge.
- The assistant is preparing the written design and journal under that approval.
  Written-spec review: pending. Implementation-plan review/execution method: pending.

## P2-005 - Written design preparation and verification

- **Actor/category:** Codex / documentation and verification; no new human prompt.
- **Recorded:** after 16:25:53 IST, 2026-10-18.
- **Branch/base:** `feat/phase-2-baseline-rag` from
  `6db76b2c887e86aca6fa58ab08706443b0bd637b`.
- **Expected behavior:** preserve the approved architecture in a reviewable spec,
  record actual decisions, and make no product/dependency/provider changes.

### Changes

- Fetched `origin/main`, fast-forwarded local main from `310c314` to `6db76b2`, and
  created the Phase 2 branch in the existing checkout. All three operations passed;
  no remote mutation or global safe-directory change occurred.
- Wrote `docs/superpowers/specs/2026-10-18-phase-2-baseline-rag-design.md`, this
  journal, prompt-registry entries, and the journal index link.
- The spec makes request limits, exact quote/span checks, bounded arithmetic,
  persistent atomic reservations, unknown-usage retention, unsupported scenario
  rejection, and phase boundaries explicit for written review.
- Spec self-review checks: placeholders, internal consistency, bounded Phase 2
  scope, and ambiguous requirements. Findings/corrections and verification results
  are recorded below after checks execute.
- Commit linkage: the containing documentation commit is the link; no commit can
  contain its own final hash. No push, PR, merge, runtime code, or dependency change.

### Verification

The existing installed environment was used without syncing/installing dependencies.

| Command | Actual result |
|---|---|
| `.venv/Scripts/python.exe -B -m ruff check --no-cache .` | Passed: all checks |
| `.venv/Scripts/python.exe -B -m ruff format --check --no-cache .` | Passed: 72 files already formatted |
| `.venv/Scripts/python.exe -B -m pytest -m 'not integration' --basetemp=.pytest-tmp-phase2-docs -q` | 142 passed; 1 skipped; 4 deselected in 9.49s |
| `.venv/Scripts/finsight-smoke.exe` | Passed: synthetic contract roundtrip; page index 0; cost unknown |
| `git -c safe.directory=E:/maai-projects/finsight-ai diff --check` | Passed before the final documentation-only evidence update |
| Spec placeholder scan (`TODO`, `TBD`, `FIXME`, `PLACEHOLDER`) | No matches |
| `git ... check-ignore` for `.env`, source PDFs, ledger, indexes and raw traces | All five representative paths ignored |

The skip is the existing unavailable Windows symlink-creation privilege. Four
real-corpus integration cases were deselected by the explicit offline marker.
The temporary test directory was created for this run and is removed after checking
its resolved workspace path; it is not an outgoing artifact.

Self-review corrected one interface ambiguity: `answer(request)` retains its
existing `Answer` return type; a correlated injected recorder receives `RunTrace`.
The spec also explicitly requires original-PDF hash checks before index preparation.
No placeholder requirements remain. Phase 3/4/5 diagrams are extension descriptions,
not authorization to implement those phases.

The final stdlib document audit passed for exactly four allowed documentation
files: six ASCII diagram blocks, six valid local file links, unique CSV prompt IDs
and eleven-column rows, a 100 KB per-file size ceiling, and no matches for the
checked credential/private-key patterns. The same check confirmed no unexpected
outgoing paths after scratch cleanup. `git diff --check` passed again. These are
targeted outgoing checks, not a claim of a comprehensive security assessment.
The local documentation commit follows this evidence update; its containing Git
history supplies the final commit identity. Written-spec review remains pending.

No real corpus/provider integration or holdout evaluation was executed at this
documentation checkpoint. Provider latency, model quality, and billed runtime cost
remain unmeasured; no Nebius/Claude request has been made.

## P2-006 - Written design approved for implementation planning

- **Actor/category:** Human / written-spec review and planning instruction.
- **Date/time:** 2026-10-18 IST; exact message time unavailable.
- **Branch/starting SHA:** `feat/phase-2-baseline-rag` at
  `f8c29d3f721d7b287f4853f3932fb758cf539894`.

### Original prompt

> reviewed, please prepare detailed implementaion plan

### Decision

- **Human review status: REVIEWED** for the written Phase 2 specification linked
  in the immediately preceding response. Human reasoning beyond this approval was
  not supplied. The requested next deliverable is the detailed implementation plan.
- This approves writing the plan; it does not claim a then-nonexistent plan was
  reviewed, select an execution method, or authorize publication/merge.
- Updated only the spec's review status/handoff link; its approved architectural
  requirements remain in place.

## P2-007 - Detailed implementation plan and dependency investigation

- **Actor/category:** Codex / planning, documentation, verification and environment diagnosis.
- **Recording clocks:** preparation began after 16:34:18 IST; review continued after
  16:43:17 IST on 2026-10-18. Exact human message time is unavailable.
- **Branch/base:** `feat/phase-2-baseline-rag`, `f8c29d3`.
- **Goal:** Make the approved design executable as reviewed tasks with explicit
  producer/consumer interfaces, files, dependency pins, RED/GREEN checks, spending
  gates, real-source acceptance and execution-method choice.

### Proposal and self-review

- Used installed `superpowers:writing-plans`; ten tasks cover runtime contracts,
  ledger/dispatch, tokenizer/chunking, Nebius cache, persistent index/retrieval,
  evidence/token budgets, Claude drafts, citations/arithmetic, service/CLI/traces,
  and real-source acceptance/review. Every implementation step remains unchecked.
- Added named tests for five high-risk conditions: uncertain billing/restart,
  repeated/Unicode source spans, corrupt or incomplete indexes/metadata,
  prompt-injection/gold leakage, and valid-looking wrong-span/operand references.
- Self-review clarified explicit cross-period arithmetic, preserving final answers
  in trace artifacts, SDK-native HTTP transport types, cache-key method signatures,
  benchmark-private selected case IDs, ledger initialization before paid work, and
  one paid smoke campaign instead of duplicate manual/test campaigns.
- Native execution is recommended for the coupled interfaces; subagent-driven is
  an alternative. No execution method is recorded as selected. No subagents were
  dispatched for plan preparation or self-review.
- Updated the spec review status, Phase 2 journal, prompt registry and journal index.
  The plan maps each spec area to an owning task; later phases remain extension
  descriptions. Plan review and implementation are pending.

### Dependency and API evidence

- Read public versioned PyPI JSON and published wheel files in memory without
  importing/installing the proposed packages. Selected exact versions are in the
  plan; existing product dependencies and `uv.lock` remain unchanged.
- Final direct additions: langchain-core 1.6.12; langchain-anthropic 1.7.6;
  langchain-chroma 1.1.0; chromadb 1.5.9; tokenizers 0.23.3; httpx 0.28.1;
  anthropic 1.15.0; langsmith 0.14.11. Both platform resolutions selected 104
  packages, including transitive httpx2 2.13.1. Resolution is not runtime/CI proof.
- Metadata-only resolver invocation used `uv pip compile` with explicit
  `--python-version 3.12 --python-platform x86_64-pc-windows-msvc` and independently
  `--python-platform x86_64-unknown-linux-gnu`, `--only-binary :all:`,
  `--no-python-downloads --default-index https://pypi.org/simple --no-progress
  --no-header --no-annotate --quiet`, with input/output/cache files in process-owned
  temporary directories. Final resolution exit codes: zero on both platforms.
- The resolver reported one upstream metadata normalization warning: it removed
  stray quotes from `>= '2.7'`. No project pin was changed to suppress that warning.
- A transport-compatibility hypothesis was checked: Anthropic 1.15 uses HTTPX2,
  whereas Nebius uses HTTPX. Published LangChain `_sdk_compat.py` and `_client_utils.py`
  show SDK-native `DefaultHttpxClient` compatibility wrappers. The hypothesis that
  declared latest versions necessarily mismatched was not upheld; no downgrade
  was made. The plan still requires a real keyless constructor regression after
  installation and forbids mixing transport client types.
- Published Chroma wrapper source confirms `collection_configuration` and scored
  by-vector search; the plan requires raw-distance verification instead of trusting
  a method name containing `relevance_scores`.
- Public Hugging Face metadata reports tokenizer revision
  `1d8ad4ca9b3dd8059ad90a75d4983776a23d44af` for Qwen3-Embedding-8B.
  No tokenizer/model assets or weights were downloaded for this planning turn.
- Consulted official Qwen, Nebius embeddings, Claude counting and thinking-cost
  documentation. Counting is documented as free but approximate; output limits
  cover thinking and answer tokens together. No account credentials were read and
  no Nebius/Claude endpoint was called. ContextHub tools remain unavailable.

### Diagnosis and failed checks

- The first pair of metadata-resolution commands failed before dependency solving:
  `Failed to initialize cache ... Access is denied (os error 5)` under the ignored
  sandbox-created `.pytest-tmp/phase2-plan` directory. Used installed
  `superpowers:systematic-debugging` to inspect ACLs and compare execution identities.
- ACL evidence: the sandbox SID owned the directory; write access belonged to
  SYSTEM, Administrators and OWNER RIGHTS. Elevated metadata execution did not
  have owner rights there. Hypothesis: actor/cache ownership, not dependency
  conflicts. Retried unchanged pins/platforms with caches created by the resolver's
  own process under its temporary directory. Both resolutions then passed; final
  full-pin checks also passed. No ACL/global settings were changed. See BUG-008.
- First formatting check failed on the new plan's Python Markdown fences; it showed
  quote/layout formatting diffs, with 72 other files already formatted. Applied
  Ruff to that plan only, then the same whole-repo check passed for 73 files.
  No executable product or test code was changed by formatting.

### Verification

| Command/check | Actual result |
|---|---|
| `.venv/Scripts/python.exe -B -m ruff check --no-cache .` | Passed: all checks |
| `.venv/Scripts/python.exe -B -m ruff format --check --no-cache .` | Initial plan-fence failure; after scoped formatting, 73 files already formatted |
| `.venv/Scripts/python.exe -B -m pytest -m 'not integration' --basetemp=.pytest-tmp/p2-plan-verification -q` | 142 passed; 1 skipped; 4 deselected in 10.35s |
| `.venv/Scripts/finsight-smoke.exe` | Passed: synthetic contract roundtrip; page zero; cost unknown |
| Final Windows/Linux wheel-only resolution | Passed: 104 packages on each; no installation |

The skip is unavailable Windows symlink creation. The four deselected tests require
the real local corpus. Future test snippets in the plan were not executed as tests;
their syntax/structure is checked separately. No new product tests exist yet.
Final structural/outgoing checks passed: ten tasks, 53 unchecked steps, nine
syntax-valid future Python examples (parsed only, not executed), eight valid local
links, unique eleven-column CSV records, six documentation-only outgoing paths,
per-file size limits, and no matches for the checked credential/private-key patterns.
Whole-repo Ruff formatting passed again for 73 files and `git diff --check` passed.
The network-enabled process SID was explicitly checked as ending in 1001, distinct
from the sandbox directory owner/process SID ending in 1003, confirming the
execution-identity boundary in the cache diagnosis. A local planning commit follows
this evidence update; its containing Git history records the final identity.
No push/PR/merge or product implementation is claimed.

### Remaining review and next step

Human plan review and execution-method selection remain pending. Account-specific
model availability, current rates, installed framework compatibility, tokenizer
asset hashes and real RAG behavior are implementation gates, not established facts
from resolution alone. No provider credits have been consumed in this planning.

## P2-008 - Native implementation authorized

- **Original human prompt:** "Native implementation and start the implementation as per plan"
- **Review:** implementation plan approved; native execution selected. Work remains
  on `feat/phase-2-baseline-rag` in the approved existing checkout, starting at
  `60ebddd552bda459d577c600001b1564c442da91`. No publication/merge permission implied.
- **Workflow:** installed Superpowers executing-plans, test-driven-development,
  using-git-worktrees verification and verification-before-completion. Per-plan
  ignored ledger: `.superpowers/sdd/2026-10-18-phase-2-baseline-rag/progress.md`.
- **Workspace ruling:** honor the accepted current-checkout/feature-branch plan;
  no separate linked worktree. Bash bookkeeping is adapted to Python/PowerShell,
  preserving plan ownership, task briefs, BASE, test evidence and completion lines.
- **Baseline:** 142 passed, one Windows symlink skip, four integration checks
  deselected in 9.86s. Runtime/provider work proceeds only within the reviewed caps.
- **Human reasoning:** native execution chosen; further reasoning not supplied.
  Asked for local-only credential configuration while offline implementation
  proceeds. No key values are requested in chat. Task evidence follows as executed.

### Task 1 - Runtime boundaries and dependency compatibility

- RED: `.venv/Scripts/python.exe -B -m pytest tests/rag/test_runtime_config.py --basetemp=.pytest-tmp/p2 -q`: 17 expected failures (missing config, credentials and integration packages).
- Added immutable bounded configuration, safe error/port/trace contracts, provider SecretStr settings and three-key log redaction. No provider clients are created at import time.
- Installed the eight approved direct pins; uv resolved 107 cross-platform packages in the complete lock (platform-only packages included). Existing direct pins retained. Keyless Claude construction and local Chroma with embeddings disabled passed under blocked sockets.
- GREEN: focused configuration/runtime suite 28 passed in 20.89s; whole keyless suite 159 passed, one Windows symlink skip, four integration deselected in 28.41s. First cold import was interrupted for diagnosis; a fresh timed run completed without a compatibility failure.
- Gates: `uv lock --check`, locked dev sync, Ruff check/format (79 files), existing synthetic smoke/CLI help, `uv build` and `git diff --check` passed. Package operations used the native-account temporary uv cache, avoiding the earlier cache ownership conflict.
- No model/tokenizer download or paid call. Human confirmed local key configuration; key values were neither requested in chat nor inspected.

### Task 2 - Persistent budget authorization

- RED: 13 expected fixture failures for the missing ledger/dispatcher. Added transactional micro-USD reservations, explicit bootstrap/identity marker, integrity/schema checks, unique request identities, retained unknown billing and current official-source rate identities.
- Focused GREEN: 16 passed in 1.12s. A Windows file-deletion regression exposed an unclosed bootstrap connection; explicit connection closing fixed the resource lifetime. An additional RED test demonstrated premature settlement of an unverified usage-priced amount; incomplete token categories now retain the complete reservation and an unknown cost.
- Covered phase/global limits, two-connection contention, restart persistence, duplicate dispatch, deleted/corrupt storage, honest over-reservation cost, stale/missing/mismatched rates, bounded explicit-status retry, no timeout retry, and deadline denial. Persisted attempts retain observed usage and basis; adapters must use dispatcher timeout per physical send.
- Gates: whole keyless suite, Ruff check/format, installed original smoke/CLI help, locked sync/check, package build and diff checks passed; exact suite totals recorded in the native ledger. No paid operations.

### Task 3 - Tokenizer integrity and exact-span fixed windows

- RED: seven failures and two fixture errors demonstrated missing tokenizer/chunking modules. Corrected a synthetic fixture to the existing Page contract's `empty` status (the plan's descriptive blank page is not a new runtime enum).
- GREEN: nine focused tests passed in 1.37s, including genuine locally trained BPE/Unicode offsets and re-encoding, exact 0:400/340:740/680:800 character-token windows, repeated rows, full character coverage, stable IDs, page isolation, empty/error pages and visible table-cut diagnostics.
- Explicit tokenizer preparation downloads only three pinned JSON files into staging; offline loading verifies asset bytes, URLs, revision and library version without downloads. No fallback token estimate replaces unavailable assets. A source that cannot form a nonblank bounded exact window fails explicitly.
- Gates: whole keyless suite, Ruff check/format (90 files), original smoke/CLI help, locked sync/check, package build and diff check passed. No public tokenizer preparation or model call occurred yet; actual production asset verification remains Task 10.

### Task 4 - Guarded Nebius embeddings and persistent cache

- RED: 13 expected missing-adapter fixture failures. GREEN: 15 passed in 5.27s using HTTPX MockTransport and blocked external sockets.
- Standard LangChain embedding interface with immutable per-run binding; explicit Nebius endpoint/default tier/dimensions and query-only instruction. Each physical batch reserves locally counted tokens plus 64 per input; HTTP timeout derives from the remaining invocation deadline. Redirects are refused; transport retries remain disabled in the owned factory.
- Cache identities bind exact submitted-text hash, document/query role, model/revision/dimension/instruction/normalization/tokenizer identity. Atomic records validate payloads, key correspondence and unit vectors. All vectors in a response are validated before that batch is persisted.
- Verified response index reordering, missing/duplicate indices, zero/wrong-dimension vectors, direct NaN/Inf normalization rejection, altered cache rejection, the 4096-dimensional profile, no send after budget denial, and successful batch reuse after a later uncertain timeout. Returned usage settles before vector validation; unknown timeout billing remains reserved. No real provider request was made.
- Whole-suite/common gate passed, including Ruff (94 files), locked checks/sync, package build and original CLI smokes. Runtime paid integration remains pending.

### Task 5 - Complete local indexes and source-checked retrieval

- RED: 15 missing-lifecycle fixture failures. Added source-only catalogs, original/cache validation, a crash-released SQLite build lock, compatible staging/resume and atomic completion manifests. HNSW uses cosine distance and one construction thread; verified the public Chroma schema because legacy configuration omits its thread setting.
- Focused GREEN: 19 passed in 10.42s. Verified complete-build zero embedding calls, interrupted-batch resume, combined/unknown/conflicting filters, full-corpus scope, raw cosine distance direction/tie order, source/cache alteration, stale dimensions and altered catalog/text/metadata/vector failures.
- Additional RED/GREEN regressions caught a coherently rehashed removed chunk, unbounded vector materialization and a vector modified after reopening. Reopen now regenerates expected source windows; vector integrity scans page at 128 records with canonical little-endian float32 hashes; selected vectors are checked again before evidence is returned.
- Interface ruling: build requires an explicit keyword-only tokenizer; open requires pages, embeddings and tokenizer. These omitted construction dependencies are needed for offline injection and source-derived membership verification. Recomputing windows adds local startup time; no extra provider call.
- Whole keyless suite: 218 passed, one Windows symlink skip, four integration deselected in 28.05s. Ruff check/format (102 files), locked sync/check, package build, original CLI smokes and diff checks passed. No real-source index or model call yet.

### Task 6 - Model-specific counting and exact interval packing

- RED: four failures/five fixture errors for missing counting/packing. Added immutable evidence slices/packets, JSON data labels, original interval subtraction and independent model-specific counting with no whitespace/embedding fallback.
- GREEN: 10 passed in 0.35s. Tests cover preserved year/unit/sign text, overlap mapping without duplicated intervals, repeated wording at distinct offsets/sources, top-k, empty context, explicit budget drops, missing counter/deadline denial, schema counting/cache identity and count failure. A missing-counter regression first failed with AttributeError, then passed with a safe typed count error.
- Full-input padding: 5000 -> 5512 accepted; 5500 -> 6050 refused. Claude count calls are separately traced as free endpoint attempts with unavailable billable usage left unknown; cached estimates preserve model/payload identity. Question-limit admission is wired before embedding in Task 9.
- Whole keyless suite: 228 passed, one Windows symlink skip, four integration deselected in 30.64s. Ruff check/format (107 files), locked sync/check, package build, original smokes/CLI help and diff checks passed. No counting endpoint or paid provider request has run.

### Task 7 - Native grounded Claude drafts

- RED: nine missing-generator fixture failures. The actual LangChain native structured-output path is tested against a mocked SDK raw response, including request serialization and usage before parser outcomes. Corrected the fake SDK seam to `messages.with_raw_response.create`/`parse`, matching the pinned integration rather than mocking a different SDK return type.
- GREEN: 11 passed in 7.49s. Verified JSON-schema method/include_raw, explicit model/max_tokens/low effort/standard_only tier, zero SDK retries, no sampling/tools/native citation blocks, refusal abstention, truncation/schema/empty failures without repair calls, deadline/input admission and source instructions preserved as JSON data.
- Native schema RED/GREEN found that SDK conversion removes fixed tuple prefixItems and leaves no typed items. Operands now use a typed homogeneous array constrained locally to length two. Explicit adaptive thinking and standard-only service tier are frozen configuration fields; thinking and answer share the 1024 output-token cap. Model feature/account availability still needs live metadata preflight.
- Original SDK usage categories, rather than normalized framework totals, drive accounting, avoiding double-counted cache/reasoning tokens and leaving absent categories unknown. Hosted LangSmith tracing is disabled around invocation.
- Whole keyless suite and common gate passed (Ruff 111 files, locked sync/check, build, original smoke/help and diff checks); exact totals follow in the native ledger. No provider/count endpoint request occurred.

### Task 8 - Citation integrity and bounded Decimal arithmetic

- RED: 21 expected missing-validator failures. GREEN: 78 tests passed in 0.44s (24 new validation cases plus 54 existing contracts).
- Application-owned citations resolve only supplied evidence IDs and exact quotes inside retained, unchanged source spans. Reject missing claim references, wrong-year spans, unsupplied IDs, quotes crossing a gap and malformed partial drafts. Public text is rendered from validated claims and numbered citations; abstentions contain no factual claims/calculation.
- Strict financial literals preserve grouping commas, parentheses negatives and decimals. Two operands must match supplied numeric text, scale/unit and period. Decimal precision is 28 with inexact-operation traps; no expression execution, conversion or silent rounding. Verified cross-period subtraction, unit-safe multiplication/division, invented operand/unit/year/code/result rejection, actual cited zero division and nonterminating division rejection.
- Interface ruling: optional keyword-only request is needed to authorize explicit comparisons across periods; absent request denies cross-period arithmetic. Presence of a quote/literal/unit/year is structural evidence, not proof that a claim or table-column association is semantically correct.
- Whole keyless suite/common gate passed (Ruff 115 files, locked sync/check, build, original CLI smokes, diff checks); exact totals follow in the native ledger. No provider requests or real-source smoke yet.

### Task 9 - Shared traced service, CLI and runtime wheel

- RED: four new CLI failures and 12 service fixture errors; 20 legacy checks passed. Implemented LangChain stage/branch composition through the existing `answer(QueryRequest) -> Answer` boundary, safe error/abstention paths, context-local trace correlation and atomic per-run JSONL sinks. Typed traces retain request/prompt/draft/evidence, candidate order, spans, attempt identity, usage basis and final answer.
- Focused GREEN: 38 service/CLI/isolation/runtime tests passed in 45.88s. Native generation also passes with inherited LangSmith tracing forced on and sockets blocked. Poisoned annotations cannot change source-derived chunks, a persisted index or prompts; injected source instructions stay in JSON fields and cannot change runtime caps.
- Synthetic installed roundtrip covers a newly created PDF, real extraction/cache, fixed windows, actual local Chroma, fake embeddings/counting/generation, citation validation and trace reload. Its initial Windows RED exposed a retained Chroma build client; explicit close on build/reopen completion and a separate failed-reopen RED/GREEN fixed resource ownership.
- Consumer-wiring regressions verified lower configured budget caps inside the ledger transaction and separate batch deadlines. Index jobs have a one-hour resumable job bound, each provider batch at most 45 seconds, and each physical attempt at most 20 seconds; answer requests retain their total 45-second bound. A 32768-token embedding input ceiling bounds conservative preflight query estimates. No index job can bypass the shared ledger.
- CLI commands: prepare-tokenizer, preflight, budget-init, build-index, ask, smoke --synthetic. Paid build/ask require explicit opt-in, validated local config/sources/rates/ledger and relevant keys; preflight never embeds/generates. Shared $5 ceiling/$4 working/$0.75 phase cap remain unchanged. CI includes installed baseline help/smoke; remote CI has not run.
- Whole keyless suite: 285 passed, one Windows symlink skip, four integration deselected in 65.55s. Ruff check/format (121 files), lock/sync, all installed CLI smokes/help, build and diff checks passed.
- Isolated runtime wheel: installed exported locked runtime dependencies without dev packages; help plus synthetic smoke passed from an empty cwd with sockets blocked and no evaluation imports. The first offline install lacked an existing base dependency in the native cache; fetching its exact locked public wheel resolved that environment gap. No model/tokenizer artifact download or paid/free provider API operation yet.
- Outgoing scan diagnosis: the generic key-prefix pattern matched the `sk-` substring inside the Task 9 journal-anchor slug in the registry, not a credential. A token-start boundary removed that false positive; staged content is scanned again before committing.

### Task 10 - Acceptance harness/code checkpoint before the long provider build

- RED/GREEN: development selector and durable campaign receipt/replay tests (three missing-selector failures plus two missing-runner fixture errors, then five passes). Select exactly three stable development IDs from distinct companies; runtime gets question text only. Started interrupted receipts deny repurchase; completed receipts validate/replay without new service calls.
- Added separately opted-in source/index/provider integration tests. Missing paid flag skips provider execution; once opted in, missing credentials/rates/index/source identity fails. Before paid dispatch: 290 keyless passes / one host skip / seven integration deselected; five explicit local source/cache/split checks passed.
- Public/free preflight verified both model IDs and Claude low effort/adaptive/native structured output. Official Nebius public models_info reports 4096 dimensions and $0.01 per million input tokens. Claude official pricing is $2 input/$10 output per million. Ignored rate snapshot was verified 2026-10-18T12:31:23Z; fingerprint `bb35abf7d8410deb441b6dfad11b90e765f97bad1bb6f543ae8c5a593f6fd9c0`.
- Tokenizer-only preparation verified all three pinned JSON SHA-256s (recorded in the acceptance summary); no weights. Full source preflight: 22070 chunks / 8589543 embedding reservation tokens, worst-case indexing $0.17179086 plus four queries $0.18054656 = $0.35233742, within phase $0.75 and global working $4. Config fingerprint `a0af1624cd3e0e7673552e9e1388c26941081acf8436d0aec2718fdeda2808b6`; catalog `938573fd948946f45003ce4bb0ddac61ddda4110b52c1b631a03be255c85741c`.
- Actual index throughput measured about 110 vectors/minute. A one-hour bulk window would end prematurely. Operational ruling: Settings now permits a four-hour maximum bulk window, recorded in build receipts; answer45/batch45/attempt20-second bounds and all dollar caps stay fixed.
- Controlled checkpoint held a temporary dispatch gate only between settled batches; no ledger rows changed. All 44 paid attempts settled, 704 vectors cached, $0.002368 accounted, reserved/unknown zero; SQLite integrity is OK. The old job reported a busy lock as integrity failure; a RED/GREEN regression now distinguishes `budget_busy` from corruption. The ledger was never reset; compatible resumption reuses completed rows/vectors.
- Expanded software identities in run/index metadata; RED caught a missing trace version field. Corrected its import wiring, then verified typed trace roundtrip. Supplemental non-axis-vector/HNSW-buffer integrity and config-fingerprint roundtrip tests pass. Most recent whole keyless gate: 293 passed, one Windows symlink skip, seven integration deselected in 64.28s; Ruff and synthetic RAG smoke passed. Locked sync/check and package build passed.
- This is a product-code checkpoint so the long provider run has reviewable committed inputs. Acceptance result inspection, independent final review and the final documentation commit remain pending. No push/PR/merge or Phase 2 completion is claimed.
