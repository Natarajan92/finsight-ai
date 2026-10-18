"""Bounded complete-passage reranking with immutable dense provenance."""

import json
import math
from pathlib import Path

from tokenizers import Tokenizer

from finsight.contracts import RetrievalCandidate, Score
from finsight.contracts.base import Contract, NonnegativeInt, Sha256, fingerprint
from finsight.contracts.retrieval_experiments import RerankerConfig
from finsight.ingestion.cache import write_json_atomic
from finsight.runtime.errors import FinsightError

from .reranker_artifacts import OnnxCrossEncoder  # noqa: F401 public offline constructor


class WindowScore(Contract):
    """Character offsets are relative to the unchanged chunk text."""

    char_start: NonnegativeInt
    char_end: NonnegativeInt
    token_start: NonnegativeInt
    token_end: NonnegativeInt
    score: float


class RerankDetail(Contract):
    chunk_id: Sha256
    original_rank: int
    dense_score: Score
    rerank_score: Score
    final_rank: int
    windows: tuple[WindowScore, ...]


class RerankResult(Contract):
    candidates: tuple[RetrievalCandidate, ...]
    details: tuple[RerankDetail, ...]
    pool_fingerprint: Sha256
    model_fingerprint: Sha256
    cache_hit: bool = False


def pool_fingerprint(candidates):
    return fingerprint([c.model_dump(mode="json") for c in candidates])


def passage_windows(tokenizer, question, text, config):
    query = tokenizer.encode(question, add_special_tokens=False)
    capacity = config.maximum_tokens - len(query.ids) - tokenizer.num_special_tokens_to_add(True)
    if capacity < 1:
        raise FinsightError("rerank_query_limit")
    source = tokenizer.encode(text, add_special_tokens=False)
    if not source.ids:
        raise FinsightError("rerank_input")
    start = 0
    windows = []
    while start < len(source.ids):
        end = min(start + capacity, len(source.ids))
        char_start = 0 if start == 0 else source.offsets[start][0]
        while end > start:
            char_end = len(text) if end == len(source.ids) else source.offsets[end - 1][1]
            encoding = tokenizer.encode(question, text[char_start:char_end])
            if len(encoding.ids) <= config.maximum_tokens:
                break
            end -= 1  # A new WordPiece boundary can resegment a Unicode word.
        if end <= start:
            raise FinsightError("rerank_query_limit")
        windows.append(
            (
                dict(char_start=char_start, char_end=char_end, token_start=start, token_end=end),
                encoding,
            )
        )
        if end == len(source.ids):
            break
        start = max(start + 1, end - min(config.window_overlap, end - start - 1))
    return tuple(windows)


def _assemble(candidates, windows, model_fingerprint):
    scored = sorted(
        candidates,
        key=lambda c: (-max(w.score for w in windows[c.chunk.chunk_id]), c.chunk.chunk_id),
    )
    results, details = [], []
    for rank, candidate in enumerate(scored, 1):
        rows = windows[candidate.chunk.chunk_id]
        score = Score(
            kind="rerank_logit", direction="higher_is_better", value=max(w.score for w in rows)
        )
        results.append(candidate.model_copy(update={"rank": rank, "score": score}))
        details.append(
            RerankDetail(
                chunk_id=candidate.chunk.chunk_id,
                original_rank=candidate.rank,
                dense_score=candidate.score,
                rerank_score=score,
                final_rank=rank,
                windows=rows,
            )
        )
    return RerankResult(
        candidates=results,
        details=details,
        pool_fingerprint=pool_fingerprint(candidates),
        model_fingerprint=model_fingerprint,
    )


class LocalReranker:
    def __init__(self, backend, config: RerankerConfig, cache_root: Path | None = None):
        self.backend, self.config = backend, config
        self.tokenizer = Tokenizer.from_str(backend.tokenizer.to_str())
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        self.cache_root = Path(cache_root) if cache_root is not None else None
        self.model_fingerprint = fingerprint(
            dict(backend=backend.fingerprint(), config=config.model_dump(mode="json"))
        )

    def rerank(self, question, candidates, context) -> RerankResult:
        context.remaining()
        if len(candidates) > 15 or len({c.chunk.chunk_id for c in candidates}) != len(candidates):
            raise FinsightError("rerank_input")
        identity = fingerprint(
            dict(question=question, pool=pool_fingerprint(candidates), model=self.model_fingerprint)
        )
        path = self.cache_root / (identity + ".json") if self.cache_root else None
        prepared = {
            c.chunk.chunk_id: passage_windows(
                self.tokenizer, question, c.chunk.content, self.config
            )
            for c in candidates
        }
        if path is not None and path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                stored = RerankResult.model_validate(raw["result"])
                if raw["identity"] != identity or raw["fingerprint"] != fingerprint(raw["result"]):
                    raise ValueError("Rerank cache changed")
                windows = {d.chunk_id: d.windows for d in stored.details}
                if set(windows) != set(prepared):
                    raise ValueError("Rerank pool changed")
                for chunk_id, rows in prepared.items():
                    geometry = [w.model_dump(exclude={"score"}) for w in windows[chunk_id]]
                    if geometry != [g for g, _ in rows]:
                        raise ValueError("Rerank coverage changed")
                if stored != _assemble(candidates, windows, self.model_fingerprint):
                    raise ValueError("Rerank provenance changed")
                context.remaining()
                return stored.model_copy(update={"cache_hit": True})
            except (ValueError, KeyError, OSError):
                raise FinsightError("rerank_cache_integrity") from None
        windows = {c.chunk.chunk_id: [] for c in candidates}
        work = [
            (identity, geometry, encoding)
            for identity, rows in prepared.items()
            for geometry, encoding in rows
        ]
        try:
            for start in range(0, len(work), self.config.batch_size):
                context.remaining()
                batch = work[start : start + self.config.batch_size]
                scores = self.backend.score([e for _, _, e in batch], context)
                context.remaining()
                if len(scores) != len(batch) or any(
                    isinstance(v, bool) or not math.isfinite(v) for v in scores
                ):
                    raise FinsightError("rerank_output")
                for (chunk_id, geometry, _), score in zip(batch, scores, strict=True):
                    windows[chunk_id].append(WindowScore(**geometry, score=float(score)))
            result = _assemble(candidates, windows, self.model_fingerprint)
            if path is not None:
                payload = result.model_dump(mode="json")
                write_json_atomic(
                    path, dict(identity=identity, result=payload, fingerprint=fingerprint(payload))
                )
            return result
        except FinsightError:
            raise
        except Exception:
            raise FinsightError("rerank_failed") from None
