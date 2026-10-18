"""Development-only acceptance and durable no-repurchase campaign receipts."""

import json
from pathlib import Path
from time import perf_counter

from finsight.config import Settings
from finsight.contracts import BaselineConfig, QueryRequest
from finsight.contracts.base import Contract, NonBlank, fingerprint
from finsight.contracts.ingestion import CorpusManifest
from finsight.indexing.builder import open_index
from finsight.indexing.store import index_build_lock
from finsight.ingestion.cache import write_json_atomic
from finsight.ingestion.fingerprints import sha256_file
from finsight.ingestion.manifest import company_key
from finsight.observability.tracing import JsonlTraceRecorder
from finsight.runtime.errors import FinsightError
from finsight.runtime.factory import create_application, local_assets, preflight, spending_setup

from .benchmark import load_benchmark
from .replay import validate_campaign_trace
from .splits import SplitManifest, SplitPolicy, freeze_splits, validate_split_pair


class SmokeCase(Contract):
    question_id: NonBlank
    request: QueryRequest


def select_development_cases(
    questions: Path, corpus: CorpusManifest, split_dir: Path, count: int = 3
) -> tuple[SmokeCase, ...]:
    if type(count) is not int or not 1 <= count <= 6:
        raise ValueError("Smoke count must be between one and six")
    cases = load_benchmark(questions, corpus)
    dev = SplitManifest.model_validate_json(
        (split_dir / "development.json").read_text(encoding="utf-8")
    )
    hold = SplitManifest.model_validate_json(
        (split_dir / "holdout.json").read_text(encoding="utf-8")
    )
    policy = SplitPolicy.model_validate_json(
        (split_dir / "split-policy.json").read_text(encoding="utf-8")
    )
    validate_split_pair(dev, hold)
    if freeze_splits(cases, policy, sha256_file(questions), corpus.source_fingerprint) != (
        dev,
        hold,
    ):
        raise ValueError("Dataset/split membership changed")
    selected = []
    companies = set()
    for case in sorted(cases, key=lambda c: c.financebench_id):
        key = company_key(case.company)
        if case.financebench_id in dev.question_ids and key not in companies:
            selected.append(
                SmokeCase(
                    question_id=case.financebench_id, request=QueryRequest(question=case.question)
                )
            )
            companies.add(key)
            if len(selected) == count:
                return tuple(selected)
    raise ValueError("Not enough distinct development companies")


class _NoDispatch:
    def for_run(self, context):
        return self

    def embed_query(self, text):
        raise FinsightError("campaign_integrity")


def _trace_summary(trace, question_id: str, latency_ms: float) -> dict[str, object]:
    return dict(
        question_id=question_id,
        trace_id=trace.run_id,
        status=trace.answer.status,
        citations=len(trace.answer.citations),
        latency_ms=latency_ms,
        usage=trace.answer.usage.model_dump(mode="json"),
        error_code=trace.answer.error.code if trace.answer.error else None,
        prompt_fingerprint=trace.prompt_fingerprint,
        trace_fingerprint=fingerprint(trace.model_dump(mode="json")),
    )


def run_development_campaign(
    settings: Settings,
    config: BaselineConfig,
    questions: Path,
    split_dir: Path,
    *,
    allow_paid: bool = False,
) -> dict[str, object]:
    corpus, pages, tokenizer = local_assets(settings, config)
    cases = (
        *select_development_cases(questions, corpus, split_dir),
        SmokeCase(
            question_id="synthetic-future-prediction",
            request=QueryRequest(
                question="Predict AMD revenue in 2030 and recommend whether to buy its stock."
            ),
        ),
    )
    retriever = open_index(
        settings.index_root / config.fingerprint(),
        config,
        corpus,
        pages=pages,
        embeddings=_NoDispatch(),
        tokenizer=tokenizer,
    )
    try:
        index_id = retriever.manifest.fingerprint()
        catalog = retriever.catalog
    finally:
        retriever.store.client.close()
    split = SplitManifest.model_validate_json(
        (split_dir / "development.json").read_text(encoding="utf-8")
    )
    identity = dict(
        config_fingerprint=config.fingerprint(),
        source_fingerprint=corpus.source_fingerprint,
        index_fingerprint=index_id,
        split_fingerprint=split.split_fingerprint,
        budget_id=config.budget_id,
        requests=[
            dict(
                question_id=c.question_id,
                request_fingerprint=fingerprint(c.request.model_dump(mode="json")),
            )
            for c in cases
        ],
    )
    campaign_id = fingerprint(identity)
    path = settings.trace_root / ("campaign-" + campaign_id + ".json")
    sink = JsonlTraceRecorder(settings.trace_root)
    # SQLite releases the lock on process death; a started receipt still blocks repurchase.
    with index_build_lock(settings.trace_root / "campaign-guard"):
        if path.exists():
            try:
                receipt = json.loads(path.read_text(encoding="utf-8"))
                if receipt["identity"] != identity:
                    raise FinsightError("campaign_integrity")
                if not receipt["complete"]:
                    raise FinsightError("campaign_interrupted")
                if len(receipt["runs"]) != len(cases):
                    raise FinsightError("campaign_integrity")
                for case, row in zip(cases, receipt["runs"], strict=True):
                    trace = sink.load(row["trace_id"])
                    if row["question_id"] != case.question_id:
                        raise FinsightError("campaign_integrity")
                    validate_campaign_trace(
                        trace,
                        case.request,
                        catalog,
                        corpus,
                        pages,
                        config,
                        index_id,
                        receipt["rate_fingerprint"],
                    )
                    if row != _trace_summary(trace, case.question_id, row["latency_ms"]):
                        raise FinsightError("campaign_integrity")
                return {**receipt, "replay": True, "campaign_id": campaign_id}
            except FinsightError:
                raise
            except (ValueError, OSError, KeyError):
                raise FinsightError("campaign_integrity") from None
        if not allow_paid:
            raise FinsightError("paid_not_authorized")
        if preflight(settings, config)["status"] != "ready":
            raise FinsightError("budget_exceeded")
        rates, ledger = spending_setup(settings, config)
        receipt = dict(
            identity=identity,
            complete=False,
            runs=[],
            rate_fingerprint=rates.fingerprint(),
            budget_before=ledger.snapshot().model_dump(mode="json"),
            scope="full_corpus",
        )
        write_json_atomic(path, receipt)
        service = create_application(settings, config, allow_paid=True)
        try:
            for case in cases:
                receipt["pending_question_id"] = case.question_id
                write_json_atomic(path, receipt)
                started = perf_counter()
                answer = service.answer(case.request)  # No labels, pages, company/document oracle.
                elapsed = (perf_counter() - started) * 1000
                trace = sink.load(service.last_trace_id)
                if trace.answer != answer:
                    raise FinsightError("campaign_integrity")
                validate_campaign_trace(
                    trace,
                    case.request,
                    catalog,
                    corpus,
                    pages,
                    config,
                    index_id,
                    receipt["rate_fingerprint"],
                )
                receipt["runs"].append(_trace_summary(trace, case.question_id, elapsed))
                receipt.pop("pending_question_id")
                write_json_atomic(path, receipt)
            receipt["complete"] = True
            receipt["budget_after"] = ledger.snapshot().model_dump(mode="json")
            write_json_atomic(path, receipt)
        finally:
            service.close()
        return {**receipt, "replay": False, "campaign_id": campaign_id}
