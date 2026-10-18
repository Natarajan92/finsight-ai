"""Role-aware embedding identities and atomic, integrity-checked vector records."""

import math
import re
from hashlib import sha256
from pathlib import Path
from typing import Literal

from finsight.contracts import BaselineConfig
from finsight.contracts.base import Contract, NonBlank, Sha256, fingerprint
from finsight.ingestion.cache import write_json_atomic
from finsight.runtime.errors import FinsightError

Role = Literal["document", "query"]


def normalize_vector(values: list[float], dimension: int) -> list[float]:
    if len(values) != dimension or any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
        for v in values
    ):
        raise FinsightError("embedding_shape")
    norm = math.hypot(*values)
    if not math.isfinite(norm) or norm == 0:
        raise FinsightError("embedding_shape")
    return [float(v / norm) for v in values]


class EmbeddingRecord(Contract):
    key: Sha256
    provider: Literal["nebius"] = "nebius"
    model: NonBlank
    role: Role
    config_fingerprint: Sha256
    submitted_text_hash: Sha256
    vector: tuple[float, ...]
    payload_hash: Sha256


class EmbeddingCache:
    def __init__(self, root: Path, config: BaselineConfig):
        self.root = Path(root)
        self.config = config
        self.config_fingerprint = fingerprint(
            {
                "schema": "1",
                "provider": "nebius",
                "model": config.embedding_model,
                "revision": config.embedding_revision,
                "dimension": config.embedding_dimension,
                "instruction": config.query_instruction,
                "normalization": config.normalize_embeddings,
                "tokenizer_model": config.tokenizer_model,
                "tokenizer_revision": config.tokenizer_revision,
            }
        )

    def submitted(self, text: str, role: Role) -> str:
        if role not in {"document", "query"}:
            raise ValueError("Unknown embedding role")
        return (
            text
            if role == "document"
            else f"Instruct: {self.config.query_instruction}\nQuery:{text}"
        )

    def key(self, text: str, role: Role) -> str:
        return fingerprint(
            {
                "config": self.config_fingerprint,
                "role": role,
                "submitted_text_hash": sha256(self.submitted(text, role).encode()).hexdigest(),
            }
        )

    def get(self, key: str) -> EmbeddingRecord | None:
        if not re.fullmatch(r"[a-f0-9]{64}", key):
            raise FinsightError("embedding_cache_integrity")
        path = self.root / (key + ".json")
        if not path.exists():
            return None
        try:
            record = EmbeddingRecord.model_validate_json(path.read_text(encoding="utf-8"))
            self._validate(record)
            if record.key != key:
                raise ValueError("Cache identity mismatch")
            return record
        except Exception:
            raise FinsightError("embedding_cache_integrity") from None

    def _validate(self, record: EmbeddingRecord) -> None:
        if (
            record.config_fingerprint != self.config_fingerprint
            or record.model != self.config.embedding_model
            or record.key
            != fingerprint(
                {
                    "config": self.config_fingerprint,
                    "role": record.role,
                    "submitted_text_hash": record.submitted_text_hash,
                }
            )
            or record.payload_hash
            != fingerprint(record.model_dump(mode="json", exclude={"payload_hash"}))
        ):
            raise FinsightError("embedding_cache_integrity")
        normalize_vector(list(record.vector), self.config.embedding_dimension)
        if not math.isclose(math.hypot(*record.vector), 1, abs_tol=1e-6):
            raise FinsightError("embedding_cache_integrity")

    def record(self, text: str, role: Role, vector: list[float]) -> EmbeddingRecord:
        payload = dict(
            key=self.key(text, role),
            provider="nebius",
            model=self.config.embedding_model,
            role=role,
            config_fingerprint=self.config_fingerprint,
            submitted_text_hash=sha256(self.submitted(text, role).encode()).hexdigest(),
            vector=normalize_vector(vector, self.config.embedding_dimension),
        )
        return EmbeddingRecord(**payload, payload_hash=fingerprint(payload))

    def put(self, record: EmbeddingRecord) -> None:
        self._validate(record)
        write_json_atomic(self.root / (record.key + ".json"), record.model_dump(mode="json"))
