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
