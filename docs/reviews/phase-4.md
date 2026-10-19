# Phase 4 local review checkpoint

Branch: `feat/phase-4-evaluation`, based on merged main `88b331a`.
Implementation is verified locally; human review is pending. No Phase 4 push,
PR or merge has occurred.

The new `finsight-evaluate` CLI wraps the existing shared AMD service. Its frozen
development-only selection, canonical trace validation, paired candidate checks,
default-off purchases, bounded estimate and persistent receipts prevent gold
leakage, incompatible replay and duplicate purchases. Private per-case/review
files are separated from sanitized Markdown/JSON/chart exports. Financial match
proxies include coverage; human faithfulness remains unknown without complete,
fingerprint-bound labels. Report-only receipt verification is distinct from
source-derived campaign replay.

One independent reviewer found two P2 scorer issues. RED regressions reproduced
quantity-prefix and period failures. The first period correction introduced
year-shaped money deletion; three more regressions exposed it. Final 51 scorer
tests and reviewer reproductions pass with no remaining reported blocker.

Final source suite: **421 passed, 1 host symlink skip, 7 integration deselected**.
Real source-only checks: **4 passed**. Ruff, lock, build, empty-cwd offline wheel
smokes, outgoing credential/annotation scans and local-file hashes passed.

Explicitly approved live evaluation stopped at the first operational error:
`generation_truncated` at 1,024 output tokens. It executed 1/5 cases at
$0.02120857 usage-priced cost; four cases remain unrun. The annotated evidence
was retrieved and retained, but no answer/citations were accepted. Offline
validation passed with provider construction/network forbidden and unchanged
ledger bytes. The failed result was preserved without retry.

The [result checkpoint](../../results/phase-4-evaluation.md) and
[journal P4-001/P4-002](../engineering-journal/phase-04.md) give full evidence.
The live quality gate, B/C/D comparison, human claim support, full-corpus
acceptance and holdout remain incomplete. No successful-answer quality or latency
claim follows from the error's retrieval measurements.
