"""Guarded native structured generation; usage precedes validation and is never repaired."""

from uuid import uuid4

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langsmith import tracing_context
from pydantic import SecretStr

from finsight.contracts import BaselineConfig, ProviderUsage
from finsight.contracts.budget import CallEstimate
from finsight.contracts.generation import DraftAnswer, GroundedPrompt
from finsight.observability.dispatch import GuardedDispatcher
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import CallContext, TokenCounter

from .counting import admit_input_tokens
from .prompts import PROMPT_VERSION


def create_chat(config: BaselineConfig, api_key: SecretStr) -> ChatAnthropic:
    return ChatAnthropic(
        model=config.generation_model,
        api_key=api_key,
        max_tokens=config.output_tokens,
        max_retries=0,
        timeout=config.attempt_timeout_s,
        output_config={"effort": config.effort},
        thinking={"type": config.thinking_type},
        model_kwargs={"service_tier": config.generation_service_tier},
    )


class ClaudeGenerator:
    def __init__(
        self,
        config: BaselineConfig,
        dispatcher: GuardedDispatcher,
        counter: TokenCounter,
        *,
        chat: ChatAnthropic,
    ):
        self.config = config
        self.dispatcher = dispatcher
        self.counter = counter
        self.chat = chat
        if (
            chat.model != config.generation_model
            or chat.max_tokens != config.output_tokens
            or chat._client.max_retries != 0
        ):
            raise FinsightError("provider_configuration")
        self.structured = chat.with_structured_output(
            DraftAnswer, method="json_schema", include_raw=True
        )

    def _usage(self, bundle) -> ProviderUsage | None:
        raw = bundle.get("raw")
        metadata = getattr(raw, "response_metadata", {})
        usage = metadata.get("usage")
        if not isinstance(usage, dict):
            return None

        def count(name):
            value = usage.get(name)
            return value if type(value) is int and value >= 0 else None

        input_count = count("input_tokens")
        output_count = count("output_tokens")  # Already includes thinking; do not add it twice.
        return ProviderUsage(
            provider="anthropic",
            model=metadata.get("model", self.config.generation_model),
            input_tokens=input_count,
            output_tokens=output_count,
            cache_read_tokens=count("cache_read_input_tokens"),
            cache_write_tokens=count("cache_creation_input_tokens"),
            usage_known=input_count is not None and output_count is not None,
        )

    def generate(self, prompt: GroundedPrompt, context: CallContext) -> DraftAnswer:
        context.remaining()
        if self.config.prompt_version != PROMPT_VERSION:
            raise FinsightError("unsupported_prompt")
        estimate = self.counter.count_prompt(prompt.system, prompt.user, prompt.schema, context)
        admit_input_tokens(estimate, self.config)
        try:
            rate = self.dispatcher.rates.card("anthropic", self.config.generation_model)
        except LookupError:
            raise FinsightError("rate_unavailable") from None
        call = CallEstimate(
            request_id=uuid4().hex,
            provider="anthropic",
            model=self.config.generation_model,
            rate_fingerprint=self.dispatcher.rates.fingerprint(),
            input_tokens=self.config.input_tokens,
            max_output_tokens=self.config.output_tokens,
            maximum_usd=rate.maximum(self.config.input_tokens, self.config.output_tokens),
        )
        messages = [SystemMessage(prompt.system), HumanMessage(prompt.user)]

        def send():
            with tracing_context(enabled=False):
                return self.structured.invoke(
                    messages,
                    config={"callbacks": []},
                    timeout=min(self.config.attempt_timeout_s, context.remaining()),
                )

        bundle = self.dispatcher.execute(call, send, self._usage, context)
        raw = bundle.get("raw")
        reason = getattr(raw, "response_metadata", {}).get("stop_reason")
        if reason == "refusal":
            return DraftAnswer(status="insufficient_evidence", limitations=("provider_refusal",))
        if reason == "max_tokens":
            raise FinsightError("generation_truncated")
        if not getattr(raw, "content", None):
            raise FinsightError("generation_empty")
        if bundle.get("parsing_error") is not None or not isinstance(
            bundle.get("parsed"), DraftAnswer
        ):
            raise FinsightError("generation_schema")
        context.remaining()
        return bundle["parsed"]
