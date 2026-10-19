"""Cache-only embeddings and durable no-repurchase dense-pool receipts."""

import copy
import json
import re
from dataclasses import dataclass, replace
from time import monotonic

from finsight.contracts.base import fingerprint
from finsight.indexing.store import index_build_lock
from finsight.ingestion.cache import write_json_atomic
from finsight.retrieval.experiments import DensePool
from finsight.runtime.errors import FinsightError


@dataclass(frozen=True)
class CachedEmbeddingsOnly:
    cache: object
    context: object = None

    def for_run(self, context):
        return replace(self, context=context)

    def _get(self, text, role):
        if self.context is not None:
            self.context.remaining()
        record = self.cache.get(self.cache.key(text, role))
        if record is None:
            raise FinsightError(
                "query_embeddings_missing" if role == "query" else "experiment_embeddings_missing"
            )
        return list(record.vector)

    def embed_documents(self, texts):
        return [self._get(t, "document") for t in texts]

    def embed_query(self, text):
        return self._get(text, "query")


def retrieve_pool(
    root,
    retriever,
    request,
    context,
    cache,
    backend_factory,
    *,
    allow_paid=False,
    attempt_id="primary",
):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", attempt_id):
        raise FinsightError("experiment_configuration")
    identity = dict(
        request=fingerprint(request.model_dump(mode="json")),
        index=retriever.manifest.fingerprint(),
        query_key=cache.key(request.question, "query"),
        attempt_id=attempt_id,
    )
    key = fingerprint(identity)
    directory = root / "pools" / key[:24]
    path = directory / "pool.json"
    bound = copy.copy(retriever)
    bound.embeddings = CachedEmbeddingsOnly(cache)
    started = monotonic()
    with index_build_lock(directory / "guard"):
        record = cache.get(identity["query_key"])
        if path.exists():
            try:
                receipt = json.loads(path.read_text(encoding="utf-8"))
                if receipt["identity"] != identity:
                    raise FinsightError("experiment_pool_integrity")
                if not receipt["complete"]:
                    raise FinsightError("experiment_interrupted")
                pool = DensePool.model_validate(receipt["pool"])
                if (
                    receipt["payload_fingerprint"] != fingerprint(receipt["pool"])
                    or record is None
                    or receipt["query_payload_hash"] != record.payload_hash
                    or pool.index_fingerprint != retriever.manifest.fingerprint()
                    or pool.candidates != bound.retrieve(request, context)
                ):
                    raise FinsightError("experiment_pool_integrity")
                return pool.model_copy(
                    update={
                        "replay": True,
                        "attempts": (),
                        "elapsed_ms": (monotonic() - started) * 1000,
                    }
                )
            except FinsightError:
                raise
            except (ValueError, OSError, KeyError):
                raise FinsightError("experiment_pool_integrity") from None
        if record is None and not allow_paid:
            raise FinsightError("query_embeddings_missing")
        receipt = dict(identity=identity, complete=False)
        write_json_atomic(path, receipt)
        backend = bound.embeddings
        try:
            if record is None:
                backend = backend_factory()
                bound.embeddings = backend
            candidates = bound.retrieve(request, context)
            context.remaining()
            dispatcher = getattr(backend, "dispatcher", None)
            attempts = (
                tuple(a for a in dispatcher.attempts if a.run_id == context.run_id)
                if dispatcher
                else ()
            )
            record = cache.get(identity["query_key"])
            if record is None:
                raise FinsightError("experiment_pool_integrity")
            pool = DensePool(
                candidates=candidates,
                index_fingerprint=retriever.manifest.fingerprint(),
                attempts=attempts,
                elapsed_ms=(monotonic() - started) * 1000,
            )
            payload = pool.model_dump(mode="json")
            write_json_atomic(
                path,
                dict(
                    identity=identity,
                    complete=True,
                    pool=payload,
                    payload_fingerprint=fingerprint(payload),
                    query_payload_hash=record.payload_hash,
                ),
            )
            return pool
        except Exception as exc:
            dispatcher = getattr(backend, "dispatcher", None)
            receipt.update(
                error_code=exc.code if isinstance(exc, FinsightError) else "internal_error",
                attempts=[
                    a.model_dump(mode="json")
                    for a in dispatcher.attempts
                    if a.run_id == context.run_id
                ]
                if dispatcher
                else [],
            )
            write_json_atomic(path, receipt)
            raise
