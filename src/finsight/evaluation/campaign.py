"""Frozen AMD development evaluation; gold joins occur after runtime answers."""

import json
import platform
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path

from finsight.contracts import QueryRequest, UsageMetrics
from finsight.contracts.base import fingerprint
from finsight.contracts.ingestion import CorpusManifest
from finsight.indexing.store import index_build_lock
from finsight.ingestion.cache import write_json_atomic
from finsight.ingestion.fingerprints import sha256_file
from finsight.runtime.errors import FinsightError
from finsight.runtime.factory import spending_setup
from finsight.runtime.software import software_versions

from .models import EvaluationConfig, EvaluationRun
from .retrieval import development_cases
from .validation import evaluated_record, validate_result

FORECAST = "Predict AMD revenue next year."


def _config(arms, max_cost_usd):
    return EvaluationConfig(arms=tuple(arms), max_cost_usd=max_cost_usd)


def selected_cases(lab, questions: Path, split_dir: Path):
    parent = CorpusManifest.model_validate_json(
        lab.settings.manifest_path.read_text(encoding="utf-8")
    )
    document = lab.corpus.documents[0]
    if (
        len(lab.corpus.documents) != 1
        or document.company != "AMD"
        or document.doc_name != "AMD_2022_10K"
    ):
        raise FinsightError("evaluation_scope")
    if document not in parent.documents:
        raise FinsightError("evaluation_source_integrity")
    cases, split = development_cases(questions, parent, split_dir)
    selected = tuple(c for c in cases if c.company == "AMD" and c.doc_name == document.doc_name)
    if len(selected) != 5 or any(
        e.doc_name != document.doc_name for c in selected for e in c.evidence
    ):
        raise FinsightError("evaluation_scope")
    return selected, split


def _cached(lab, question, arm):
    try:
        result = lab.ask_pilot(QueryRequest(question=question), arm)
    except FinsightError as exc:
        if exc.code == "paid_not_authorized":
            return None
        raise
    validate_result(lab, question, arm, result)
    return result


def _prepare(lab, questions, split_dir, config):
    cases, split = selected_cases(lab, questions, split_dir)
    indexes, missing = {}, {}
    for arm in config.arms:
        try:
            indexes[arm] = lab.open(arm).manifest.fingerprint()
            if lab.config(arm).rerank:
                _ = lab.reranker
        except FinsightError as exc:
            missing[arm] = exc.code
    plan = dict(
        scope="AMD_2022_10K-document-scoped-development",
        status="assets_missing" if missing else "ready",
        arms=list(config.arms),
        question_ids=[c.financebench_id for c in cases],
        missing_arms=missing,
        maximum_usd="0",
        pending_answers=0,
        requires_live=False,
        source_fingerprint=lab.corpus.source_fingerprint,
        split_fingerprint=split.split_fingerprint,
        dataset_fingerprint=sha256_file(questions),
        indexes=indexes,
        config_fingerprints={a: lab.config(a).fingerprint() for a in config.arms},
        campaign_limit_usd=str(config.max_cost_usd),
        provider_network_calls=0,
    )
    cached = {}
    if missing:
        return plan, cases, split, cached, None
    for case in cases:
        for arm in config.arms:
            cached[(case.financebench_id, arm)] = _cached(lab, case.question, arm)
    for arm in config.arms:
        cached[("forecast", arm)] = _cached(lab, FORECAST, arm)
    pending = sum(cached[(c.financebench_id, a)] is None for c in cases for a in config.arms)
    plan.update(pending_answers=pending, requires_live=any(v is None for v in cached.values()))
    ledger = None
    if pending:
        rates, ledger = spending_setup(lab.settings, lab.baseline)
        embedding = rates.card("nebius", lab.baseline.embedding_model)
        generation = rates.card("anthropic", lab.baseline.generation_model)
        # Reserve the full configured ceilings and both eligible physical attempts.
        per_query = (
            embedding.maximum(32768 + 64, 0)
            + generation.maximum(lab.baseline.input_tokens, lab.baseline.output_tokens)
        ) * 2 + Decimal("0.000004")
        maximum = per_query * pending
        snapshot = ledger.snapshot()
        available = min(snapshot.available_usd, ledger.phase_available(3, limit_usd=lab.phase3_usd))
        plan.update(
            maximum_usd=str(maximum),
            available_usd=str(available),
            budget=snapshot.model_dump(mode="json"),
        )
        if maximum > min(config.max_cost_usd, available):
            plan["status"] = "budget_conflict"
    return plan, cases, split, cached, ledger


def plan_evaluation(
    lab, questions: Path, split_dir: Path, *, arms="A", max_cost_usd=Decimal("0.25")
):
    return _prepare(lab, questions, split_dir, _config(arms, max_cost_usd))[0]


def save_run(path: Path, run: EvaluationRun):
    payload = run.model_dump(mode="json")
    write_json_atomic(path, dict(payload=payload, payload_fingerprint=fingerprint(payload)))


def load_run(path: Path) -> EvaluationRun:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw["payload_fingerprint"] != fingerprint(raw["payload"]):
            raise ValueError("Run changed")
        return EvaluationRun.model_validate(raw["payload"])
    except (ValueError, OSError, KeyError, TypeError):
        raise FinsightError("evaluation_run_integrity") from None


def _usage(records):
    if not records:
        return UsageMetrics()

    def total(field):
        values = [getattr(r.answer.usage, field) for r in records]
        return None if any(v is None for v in values) else sum(values)

    return UsageMetrics(**{k: total(k) for k in UsageMetrics.model_fields})


def _safety(lab, arms, allow_paid, cached):
    records = []
    for arm in arms:
        result = cached[("forecast", arm)] or lab.ask_pilot(
            QueryRequest(question=FORECAST), arm, allow_paid=allow_paid
        )
        trace, _ = validate_result(lab, FORECAST, arm, result)
        paid = [a for a in trace.attempts if a.purpose != "free_token_count"]
        records.append(
            dict(
                name="forecast",
                arm=arm,
                trace_id=trace.run_id,
                passed=trace.answer.status == "insufficient_evidence" and not paid,
                original_paid_attempts=len(paid),
            )
        )
        try:
            lab.ask_pilot(
                QueryRequest(question="Revenue in 2022?", company="PepsiCo"),
                arm,
                allow_paid=allow_paid,
            )
        except FinsightError as exc:
            if exc.code != "experiment_pilot_scope":
                raise
            records.append(
                dict(name="wrong_company_filter", arm=arm, passed=True, original_paid_attempts=0)
            )
        else:
            records.append(dict(name="wrong_company_filter", arm=arm, passed=False))
    return tuple(records)


def run_evaluation(
    lab,
    questions: Path,
    split_dir: Path,
    output_root: Path,
    *,
    arms="A",
    max_cost_usd=Decimal("0.25"),
    allow_paid=False,
) -> EvaluationRun:
    config = _config(arms, max_cost_usd)
    plan, cases, split, cached, ledger = _prepare(lab, questions, split_dir, config)
    if plan["status"] == "assets_missing":
        raise FinsightError("evaluation_assets_missing")
    if plan["status"] == "budget_conflict":
        raise FinsightError("budget_exceeded")
    identity = fingerprint(
        {
            "config": config.model_dump(mode="json"),
            "source": plan["source_fingerprint"],
            "dataset": plan["dataset_fingerprint"],
            "split": split.split_fingerprint,
            "questions": plan["question_ids"],
            "indexes": plan["indexes"],
            "runtime_configs": plan["config_fingerprints"],
        }
    )
    directory = output_root / identity[:20]
    path = directory / "run.json"
    if plan["requires_live"] and not allow_paid:
        raise FinsightError("paid_not_authorized")
    records = []
    before = ledger.snapshot() if ledger else None
    runtime_configs = {a: lab.config(a).model_dump(mode="json") for a in config.arms}
    software = {
        **software_versions(),
        "python": platform.python_version(),
        "altair": version("altair"),
    }

    def result(complete=False, safety=()):
        after = ledger.snapshot() if ledger else None
        new_costs = [r.answer.usage.cost_usd for r in records if not r.replay]
        return EvaluationRun(
            config=config,
            identity=identity,
            source_fingerprint=plan["source_fingerprint"],
            dataset_fingerprint=plan["dataset_fingerprint"],
            split_fingerprint=split.split_fingerprint,
            runtime_configs=runtime_configs,
            runtime_config_fingerprints=plan["config_fingerprints"],
            index_fingerprints=plan["indexes"],
            software=software,
            question_ids=tuple(plan["question_ids"]),
            expected_records=len(cases) * len(config.arms),
            records=tuple(records),
            complete=complete,
            replay=bool(records) and all(r.replay for r in records),
            safety=safety,
            new_cost_usd=None if any(c is None for c in new_costs) else sum(new_costs, Decimal(0)),
            new_reservation_usd=after.reserved_usd - before.reserved_usd if after else Decimal(0),
            ledger_accounted_delta_usd=(after.accounted_usd - before.accounted_usd)
            if after
            else Decimal(0),
            original_usage=_usage(records),
        )

    with index_build_lock(directory / "guard"):
        previous = load_run(path) if path.exists() else None
        if previous and previous.identity != identity:
            raise FinsightError("evaluation_replay_integrity")
        if previous and previous.complete and plan["requires_live"]:
            # Another worker may have completed while this plan was being prepared.
            for case in cases:
                for arm in config.arms:
                    if cached[(case.financebench_id, arm)] is None:
                        cached[(case.financebench_id, arm)] = _cached(lab, case.question, arm)
            for arm in config.arms:
                if cached[("forecast", arm)] is None:
                    cached[("forecast", arm)] = _cached(lab, FORECAST, arm)
            if any(v is None for v in cached.values()):
                raise FinsightError("evaluation_replay_integrity")
        if previous is None:
            save_run(path, result())
        for case in cases:
            for arm in config.arms:
                response = cached[(case.financebench_id, arm)] or lab.ask_pilot(
                    QueryRequest(question=case.question), arm, allow_paid=allow_paid
                )
                record = evaluated_record(lab, case, arm, response)
                records.append(record)
                if previous and previous.complete:
                    original = next(
                        (
                            r
                            for r in previous.records
                            if (r.question_id, r.arm) == (record.question_id, record.arm)
                        ),
                        None,
                    )
                    if original is None or original.model_dump(
                        exclude={"replay"}
                    ) != record.model_dump(exclude={"replay"}):
                        raise FinsightError("evaluation_replay_integrity")
                else:
                    save_run(path, result())
                if record.status == "error":
                    return result()
        # Paired experiments must use identical pre-rank candidates for each case.
        for case in cases:
            by_arm = {r.arm: r for r in records if r.question_id == case.financebench_id}
            for left, right in (("A", "C"), ("B", "D")):
                if (
                    left in by_arm
                    and right in by_arm
                    and (
                        by_arm[left].dense_pool_fingerprint != by_arm[right].dense_pool_fingerprint
                    )
                ):
                    raise FinsightError("evaluation_paired_pool_integrity")
        safety = _safety(lab, config.arms, allow_paid, cached)
        final = result(complete=all(s["passed"] is True for s in safety), safety=safety)
        if previous and previous.complete:
            if previous.safety != final.safety:
                raise FinsightError("evaluation_replay_integrity")
        else:
            save_run(path, final)
        return final
