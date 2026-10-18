# ADR 0001: Phase 0 contract-first modular monolith

- Status: approved design; implementation result awaits human review.
- Date: 2026-10-18. Human approved the Phase 0 plan in prompt P0-005.

## Decision and alternatives

Use the modular monolith from `project.md`, a src-layout installable package,
Python 3.12.15 and uv 0.12.23. Keep the current checkout on
`chore/phase-0-foundation`, as explicitly selected by the human. A separate
worktree would need the untracked instructions/data to be copied or referenced.

Install only pinned Pydantic v2, pydantic-settings, pytest and Ruff now. The global
3.10 environment has incompatible packages. Installing the full RAG stack in
Phase 0 adds native/ML dependency risk without implementing its behavior.
No LangChain, vector store, provider SDK, parser, Streamlit or model is a Phase 0
dependency. Those choices remain reviewable in their owning phases.

## Interfaces and dependency direction

- `contracts`: Pydantic/stdlib only. Unknown fields forbidden; source text is
  validated without stripping whitespace. IDs remain supplied stable strings;
  source-derived ID generation belongs to Phase 1/2, not this foundation.
- `DocumentManifest`: exact source identity, SHA-256 and positive page count.
  Company, period, type and source URL require explicit values or explicit `None`.
  Metadata missing from the dataset is never inferred from a filename. Fiscal
  period can record year-only precision until independently verified.
- `Page` and `Chunk`: zero-based indices; ordered, nonoverlapping half-open spans
  into unchanged extracted page text; explicit chunking/config provenance. A
  contract cannot verify offsets against a page that was not supplied to it.
- `Score`: finite value, score kind and consistent direction. No cross-kind
  normalization is implied. A reranker logit is not a probability.
- `QueryRequest`: defaults fixed/dense, no rerank, final top 5; allowed top-k 1..15.
  Company/document/period filters are explicit. Future service applies combined
  filters conjunctively and must not derive them from gold document names.
- `Answer`: answered/partial need text and citations; partial needs limitations;
  error needs `AppError`; failure/abstention cannot carry citations/calculations.
  Unknown metrics are `None`, never fabricated zero. Decimal calculations retain
  units, but correctness/support is not established by schema validation.
- `ExperimentConfig`/`ExperimentResult`: config fingerprint is SHA-256 over sorted,
  compact JSON including explicit defaults/unknowns. Source/dataset/split
  fingerprints and typed measured outputs are recorded without gold content.
  Models are frozen at field assignment; nested metric/operand dictionaries are
  not deep-immutable. Persisted experiment records must be serialized snapshots.
- `application.ApplicationService`: `answer(QueryRequest) -> Answer` protocol
  only; both future UI and evaluator call the implementation. Runtime never imports
  evaluation. Gold case/annotation types and loaders remain absent until approval.
- `config.Settings`: explicit environment loading with `FINSIGHT_` prefix;
  settings ignore unrelated dotenv entries. No credentials required for Phase 0.
- `observability.logging`: formats then redacts the configured API secret, including
  exception traces, on the application logger. No propagation to root. New provider
  credentials must be added to this policy when those integrations are introduced;
  arbitrary undocumented secrets are not automatically discovered. Handler failures
  emit only a fixed safe diagnostic, never raw record arguments or exception traces.

## Documentation checked

ContextHub CLI 0.1.4: `pydantic/package` 2.13.4 revision 2,
`pydantic/settings` 2.14.1 revision 2, and `uv/package` 0.11.17 revision 2;
all dated 2026-05-29. The uv guide predates installed uv 0.12.23; local `--help`
and actual lock/sync/compile commands checked compatibility.

Official cross-checks: [models](https://docs.pydantic.dev/latest/concepts/models/),
[settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/),
[uv lock/sync](https://docs.astral.sh/uv/concepts/projects/sync/),
[uv CI](https://docs.astral.sh/uv/guides/integration/github/).

Superpowers skills actually used: using-superpowers, brainstorming, writing-plans,
using-git-worktrees (preference/detection only), executing-plans,
test-driven-development (including writing-good-tests), systematic-debugging,
verification-before-completion, requesting-code-review, receiving-code-review,
and finishing-a-development-branch. No automated external chat capture is claimed.
PDF inspection guidance was used during the audit.
