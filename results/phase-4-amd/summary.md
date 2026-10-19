# AMD development evaluation

Run: `903312df32ad961d35f30258f8745dd8e60c7e4a871f08edff69baeb3f945836`

Scope: AMD 2022 Form 10-K, frozen development questions only.

| Arm | Cases / expected | Matches / scored | Coverage | Page hit@5 | p50 / p95 ms | Human faithfulness |
|---|---:|---:|---:|---:|---:|---:|
| A | 1 / 5 | 0 / 0 | 0.000 | 1.000 | 18344.000 / 18344.000 | unknown |

New usage-priced cost this execution: 0.02120857 USD.

Arms not evaluated: B, C, D.

## Case diagnostics

| Case | Arm | Status | Automatic check | Reason | Context gold-page recall |
|---|---|---|---|---|---:|
| financebench\_id\_00222 | A | error | unknown | operational\_error | 1.000 |

These diagnostics locate measured gaps; they are not human judgments of semantic support.

## Limitations

- Five-question document-scoped development pilot; not the full-corpus benchmark.
- Automatic match is a value/text proxy with coverage; semantic review is required.
- Faithfulness needs complete fingerprint-bound human review; no paid model judge.
- Annotated-page recall can miss equivalent evidence; it is not citation support.
- Original usage differs from new spending; ledger deltas may include other writers.
- Small-sample p50/p95 do not establish the latency or 95% faithfulness targets.

The private cases and human review worksheet are under `data/evaluation/phase4/`.
The aggregate chart HTML uses CDN JavaScript; JSON/CSV/Markdown remain offline-readable.
