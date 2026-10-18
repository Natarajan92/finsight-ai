"""Acceptance boundaries: invalid provenance or state must not cross modules."""

import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from finsight import contracts


def model(name):
    result = getattr(contracts, name, None)
    assert result is not None, f"Missing approved contract: {name}"
    return result


def test_manifest_preserves_explicit_unknowns_and_source_identity(source):
    manifest = model("DocumentManifest")(
        **(source | {"company": None, "fiscal_period": None}),
        document_id="synthetic-document",
        page_count=1,
        ingestion_version="unprocessed",
    )
    restored = type(manifest).model_validate_json(manifest.model_dump_json())
    assert restored.company is None
    assert restored.fiscal_period is None
    assert restored.document_id == "synthetic-document"
    assert restored.local_path == "synthetic/report.pdf"


@pytest.mark.parametrize("field,value", [("sha256", "not-a-hash"), ("page_count", 0)])
def test_manifest_rejects_invalid_identity(field, value, source):
    payload = source | {
        "document_id": "synthetic-document",
        "page_count": 1,
        "ingestion_version": "v0",
    }
    payload[field] = value
    with pytest.raises(ValidationError):
        model("DocumentManifest")(**payload)


def test_page_preserves_table_whitespace_and_zero_index():
    text = "  2022\tUSD millions\nRevenue 1,000\nLoss (25)\n"
    page = model("Page")(
        document_id="synthetic-document",
        page_index=0,
        text=text,
        extraction_status="ok",
        parser_version="synthetic-v0",
    )
    restored = type(page).model_validate_json(page.model_dump_json())
    assert restored.page_index == 0
    assert restored.text == text


@pytest.mark.parametrize("page_index", [-1, True, "0"])
def test_page_indices_are_strict_nonnegative_integers(page_index):
    with pytest.raises(ValidationError):
        model("Page")(
            document_id="synthetic-document",
            page_index=page_index,
            text="x",
            extraction_status="ok",
            parser_version="synthetic",
        )


@pytest.mark.parametrize("start,end", [(5, 4), (4, 4), (-1, 4)])
def test_source_spans_are_nonempty_half_open_ranges(start, end):
    with pytest.raises(ValidationError):
        model("SourceSpan")(page_index=0, char_start=start, char_end=end)


def test_cross_page_chunk_roundtrip_keeps_each_source_span(chunk_data):
    chunk = model("Chunk")(
        **(
            chunk_data
            | {
                "page_end": 1,
                "source_spans": [
                    {"page_index": 0, "char_start": 10, "char_end": 40},
                    {"page_index": 1, "char_start": 0, "char_end": 10},
                ],
            }
        )
    )
    restored = type(chunk).model_validate_json(chunk.model_dump_json())
    assert restored.chunk_id == "synthetic-chunk-0"
    assert [(s.page_index, s.char_start, s.char_end) for s in restored.source_spans] == [
        (0, 10, 40),
        (1, 0, 10),
    ]
    assert restored.content == "2022 | USD millions\nRevenue 1,000\nLoss (25)"


@pytest.mark.parametrize(
    "updates",
    [
        {"page_end": -1},
        {"page_start": 1},
        {"token_count": -1},
        {"source_spans": []},
        {
            "source_spans": [
                {"page_index": 0, "char_start": 10, "char_end": 30},
                {"page_index": 0, "char_start": 20, "char_end": 40},
            ]
        },
        {
            "page_end": 1,
            "source_spans": [
                {"page_index": 1, "char_start": 0, "char_end": 10},
                {"page_index": 0, "char_start": 0, "char_end": 10},
            ],
        },
    ],
)
def test_chunks_reject_broken_provenance(chunk_data, updates):
    with pytest.raises(ValidationError):
        model("Chunk")(**(chunk_data | updates))


@pytest.mark.parametrize(
    "kind,direction,value",
    [
        ("cosine_similarity", "higher_is_better", float("nan")),
        ("rerank_logit", "higher_is_better", float("inf")),
        ("cosine_distance", "higher_is_better", 0.4),
        ("cosine_similarity", "lower_is_better", 0.4),
    ],
)
def test_scores_cannot_hide_nonfinite_values_or_distance_order(kind, direction, value):
    with pytest.raises(ValidationError):
        model("Score")(kind=kind, direction=direction, value=value)


def test_candidate_keeps_rank_score_and_source(chunk_data, source):
    candidate = model("RetrievalCandidate")(
        chunk=chunk_data,
        source=source,
        rank=1,
        score={"kind": "cosine_distance", "direction": "lower_is_better", "value": 0.25},
    )
    assert candidate.chunk.page_start == 0
    assert candidate.score.value == 0.25
    assert candidate.score.direction == "lower_is_better"


def test_query_defaults_and_explicit_scope():
    request = model("QueryRequest")(question="What was revenue?")
    assert (request.chunk_strategy, request.rerank, request.top_k) == ("fixed", False, 5)
    assert request.company is None and request.document_ids is None and request.period is None


@pytest.mark.parametrize(
    "updates",
    [
        {"question": " \n\t"},
        {"top_k": 0},
        {"top_k": 16},
        {"top_k": True},
        {"company": " "},
        {"document_ids": []},
        {"document_ids": [""]},
        {"rerank": "false"},
    ],
)
def test_query_rejects_ambiguous_empty_inputs_and_invalid_limits(updates):
    with pytest.raises(ValidationError):
        model("QueryRequest")(**({"question": "Revenue?"} | updates))


@pytest.mark.parametrize("gold_field", ["answer", "justification", "evidence", "evidence_page_num"])
def test_query_rejects_gold_annotation_injection(gold_field):
    with pytest.raises(ValidationError):
        model("QueryRequest")(**{"question": "Revenue?", gold_field: "SYNTHETIC_GOLD"})


def test_answer_roundtrip_preserves_citation_and_unknown_usage(evidence_data):
    answer = model("Answer")(
        status="answered", answer_text="Revenue was 1,000 million USD.", citations=[evidence_data]
    )
    restored = type(answer).model_validate_json(answer.model_dump_json())
    assert restored.citations[0].page_index == 0
    assert restored.citations[0].source_quote == "Revenue 1,000"
    assert restored.usage.cost_usd is None
    assert restored.usage.latency_ms is None
    assert json.loads(restored.model_dump_json())["usage"]["input_tokens"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"status": "answered", "answer_text": "unsupported"},
        {"status": "partial", "answer_text": "unsupported"},
        {"status": "error"},
        {"status": "invented"},
        {"status": "insufficient_evidence", "error": {"code": "bad", "message": "bad"}},
    ],
)
def test_answer_rejects_inconsistent_states(payload):
    with pytest.raises(ValidationError):
        model("Answer")(**payload)


def test_partial_answer_requires_limitations(evidence_data):
    with pytest.raises(ValidationError):
        model("Answer")(status="partial", answer_text="Revenue found.", citations=[evidence_data])
    answer = model("Answer")(
        status="partial",
        answer_text="Revenue found.",
        citations=[evidence_data],
        limitations=["Prior-year comparison was not available."],
    )
    assert answer.status == "partial"


@pytest.mark.parametrize("status", ["insufficient_evidence", "error"])
def test_failure_states_cannot_carry_factual_citations(status, evidence_data):
    with pytest.raises(ValidationError):
        model("Answer")(
            status=status,
            citations=[evidence_data],
            error={"code": "provider_timeout", "message": "Timed out"}
            if status == "error"
            else None,
        )


def test_error_and_abstention_have_valid_structured_paths():
    assert model("Answer")(status="insufficient_evidence").citations == ()
    answer = model("Answer")(
        status="error",
        error={"code": "provider_timeout", "message": "Timed out", "retryable": True},
    )
    assert answer.error.code == "provider_timeout"


@pytest.mark.parametrize(
    "updates",
    [
        {"input_tokens": -1},
        {"latency_ms": -1},
        {"cost_usd": Decimal("NaN")},
        {"cost_usd": Decimal("-0.01")},
    ],
)
def test_resource_accounting_rejects_invalid_measurements(updates):
    with pytest.raises(ValidationError):
        model("UsageMetrics")(**updates)


def test_calculation_keeps_units_and_decimal_values():
    calc = model("Calculation")(
        expression="revenue - cost",
        operands={"revenue": "1000", "cost": "1025"},
        result="-25",
        unit="USD millions",
    )
    assert calc.result == Decimal("-25")
    assert calc.unit == "USD millions"


def test_experiment_fingerprint_is_deterministic_and_sensitive_to_reranking():
    config_type = model("ExperimentConfig")
    first = config_type(seed=7, rerank=False)
    reordered = config_type.model_validate_json('{"rerank":false,"seed":7}')
    assert first.fingerprint() == reordered.fingerprint()
    assert len(first.fingerprint()) == 64
    assert first.fingerprint() != config_type(seed=7, rerank=True).fingerprint()


def test_experiment_rejects_context_selection_larger_than_candidate_pool():
    with pytest.raises(ValidationError):
        model("ExperimentConfig")(candidate_count=3, top_k=5)


def test_result_cannot_misreport_config_fingerprint():
    config = model("ExperimentConfig")()
    with pytest.raises(ValidationError):
        model("ExperimentResult")(
            config=config,
            config_fingerprint="0" * 64,
            source_fingerprint="a" * 64,
            dataset_fingerprint="b" * 64,
            split_fingerprint="c" * 64,
        )


def test_all_public_contracts_generate_resolved_json_schemas():
    names = [
        "DocumentManifest",
        "Page",
        "Chunk",
        "QueryRequest",
        "RetrievalCandidate",
        "Evidence",
        "Answer",
        "ExperimentConfig",
        "ExperimentResult",
        "SourceSpan",
        "Score",
        "UsageMetrics",
        "Calculation",
        "AppError",
        "QueryEvaluationRecord",
    ]
    for name in names:
        assert model(name).model_json_schema()["title"] == name
