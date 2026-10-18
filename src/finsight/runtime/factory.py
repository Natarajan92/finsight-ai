"""Explicit construction/preflight; no clients, files or network at module import."""

from decimal import Decimal
from time import monotonic
from uuid import uuid4

import httpx

from finsight.application import BaselineApplicationService
from finsight.chunking.tokenizer import LocalOffsetTokenizer, TokenizerArtifact
from finsight.config import Settings
from finsight.contracts import BaselineConfig
from finsight.contracts.budget import RateBook
from finsight.contracts.ingestion import CorpusManifest
from finsight.generation.claude import ClaudeGenerator, create_chat
from finsight.generation.counting import ClaudeTokenCounter
from finsight.indexing.builder import build_index, open_index
from finsight.indexing.catalog import create_catalog
from finsight.indexing.embedding_cache import EmbeddingCache
from finsight.indexing.nebius import CachedNebiusEmbeddings
from finsight.ingestion.cache import write_json_atomic
from finsight.ingestion.pages import CachedPageRepository
from finsight.observability.budget import BudgetLedger
from finsight.observability.dispatch import GuardedDispatcher
from finsight.observability.tracing import JsonlTraceRecorder
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import CallContext


def local_assets(settings: Settings, config: BaselineConfig):
    try:
        corpus = CorpusManifest.model_validate_json(
            settings.manifest_path.read_text(encoding="utf-8")
        )
        if corpus.source_fingerprint != config.source_fingerprint:
            raise FinsightError("source_integrity")
        artifact = TokenizerArtifact.load(settings.tokenizer_dir)
        if (
            artifact.model != config.tokenizer_model
            or artifact.revision != config.tokenizer_revision
        ):
            raise FinsightError("tokenizer_integrity")
        tokenizer = LocalOffsetTokenizer(artifact)
        pages = CachedPageRepository(corpus, settings.source_pdf_dir, settings.page_cache_root)
        return corpus, pages, tokenizer
    except FinsightError:
        raise
    except (ValueError, OSError):
        raise FinsightError("source_integrity") from None


def spending_setup(settings: Settings, config: BaselineConfig):
    try:
        rates = RateBook.model_validate_json(settings.rates_path.read_text(encoding="utf-8"))
        if not rates.fresh():
            raise FinsightError("rate_expired")
        rates.card("nebius", config.embedding_model)
        rates.card("anthropic", config.generation_model)
    except FinsightError:
        raise
    except (ValueError, LookupError, OSError):
        raise FinsightError("rate_unavailable") from None
    ledger = BudgetLedger.open(
        settings.ledger_path, config.budget_id, anchor_path=settings.budget_anchor_path
    )
    return rates, ledger


def preflight(settings: Settings, config: BaselineConfig) -> dict[str, object]:
    corpus, pages, tokenizer = local_assets(settings, config)
    rates, ledger = spending_setup(settings, config)
    catalog = create_catalog(corpus, pages, config, tokenizer)
    if not catalog.chunks:
        raise FinsightError("corpus_unindexable")
    cache = EmbeddingCache(settings.embedding_cache_root, config)
    uncached = [c for c in catalog.chunks if cache.get(cache.key(c.content, "document")) is None]
    tokens = sum(tokenizer.count(c.content) + 64 for c in uncached)
    embedding_rate = rates.card("nebius", config.embedding_model)
    generation_rate = rates.card("anthropic", config.generation_model)
    # Every eligible request can retry once. Queries are bounded by the embedding context.
    indexing = embedding_rate.maximum(tokens, 0) * 2
    query = embedding_rate.maximum(32768 + 64, 0) + generation_rate.maximum(
        config.input_tokens, config.output_tokens
    )
    campaign = indexing + query * 4 * 2
    snapshot = ledger.snapshot()
    global_used = Decimal("4") - snapshot.available_usd
    phase_used = Decimal("0.75") - snapshot.phase2_available_usd
    allowed = min(
        snapshot.available_usd,
        snapshot.phase2_available_usd,
        max(Decimal(0), config.working_usd - global_used),
        max(Decimal(0), config.phase2_usd - phase_used),
    )
    return dict(
        status="ready" if campaign <= allowed else "budget_conflict",
        source_fingerprint=corpus.source_fingerprint,
        config_fingerprint=config.fingerprint(),
        catalog_fingerprint=catalog.payload_fingerprint,
        rate_fingerprint=rates.fingerprint(),
        budget_id=config.budget_id,
        documents=len(corpus.documents),
        pages=sum(d.page_count for d in corpus.documents),
        chunks=len(catalog.chunks),
        uncached_chunks=len(uncached),
        embedding_reserved_tokens=tokens,
        indexing_maximum_usd=str(indexing),
        four_query_maximum_usd=str(query * 8),
        campaign_maximum_usd=str(campaign),
        available_usd=str(allowed),
        budget=snapshot.model_dump(mode="json"),
        provider_network_calls=0,
        estimate_basis=(
            "all uncached inputs plus overhead; four queries; eligible retry on every send"
        ),
    )


def require_paid(settings: Settings, config: BaselineConfig, allow_paid: bool, *, generation: bool):
    if not allow_paid:
        raise FinsightError("paid_not_authorized")
    if (
        config.embedding_model != "Qwen/Qwen3-Embedding-8B"
        or config.embedding_dimension != 4096
        or config.source_fingerprint != BaselineConfig().source_fingerprint
    ):
        raise FinsightError("provider_configuration")
    if not settings.nebius_api_key or (generation and not settings.anthropic_api_key):
        raise FinsightError("credentials_missing")


def create_application(
    settings: Settings, config: BaselineConfig, *, allow_paid: bool = False
) -> BaselineApplicationService:
    require_paid(settings, config, allow_paid, generation=True)
    corpus, pages, tokenizer = local_assets(settings, config)
    rates, ledger = spending_setup(settings, config)
    dispatcher = GuardedDispatcher(ledger, rates, config=config)
    client = httpx.Client(
        transport=httpx.HTTPTransport(retries=0), follow_redirects=False, timeout=20
    )
    chat = None
    try:
        embeddings = CachedNebiusEmbeddings(
            client,
            settings.nebius_api_key,
            tokenizer,
            EmbeddingCache(settings.embedding_cache_root, config),
            config,
            dispatcher,
        )
        retriever = open_index(
            settings.index_root / config.fingerprint(),
            config,
            corpus,
            pages=pages,
            embeddings=embeddings,
            tokenizer=tokenizer,
        )
        chat = create_chat(config, settings.anthropic_api_key)
        counter = ClaudeTokenCounter(
            chat._client, config.generation_model, attempt_timeout_s=config.attempt_timeout_s
        )
        generator = ClaudeGenerator(config, dispatcher, counter, chat=chat)
        service = BaselineApplicationService(
            config, retriever, counter, generator, pages, JsonlTraceRecorder(settings.trace_root)
        )
        service.resource_closers = (client.close, chat._client.close, retriever.store.client.close)
        return service
    except Exception:
        client.close()
        if chat is not None:
            chat._client.close()
        raise


def build_local_index(settings: Settings, config: BaselineConfig, *, allow_paid: bool = False):
    require_paid(settings, config, allow_paid, generation=False)
    report = preflight(settings, config)
    if report["status"] != "ready":
        raise FinsightError("budget_exceeded")
    corpus, pages, tokenizer = local_assets(settings, config)
    rates, ledger = spending_setup(settings, config)
    dispatcher = GuardedDispatcher(ledger, rates, config=config)
    identity = uuid4().hex
    root = settings.index_root / config.fingerprint()
    started = monotonic()
    manifest = None
    try:
        with httpx.Client(
            transport=httpx.HTTPTransport(retries=0),
            follow_redirects=False,
            timeout=config.attempt_timeout_s,
        ) as client:
            backend = CachedNebiusEmbeddings(
                client,
                settings.nebius_api_key,
                tokenizer,
                EmbeddingCache(settings.embedding_cache_root, config),
                config,
                dispatcher,
            )
            manifest = build_index(
                corpus,
                pages,
                config,
                backend,
                root,
                CallContext(identity, 2, started + settings.index_job_timeout_s),
                tokenizer=tokenizer,
            )
        return manifest
    finally:
        write_json_atomic(
            settings.trace_root / (identity + "-index.json"),
            dict(
                run_id=identity,
                budget_id=config.budget_id,
                source_fingerprint=config.source_fingerprint,
                config_fingerprint=config.fingerprint(),
                rate_fingerprint=rates.fingerprint(),
                index_fingerprint=manifest.fingerprint() if manifest else None,
                attempts=[a.model_dump(mode="json") for a in dispatcher.attempts],
                budget=ledger.snapshot().model_dump(mode="json"),
                latency_ms=(monotonic() - started) * 1000,
                job_timeout_s=settings.index_job_timeout_s,
            ),
        )


def verify_provider_models(settings: Settings, config: BaselineConfig) -> dict[str, object]:
    """Explicit free metadata requests only; dimension is checked on first paid batch."""
    require_paid(settings, config, True, generation=True)
    import anthropic

    try:
        with httpx.Client(
            transport=httpx.HTTPTransport(retries=0), timeout=20, follow_redirects=False
        ) as client:
            response = client.get(
                "https://api.tokenfactory.nebius.com/v1/models",
                headers={"Authorization": "Bearer " + settings.nebius_api_key.get_secret_value()},
            )
            response.raise_for_status()
            if config.embedding_model not in {r["id"] for r in response.json()["data"]}:
                raise FinsightError("provider_model_unavailable")
        with anthropic.Anthropic(
            api_key=settings.anthropic_api_key.get_secret_value(), max_retries=0, timeout=20
        ) as client:
            model = client.models.retrieve(config.generation_model)
        if model.id != config.generation_model:
            raise FinsightError("provider_model_unavailable")
        return dict(
            status="available",
            embedding_model=config.embedding_model,
            generation_model=model.id,
            hosted_embedding_revision="unknown",
            dimension_check="first authorized batch",
            paid_calls=0,
            metadata_calls=2,
        )
    except FinsightError:
        raise
    except Exception:
        raise FinsightError("provider_preflight_failed") from None
