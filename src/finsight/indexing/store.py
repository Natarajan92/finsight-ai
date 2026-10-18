"""Pinned local Chroma; all queries supply vectors; no hosted/default embeddings."""

import math
import os
import re
import sys
import tempfile
from array import array
from contextlib import closing, contextmanager
from hashlib import sha256
from pathlib import Path

import chromadb
from langchain_chroma import Chroma

from finsight.contracts.documents import Chunk, DocumentManifest
from finsight.runtime.errors import FinsightError


def _vector_bytes(vector) -> bytes:
    values = array("f", map(float, vector))
    if sys.byteorder != "little":
        values.byteswap()
    return values.tobytes()


def vector_hash(vector) -> str:
    return sha256(_vector_bytes(vector)).hexdigest()


class VectorReferences:
    """Exact input bytes; cosine HNSW may renormalize its float32 storage."""

    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, identity: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{64}", identity):
            raise FinsightError("index_integrity")
        return self.root / (identity + ".f32")

    def put(self, identity: str, vector) -> str:
        payload = _vector_bytes(vector)
        path = self._path(identity)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            if path.read_bytes() != payload:
                raise FinsightError("index_integrity")
            return sha256(payload).hexdigest()
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)
        return sha256(payload).hexdigest()

    def get(self, identity: str, expected_hash: str, dimension: int):
        try:
            with self._path(identity).open("rb") as handle:
                payload = handle.read(dimension * 4 + 1)
            if len(payload) != dimension * 4 or sha256(payload).hexdigest() != expected_hash:
                raise ValueError("Canonical vector changed")
            values = array("f")
            values.frombytes(payload)
            if sys.byteorder != "little":
                values.byteswap()
            if any(not math.isfinite(v) for v in values) or not math.isclose(
                math.hypot(*values), 1, abs_tol=1e-6
            ):
                raise ValueError("Invalid canonical vector")
            return values
        except (ValueError, OSError):
            raise FinsightError("index_integrity") from None


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
        self.references = VectorReferences(root.parent / "vector-references")
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

    def validate_vector(self, identity, vector, expected_hash: str, dimension: int) -> None:
        expected = self.references.get(identity, expected_hash, dimension)
        if (
            len(vector) != dimension
            or any(not math.isfinite(float(v)) for v in vector)
            or not math.isclose(math.hypot(*vector), 1, abs_tol=1e-4)
            or math.dist(vector, expected) > 1e-6
        ):
            raise FinsightError("index_integrity")

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
                or (complete and identity not in hashes)
            ):
                raise FinsightError("index_integrity")
            if identity in hashes:
                self.validate_vector(identity, vector, hashes[identity], dimension)
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
