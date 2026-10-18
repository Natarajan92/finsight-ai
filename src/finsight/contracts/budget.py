"""Money and rate identities used by every paid provider attempt."""

from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal
from typing import Literal, Self
from urllib.parse import urlparse

from pydantic import model_validator

from .base import Contract, NonBlank, NonnegativeInt, Sha256, fingerprint
from .runtime import Money, ProviderUsage


def micro_usd(value: Decimal) -> int:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError("Money must be a finite nonnegative Decimal")
    return int((value * 1_000_000).to_integral_value(rounding=ROUND_CEILING))


def dollars(value: int) -> Decimal:
    return Decimal(value) / 1_000_000


class RateCard(Contract):
    provider: Literal["nebius", "anthropic"]
    model: NonBlank
    service_tier: Literal["default"] = "default"
    input_per_million: Money
    output_per_million: Money
    cache_read_per_million: Money | None = None
    cache_write_per_million: Money | None = None
    source_url: NonBlank
    verified_at: datetime

    @model_validator(mode="after")
    def official_source(self) -> Self:
        parsed = urlparse(self.source_url)
        allowed = (
            {"nebius.com", "docs.tokenfactory.nebius.com", "tokenfactory.nebius.com"}
            if self.provider == "nebius"
            else {"platform.claude.com", "www.anthropic.com", "anthropic.com"}
        )
        if parsed.scheme != "https" or parsed.hostname not in allowed or parsed.username:
            raise ValueError("Rate source must be an official HTTPS provider page")
        if self.verified_at.utcoffset() is None:
            raise ValueError("Rate verification needs an aware UTC time")
        return self

    def maximum(self, input_tokens: int, output_tokens: int) -> Decimal:
        return (
            input_tokens * self.input_per_million + output_tokens * self.output_per_million
        ) / 1_000_000

    def observed(self, usage: ProviderUsage) -> Decimal | None:
        if usage.cost_usd is not None and usage.cost_basis == "provider_reported":
            return usage.cost_usd
        if usage.input_tokens is None or usage.output_tokens is None:
            return None
        if self.provider == "anthropic" and (
            usage.cache_read_tokens is None or usage.cache_write_tokens is None
        ):
            return None
        result = self.maximum(usage.input_tokens, usage.output_tokens)
        for count, rate in (
            (usage.cache_read_tokens, self.cache_read_per_million),
            (usage.cache_write_tokens, self.cache_write_per_million),
        ):
            if count:
                if rate is None:
                    return None
                result += count * rate / 1_000_000
        return result


class RateBook(Contract):
    schema_version: Literal["1"] = "1"
    cards: tuple[RateCard, ...]

    @model_validator(mode="after")
    def unique_cards(self) -> Self:
        keys = [(c.provider, c.model, c.service_tier) for c in self.cards]
        if not keys or len(set(keys)) != len(keys):
            raise ValueError("Rate cards must be nonempty and unique")
        return self

    def fingerprint(self) -> str:
        return fingerprint(self.model_dump(mode="json"))

    def card(self, provider: str, model: str, tier: str = "default") -> RateCard:
        # Runtime errors are raised by dispatch, keeping contracts provider-free.
        for card in self.cards:
            if (card.provider, card.model, card.service_tier) == (provider, model, tier):
                return card
        raise LookupError("No verified rate for provider/model/tier")

    def fresh(self, now: datetime | None = None) -> bool:
        instant = now or datetime.now(UTC)
        return all(
            timedelta(0) <= instant - c.verified_at <= timedelta(hours=24) for c in self.cards
        )


class CallEstimate(Contract):
    request_id: NonBlank
    provider: Literal["nebius", "anthropic"]
    model: NonBlank
    rate_fingerprint: Sha256
    input_tokens: NonnegativeInt
    max_output_tokens: NonnegativeInt
    maximum_usd: Money
    service_tier: Literal["default"] = "default"


class Reservation(Contract):
    reservation_id: NonBlank
    request_id: NonBlank
    maximum_usd: Money
    state: Literal["reserved", "dispatched", "settled", "unknown"]


class BudgetSnapshot(Contract):
    budget_id: NonBlank
    accounted_usd: Money
    reserved_usd: Money
    available_usd: Money
    phase2_available_usd: Money
    reserve_usd: Money = Decimal("1")
