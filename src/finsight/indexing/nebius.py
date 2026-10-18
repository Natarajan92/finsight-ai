"""Explicit Nebius embeddings through the shared durable spending guard."""

from dataclasses import dataclass, replace
from uuid import uuid4

import httpx
from langchain_core.embeddings import Embeddings
from pydantic import SecretStr

from finsight.contracts import BaselineConfig, ProviderUsage
from finsight.contracts.budget import CallEstimate, RateBook
from finsight.observability.dispatch import GuardedDispatcher
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import CallContext, OffsetTokenizer

from .embedding_cache import EmbeddingCache, Role, normalize_vector

ENDPOINT = "https://api.tokenfactory.nebius.com/v1/embeddings"


@dataclass(frozen=True)
class CachedNebiusEmbeddings(Embeddings):
    client: httpx.Client
    api_key: SecretStr
    tokenizer: OffsetTokenizer
    cache: EmbeddingCache
    config: BaselineConfig
    dispatcher: GuardedDispatcher
    context: CallContext | None = None

    def for_run(self, context: CallContext) -> "CachedNebiusEmbeddings":
        return replace(self, context=context)

    def estimate_embedding_batch(
        self, texts: list[str], role: Role, rates: RateBook
    ) -> CallEstimate:
        counts = [self.tokenizer.count(self.cache.submitted(t, role)) for t in texts]
        if any(c > 32768 for c in counts):
            raise FinsightError("embedding_token_limit")
        count = sum(c + 64 for c in counts)
        try:
            card = rates.card("nebius", self.config.embedding_model)
        except LookupError:
            raise FinsightError("rate_unavailable") from None
        return CallEstimate(
            request_id=uuid4().hex,
            provider="nebius",
            model=self.config.embedding_model,
            rate_fingerprint=rates.fingerprint(),
            input_tokens=count,
            max_output_tokens=0,
            input_count=len(texts),
            maximum_usd=card.maximum(count, 0),
        )

    def _usage(self, raw: httpx.Response) -> ProviderUsage | None:
        usage = raw.json().get("usage")
        if not isinstance(usage, dict):
            return None
        count = usage.get("prompt_tokens")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            count = None
        return ProviderUsage(
            provider="nebius",
            model=self.config.embedding_model,
            input_tokens=count,
            output_tokens=0,
            usage_known=count is not None,
        )

    def _embed(self, texts: list[str], role: Role) -> list[list[float]]:
        if self.context is None:
            raise FinsightError("missing_call_context")
        self.context.remaining()
        if any(not text.strip() for text in texts):
            raise FinsightError("embedding_input")
        records = {}
        pending = {}
        keys = [self.cache.key(text, role) for text in texts]
        for text, key in zip(texts, keys, strict=True):
            cached = self.cache.get(key)
            if cached is not None:
                records[key] = cached
            else:
                pending[key] = text
        items = list(pending.items())
        for offset in range(0, len(items), 16):
            batch = items[offset : offset + 16]
            original = [text for _, text in batch]
            submitted = [self.cache.submitted(text, role) for text in original]
            estimate = self.estimate_embedding_batch(original, role, self.dispatcher.rates)

            def send(inputs=submitted):
                response = self.client.post(
                    ENDPOINT,
                    headers={"Authorization": "Bearer " + self.api_key.get_secret_value()},
                    json={
                        "model": self.config.embedding_model,
                        "input": inputs,
                        "dimensions": self.config.embedding_dimension,
                        "encoding_format": "float",
                        "service_tier": "default",
                    },
                    follow_redirects=False,
                    timeout=self.dispatcher.timeout(self.context),
                )
                response.raise_for_status()
                return response

            raw = self.dispatcher.execute(estimate, send, self._usage, self.context)
            try:
                payload = raw.json()
                data = payload["data"]
                if (
                    payload.get("model") != self.config.embedding_model
                    or len(data) != len(batch)
                    or any(type(row["index"]) is not int for row in data)
                    or sorted(row["index"] for row in data) != list(range(len(batch)))
                ):
                    raise FinsightError("embedding_shape")
                ordered = sorted(data, key=lambda row: row["index"])
                vectors = [
                    normalize_vector(row["embedding"], self.config.embedding_dimension)
                    for row in ordered
                ]
            except (KeyError, ValueError, TypeError):
                raise FinsightError("embedding_shape") from None
            # Validate the whole batch before committing any vectors from it.
            for (key, text), vector in zip(batch, vectors, strict=True):
                record = self.cache.record(text, role, vector)
                self.cache.put(record)
                records[key] = record
        return [list(records[key].vector) for key in keys]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts, "document")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], "query")[0]
