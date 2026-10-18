"""Local run records; benchmark labels and provider objects are excluded."""

from typing import Literal

from .answers import Answer
from .base import Contract, NonBlank, NonnegativeFloat
from .retrieval import RetrievalCandidate
from .runtime import Money, ProviderUsage


class ProviderAttempt(Contract):
    request_id: NonBlank
    run_id: NonBlank
    provider: Literal["nebius", "anthropic"]
    model: NonBlank
    purpose: NonBlank
    reservation_id: str | None = None
    maximum_usd: Money = 0
    usage: ProviderUsage | None = None
    error_code: str | None = None
    latency_ms: NonnegativeFloat = 0


class RunTrace(Contract):
    run_id: NonBlank
    config_fingerprint: NonBlank
    source_fingerprint: NonBlank
    index_fingerprint: str | None = None
    prompt_fingerprint: str | None = None
    request_fingerprint: NonBlank
    filters: dict[str, object] = {}
    retrieved: tuple[RetrievalCandidate, ...] = ()
    packed: tuple[dict[str, object], ...] = ()
    timings_ms: dict[str, float] = {}
    attempts: tuple[ProviderAttempt, ...] = ()
    answer: Answer
    replay: bool = False
