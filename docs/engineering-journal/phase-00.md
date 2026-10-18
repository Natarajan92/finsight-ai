# Phase 0 engineering journal

## P0-001 - Planning and read-only audit

- Date: 2026-10-18, Asia/Kolkata (IST, UTC+05:30). Individual message times are
  unavailable; audit clock observed 13:11:23 IST.
- Starting branch/SHA: `main`, `75461c03528f00f5ae3b62c9f872f0e987122eae`.
- Actor: human prompt to Codex; category: planning.
- Original prompt, faithful excerpt: "Read `project.md` completely and follow its
  architecture, branching, testing, evaluation, documentation, and approval
  requirements." "Do not implement Phase 1 or later." "Do not index FinanceBench
  reference answers or evidence annotations." "Do not modify original FinanceBench
  files." "Do not push, merge, or deploy anything without my approval."
- Goal: audit repository/environment/corpus and propose only Phase 0.
- Agent proposal: isolated Python 3.12.15, minimal contracts, config/logging, keyless
  tests/CI, reusable documentation; all later processing remains unimplemented.
- Human review at planning checkpoint: pending then; approval received in P0-005.
- No files changed during Plan mode; no journal previously existed.
- Baseline: no app/tests/CI; global `pip check` reported seven dependency conflicts;
  `python -B -m pytest --version` and `python -B -m ruff --version` both failed
  because the modules were absent. This was not a project test run.
- See [audit](../phase-0-audit.md) for actual coverage and source fingerprints.

## P0-002 - Corpus decision

- Human selected exactly: "All 53 filings (Recommended)".
- Record all six companies' metadata-matched filings; retain source duplicate
  files unchanged and exclude aliases from a future manifest.
- Human rationale: not supplied; do not invent it.

## P0-003 - Deadline clarification

- Human response verbatim: "Keep deadline and we need to complete all the phases
  within that with better engineering quality as well."
- Deadline: 2026-10-19 12:29 IST (2026-10-18 23:59 Pacific daylight time).
- Agent proposed 20.5 hours of conditional time boxes including contingency;
  this was not a guarantee or authorization to implement later phases.

## P0-004 - Workspace decision

- Human selected exactly: "Branch here (Recommended)".
- Work in this checkout on a feature branch; preserve existing untracked inputs.

## P0-005 - Approved Phase 0 implementation

- Captured 2026-10-18; implementation clock observed 13:26:01 IST.
- Human prompt, faithful excerpt: "PLEASE IMPLEMENT THIS PLAN:" followed by the
  Phase 0 plan saved in summarized task form under `docs/superpowers/plans/`.
- Human approval: APPROVED for the supplied Phase 0 plan and local implementation.
  Independent human diagnosis/rationale was not supplied. Final result review: PENDING.
- Expected result: validated contracts, isolated pinned environment, config/logging,
  synthetic smoke, keyless CI and documentation; no ingestion/index/provider work.
- Branch: `chore/phase-0-foundation`, base SHA above.
- Initial branch creation failed because the sandbox could not write Git refs.
  The identical command with scoped escalation succeeded; global Git configuration
  was not changed. No remote write occurred.
- Verification was pending at entry opening; actual evidence follows below.
  The containing phase commit links implementation to this journal; no PR exists.

## Execution ledger

- Pre-flight: contract models are shared by configuration-independent smoke and
  the application protocol. Settings alone depend on pydantic-settings; contracts
  depend only on Pydantic/stdlib. Evaluation annotations have no runtime consumer.
- Ruling: use this durable journal as the execution ledger instead of the skill's
  Bash scratch helpers. The approved plan is conversational and the host is
  PowerShell; behavior/test evidence is retained here. Cost if wrong: manual
  progress bookkeeping, not a product behavior change.
- Ruling: one phase-level commit after all checks, rather than commits with
  intentionally failing tests. `project.md` requires all commit gates to pass.
  Cost if wrong: a coarser review range for this small foundation.
- Task 1: complete. `uv lock` and `uv sync --locked --group dev` succeeded;
  15 distributions installed in a new `.venv`. Cache/checkout are on different
  drives; uv fell back from hardlinks to copying. Use `UV_LINK_MODE=copy` below.
- Task 2 RED: `uv run --locked pytest tests/test_contracts.py --tb=short -q`:
  54 failed, all expected assertions naming missing contracts (no collection errors).
- Task 2 GREEN: `uv run --locked pytest --tb=short -q`: 54 passed in 1.25s.
- Task 3 initial RED: runtime tests had 4 failures, 1 pass, 4 setup errors because
  the sandbox cannot access the pre-existing global `pytest-of-valli` temp directory.
  No application fix was made for this environment problem.
- Task 3 corrected RED: `uv run --locked pytest tests/test_runtime.py
  --basetemp=.pytest_cache/runtime-red --tb=line -q`: 7 failed, 2 passed, no errors;
  failures named missing Settings/logging/smoke behavior. Architecture checks
  already passed against the new boundary-only package.
- Task 3 GREEN: `uv run --locked pytest --basetemp=.pytest_cache/runtime-green
  --tb=short -q`: 63 passed in 2.86s. `uv run --locked finsight-smoke` reported
  `synthetic_contract_roundtrip`, passed, page index 0, cost unknown.
- First lint/format check: six lint findings (adjacent zip strictness, import order,
  test line lengths), five files needing formatting. Replaced adjacent zip with
  `itertools.pairwise`; applied Ruff's import sorting and formatting to new Python
  files only. These are behavior-preserving changes under the passing tests.
- Task 3 complete: config, redacting logging, protocol and synthetic smoke added;
  reserved later-phase packages contain docstrings only. Lint/format green;
  `uv build` built wheel and source distribution.

## P0-006 - Independent review and correction

- Recorded 2026-10-18 13:38:11 IST; individual review message times unavailable.
- Actor: Codex dispatched one fresh-context read-only review agent under the
  executing-plans/requesting-code-review skills. This is an **agent-authored**
  review prompt, not another human prompt.
- Exact material excerpt: "Perform one independent, read-only review of the
  FinSight AI Phase 0 implementation"; "Do not edit files, stage, commit,
  checkout, or spawn agents."
- Review result: no Critical findings, two Important findings, no deferred Minors.
  See [review report](../reviews/phase-0.md) and BUG-001/BUG-002.
- Human final-result review: PENDING. Human reasoning/diagnosis was not supplied.
- Verified CI issue locally: `$ErrorActionPreference='Stop'`; Python exits 1 then
  Python exits 0; final native `$LASTEXITCODE` observed 0. Split each Actions
  native command into a separate step. Actual GitHub execution is still NOT RUN.
- Logging RED command: `uv run --locked pytest tests/test_runtime.py -k
  'malformed_log_format or failed_log_stream' --basetemp=.pytest_cache/review-red
  --tb=line -q`: 2 failed, 9 deselected. Both reproduced synthetic secret exposure.
- Logging correction: safe application handler never prints the failed raw event
  or exception. It emits a fixed diagnostic; global logging behavior is unchanged.
- GREEN: `uv run --locked pytest --basetemp=.pytest_cache/review-green -q`:
  **65 passed in 1.66s**, 0 failed, 0 skipped. No integration/provider tests exist.
- Rebuilt wheel and source distribution after correction. One fix pass, no second
  review dispatch; every substantive code correction has a failed regression first.

## Final verification evidence

All commands run from the repository root unless an explicit empty cwd is noted.
For restricted local runs: `UV_CACHE_DIR=$env:TEMP/finsight-uv-cache`,
`UV_LINK_MODE=copy`. No system environment/package configuration was modified.

| Command/check actually executed | Result |
|---|---|
| `uv lock --check` | PASS, lock matches pinned project |
| `uv sync --locked --group dev` | PASS, new isolated Python 3.12.15 environment |
| `uv run --locked ruff check .` | PASS |
| `uv run --locked ruff format --check .` | PASS |
| `uv run --locked pytest --basetemp=.pytest_cache/review-green -q` | 65 PASS, 0 fail/skip |
| `uv run --locked finsight-smoke` | PASS: synthetic contract roundtrip, page 0, cost unknown |
| `uv build` | PASS: `dist/finsight_ai-0.1.0.tar.gz` and `.whl` |
| `UV_PROJECT_ENVIRONMENT=.pytest_cache/fresh-locked; uv sync --locked --group dev` | PASS: 15 distributions installed from lock |
| Fresh environment `uv run --locked pytest --basetemp=.pytest_cache/fresh-tests -q` before review fixes | 63 PASS in 2.42s |
| `uv pip check --python .pytest_cache/fresh-locked/Scripts/python.exe` | PASS: 15 compatible distributions |
| `uv venv --python 3.12.15 .pytest_cache/wheel-final` | PASS: separate runtime-only environment |
| `uv pip install --python .pytest_cache/wheel-final/Scripts/python.exe dist/finsight_ai-0.1.0-py3-none-any.whl` | PASS: 8 runtime distributions |
| Wheel Python `-I` from empty cwd: import origin, smoke, malformed-log safety | PASS; no checkout import, cost unknown, no secret in stderr |
| Wheel/source archive member inspection | PASS: no original data, `.env`, local venv or source templates |
| `git diff --check` | PASS; Git notes normal Windows LF/CRLF conversion |
| SHA-256 comparisons against planning baseline | PASS: 55 selected-company PDFs and both annotation JSONLs unchanged |
| Windows/Ubuntu GitHub Actions | NOT RUN: push/publication not authorized |
| Real provider, index, benchmark, holdout, faithfulness, latency/cost experiments | NOT RUN: later phases not authorized |

Source fingerprint remains
`7d8ca4d2d901038058ac345778ecb5898f20e04e6f5a0c97ffd344db41a776fe`.
No split/index fingerprint exists. Model tokens/cost/latency: unknown, no model call
made. Test runtimes above are test-run durations, not answer latency measurements.

- Final: Ruling: use the reviewed scope boundary for semantic support, arithmetic,
  retrieval and generation; no Phase 0 implementation/quality claim for them.
  Cost if wrong: later phases must supply those checks before release claims.
- Final: Ruling: the reviewer's independent corpus/action/CI limits are recorded
  explicitly. Executor verified source hashes, official action refs and fresh
  installation; corpus mapping remains audit evidence and remote CI remains
  pending. Cost if wrong: upstream/CI checks can reveal issues before release.
- No deferred minor findings. Both Important findings corrected.
- Final pre-commit gates: inline staged-content inspection checked 48 explicitly
  allowlisted files (128,982 bytes at that check), with zero known secret-pattern
  findings, no source PDFs/JSONLs/private `.env`/templates/venvs/builds, no file over
  1 MB. Ignore checks passed for raw data, `.env`, environments, caches and builds;
  `.env.example` remains versioned. This is a limited pattern scan, not a claim
  that arbitrary unknown credential formats can be detected.
- Pre-commit commands: `git diff --cached --check`, `uv lock --check`,
  `uv sync --locked --group dev`, `uv run --locked ruff check .`,
  `uv run --locked ruff format --check .`,
  `uv run --locked pytest --basetemp=.pytest_cache/precommit -q`, and
  `uv run --locked finsight-smoke` all passed; **65 passed in 2.29s**, 0 fail/skip.
- `main` still resolves to `75461c03528f00f5ae3b62c9f872f0e987122eae`.
  Finishing-a-development-branch keeps the approved local feature branch; the
  user's explicit no-push/no-merge boundary already settles integration choice.
- Task 4: verification complete. This entry and the approved phase are delivered
  in the containing local commit. Find its SHA with
  `git log -1 --format=%H -- docs/engineering-journal/phase-00.md`.
- Final human review PENDING. No remote PR, push, merge, deployment or Phase 1 work.
- Next recommended phase: dataset/provenance, only after separate approval and
  the repository's branch/PR gate. No measured RAG quality or provider usage exists.
