# Phase 0 Foundation Implementation Plan

Approved by the human's explicit "PLEASE IMPLEMENT THIS PLAN" request on 2026-10-18.

**Goal:** A reproducible, tested Python foundation, without Phase 1 or later behavior.
**Architecture:** Modular Python monolith with pure shared contracts, an application
service protocol, explicit settings, and application-owned logging.
**Spec:** `project.md` and the approved design in `docs/decisions/0001-foundation.md`.
**Execution:** Native implementation using Superpowers executing-plans and TDD;
one independent whole-change review at the end.

## Global constraints

- Python 3.12.15; uv 0.12.23; pinned Pydantic v2, settings, pytest, Ruff, uv-build.
- Branch here: `chore/phase-0-foundation`; leave `main` untouched.
- Preserve all original FinanceBench files. No benchmark answers/annotations in runtime.
- Corpus decision: 53 canonical filings, excluding two duplicate Amcor aliases later.
- No push, remote PR publication, merge, deployment, provider calls, or Phase 1 work.
- Keep exact human decisions distinct from assistant proposals and executed evidence.

## Tasks

1. [x] Bootstrap the environment, package metadata, documentation, and test harness.
2. [x] Specify contract behavior in failing tests, implement minimal models, verify.
3. [x] Specify settings/logging/protocol/synthetic smoke behavior in failing tests,
   implement, verify, and add keyless Windows/Linux CI.
4. [x] Verify locked/fresh installation, wheel, source immutability and staged
   contents; obtain independent review, correct important findings, commit locally.

## Review focus

- Cross-page spans, overlap, page zero, and unchanged table whitespace.
- Structured answer states and unknown resource accounting.
- Gold injection through unknown fields or evaluation imports.
- Secret values in formatted messages, exception traces, and propagated logs.
- Fresh installs without local PDFs, credentials, source checkout, or network calls.

## Acceptance commands

Use a writable temporary `UV_CACHE_DIR`, then run `uv lock --check`,
`uv sync --locked --group dev`, `uv run --locked ruff check .`,
`uv run --locked ruff format --check .`, `uv run --locked pytest`,
`uv run --locked finsight-smoke`, and `uv build`.
Additional final checks: clean temporary environment/wheel smoke, staged secret and
large-file/ignore checks, selected source PDF and both JSONL hash comparisons.
Record actual counts and failures in the journal. CI is not executed until an
explicitly approved push. Stop after the Phase 0 checkpoint.
