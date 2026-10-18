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
- Verification: local full gates and the new remote run are recorded in the journal.

## ENV-003 - Windows preview encoding resembled damaged extraction

- Phase 1 source QA printed nonbreaking spaces/dashes as replacement glyphs in
  terminal output. Hypothesis: the parser might be emitting U+FFFD.
- Direct cached-text codepoint inspection over all 9,504 pages found **zero U+FFFD**;
  NBSP, em/en dashes, and curly punctuation remain intact in UTF-8 cache data.
- Root cause: preview/stdout decoding, not PDF content corruption. Use process-local
  `PYTHONIOENCODING=utf-8` for Unicode previews; no parser/text normalization change.

## BUG-004 - Text-empty pages hid image-only coverage gaps

- Visual source QA found nine scanned Amcor appendix pages among 18 text-empty
  pages. Empty status was explicit, but did not distinguish a blank page from
  image content with no text layer.
- RED: `test_image_without_text_is_an_explicit_coverage_gap` failed because only
  `empty_page` was recorded.
- Fix: append `image_content_without_text` when an empty page contains images;
  keep raw text and page identity unchanged. Bump extractor version to `phase1-v2`
  so cached v1 records do not conceal the new diagnostic.
- Focused GREEN: the same regression test passed. Full-corpus regeneration and
  final regression counts are recorded in P1-004; OCR remains outside scope.

## BUG-005 - Silent native PDF repairs and syntax warnings

- Independent review P1-005 reproduced a truncated cross-reference table repaired
  during open, and an unmatched content-stream array whose text extraction returned
  without a Python exception. Both were incorrectly accepted as successful sources.
- RED: inspection/manifest and library/CLI cache regressions failed before changes.
- Fix: reject `Document.is_repaired` and native open warnings; reset/consume MuPDF's
  process-global warning buffer around serial operations. Syntax/unknown page warnings produce
  `error` / `pdf_parser_warning`, nonzero CLI status, and no cache write. A following
  healthy source remains unaffected. No source repair or rewrite is attempted.
- Extractor `phase1-v3` invalidates weaker v2 caches. Full verification: P1-005.
- Failed hypothesis: rejecting every page warning returned **618 errors** in the
  full corpus. Source-only probes identified the specific ActualText-position
  warning, indicating possible lost/mispositioned text. A generated marked-content
  regression failed before classification, then passed with unchanged available
  text and an explicit `actualtext_position_warning` diagnostic. No parsing flags
  changed; all syntax/unknown warnings continue to fail and cannot be cached.

## BUG-006 - needs_pass did not identify readable owner encryption

- An encrypted PDF can have an empty user password and `needs_pass=False`.
  Inspection accepted unknown sources and did not report encryption.
- RED: unknown-hash, no-copy-permission, and approved-diagnostic regressions failed.
- Human P1-006 approved the exact nine original hashes, read-only, with diagnostics.
- Fix: inspect metadata encryption, require exact hash approval and copy permission,
  reject password-required sources, and emit manifest/page diagnostics. No broad
  encryption permission, password attempt, decryption, or original rewrite.

## BUG-007 - Self-consistent split checksums did not enforce frozen policy

- A development/holdout swap within the same company/reasoning stratum preserved
  quotas and could be assigned internally consistent hashes. Validation accepted it
  and overwrote development diagnostics, risking feedback on holdout membership.
- RED: direct audit and CLI regressions failed with the forged pair.
- Fix: recompute the declared fixed policy and compare full split manifests before
  reading cached evidence or producing feedback; reject altered membership and
  preserve existing diagnostics. Original split IDs/algorithm/fingerprints unchanged.
- Focused correction suite: eight expected failures / three passes before fixes,
  then eleven passes. Whole-suite evidence and remaining Minor: P1-005.
