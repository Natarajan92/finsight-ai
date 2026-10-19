"""Durable AMD answer receipts around the shared application service."""

import json

from finsight.contracts import Answer, QueryRequest
from finsight.contracts.base import fingerprint
from finsight.contracts.documents import SourceMetadata
from finsight.indexing.store import index_build_lock
from finsight.ingestion.cache import write_json_atomic
from finsight.runtime.errors import FinsightError


def scoped_request(lab, request: QueryRequest, arm: str) -> QueryRequest:
    documents = lab.corpus.documents
    if len(documents) != 1:
        raise FinsightError("experiment_pilot_scope")
    document = documents[0]
    if (
        document.company != "AMD"
        or document.doc_name != "AMD_2022_10K"
        or request.company not in {None, "AMD"}
        or request.period not in {None, document.fiscal_period}
        or request.document_ids not in {None, (document.document_id,)}
    ):
        raise FinsightError("experiment_pilot_scope")
    config = lab.config(arm)
    return QueryRequest(
        **{
            **request.model_dump(),
            "company": document.company,
            "period": document.fiscal_period,
            "document_ids": (document.document_id,),
            "chunk_strategy": config.chunk_strategy,
            "rerank": config.rerank,
        }
    )


def _validate_answer(lab, retriever, answer):
    document = lab.corpus.documents[0]
    lab.pages.validate(document.document_id)
    source = SourceMetadata(**{k: getattr(document, k) for k in SourceMetadata.model_fields})
    for citation in answer.citations:
        chunk = retriever.catalog.chunks_by_id.get(citation.chunk_id)
        if (
            citation.document_id != document.document_id
            or citation.source != source
            or not 0 <= citation.page_index < document.page_count
            or chunk is None
            or citation.page_index not in {s.page_index for s in chunk.source_spans}
            or citation.source_quote not in chunk.content
            or citation.source_quote
            not in lab.pages.get(document.document_id, citation.page_index).text
        ):
            raise FinsightError("experiment_replay_integrity")


def ask_pilot(lab, request: QueryRequest, arm: str, *, allow_paid: bool = False) -> dict:
    request = scoped_request(lab, request, arm)
    retriever = lab.open(arm)
    identity = dict(
        schema_version="1",
        request=request.model_dump(mode="json"),
        source=lab.corpus.source_fingerprint,
        index=retriever.manifest.fingerprint(),
        config=lab.config(arm).fingerprint(),
    )
    directory = lab.trace_root / "pilot" / fingerprint(identity)
    path = directory / "answer.json"
    with index_build_lock(directory / "guard"):
        if path.exists():
            try:
                receipt = json.loads(path.read_text(encoding="utf-8"))
                if receipt["identity"] != identity:
                    raise FinsightError("experiment_replay_integrity")
                if receipt["complete"] is not True:
                    raise FinsightError("experiment_interrupted")
                result = receipt["result"]
                if receipt["payload_fingerprint"] != fingerprint(result):
                    raise FinsightError("experiment_replay_integrity")
                answer = Answer.model_validate(result["answer"])
                _validate_answer(lab, retriever, answer)
                return {**result, "replay": True}
            except FinsightError:
                raise
            except (ValueError, OSError, KeyError, TypeError):
                raise FinsightError("experiment_replay_integrity") from None
        if not allow_paid:
            raise FinsightError("paid_not_authorized")
        # Setup validates rates, authority, credentials and index before a start marker.
        service = lab.application(arm, allow_paid=True)
        write_json_atomic(path, dict(identity=identity, complete=False))
        # A crash/exception after this point leaves the marker, blocking repurchase.
        answer = service.answer(request)
        _validate_answer(lab, retriever, answer)
        result = dict(
            answer=answer.model_dump(mode="json"),
            trace_id=service.last_trace_id,
            request=request.model_dump(mode="json"),
            source_fingerprint=lab.corpus.source_fingerprint,
            index_fingerprint=retriever.manifest.fingerprint(),
            arm=arm,
            replay=False,
        )
        write_json_atomic(
            path,
            dict(
                identity=identity,
                complete=True,
                result=result,
                payload_fingerprint=fingerprint(result),
            ),
        )
        return result
