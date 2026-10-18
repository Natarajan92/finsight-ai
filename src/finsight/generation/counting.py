"""Approximate model-specific counts with explicit padding; no local fallback."""

import json
import math
from threading import Lock
from uuid import uuid4

from finsight.contracts import BaselineConfig
from finsight.contracts.base import fingerprint
from finsight.contracts.tracing import ProviderAttempt
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import CallContext, TokenCounter


def admit_input_tokens(estimate: int, config: BaselineConfig) -> int:
    if type(estimate) is not int or estimate < 0:
        raise FinsightError("token_count_unavailable")
    padded = estimate + max(512, math.ceil(estimate * 0.10))
    if padded > config.input_tokens:
        raise FinsightError("input_token_limit")
    return padded


def validate_question(
    question: str, counter: TokenCounter, context: CallContext, config: BaselineConfig
) -> int:
    context.remaining()
    count = counter.count_text(question, context)
    if type(count) is not int or count < 0:
        raise FinsightError("token_count_unavailable")
    if count > config.question_tokens:
        raise FinsightError("question_token_limit")
    return count


class ClaudeTokenCounter:
    def __init__(self, client, model: str):
        self.client = client
        self.model = model
        self._counts = {}
        self._attempts = []
        self.records = []
        self._lock = Lock()

    @property
    def attempts(self):
        with self._lock:
            return tuple(self._attempts)

    def _count(self, system: str, user: str, context: CallContext) -> int:
        context.remaining()
        payload = {"model": self.model, "messages": [{"role": "user", "content": user}]}
        if system:
            payload["system"] = system
        identity = fingerprint(payload)
        with self._lock:
            cached = self._counts.get(identity)
        if cached is not None:
            self.records.append(
                dict(
                    run_id=context.run_id,
                    request_fingerprint=identity,
                    estimate=cached,
                    method="claude_count_tokens",
                    cached=True,
                )
            )
            return cached
        started = context.clock()
        error = None
        try:
            client = self.client.with_options(max_retries=0, timeout=min(20, context.remaining()))
            response = client.messages.count_tokens(**payload)
            count = response.input_tokens
            if type(count) is not int or count < 0:
                raise ValueError("Missing token estimate")
            with self._lock:
                self._counts[identity] = count
            self.records.append(
                dict(
                    run_id=context.run_id,
                    request_fingerprint=identity,
                    estimate=count,
                    method="claude_count_tokens",
                    cached=False,
                )
            )
            context.remaining()
            return count
        except FinsightError as exc:
            error = exc.code
            raise
        except Exception:
            error = "token_count_unavailable"
            raise FinsightError(error) from None
        finally:
            with self._lock:
                self._attempts.append(
                    ProviderAttempt(
                        request_id=uuid4().hex,
                        run_id=context.run_id,
                        provider="anthropic",
                        model=self.model,
                        purpose="free_token_count",
                        error_code=error,
                        latency_ms=max(0, (context.clock() - started) * 1000),
                    )
                )

    def count_text(self, text: str, context: CallContext) -> int:
        return self._count("", text, context)

    def count_prompt(
        self, system: str, user: str, schema: dict[str, object], context: CallContext
    ) -> int:
        serialized = json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return self._count(system, user + "\nOutput schema:\n" + serialized, context)
