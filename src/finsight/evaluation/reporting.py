"""Private case/review files and sanitized measured aggregates/charts."""

import csv
import math
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path

from finsight.ingestion.cache import write_json_atomic

from .review import csv_text, read_review, write_review


def _percentile(values, p):
    return sorted(values)[max(0, math.ceil(p * len(values)) - 1)] if values else None


def aggregate_run(run, *, review=None):
    labels = read_review(run, review)
    arms = {}
    for arm in run.config.arms:
        records = [r for r in run.records if r.arm == arm]
        statuses = Counter(r.status for r in records)
        matches = [r.match["match"] for r in records if r.match["match"] is not None]
        metrics = {}
        for metric in sorted({k for r in records for k in r.metrics}):
            values = [r.metrics[metric] for r in records if r.metrics.get(metric) is not None]
            metrics[metric] = dict(
                mean=sum(values) / len(values) if values else None,
                measured_cases=len(values),
                expected_cases=len(run.question_ids),
            )
        times = [
            r.answer.usage.latency_ms for r in records if r.answer.usage.latency_ms is not None
        ]
        costs = [r.answer.usage.cost_usd for r in records]
        claim_keys = [
            (r.question_id, r.arm, r.trace_id, str(c.index)) for r in records for c in r.claims
        ]
        reviewed = [labels[k] for k in claim_keys if k in labels]
        faithfulness = None
        if (
            run.complete
            and claim_keys
            and len(reviewed) == len(claim_keys)
            and "uncertain" not in reviewed
        ):
            faithfulness = reviewed.count("supported") / len(claim_keys)
        arms[arm] = dict(
            expected_cases=len(run.question_ids),
            completed_cases=len(records),
            missing_cases=len(run.question_ids) - len(records),
            statuses=dict(statuses),
            automatic_match_rate=sum(matches) / len(matches) if matches else None,
            automatic_match_coverage=len(matches) / len(run.question_ids),
            automatic_scored_cases=len(matches),
            automatic_matches=sum(matches),
            metrics=metrics,
            original_cost_usd=str(sum(costs, Decimal(0)))
            if costs and all(c is not None for c in costs)
            else None,
            cost_measured_cases=sum(c is not None for c in costs),
            latency_p50_ms=_percentile(times, 0.5),
            latency_p95_ms=_percentile(times, 0.95),
            latency_measured_cases=len(times),
            material_claims=len(claim_keys),
            reviewed_claims=len(reviewed),
            human_review_coverage=len(reviewed) / len(claim_keys) if claim_keys else None,
            claim_faithfulness=faithfulness,
        )
    return dict(
        scope="AMD_2022_10K-document-scoped-development",
        run_id=run.identity,
        source_fingerprint=run.source_fingerprint,
        dataset_fingerprint=run.dataset_fingerprint,
        split_fingerprint=run.split_fingerprint,
        runtime_configs=run.runtime_configs,
        runtime_config_fingerprints=run.runtime_config_fingerprints,
        index_fingerprints=run.index_fingerprints,
        software=run.software,
        scorer_version=run.config.scorer_version,
        numeric_tolerance="relative 0.001; absolute 0; unit compatibility required",
        question_ids=list(run.question_ids),
        complete=run.complete,
        replay=run.replay,
        requested_arms=list(run.config.arms),
        not_evaluated_arms=[a for a in "ABCD" if a not in run.config.arms],
        four_arm_comparison_complete=run.complete and set(run.config.arms) == set("ABCD"),
        new_usage_priced_cost_usd=str(run.new_cost_usd) if run.new_cost_usd is not None else None,
        global_ledger_accounted_delta_usd=str(run.ledger_accounted_delta_usd)
        if run.ledger_accounted_delta_usd is not None
        else None,
        global_ledger_reservation_delta_usd=str(run.new_reservation_usd)
        if run.new_reservation_usd is not None
        else None,
        quantile_method="nearest-rank; original request latency, not replay latency",
        arms=arms,
        safety=list(run.safety),
        limitations=[
            "Five-question document-scoped development pilot; not the full-corpus benchmark.",
            "Automatic match is a value/text proxy with coverage; semantic review is required.",
            "Faithfulness needs complete fingerprint-bound human review; no paid model judge.",
            "Annotated-page recall can miss equivalent evidence; it is not citation support.",
            "Original usage differs from new spending; ledger deltas may include other writers.",
            "Small-sample p50/p95 do not establish the latency or 95% faithfulness targets.",
        ],
    )


def _display(value):
    if value is None:
        return "unknown"
    return f"{value:.3f}" if isinstance(value, float) else str(value)


def _markdown(text):
    return re.sub(r"([\\`*_{}\[\]()#+.!|>$<>])", r"\\\1", str(text).replace("\n", " "))


def markdown_report(run, summary):
    lines = [
        "# AMD development evaluation",
        "",
        f"Run: `{run.identity}`",
        "",
        "Scope: AMD 2022 Form 10-K, frozen development questions only.",
        "",
        "| Arm | Cases / expected | Matches / scored | Coverage | "
        "Page hit@5 | p50 / p95 ms | Human faithfulness |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for arm, row in summary["arms"].items():
        hit = row["metrics"].get("page_hit_at_5", {}).get("mean")
        lines.append(
            f"| {arm} | {row['completed_cases']} / {row['expected_cases']} | "
            f"{row['automatic_matches']} / {row['automatic_scored_cases']} | "
            f"{_display(row['automatic_match_coverage'])} | {_display(hit)} | "
            f"{_display(row['latency_p50_ms'])} / {_display(row['latency_p95_ms'])} | "
            f"{_display(row['claim_faithfulness'])} |"
        )
    lines += [
        "",
        "New usage-priced cost this execution: "
        f"{_display(summary['new_usage_priced_cost_usd'])} USD.",
        "",
        f"Arms not evaluated: {', '.join(summary['not_evaluated_arms']) or 'none'}.",
        "",
        "## Case diagnostics",
        "",
        "| Case | Arm | Status | Automatic check | Reason | Context gold-page recall |",
        "|---|---|---|---|---|---:|",
    ]
    for r in run.records:
        lines.append(
            f"| {_markdown(r.question_id)} | {r.arm} | {r.status} | "
            f"{_display(r.match['match'])} | {_markdown(r.match['reason'])} | "
            f"{_display(r.metrics.get('retained_context_gold_page_recall'))} |"
        )
    lines += [
        "",
        "These diagnostics locate measured gaps; they are not human judgments of semantic support.",
        "",
        "## Limitations",
        "",
    ] + ["- " + text for text in summary["limitations"]]
    lines += [
        "",
        "The private cases and human review worksheet are under `data/evaluation/phase4/`.",
        "The aggregate chart HTML uses CDN JavaScript; JSON/CSV/Markdown remain offline-readable.",
        "",
    ]
    return "\n".join(lines)


def write_reports(run, output_dir: Path, *, review=None):
    private = Path("data/evaluation/phase4") / run.identity[:20]
    public = output_dir.resolve()
    private = private.resolve()
    if public == private or public in private.parents or private in public.parents:
        raise ValueError("Separate public summaries from private annotations")
    summary = aggregate_run(run, review=review)
    public.mkdir(parents=True, exist_ok=True)
    private.mkdir(parents=True, exist_ok=True)
    write_json_atomic(public / "summary.json", summary, indent=2)
    (public / "summary.md").write_text(markdown_report(run, summary), encoding="utf-8")
    fields = [
        "question_id",
        "arm",
        "status",
        "question",
        "reference",
        "answer",
        "automatic_match",
        "reason",
        "trace_id",
    ]
    with (private / "cases.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for r in run.records:
            row = dict(
                question_id=r.question_id,
                arm=r.arm,
                status=r.status,
                question=r.question,
                reference=r.reference,
                answer=r.answer.answer_text,
                automatic_match=r.match["match"],
                reason=r.match["reason"],
                trace_id=r.trace_id,
            )
            writer.writerow({k: csv_text(v) for k, v in row.items()})
    (private / "cases.jsonl").write_text(
        "".join(r.model_dump_json() + "\n" for r in run.records), encoding="utf-8"
    )
    worksheet = private / "review.csv"
    write_review(run, worksheet)
    import altair as alt

    data = [
        dict(arm=arm, metric=name, value=row["mean"], measured_cases=row["measured_cases"])
        for arm, metrics in summary["arms"].items()
        for name, row in metrics["metrics"].items()
        if row["mean"] is not None
    ]
    chart = (
        alt.Chart(alt.Data(values=data))
        .mark_bar()
        .encode(
            x=alt.X("metric:N", title="Measured retrieval / integrity proxy"),
            y=alt.Y("value:Q", scale=alt.Scale(domain=[0, 1]), title="Mean"),
            color="arm:N",
            xOffset="arm:N",
            tooltip=["arm:N", "metric:N", "value:Q", "measured_cases:Q"],
        )
        .properties(width=640, height=320, title="AMD development pilot — measured proxies")
    )
    (public / "metrics.html").write_text(chart.to_html(), encoding="utf-8")
    (public / "metrics.vega-lite.json").write_text(chart.to_json(), encoding="utf-8")
    return dict(
        public=[
            public / n
            for n in ("summary.json", "summary.md", "metrics.html", "metrics.vega-lite.json")
        ],
        review=worksheet,
        private=[private / "cases.csv", private / "cases.jsonl", worksheet],
    )
