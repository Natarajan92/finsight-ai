"""Local run records; benchmark labels and provider objects are excluded."""

from typing import Literal

from .answers import Answer
from .base import Contract, NonBlank, NonnegativeFloat
from .context import EvidencePacket
from .generation import DraftAnswer, GroundedPrompt
from .retrieval import QueryRequest, RetrievalCandidate
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
    started_monotonic: NonnegativeFloat = 0
    input_count: int = 1


class RunTrace(Contract):
    run_id: NonBlank
    config_fingerprint: NonBlank
    source_fingerprint: NonBlank
    index_fingerprint: str | None = None
    prompt_fingerprint: str | None = None
    request_fingerprint: NonBlank
    request: QueryRequest
    budget_id: NonBlank
    rate_fingerprint: str | None = None
    packet: EvidencePacket | None = None
    prompt: GroundedPrompt | None = None
    draft: DraftAnswer | None = None
    counting: tuple[dict[str, object], ...] = ()
    filters: dict[str, object] = {}
    retrieved: tuple[RetrievalCandidate, ...] = ()
    packed: tuple[dict[str, object], ...] = ()
    timings_ms: dict[str, float] = {}
    attempts: tuple[ProviderAttempt, ...] = ()
    answer: Answer
    replay: bool = False
