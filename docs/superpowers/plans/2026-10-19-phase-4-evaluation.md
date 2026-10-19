# Phase 4 Evaluation Implementation Plan

> Use superpowers:executing-plans with native execution and one independent review.
> The user requested fast-tracked next-phase implementation; prior judgment and
> execution preferences persist. No repeated design/execution approval loop.

**Goal:** Reproducible, evidence-validated AMD development evaluation and reports.
**Architecture:** Offline selection/scoring surround the unchanged shared AMD
service. Runtime receipts and source-derived traces are the evidence authority.
**Tech stack:** Existing Python/Pydantic/pytest/Altair stack; no new paid service.
**Spec:** `docs/superpowers/specs/2026-10-19-phase-4-evaluation-design.md`.

## Constraints and review focus

- Five AMD_2022_10K development cases; no holdout execution or gold runtime inputs.
- Same existing budget, $0.25 maximum campaign estimate, explicit --allow-paid.
- Errors, partial answers, ambiguous normalization and pending human review stay visible.
- Verify source/index/request/trace and prompt before scoring or replay.
- No silent arm omission, duplicate purchases or original-cost/replay-cost confusion.
- Preserve both existing dirty files; work on merged main in current phase branch.

### Task 1: Conservative financial scoring

Files: `evaluation/normalization.py`, `evaluation/scoring.py`,
`tests/test_evaluation_scoring.py`.

- [x] Write RED tests for currency/scale equivalence, parentheses/minus, precision,
  percent versus percentage points, conflicting numbers, wrong periods, abstention,
  partial/complex answers and unknown metrics.
- [x] Implement parse_quantity and score_answer with explicit method/review reasons.
- [x] Run focused tests GREEN; keep scorer version and tolerance frozen in run identity.

### Task 2: Frozen development campaign and trace validation

Files: `evaluation/campaign.py`, `evaluation/validation.py`, `evaluation/replay.py`,
`evaluation/models.py`, `tests/rag/test_evaluation_campaign.py`.

- [x] RED tests: exact dev selection, no annotation fields in runtime, default-off
  purchases, maximum estimate, changed split/source/trace, interruption and free replay.
- [x] Implement plan/run, strict complete requested-arm readiness, persistent
  checksummed receipts, conservative preflight and per-case verified metrics.
- [x] Generalize existing trace validator with explicit experiment fingerprint/
  rerank score options while preserving baseline defaults and validation tests.
- [x] Run synthetic PDF/Chroma/shared-service campaign and replay GREEN.

### Task 3: Reports, review worksheet and CLI

Files: `evaluation/reporting.py`, `evaluation/runner_cli.py`, pyproject/lock,
`tests/test_evaluation_reports.py`, README and phase journal/results.

- [x] RED tests: honest metric denominators/unknowns, CSV formula handling,
  fingerprint-bound human review, safe exports, CLI default-off behavior and errors.
- [x] Implement finsight-evaluate plan/run/report, private per-case outputs and
  sanitized summaries/aggregate chart. No reference answers in exported summaries.
- [x] Attempt the planned five-case AMD baseline within preflight; stop on error
  and validate saved records offline. Actual: 1/5, generation_truncated; four unrun.
  Record outcomes, missing arms, spend and unresolved semantic review.
- [x] Run full source snapshot checks and independent final review, fix important
  findings with regressions, update evidence and leave phase work local for review.

Implementation checkpoint: 421 full-source passes, four real source-only passes.
Human review is pending; the live five-case quality gate remains incomplete.
No holdout, new allowance, failed-question repurchase or Phase 4 publication.
