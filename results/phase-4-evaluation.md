# Phase 4 AMD development checkpoint

Implementation and independent review fixes are verified. **Live evaluation is
incomplete:** the campaign stopped after its first operational error. Four
official development cases remain unrun. Holdout was not executed.

## Reproduce

```powershell
uv run --locked finsight-evaluate plan --arms A --max-cost-usd 0.25
uv run --locked finsight-evaluate run --arms A --max-cost-usd 0.25 --allow-paid
```

The second command requires deliberate paid opt-in. It reopens the existing
terminal error; it cannot repurchase that question. Do not delete receipts or
raise limits to obtain a successful result. A default `run` against an incomplete
campaign with missing answers refuses live execution. The `report --run` command
rebuilds reports without provider clients; source-derived validation of the saved
partial record was additionally verified offline.

## Actual run, 2026-10-19 IST

- Run: `903312df32ad961d35f30258f8745dd8e60c7e4a871f08edff69baeb3f945836`.
- Document: AMD_2022_10K, 121 PDF pages / 313 fixed chunks, arm A only.
- Split: `e6ec481633654b779721f1d94c7aa05a65e43c9f37deae177819658d2b665431`.
- Source: `723a5092e7ad3aa96c406c9d81e63c0cbb8b2990a64772b2aba3a090fe83b5f3`.
- Index: `6721d3b1fc5ad652d5d910862ac1785ba03fd6df5e0d9bf02cba745008018a62`.
- Runtime A: `731b0b765341096fdfdb5ec4ccff5de95c47c9fd81c0edd1f4cf0d5a3fd84500`.
- Preflight maximum: $0.22570320; selected all five AMD development IDs.
- Executed: financebench_id_00222; result `error`, code `generation_truncated`.
- Unrun: financebench_id_00563, financebench_id_00917,
  financebench_id_01198, financebench_id_01279.
- Provider usage: one query embedding (57 input tokens), one generation
  (5,484 input / 1,024 output tokens), total usage-priced cost **$0.02120857**.
  Free token-count checks are separate from paid generation.
- Original request elapsed time: 18,344 ms. The single error's p50/p95 equal that
  value; no successful-answer latency distribution is established.
- Ledger after: $0.052112 accounted, $0.000065 existing uncertain reservation,
  $3.947823 working availability, $1 reserve untouched. Accounted delta
  $0.021209 differs from usage pricing because of ledger rounding. No allowance
  was created and no new uncertain reservation remains.
- Saved partial record reopened with provider construction and socket connections
  forbidden: 1 record validated, zero network calls, zero new spending, identical
  ledger bytes. The original failed run was preserved, not overwritten.

## Failure analysis

1. **Retrieval and packing:** the annotated page was retrieved at rank one,
   remained in top five and survived packing. Candidate coverage, page recall and
   retained-context gold-page recall are 1 for this one measured case. This does
   not prove semantic sufficiency or establish retrieval quality across five cases.
2. **Generation:** Claude reached the existing 1,024-token output ceiling. The
   adapter rejected the truncated structured answer, so no answer or citations
   were accepted. The campaign stopped; it did not buy another completion or hide
   the error. Response verbosity/output capacity is an open runtime limitation.
3. **Scoring:** zero of five expected cases received an automatic score. Match
   rate, citation support and human faithfulness remain unknown; no draft claims
   were accepted for review. The remaining four cases cannot diagnose retrieval
   or generation. Review/tuning requires a separately reviewed runtime change,
   an explicit new configuration identity and a bounded fresh campaign.

Arms B/C/D were not evaluated because real semantic/reranker assets are absent.
The synthetic A/C campaign verifies candidate-pool reuse and receipt logic only.
Real safety negatives were not reached after the operational stop; production
admission/wrong-scope logic is covered by synthetic service tests. This run proves
neither the 95% faithfulness target nor the latency target.

See [measured aggregates](phase-4-amd/summary.md),
[JSON/config/software evidence](phase-4-amd/summary.json),
[aggregate chart](phase-4-amd/metrics.html), and the
[engineering journal](../docs/engineering-journal/phase-04.md). Original questions,
gold answers, quotations, traces and review worksheet remain in ignored storage.
