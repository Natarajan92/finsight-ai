"""Evidence admission preserves novel source intervals and includes label costs."""

import importlib

import pytest

from finsight.contracts import (
    BaselineConfig,
    QueryRequest,
    RetrievalCandidate,
    Score,
    SourceMetadata,
)
from finsight.runtime.errors import FinsightError
from finsight.runtime.ports import CallContext


@pytest.fixture
def packing_setup(page_factory, char_tokenizer):
    assert importlib.util.find_spec("finsight.context.packing"), "Missing evidence packer"
    from finsight.chunking.fixed import chunk_pages

    module = importlib.import_module("finsight.context.packing")
    document, page = page_factory("2021 2022 USD millions\nRevenue 1,000\nLoss (25)\n" * 18)
    chunks = chunk_pages(document, (page,), BaselineConfig(), char_tokenizer)
    source = SourceMetadata(**{f: getattr(document, f) for f in SourceMetadata.model_fields})
    candidates = tuple(
        RetrievalCandidate(
            chunk=c,
            source=source,
            rank=i,
            score=Score(kind="cosine_distance", direction="lower_is_better", value=i / 10),
        )
        for i, c in enumerate(chunks, 1)
    )

    class Pages:
        def get(self, document_id, page_index):
            assert (document_id, page_index) == (page.document_id, 0)
            return page

    class Counter:
        def count_text(self, text, context):
            context.remaining()
            return len(text)

    return module, candidates, Pages(), Counter(), CallContext("run", 2, 100, clock=lambda: 0), page


def pack(setup, **changes):
    module, candidates, pages, counter, context, _ = setup
    return module.pack_evidence(
        changes.get("candidates", candidates),
        pages,
        changes.get("request", QueryRequest(question="Revenue?")),
        changes.get("counter", counter),
        changes.get("context", context),
        changes.get("config", BaselineConfig()),
    )


def test_overlapping_spans_keep_all_novel_rows_and_exact_mapping(packing_setup):
    packet = pack(packing_setup)
    assert packet.token_count <= 3500
    assert len({s.chunk_id for s in packet.slices}) <= 5
    assert packet.slices[0].page_index == 0
    text = "".join(s.text for s in packet.slices)
    assert all(t in text for t in ["2021", "2022", "USD millions", "(25)"])
    covered = []
    for item in packet.slices:
        span = item.source_spans[0]
        assert item.text == packing_setup[-1].text[span.char_start : span.char_end]
        covered.extend(range(span.char_start, span.char_end))
    assert len(covered) == len(set(covered))
    assert set(covered) == set(range(len(packing_setup[-1].text)))


def test_duplicates_and_top_k_limits(packing_setup):
    candidates = packing_setup[1]
    packet = pack(
        packing_setup,
        candidates=(candidates[0], candidates[0], *candidates[1:]),
        request=QueryRequest(question="Revenue?", top_k=1),
    )
    assert len({s.chunk_id for s in packet.slices}) == 1
    assert len(packet.slices) == 1


def test_empty_and_budget_drops_are_explicit(packing_setup):
    assert pack(packing_setup, candidates=()).slices == ()
    packet = pack(packing_setup, config=BaselineConfig(context_tokens=10))
    assert packet.slices == ()
    assert packet.dropped_ids
    assert "context_budget_dropped" in packet.limitations


def test_missing_counter_or_deadline_blocks_context(packing_setup):
    with pytest.raises(FinsightError, match="token_count_unavailable"):
        pack(packing_setup, counter=None)
    with pytest.raises(FinsightError, match="deadline_exceeded"):
        pack(packing_setup, context=CallContext("run", 2, 0, clock=lambda: 1))


def test_same_words_at_distinct_source_offsets_are_retained(packing_setup):
    packet = pack(packing_setup)
    # Identical rows later on the page are novel occurrences, not text duplicates.
    assert "".join(s.text for s in packet.slices).count("Revenue 1,000") == 18


def test_same_words_on_different_sources_remain_distinct(packing_setup):
    module, candidates, _, counter, context, page = packing_setup
    original = candidates[0]
    other = original.model_copy(
        update={
            "chunk": original.chunk.model_copy(
                update={"chunk_id": "other-source-chunk", "document_id": "other-source"}
            ),
            "source": original.source.model_copy(update={"doc_name": "Other_2022_10K"}),
        }
    )

    class Pages:
        def get(self, identity, index):
            return page.model_copy(update={"document_id": identity})

    packet = module.pack_evidence(
        (original, other),
        Pages(),
        QueryRequest(question="Revenue?"),
        counter,
        context,
        BaselineConfig(),
    )
    assert len(packet.slices) == 2
    assert packet.slices[0].text == packet.slices[1].text
    assert packet.slices[0].evidence_id != packet.slices[1].evidence_id
