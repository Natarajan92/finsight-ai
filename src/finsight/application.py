"""Shared service boundary for the future UI and offline benchmark."""

import re
from contextvars import ContextVar
from time import monotonic
from typing import Protocol
from uuid import uuid4

from langchain_core.runnables import RunnableBranch, RunnableLambda
from langsmith import tracing_context

from finsight.citations.validation import validate_draft
from finsight.context.packing import pack_evidence
from finsight.contracts import Answer, AppError, BaselineConfig, QueryRequest, UsageMetrics
from finsight.contracts.base import fingerprint
from finsight.contracts.tracing import RunTrace
from finsight.generation.counting import validate_question
from finsight.generation.prompts import build_prompt
from finsight.ingestion.manifest import company_key
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import CallContext
from finsight.runtime.software import software_versions


class ApplicationService(Protocol):
    """Implementations receive questions/explicit filters, never benchmark labels."""

    def answer(self, request: QueryRequest) -> Answer: ...


def error_answer(code: str, usage: UsageMetrics | None = None) -> Answer:
    safe = code if re.fullmatch(r"[a-z_]{1,64}", code) else "internal_error"
    return Answer(
        status="error",
        error=AppError(code=safe, message=safe.replace("_", " ")),
        usage=usage or UsageMetrics(),
    )


class BaselineApplicationService:
    def __init__(
        self,
        config: BaselineConfig,
        retriever,
        counter,
        generator,
        pages,
        recorder,
        clock=monotonic,
        *,
        phase=2,
        run_fingerprint=None,
    ):
        self.config = config
        self.retriever = retriever
        self.counter = counter
        self.generator = generator
        self.pages = pages
        self.recorder = recorder
        self.clock = clock
        if type(phase) is not int or phase not in {2, 3}:
            raise FinsightError("experiment_configuration")
        if run_fingerprint is not None and not re.fullmatch(r"[a-f0-9]{64}", run_fingerprint):
            raise FinsightError("experiment_configuration")
        self.phase = phase
        self.run_fingerprint = run_fingerprint
        self._last_id = ContextVar("finsight_trace_id", default=None)
        self._last_trace = ContextVar("finsight_terminal_trace", default=None)
        identity = RunnableLambda(lambda state: state)
        generation = self._stage("generation", self._generate) | self._stage(
            "validation", self._validate
        )
        work = (
            self._stage("retrieval", self._retrieve)
            | self._stage("packing", self._pack)
            | RunnableBranch((lambda s: s["answer"] is not None, identity), generation)
        )
        self.pipeline = self._stage("admission", self._admit) | RunnableBranch(
            (lambda s: s["answer"] is not None, identity), work
        )
        self.resource_closers = ()

    @property
    def last_trace_id(self):
        return self._last_id.get()

    @property
    def last_trace(self):
        return self._last_trace.get()

    def _stage(self, name, function):
        def timed(state):
            state["context"].remaining()
            started = self.clock()
            try:
                function(state)
                return state
            finally:
                state["timings"][name] = max(0, (self.clock() - started) * 1000)

        return RunnableLambda(timed)

    def _admit(self, state):
        request = state["request"]
        if request.chunk_strategy != getattr(
            self.retriever, "chunk_strategy", "fixed"
        ) or request.rerank != getattr(self.retriever, "rerank", False):
            raise FinsightError("unsupported_scenario")
        if re.search(
            r"\b(?:forecast|predict|prediction)\b|next year|\bwill\b", request.question, re.I
        ):
            state["answer"] = Answer(
                status="insufficient_evidence",
                limitations=(
                    "Forecasts require information outside the supplied historical filings.",
                ),
            )
            return
        documents = getattr(getattr(self.retriever, "corpus", None), "documents", ())
        if documents and not request.company and not request.document_ids:
            named = any(
                d.company and company_key(d.company) in company_key(request.question)
                for d in documents
            )
            if not named:
                state["answer"] = Answer(
                    status="insufficient_evidence",
                    limitations=(
                        "Please specify a company and reporting period for this question.",
                    ),
                )
                return
        validate_question(request.question, self.counter, state["context"], self.config)

    def _retrieve(self, state):
        state["retrieved"] = self.retriever.retrieve(state["request"], state["context"])

    def _pack(self, state):
        state["packet"] = pack_evidence(
            state["retrieved"],
            self.pages,
            state["request"],
            self.counter,
            state["context"],
            self.config,
        )
        if not state["packet"].slices:
            state["answer"] = Answer(
                status="insufficient_evidence",
                limitations=("No usable source evidence was retrieved within the context limit.",),
            )

    def _generate(self, state):
        state["prompt"] = build_prompt(state["request"], state["packet"])
        state["draft"] = self.generator.generate(state["prompt"], state["context"])

    def _validate(self, state):
        state["answer"] = validate_draft(
            state["draft"], state["packet"], self.pages, UsageMetrics(), request=state["request"]
        )

    def _attempts(self, run_id):
        sources = [
            getattr(self.generator, "dispatcher", None),
            getattr(getattr(self.retriever, "embeddings", None), "dispatcher", None),
            self.counter,
        ]
        seen = set()
        records = []
        for source in sources:
            if source is None or id(source) in seen:
                continue
            seen.add(id(source))
            records.extend(r for r in getattr(source, "attempts", ()) if r.run_id == run_id)
        return tuple(sorted(records, key=lambda r: r.started_monotonic))

    def _usage(self, attempts, started):
        paid = [r for r in attempts if r.purpose != "free_token_count"]

        def total(field):
            values = [getattr(r.usage, field, None) for r in paid]
            return None if any(v is None for v in values) else sum(values)

        cost = total("cost_usd")
        return UsageMetrics(
            input_tokens=total("input_tokens"),
            output_tokens=total("output_tokens"),
            model_calls=sum(r.provider == "anthropic" for r in paid),
            embeddings=sum(r.input_count for r in paid if r.provider == "nebius"),
            cost_usd=cost,
            latency_ms=max(0, (self.clock() - started) * 1000),
        )

    def answer(self, request: QueryRequest) -> Answer:
        run_id = uuid4().hex
        self._last_id.set(run_id)
        started = self.clock()
        context = CallContext(run_id, self.phase, started + self.config.deadline_s, self.clock)
        state = dict(
            request=request,
            context=context,
            answer=None,
            retrieved=(),
            packet=None,
            prompt=None,
            draft=None,
            timings={},
        )
        try:
            QueryRequest.model_validate(request.model_dump(mode="json"))
            with tracing_context(enabled=False):
                self.pipeline.invoke(state, config={"callbacks": []})
            context.remaining()
        except FinsightError as exc:
            if exc.code in {"scope_unavailable", "scope_conflict"}:
                state["answer"] = Answer(
                    status="insufficient_evidence",
                    limitations=(
                        "No filing matches that scope; clarify the company, document or period.",
                    ),
                )
            else:
                state["answer"] = error_answer(exc.code)
        except Exception:
            state["answer"] = error_answer("internal_error")
        attempts = self._attempts(run_id)
        usage = self._usage(attempts, started)
        answer = state["answer"].model_copy(update={"usage": usage})
        manifest = getattr(self.retriever, "manifest", None)
        dispatcher = getattr(self.generator, "dispatcher", None)
        rates = getattr(dispatcher, "rates", None)
        packet = state["packet"]
        trace = RunTrace(
            software=software_versions(),
            run_id=run_id,
            budget_id=self.config.budget_id,
            config_fingerprint=self.run_fingerprint or self.config.fingerprint(),
            source_fingerprint=self.config.source_fingerprint,
            index_fingerprint=manifest.fingerprint() if manifest else None,
            request_fingerprint=fingerprint(request.model_dump(mode="json")),
            request=request,
            rate_fingerprint=rates.fingerprint() if rates else None,
            prompt_fingerprint=state["prompt"].fingerprint if state["prompt"] else None,
            filters=request.model_dump(mode="json", exclude={"question"}),
            retrieved=state["retrieved"],
            packet=packet,
            prompt=state["prompt"],
            draft=state["draft"],
            attempts=attempts,
            packed=tuple(
                dict(
                    evidence_id=s.evidence_id, source_spans=[p.model_dump() for p in s.source_spans]
                )
                for s in packet.slices
            )
            if packet
            else (),
            timings_ms=state["timings"],
            counting=tuple(
                r for r in getattr(self.counter, "records", ()) if r["run_id"] == run_id
            ),
            answer=answer,
        )
        try:
            self.recorder.record(trace)
        except Exception:
            answer = error_answer("trace_write_failed", usage)
            trace = trace.model_copy(update={"answer": answer})
        self._last_trace.set(trace)
        return answer

    def close(self):
        for close in self.resource_closers:
            close()
