"""Shared service boundary for the future UI and offline benchmark."""

from typing import Protocol

from finsight.contracts import Answer, QueryRequest


class ApplicationService(Protocol):
    """Implementations receive questions/explicit filters, never benchmark labels."""

    def answer(self, request: QueryRequest) -> Answer: ...
