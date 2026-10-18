"""Framework-independent ports and immutable invocation identity."""

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic
from typing import Protocol

from finsight.contracts.documents import Page
from finsight.contracts.runtime import BaselineConfig
from finsight.contracts.tracing import RunTrace
from finsight.runtime.errors import FinsightError


@dataclass(frozen=True)
class CallContext:
    run_id: str
    phase: int
    deadline: float
    clock: Callable[[], float] = field(default=monotonic, repr=False, compare=False)

    def remaining(self) -> float:
        value = self.deadline - self.clock()
        if value <= 0:
            raise FinsightError("deadline_exceeded", "Application deadline elapsed")
        return value


class OffsetTokenizer(Protocol):
    def count(self, text: str) -> int: ...
    def offsets(self, text: str) -> tuple[tuple[int, int], ...]: ...


class EmbeddingBackend(Protocol):
    def for_run(self, context: CallContext) -> "EmbeddingBackend": ...
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...


class PageRepository(Protocol):
    def get(self, document_id: str, page_index: int) -> Page: ...


class TokenCounter(Protocol):
    def count_text(self, text: str, context: CallContext) -> int: ...
    def count_prompt(
        self, system: str, user: str, schema: dict[str, object], context: CallContext
    ) -> int: ...


class TraceRecorder(Protocol):
    def record(self, trace: RunTrace) -> None: ...


def load_baseline_config(path: Path) -> BaselineConfig:
    return BaselineConfig.model_validate_json(path.read_text(encoding="utf-8"))
