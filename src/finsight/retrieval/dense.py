"""Fair filter admission and provenance joins around vector-only dense search."""

from finsight.contracts import QueryRequest, RetrievalCandidate, Score, SourceMetadata
from finsight.contracts.base import fingerprint
from finsight.indexing.catalog import page_key
from finsight.indexing.embedding_cache import normalize_vector
from finsight.indexing.store import chunk_metadata
from finsight.ingestion.manifest import company_key
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import CallContext


class DenseRetriever:
    def __init__(self, store, catalog, manifest, corpus, config, pages, embeddings):
        self.store = store
        self.catalog = catalog
        self.manifest = manifest
        self.corpus = corpus
        self.config = config
        self.pages = pages
        self.embeddings = embeddings

    def _scope(self, request: QueryRequest) -> set[str]:
        docs = self.corpus.documents
        selected = {d.document_id for d in docs}
        if request.company is not None:
            matching = {
                d.document_id
                for d in docs
                if d.company and company_key(d.company) == company_key(request.company)
            }
            if not matching:
                raise FinsightError("scope_unavailable")
            selected &= matching
        if request.period is not None:
            matching = {d.document_id for d in docs if d.fiscal_period == request.period}
            if not matching:
                raise FinsightError("scope_unavailable")
            selected &= matching
        if request.document_ids is not None:
            matching = set(request.document_ids)
            if not matching <= {d.document_id for d in docs}:
                raise FinsightError("scope_unavailable")
            selected &= matching
        if not selected:
            raise FinsightError("scope_conflict")
        return selected

    def retrieve(
        self, request: QueryRequest, context: CallContext
    ) -> tuple[RetrievalCandidate, ...]:
        context.remaining()
        if request.chunk_strategy != "fixed" or request.rerank:
            raise FinsightError("unsupported_scenario")
        scope = self._scope(request)
        vector = normalize_vector(
            self.embeddings.for_run(context).embed_query(request.question),
            self.config.embedding_dimension,
        )
        where = (
            {"document_id": {"$in": sorted(scope)}}
            if any((request.company, request.period, request.document_ids))
            else None
        )
        pool = self.store.wrapper.similarity_search_by_vector_with_relevance_scores(
            vector, k=self.config.candidate_count, filter=where
        )
        identities = [item.metadata.get("chunk_id") for item, _ in pool]
        if len(identities) != len(set(identities)) or any(
            identity not in self.manifest.vector_hashes for identity in identities
        ):
            raise FinsightError("index_integrity")
        if identities:
            stored = self.store.collection.get(ids=identities, limit=128, include=["embeddings"])
            if set(stored["ids"]) != set(identities):
                raise FinsightError("index_integrity")
            for identity, stored_vector in zip(stored["ids"], stored["embeddings"], strict=True):
                self.store.validate_vector(
                    identity,
                    stored_vector,
                    self.manifest.vector_hashes[identity],
                    self.config.embedding_dimension,
                )
        chunks = self.catalog.chunks_by_id
        documents = {d.document_id: d for d in self.corpus.documents}
        joined = []
        verified = set()
        for item, distance in pool:
            identity = item.metadata.get("chunk_id")
            chunk = chunks.get(identity)
            if (
                chunk is None
                or chunk.document_id not in scope
                or item.page_content != chunk.content
                or item.metadata != chunk_metadata(chunk, documents[chunk.document_id])
            ):
                raise FinsightError("index_integrity")
            if chunk.document_id not in verified and hasattr(self.pages, "validate"):
                self.pages.validate(chunk.document_id)
                verified.add(chunk.document_id)
            page = self.pages.get(chunk.document_id, chunk.page_start)
            span = chunk.source_spans[0]
            if (
                fingerprint(page.model_dump(mode="json"))
                != self.catalog.page_fingerprints[page_key(chunk.document_id, chunk.page_start)]
                or page.text[span.char_start : span.char_end] != chunk.content
            ):
                raise FinsightError("source_integrity")
            joined.append((float(distance), chunk))
        joined.sort(key=lambda pair: (pair[0], pair[1].chunk_id))
        return tuple(
            RetrievalCandidate(
                chunk=chunk,
                source=SourceMetadata(
                    **{
                        name: getattr(documents[chunk.document_id], name)
                        for name in SourceMetadata.model_fields
                    }
                ),
                rank=rank,
                score=Score(kind="cosine_distance", direction="lower_is_better", value=distance),
            )
            for rank, (distance, chunk) in enumerate(joined, 1)
        )
