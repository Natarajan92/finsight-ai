# Phase 4 — AMD development evaluation

The user confirmed PR #5 was reviewed/merged and asked to start the next phase,
fast-tracking execution without sacrificing logic. Continue the prior authorized
use of judgment, native execution and AMD single-filing scope. Base is merged
main `88b331a`; branch `feat/phase-4-evaluation`. Preserve the executed notebook
and unrelated Phase 2 plan edits. No publication or merge of this phase is inferred.

Deliver an offline evaluator and CLI over the same guarded AMD application.
Recompute/validate the original 52-case frozen split, then select all five
development cases for the explicitly declared AMD_2022_10K workspace. This is a
document-scoped pilot, never the primary 53-filing benchmark. Holdout annotations
are used only by existing split-integrity validation, never to run/score/tune cases.
Runtime receives question text and the same explicit filing filters for every
question, never annotated pages, reference answers, rationale or evaluator fields.

Support selecting A/B/C/D without silently dropping unavailable arms. Default A
matches the available index; requesting unavailable assets fails before purchase.
Paired-arm dense pools retain the same question/filter/config identity. Existing
full-corpus prerequisite and holdout gates remain intact. Report comparison
incomplete unless every arm is actually evaluated on the identical cases.

Scoring is conservative: exact normalized text, simple boolean polarity only for
unambiguous short references, and finite Decimal financial quantities with currency,
scale, signs, percent/ratio versus percentage-point units. Do not score a number
found somewhere in an otherwise incompatible multi-number response as correct.
Ambiguity, partial answers and complex references require review. Automatic match
rate always includes its coverage/denominator; it is not semantic faithfulness.

Validate saved answers against their canonical runtime trace, source catalog,
source spans, packed context, request/config/index identities and rebuilt prompt.
Derive retrieval page/document recall, MRR, candidate versus retained-context
coverage, citation integrity and original usage/latency from verified traces.
Original usage must not be presented as new replay spending. Preserve unknown
measurements; errors/missing cases are not silently removed from completion counts.

Generate per-case JSONL/CSV, aggregate Markdown/JSON, an aggregate chart artifact
using an existing plotting library, and a human review worksheet. Raw questions,
gold answers, model answers and evidence stay under ignored data/evaluation.
Exported summaries contain only IDs, aggregate measurements and limitations.
Human semantic labels bind to exact trace/claim fingerprints; empty or uncertain
reviews cannot produce a completed faithfulness score. No paid LLM judge.

Planning and replay are offline. New answers require --allow-paid, fresh verified
rates, intact existing budget authority and a conservative campaign estimate of
at most $0.25. Reuse the app's Phase 3 $0.75 sublimit under $5 total/$4 working/$1
reserve; do not create an allowance or weaken atomic per-call reservations.
Per-question durable receipts prevent repurchase after interruption; campaign
replay revalidates runtime inputs and evidence before rescoring. Timeout or
uncertain state stops execution. Run a bounded real A baseline only if preflight
passes; do not buy extra answers to turn failures into successes.

Separate safety negatives from FinanceBench. Unit tests exercise historical-only
admission and wrong-scope rejection with the production service. The real pilot
may include a forecast abstention with no paid provider calls, explicitly separate
from the five official cases. Missing semantic/reranker assets and unavailable
faithfulness remain visible limitations.

Acceptance: meaningful normalization/replay/leakage/budget/report regressions,
synthetic end-to-end evaluator, actual AMD plan/run/replay/report where permitted,
one independent review, full clean-source tests, lint/format/lock/build/smokes,
documented failures and actual metrics. A partial live run is reported honestly.
