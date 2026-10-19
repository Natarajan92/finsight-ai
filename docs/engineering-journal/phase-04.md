# Phase 4 engineering journal

## P4-001 -- Fast-track AMD development evaluation

- **Date/time:** 2026-10-19 IST; individual message times unavailable.
- **Branch/base:** `feat/phase-4-evaluation`, merged PR #5 at
  `88b331afa69d6cce7ddceeaea81bcd87f0f153e1`.
- **Exact human prompt:** "Code reviewed and Merged to main. Lets start the next
  phase development and fast track the process. But dont give up on logic."
- **Context:** Prior user preference: use judgment and the existing document to
  build financial RAG for AMD. Preserve local executed notebook and Phase 2 plan
  edits. The full-corpus index and other experiment assets remain incomplete.
- **Proposal:** Native Phase 4 implementation on five frozen AMD development
  cases, no holdout, same service/ledger, default A, explicit missing-arm errors.
  Design and plan live under `docs/superpowers/`; no repeated approval loop.
- **Human analysis of this phase:** Not supplied; review pending. The previous
  merged work is user-reported reviewed and its GitHub merge was independently
  verified. That does not imply review of these new changes.
- **Skills used:** Superpowers brainstorming (prior judgment preference retained),
  writing-plans, executing-plans, TDD, verification-before-completion and one
  independent final-review agent. No implementer subagents or parallel edits.

### Implementation and failed attempts

- Added normalization/scoring, strict campaign/run models, source-derived trace
  validation, default-off CLI, private case/review CSV/JSONL, public aggregate
  Markdown/JSON and Altair/Vega-Lite chart. No runtime annotation inputs or judge.
- Financial tests started RED (missing scorer), then 25 passed. Campaign/report
  tests exercise the real shared service on synthetic PDFs/Chroma; only provider
  boundaries are fake. The first fixture assertion accidentally inspected the
  separate forecast trace; corrected it to reopen the official case trace.
- Campaign lock regression protects a receipt changed between planning and lock
  acquisition. Complete campaigns cannot be overwritten by stale state.
- Offline uv resolution initially lacked cached watchdog metadata. Ordinary
  resolution succeeded; all 152 package versions remain unchanged. Altair 6.3.0
  was already installed transitively and is now a direct dependency.
- Independent reviewer found two P2 scoring issues (BUG-023/024). Twenty failing
  regressions reproduced sign/unit-prefix and period problems before fixes.
  The initial period fix erased year-shaped monetary quantities; three additional
  failing cases caught that regression. Financial spans are now protected.
- Reviewer rechecked all reproductions: 51 scoring tests passed, no remaining
  blocker from the reported findings. This is agent review, not human acceptance.

## P4-002 -- Explicit live evaluation approval

- Automatic approval review rejected the initial paid run because external
  destinations/payload had not been explicitly approved for this evaluation.
  No call was dispatched by that rejected action. Offline work continued.
- The approval question specified public FinanceBench development questions to
  Nebius for embeddings and those questions plus public AMD 2022 10-K excerpts
  to Anthropic for answers, worst-case $0.22570320 within $0.25, existing ledger,
  no holdout and no new allowance.
- **Exact human response:** "Approve the five-case run".
- Preflight selected all five AMD development cases, found the fixed index ready,
  and reported zero provider network calls. Ledger before execution: $0.030903
  accounted, $0.000065 uncertain reservation, $3.969032 available, $1 reserve.
  Existing Phase 3 availability: $0.738081. No rates or budget caps were changed.
- The approved run stopped on the first case, `generation_truncated`, at the
  existing 1,024 output-token ceiling. It recorded 1/5 cases, no accepted answer,
  one embedding and one generation, $0.02120857 usage-priced cost, 18,344 ms.
  Four cases and the separate real safety negatives were not run; no retry.
- Candidate/top-five/retained annotated-page coverage was 1 for that case. No
  automatic score or human faithfulness value exists. See the sanitized
  [checkpoint](../../results/phase-4-evaluation.md) and generated aggregate files.
- Offline partial replay used the existing pilot receipt, canonical source trace
  and gold join with provider construction and socket connections forbidden.
  Record equality and unchanged ledger bytes passed; new cost zero.
- Ledger after: $0.052112 accounted, $0.000065 existing reserved, $3.947823
  available, $1 untouched reserve. The $0.021209 ledger delta includes rounding.

### Verification checkpoint

- Initial complete-source suite: 395 passed, 1 host symlink skip, 7 integration
  deselected. Then 26 additional scoring regressions were added during review.
- Focused evaluator/service/split suite before the final three monetary-year
  cases: 74 passed. All 51 final scorer tests passed after those additional fixes.
- `uv lock --check`: 152 packages resolved; no dependency version changes.
- `uv build`: source distribution and wheel built. `finsight-evaluate --help`
  exposes plan/run/report. `finsight-smoke` and synthetic RAG smoke passed,
  measured provider calls zero; synthetic cost remains unknown.
- Final current-source snapshot (committed, outputless notebook; the user's
  executed copy is preserved): **421 passed, 1 Windows symlink skip, 7 integration
  deselected**, 80.87s. Command: `python -m pytest --basetemp=<short-scratch> -q`.
- Real source-only checks: `pytest -m integration tests/test_corpus_integration.py
  --basetemp=.pytest-tmp/p4-source -q`: **4 passed**, 13.46s; no provider calls.
- Ruff lint/format passed for all 131 source/test files in that snapshot. The
  snapshot prevents notebook output checks from modifying the human's experiment.
- Wheel imported from an extracted wheel in an empty cwd with socket connects
  forbidden; foundation/synthetic RAG smokes and evaluator help passed. Runtime
  smoke imported no evaluation modules. Wheel/sdist contain no scratch/cache/data.
- `finsight-evaluate report --run <private-run> --output <scratch>` regenerated
  the incomplete reports; it correctly retained the incomplete status.
- Initial outgoing 27-file scan (before adding the review checkpoint): no configured
  credential values, no benchmark
  question/reference text in public aggregates, no raw caches/traces/data files.
  Original notebook and unrelated Phase 2 plan hashes are unchanged. Final Git
  diff whitespace check passed. No Phase 4 push/PR/merge was performed.
- Remaining: human review, full five-case live gate, B/C/D real assets/comparison,
  human claim-support labels and untouched holdout. The observed output-limit
  issue requires a reviewed follow-up; no target attainment is claimed.
