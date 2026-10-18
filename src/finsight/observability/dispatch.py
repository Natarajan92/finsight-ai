"""Reserve before sending; retain uncertain billing; retries are physical attempts."""

from collections.abc import Callable
from decimal import Decimal
from threading import Lock
from typing import TypeVar

from finsight.contracts.budget import CallEstimate, RateBook
from finsight.contracts.runtime import BaselineConfig, ProviderUsage
from finsight.contracts.tracing import ProviderAttempt
from finsight.runtime.deadlines import bounded_call
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import CallContext

from .budget import BudgetLedger

T = TypeVar("T")


class GuardedDispatcher:
    def __init__(
        self,
        ledger: BudgetLedger,
        rates: RateBook,
        *,
        config: BaselineConfig | None = None,
        phase3_usd: Decimal = Decimal("0.75"),
    ):
        self.ledger = ledger
        self.rates = rates
        self.config = config or BaselineConfig()
        self.phase3_usd = phase3_usd
        self._attempts: list[ProviderAttempt] = []
        self._lock = Lock()

    @property
    def attempts(self) -> tuple[ProviderAttempt, ...]:
        with self._lock:
            return tuple(self._attempts)

    def timeout(self, context: CallContext) -> float:
        return min(self.config.attempt_timeout_s, context.remaining())

    def execute(
        self,
        estimate: CallEstimate,
        send: Callable[[], T],
        usage_of: Callable[[T], ProviderUsage | None],
        context: CallContext,
    ) -> T:
        for attempt_number in range(2):
            context.remaining()
            if not self.rates.fresh():
                raise FinsightError("rate_expired")
            try:
                card = self.rates.card(estimate.provider, estimate.model, estimate.service_tier)
            except LookupError:
                raise FinsightError("rate_unavailable") from None
            if (
                estimate.rate_fingerprint != self.rates.fingerprint()
                or estimate.maximum_usd
                < card.maximum(estimate.input_tokens, estimate.max_output_tokens)
            ):
                raise FinsightError("rate_integrity")
            identity = estimate.request_id + (":retry1" if attempt_number else "")
            reservation = self.ledger.reserve(
                identity,
                estimate.provider,
                estimate.model,
                estimate.maximum_usd,
                context.phase,
                working_usd=self.config.working_usd,
                phase2_usd=self.config.phase2_usd,
                phase3_usd=self.phase3_usd,
            )
            context.remaining()
            self.ledger.mark_dispatched(reservation.reservation_id)
            started = context.clock()
            usage = None
            error = None
            retry = False
            try:
                raw = bounded_call(send, self.timeout(context))
                usage = usage_of(raw)
                if usage is not None:
                    if (usage.provider, usage.model) != (estimate.provider, estimate.model):
                        raise FinsightError("provider_usage")
                    cost = card.observed(usage)
                    basis = (
                        "unknown"
                        if cost is None
                        else "provider_reported"
                        if usage.cost_basis == "provider_reported"
                        else "usage_priced"
                    )
                    usage = usage.model_copy(update={"cost_usd": cost, "cost_basis": basis})
                self.ledger.settle(
                    reservation.reservation_id, usage.cost_usd if usage else None, usage=usage
                )
                return raw
            except Exception as exc:
                status = getattr(exc, "status_code", None)
                if status is None:
                    status = getattr(getattr(exc, "response", None), "status_code", None)
                is_timeout = isinstance(exc, TimeoutError) or "Timeout" in type(exc).__name__
                code = (
                    exc.code
                    if isinstance(exc, FinsightError)
                    else "provider_timeout"
                    if is_timeout
                    else "provider_status"
                    if status is not None
                    else "provider_failure"
                )
                error = code
                # Explicit HTTP errors may still have unknown billing. Never assume free.
                self.ledger.settle(reservation.reservation_id, None)
                retry = status in {429, 502, 503, 504} and attempt_number == 0 and not is_timeout
                if not retry:
                    raise FinsightError(code) from None
            finally:
                record = ProviderAttempt(
                    request_id=identity,
                    run_id=context.run_id,
                    provider=estimate.provider,
                    model=estimate.model,
                    purpose="embeddings" if estimate.provider == "nebius" else "generation",
                    reservation_id=reservation.reservation_id,
                    maximum_usd=reservation.maximum_usd,
                    usage=usage,
                    error_code=error,
                    latency_ms=max(0, (context.clock() - started) * 1000),
                    started_monotonic=started,
                    input_count=estimate.input_count,
                )
                with self._lock:
                    self._attempts.append(record)
            if retry:
                context.remaining()
        raise FinsightError("provider_failure")
