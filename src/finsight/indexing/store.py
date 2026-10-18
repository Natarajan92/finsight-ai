"""Pinned local Chroma; all queries supply vectors; no hosted/default embeddings."""

import math
import sys
from array import array
from contextlib import closing, contextmanager
from hashlib import sha256
from pathlib import Path

import chromadb
from langchain_chroma import Chroma

from finsight.contracts.documents import Chunk, DocumentManifest
from finsight.runtime.errors import FinsightError


def vector_hash(vector) -> str:
    # Chroma stores float32. Canonicalize before hashing on both insertion and reopen.
    values = array("f", map(float, vector))
    if sys.byteorder != "little":
        values.byteswap()
    return sha256(values.tobytes()).hexdigest()


def chunk_metadata(chunk: Chunk, document: DocumentManifest) -> dict[str, str | int]:
    return dict(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        company=document.company or "",
        period=document.fiscal_period or "",
        config_fingerprint=chunk.config_fingerprint,
        page_index=chunk.page_start,
    )


class LocalVectorStore:
    def __init__(self, root: Path, *, create: bool):
        if not create and not (root / "chroma.sqlite3").is_file():
            raise FinsightError("index_incomplete")
        self.client = chromadb.PersistentClient(
            path=str(root), settings=chromadb.Settings(anonymized_telemetry=False)
        )
        self.wrapper = Chroma(
            client=self.client,
            collection_name="fixed_dense_v1",
            embedding_function=None,
            create_collection_if_not_exists=create,
            collection_configuration={"hnsw": {"space": "cosine", "num_threads": 1}},
        )
        self.collection = self.client.get_collection("fixed_dense_v1", embedding_function=None)
        settings = self.collection.schema.keys["#embedding"].float_list.vector_index.config
        if (
            settings.space != "cosine"
            or settings.hnsw.num_threads != 1
            or settings.embedding_function is not None
        ):
            self.client.close()
            raise FinsightError("index_integrity")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.client.close()

    def rows(self):
        for offset in range(0, self.collection.count(), 128):
            result = self.collection.get(
                limit=128, offset=offset, include=["documents", "metadatas", "embeddings"]
            )
            for key, text, metadata, vector in zip(
                result["ids"],
                result["documents"],
                result["metadatas"],
                result["embeddings"] if result["embeddings"] is not None else [],
                strict=True,
            ):
                yield key, (text, metadata, vector)

    def validate(self, catalog, corpus, dimension: int, hashes: dict[str, str], *, complete: bool):
        rows = set()
        chunks = catalog.chunks_by_id
        docs = {d.document_id: d for d in corpus.documents}
        for identity, (text, metadata, vector) in self.rows():
            if identity in rows or identity not in chunks:
                raise FinsightError("index_integrity")
            rows.add(identity)
            chunk = chunks[identity]
            if (
                text != chunk.content
                or metadata != chunk_metadata(chunk, docs[chunk.document_id])
                or len(vector) != dimension
                or any(not math.isfinite(float(v)) for v in vector)
                or not math.isclose(math.hypot(*vector), 1, abs_tol=1e-4)
                or (identity in hashes and vector_hash(vector) != hashes[identity])
                or (complete and identity not in hashes)
            ):
                raise FinsightError("index_integrity")
        if complete and rows != set(chunks):
            raise FinsightError("index_integrity")
        return rows


@contextmanager
def index_build_lock(root: Path):
    import sqlite3

    root.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(root / "build-guard.sqlite3", timeout=0.1)) as connection:
        try:
            connection.execute("CREATE TABLE IF NOT EXISTS guard (id INTEGER)")
            connection.commit()
            connection.execute("BEGIN IMMEDIATE")
        except sqlite3.Error:
            raise FinsightError("index_busy") from None
        try:
            yield
        finally:
            connection.rollback()
