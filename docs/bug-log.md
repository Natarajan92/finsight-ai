# Bug and environment investigation log

## ENV-001 - Restricted shared Git/cache/temp paths

- Phase/branch: 0, `chore/phase-0-foundation`; prompts P0-001/P0-005.
- Symptom: Git dubious ownership; writes to refs denied; default ContextHub/uv
  cache access denied; pytest's existing `pytest-of-valli` directory denied.
- Diagnosis: explicit ownership/path permission errors, not failed product logic.
- Actions: per-command `git -c safe.directory=E:/maai-projects/finsight-ai`;
  approved scoped escalation for local branch metadata; writable temporary CLI
  caches; `pytest --basetemp=.pytest_cache/...` for owned test scratch directories.
- Failed runtime attempt: 4 failed, 1 passed, 4 setup errors. Corrected test-only
  directory: 7 failed, 2 passed, 0 errors, exposing the intended missing behavior.
- No global Git/PowerShell policy changes, system package upgrades, or source changes.
- Remaining risk: other restricted sessions may need the README cache/temp options.

## ENV-002 - Global Python cannot be the project environment

- `python -B -m pip check`: seven dependency conflicts; pytest/Ruff unavailable,
  Pydantic v1 incompatible with the approved v2 contract implementation.
- Corrective decision: isolate Python 3.12.15 with uv; do not fix unrelated global
  packages. `uv lock` and `uv sync --locked --group dev` installed successfully.
- uv cache was on another drive: copy fallback warning. Use `UV_LINK_MODE=copy`.
- Managed-interpreter dry-run was rejected during planning; standalone compilation
  proved dependency resolution without bypassing the environment guard.

## BUG-001 - Logging's fallback could expose the configured secret

- Detected by independent review, P0-005; no real credential was used.
- Reproduction: `logger.warning("Provider failed", "synthetic-secret-value")`
  causes formatting failure. Standard `handleError` printed raw `Arguments:` to
  stderr. A failing stream likewise exposed the record/exception.
- Hypothesis confirmed by two regression tests: both failed on secret disclosure
  before the fix, with 9 unrelated tests deselected.
- Fix: application-owned handler emits a fixed safe stderr diagnostic, suppresses
  secondary stderr failures, and never changes global `logging.raiseExceptions`.
- Regression tests: `test_malformed_log_format_cannot_leak_raw_secret_arguments`
  and `test_failed_log_stream_cannot_leak_secret_record_or_exception`.
- Full-suite result: recorded in the journal after execution.

## BUG-002 - Windows CI native exit status could be overwritten

- Detected by independent review, P0-005.
- Reproduction with `$ErrorActionPreference='Stop'`: Python exits 1, then a second
  Python exits 0; observed final `$LASTEXITCODE` is 0. Multiline lint/format and
  smoke/build steps could therefore incorrectly pass under GitHub's PowerShell.
- Fix: split all native commands into individual Actions steps, letting the
  runner's native exit check apply to every gate. No product code changed.
- Local shell reproduction verified the failure mode; actual remote workflow
  remains unexecuted pending push approval. No text-matching YAML test substituted
  for running CI.

## BUG-003 - First published CI run exposed fresh-runner setup assumptions

- Detected after the authorized Phase 0 push, prompt P0-007. Run:
  https://github.com/Natarajan92/finsight-ai/actions/runs/39111323063
- Windows setup-python could not find a Python 3.12.15 x64 build for Windows
  2025. Local success used uv's standalone managed Python, a different source.
- Linux installed successfully, then tests reported 61 passed / 4 setup errors:
  `.pytest_cache/ci` had a nonexistent parent on a fresh checkout. Local runs had
  already populated `.pytest_cache`, masking that assumption.
- Root-cause evidence: read both actual job logs through the connected GitHub
  tool. Local reproduction with `--basetemp=.pytest_cache/absent-ci-parent/ci`
  produced the same FileNotFoundError before any product test behavior ran.
- Correction: official pinned setup-uv action, uv 0.12.23, `uv python install`
  respecting the unchanged `.python-version`; CI basetemp is a direct child of
  the existing runner temp directory. Restricted local instructions now use the
  ignored root `.pytest-tmp` path, whose parent exists on a fresh checkout.
- No runtime code, Python/package pins, source documents or tests were changed.
- Verification: local 65-test suite passed. Corrected commit `61e377e` passed
  all Windows/Ubuntu steps in run `39111532667`, with 65 tests on each platform,
  successful smoke, and successful wheel/source builds. See P0-008.
