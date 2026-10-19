"""Four-arm runtime orchestration. No benchmark questions, labels or scoring."""

from time import monotonic
from typing import Literal

from pydantic import Field

from finsight.contracts import QueryRequest, RetrievalCandidate
from finsight.contracts.base import Contract, Sha256
from finsight.contracts.retrieval_experiments import RetrievalExperimentConfig
from finsight.contracts.tracing import ProviderAttempt
from finsight.retrieval.reranking import RerankResult, pool_fingerprint
from finsight.runtime.errors import FinsightError


class DensePool(Contract):
    candidates: tuple[RetrievalCandidate, ...]
    index_fingerprint: Sha256
    attempts: tuple[ProviderAttempt, ...] = ()
    elapsed_ms: float = 0
    replay: bool = False


class ArmTrace(Contract):
    schema_version: Literal["1"] = "1"
    run_id: str
    phase: Literal[3] = 3
    arm: Literal["A", "B", "C", "D"]
    status: Literal["complete", "error"]
    request: QueryRequest
    config_fingerprint: Sha256
    source_fingerprint: Sha256
    index_fingerprint: Sha256 | None = None
    pool_fingerprint: Sha256 | None = None
    pool: tuple[RetrievalCandidate, ...] = ()
    selected: tuple[RetrievalCandidate, ...] = ()
    rerank_result: RerankResult | None = None
    attempts: tuple[ProviderAttempt, ...] = ()
    pool_reused: bool = False
    pool_replay: bool = False
    timings_ms: dict[str, float] = Field(default_factory=dict)
    error_code: str | None = None


def arm_request(request: QueryRequest, config: RetrievalExperimentConfig) -> QueryRequest:
    return QueryRequest(
        **{
            **request.model_dump(),
            "chunk_strategy": config.chunk_strategy,
            "rerank": config.rerank,
            "top_k": config.baseline.top_k,
        }
    )


def run_arms(request, configs, retrieve, reranker, context_factory):
    if not configs or len({c.arm for c in configs}) != len(configs):
        raise FinsightError("experiment_configuration")
    frozen = configs[0].model_dump(exclude={"arm"})
    if any(c.model_dump(exclude={"arm"}) != frozen for c in configs):
        raise FinsightError("experiment_configuration")
    pools, traces, stop = {}, [], False
    for config in configs:
        context = context_factory("arm-" + config.arm)
        started = monotonic()
        values = dict(
            run_id=context.run_id,
            arm=config.arm,
            request=arm_request(request, config),
            config_fingerprint=config.fingerprint(),
            source_fingerprint=config.baseline.source_fingerprint,
        )
        if stop:
            traces.append(ArmTrace(**values, status="error", error_code="experiment_stopped"))
            continue
        try:
            reused = config.chunk_strategy in pools
            if not reused:
                plain = QueryRequest(**{**values["request"].model_dump(), "rerank": False})
                try:
                    pools[config.chunk_strategy] = retrieve(config.chunk_strategy, plain, context)
                except FinsightError as exc:
                    pools[config.chunk_strategy] = exc
            pool = pools[config.chunk_strategy]
            if isinstance(pool, FinsightError):
                raise pool
            values.update(
                pool=pool.candidates,
                index_fingerprint=pool.index_fingerprint,
                pool_fingerprint=pool_fingerprint(pool.candidates),
                pool_reused=reused,
                pool_replay=pool.replay,
                attempts=() if reused else pool.attempts,
            )
            rerank_started = monotonic()
            ranked = None
            if config.rerank:
                if reranker is None:
                    raise FinsightError("reranker_unavailable")
                ranked = reranker.rerank(request.question, pool.candidates, context)
            selected = (ranked.candidates if ranked else pool.candidates)[: config.baseline.top_k]
            context.remaining()
            traces.append(
                ArmTrace(
                    **values,
                    status="complete",
                    selected=selected,
                    rerank_result=ranked,
                    timings_ms=dict(
                        dense_pool_ms=pool.elapsed_ms,
                        rerank_ms=(monotonic() - rerank_started) * 1000 if ranked else 0,
                        arm_elapsed_ms=(monotonic() - started) * 1000,
                    ),
                )
            )
        except FinsightError as exc:
            traces.append(ArmTrace(**values, status="error", error_code=exc.code))
            stop = exc.code in {
                "provider_timeout",
                "provider_failure",
                "provider_status",
                "deadline_exceeded",
                "experiment_interrupted",
                "experiment_pool_integrity",
                "embedding_cache_integrity",
                "source_integrity",
                "index_integrity",
            }
        except Exception:
            traces.append(ArmTrace(**values, status="error", error_code="internal_error"))
            stop = True
    return tuple(traces)
