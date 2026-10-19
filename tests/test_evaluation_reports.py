"""Public reports omit gold and preserve unknowns and review denominators."""

import csv
import importlib.util
import json
from decimal import Decimal

import pytest

from finsight.contracts import Answer, UsageMetrics
from finsight.evaluation.models import (
    EvaluationConfig,
    EvaluationRecord,
    EvaluationRun,
    ReviewClaim,
)
from finsight.runtime.errors import FinsightError


@pytest.fixture
def report_run(evidence_data):
    records = []
    for i in (1, 2):
        answer = Answer(
            status="answered",
            answer_text="PRIVATE_ANSWER_SENTINEL",
            citations=(evidence_data,),
            usage=UsageMetrics(
                latency_ms=10 if i == 1 else 100, cost_usd=Decimal("0.01") if i == 1 else None
            ),
        )
        records.append(
            EvaluationRecord(
                question_id=f"q{i}",
                arm="A",
                question="=PRIVATE_QUESTION_SENTINEL",
                reference="PRIVATE_GOLD_SENTINEL",
                status="answered",
                answer=answer,
                trace_id=f"trace{i}",
                trace_fingerprint=str(i) * 64,
                metrics={"page_hit_at_5": 1.0 if i == 1 else 0.0, "claim_faithfulness": None},
                match={
                    "match": True if i == 1 else None,
                    "method": "numeric",
                    "reason": "example",
                    "claim_faithfulness": None,
                },
                claims=(
                    ReviewClaim(
                        index=1, text="PRIVATE_CLAIM_SENTINEL", fingerprint=str(i + 2) * 64
                    ),
                ),
            )
        )
    return EvaluationRun(
        config=EvaluationConfig(),
        identity="a" * 64,
        source_fingerprint="b" * 64,
        dataset_fingerprint="c" * 64,
        split_fingerprint="d" * 64,
        question_ids=("q1", "q2"),
        expected_records=2,
        records=tuple(records),
        complete=True,
        safety=({"name": "forecast", "arm": "A", "passed": True},),
        new_cost_usd=Decimal(0),
    )


def reporting():
    assert importlib.util.find_spec("finsight.evaluation.reporting"), "Missing evaluation reports"
    from finsight.evaluation import reporting

    return reporting


def test_aggregate_has_honest_coverage_unknown_cost_and_small_sample_quantiles(report_run):
    summary = reporting().aggregate_run(report_run)
    arm = summary["arms"]["A"]
    assert arm["expected_cases"] == 2 and arm["completed_cases"] == 2
    assert arm["automatic_match_rate"] == 1 and arm["automatic_match_coverage"] == 0.5
    assert arm["metrics"]["page_hit_at_5"]["mean"] == 0.5
    assert arm["original_cost_usd"] is None
    assert arm["latency_p50_ms"] == 10 and arm["latency_p95_ms"] == 100
    assert arm["claim_faithfulness"] is None and arm["human_review_coverage"] == 0
    assert summary["four_arm_comparison_complete"] is False


def test_public_exports_do_not_disclose_questions_gold_answers_or_claims(
    report_run, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    paths = reporting().write_reports(report_run, tmp_path / "results")
    for path in paths["public"]:
        content = path.read_text(encoding="utf-8")
        assert "PRIVATE_" not in content
    private = tmp_path / "data/evaluation/phase4" / report_run.identity[:20]
    with (private / "cases.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["question"] == "'=PRIVATE_QUESTION_SENTINEL"
    assert rows[0]["reference"] == "PRIVATE_GOLD_SENTINEL"
    assert (private / "cases.jsonl").is_file() and (private / "review.csv").is_file()
    assert json.loads((tmp_path / "results/summary.json").read_text())["complete"] is True


def test_partial_and_stale_human_reviews_cannot_claim_complete_faithfulness(
    report_run, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    module = reporting()
    paths = module.write_reports(report_run, tmp_path / "results")
    path = paths["review"]
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames
    rows[0].update(
        verdict="supported",
        reviewer="Synthetic reviewer",
        notes="Exact quote supports this synthetic claim.",
    )

    def save():
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    save()
    summary = module.aggregate_run(report_run, review=path)
    assert summary["arms"]["A"]["claim_faithfulness"] is None
    assert summary["arms"]["A"]["human_review_coverage"] == 0.5
    rows[1].update(
        verdict="unsupported", reviewer="Synthetic reviewer", notes="Synthetic contradiction."
    )
    save()
    assert module.aggregate_run(report_run, review=path)["arms"]["A"]["claim_faithfulness"] == 0.5
    rows[1]["claim_fingerprint"] = "0" * 64
    save()
    with pytest.raises(FinsightError, match="review_integrity"):
        module.aggregate_run(report_run, review=path)


def test_cli_defaults_do_not_purchase_and_errors_do_not_print_gold(capsys, monkeypatch):
    assert importlib.util.find_spec("finsight.evaluation.runner_cli"), "Missing evaluation CLI"
    from finsight.evaluation import runner_cli

    def fail(*args, **kwargs):
        raise ValueError("PRIVATE_GOLD_SENTINEL")

    monkeypatch.setattr(runner_cli, "create_experiment_lab", fail)
    assert runner_cli.main(["run"]) == 1
    captured = capsys.readouterr().out
    assert "PRIVATE_GOLD_SENTINEL" not in captured and json.loads(captured)["status"] == "error"
