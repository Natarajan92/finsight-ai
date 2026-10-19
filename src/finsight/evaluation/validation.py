"""Reopen source-derived evidence before scoring an AMD runtime receipt."""

from finsight.contracts import Answer, QueryRequest
from finsight.contracts.base import fingerprint
from finsight.observability.tracing import JsonlTraceRecorder
from finsight.retrieval.reranking import pool_fingerprint
from finsight.runtime.errors import FinsightError
from finsight.runtime.experiment_pilot import scoped_request

from .models import EvaluationRecord, ReviewClaim
from .replay import validate_campaign_trace
from .retrieval import retrieval_metrics
from .scoring import score_answer


def validate_result(lab, question, arm, result):
    expected = scoped_request(lab, QueryRequest(question=question), arm)
    retriever = lab.open(arm)
    trace = JsonlTraceRecorder(lab.trace_root / "answers").load(result["trace_id"])
    answer = Answer.model_validate(result["answer"])
    if answer != trace.answer or result["request"] != expected.model_dump(mode="json"):
        raise FinsightError("evaluation_trace_integrity")
    validate_campaign_trace(
        trace,
        expected,
        retriever.catalog,
        lab.corpus,
        lab.pages,
        lab.config(arm).index_config(),
        retriever.manifest.fingerprint(),
        trace.rate_fingerprint,
        run_fingerprint=lab.config(arm).fingerprint(),
        reranked=lab.config(arm).rerank,
    )
    pool = None
    if trace.retrieved:
        plain = QueryRequest(**{**expected.model_dump(), "rerank": False})
        pool = lab.pool(lab.config(arm).chunk_strategy, plain, lab.context("eval-replay"))
        ranked = (
            lab.reranker.rerank(question, pool.candidates, lab.context("eval-rerank")).candidates
            if lab.config(arm).rerank
            else pool.candidates
        )
        if trace.retrieved != ranked:
            raise FinsightError("evaluation_trace_integrity")
    return trace, pool


def evaluated_record(lab, case, arm, result):
    trace, pool = validate_result(lab, case.question, arm, result)
    by_name = {d.doc_name: d.document_id for d in lab.corpus.documents}
    if any(e.doc_name not in by_name for e in case.evidence):
        raise FinsightError("evaluation_scope")
    gold = {(by_name[e.doc_name], e.evidence_page_num) for e in case.evidence}
    metrics = retrieval_metrics(trace.retrieved, gold, pool=pool.candidates if pool else ())
    retained = (
        {(s.document_id, s.page_index) for s in trace.packet.slices} if trace.packet else set()
    )
    selected_docs = {c.chunk.document_id for c in trace.retrieved[:5]}
    gold_docs = {d for d, _ in gold}
    metrics.update(
        document_recall_at_5=len(selected_docs & gold_docs) / len(gold_docs),
        all_gold_pages_at_5=float(metrics["gold_page_recall_at_5"] == 1),
        retained_context_gold_page_recall=len(retained & gold) / len(gold),
        citation_integrity=1.0 if trace.answer.citations else None,
        claim_faithfulness=None,
    )
    if trace.answer.status == "error" and not trace.retrieved:
        metrics = {k: None for k in metrics}
    elif trace.packet is None:
        metrics["retained_context_gold_page_recall"] = None
    claims = (
        tuple(
            ReviewClaim(
                index=i,
                text=c.text,
                fingerprint=fingerprint(
                    {"trace_id": trace.run_id, "index": i, "claim": c.model_dump(mode="json")}
                ),
            )
            for i, c in enumerate(trace.draft.claims, 1)
        )
        if trace.draft and trace.answer.status in {"answered", "partial"}
        else ()
    )
    return EvaluationRecord(
        question_id=case.financebench_id,
        arm=arm,
        question=case.question,
        reference=case.answer,
        status=trace.answer.status,
        answer=trace.answer,
        trace_id=trace.run_id,
        trace_fingerprint=fingerprint(trace.model_dump(mode="json")),
        runtime_config_fingerprint=trace.config_fingerprint,
        index_fingerprint=trace.index_fingerprint,
        dense_pool_fingerprint=pool_fingerprint(pool.candidates) if pool else None,
        metrics=metrics,
        match=score_answer(
            trace.answer,
            case.answer,
            question=case.question,
            period=lab.corpus.documents[0].fiscal_period,
        ),
        claims=claims,
        replay=result["replay"],
    )
