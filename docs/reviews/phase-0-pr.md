# Phase 0 foundation PR draft

Create against `main` from `chore/phase-0-foundation`. The connected integration
returned HTTP 403 for PR creation, and the local GitHub CLI lacks authenticated
PR access. This file is a reviewable draft, not evidence that a PR exists.

## Objective and scope

Establish a reproducible Phase 0 Python foundation for future Financial Document
Intelligence work. Human-approved implementation: `b260de1`; approval journal and
publication checks: `4ede320`. Include the subsequent fresh-runner CI corrections.

## Changes and architecture

Typed provenance/query/answer/experiment contracts, application-service protocol,
settings, safe logging, synthetic smoke, pinned Python/uv/dependencies, keyless
Windows/Linux CI, README, ADR 0001, source audit and engineering journal. Runtime
does not import evaluation labels. Later-phase packages remain boundaries only.

## Verification

Locally run lock check, Ruff lint/format, all 65 synthetic unit tests, installed
smoke and package build; isolated fresh installation/wheel checks also passed.
Original selected PDF/JSONL hashes remained unchanged; versioned files passed a
limited known-secret-pattern, artifact, size and ignore scan.

See latest branch Actions for actual remote status. The first run failed on
Windows interpreter availability and Linux temp-parent setup; both root causes
and corrections are recorded under P0-008 and BUG-003.

## Risks and evidence

- Full canonical six-company corpus: 53 filings; 52 matching benchmark questions.
- No actual extraction/index/split/provider/benchmark run; no RAG quality metrics.
- Two independent-review Important findings corrected with regression evidence.
- Journal: P0-001 through P0-008; ADR 0001; `docs/reviews/phase-0.md`.
- Human approved Phase 0 and its push. Merge/deployment still require approval.
- Phase 1 must use merged main or an explicitly approved stacked base.
