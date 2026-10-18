# Phase 3 engineering journal

## P3-001 — Approved controlled retrieval implementation

- **Human prompt:** "PLEASE IMPLEMENT THIS PLAN", followed by the complete Phase 3
  plan recorded in the approved design and implementation plan.
- **Decisions:** AMD pilot then 36 development cases/53 filings; Nebius semantic
  embeddings; local CPU reranker; additional Phase 3 cap $0.75 under shared $5/$4/$1
  budget; no bulk generation, holdout, UI or later-phase work. Optional four AMD
  answers remain manual. The plan is approved for native implementation.
- **Starting state:** merged main `08ebb3d9c54978ecf1eb21f453df9608fd0168ea` (PR #4),
  new branch `feat/phase-3-retrieval-experiments`, existing checkout retained.
  `notebooks/01_single_document_rag.ipynb` is modified with the human's experiments
  and outputs; preserve it byte-for-byte and never stage it.
- **Current evidence:** AMD fixed index complete (313 chunks) and one saved answer
  with one citation. Full-corpus baseline is still incomplete, so expanded live
  comparison is conditional. No quality result is inferred from a saved answer.
- **Execution:** Superpowers executing-plans and TDD, no implementer agents; one
  independent whole-branch reviewer at the end. Ledger and tests carry progress.
  No Phase 3 publication approval is inferred from Phase 2 publication approval.

### Task 1 — Configurations and atomic spending

- Three RED cases reproduced missing experiment contracts, unbounded Phase 3
  concurrent reservations and missing phase-specific availability. GREEN focused
  budget/config/dispatcher run: 41 passed. Fixed A/C retain the exact baseline
  identity; semantic B/D have one shared distinct index identity; all run identities
  differ. Legacy budget authority/schema/Phase 2 cap remain unchanged.
- The old global-budget test used Phase 3 as an uncapped later-phase placeholder;
  moved that generic reservation to Phase 4 because Phase 3 is now explicitly
  capped. Its global-bound assertion remains. New cases pin Phase 3 independently.
- Initial keyless baseline excluding the human's executed notebook: 308 passed,
  two failures (installed synthetic CLI and isolated import subprocess), one host
  symlink skip/seven integration deselections. Repeated focused checks passed the
  CLI; isolated imports pass standalone but failed in the first staged full run
  (320 passed/one failure). Improved that existing test's stderr diagnostic without
  changing its assertion. Investigation/verification continues; no false green.
- Repeated full staged-tree run with native thread pools bounded on this 5.9 GiB
  host: **321 passed, one host symlink skip, seven integration deselected**, 58.41s.
  Ruff lint/format passed for 137 files using `--no-respect-gitignore` because the
  clean snapshot is inside ignored scratch storage. The initial snapshot lint had
  found no files; it was rerun correctly. No runtime isolation assertion was relaxed.
