"""Filter admission precedes embedding; raw cosine distances keep their direction."""

import pytest

from finsight.contracts import QueryRequest
from finsight.runtime.errors import FinsightError


def retrieve_setup(setup):
    module, corpus, repo, config, embeddings, root, context, tokenizer = setup
    module.build_index(corpus, repo, config, embeddings, root, context, tokenizer=tokenizer)
    return module.open_index(
        root, config, corpus, pages=repo, embeddings=embeddings, tokenizer=tokenizer
    ), context


def test_combined_filters_and_unfiltered_scope(index_setup):
    retriever, context = retrieve_setup(index_setup)
    document = next(d for d in index_setup[1].documents if d.company == "AMD")
    results = retriever.retrieve(
        QueryRequest(
            question="Revenue?", company="AMD", period="2022", document_ids=(document.document_id,)
        ),
        context,
    )
    assert 0 < len(results) <= 15
    assert all(r.source.company == "AMD" and r.source.fiscal_period == "2022" for r in results)
    assert [r.rank for r in results] == list(range(1, len(results) + 1))
    assert all(
        r.score.kind == "cosine_distance" and r.score.direction == "lower_is_better"
        for r in results
    )
    assert {
        r.source.company for r in retriever.retrieve(QueryRequest(question="Revenue?"), context)
    } == {"AMD", "PepsiCo"}


@pytest.mark.parametrize(
    "filters",
    [
        {"company": "Unknown"},
        {"period": "2099"},
        {"document_ids": ("forged",)},
        {"company": "AMD", "period": "2021"},
    ],
)
def test_unknown_or_conflicting_scope_never_embeds(index_setup, filters):
    retriever, context = retrieve_setup(index_setup)
    with pytest.raises(FinsightError, match="scope_"):
        retriever.retrieve(QueryRequest(question="Revenue?", **filters), context)
    assert index_setup[4].queries == 0


def test_equal_distance_ties_have_stable_chunk_order(index_setup):
    retriever, context = retrieve_setup(index_setup)
    first = retriever.retrieve(QueryRequest(question="Revenue?"), context)
    second = retriever.retrieve(QueryRequest(question="Revenue?"), context)
    assert first == second
    assert [r.chunk.chunk_id for r in first] == sorted(r.chunk.chunk_id for r in first)
    assert all(abs(r.score.value) < 1e-6 for r in first)


def test_vector_changed_after_reopen_fails_before_generation(index_setup):
    retriever, context = retrieve_setup(index_setup)
    retriever.store.collection.update(
        ids=[retriever.manifest.chunk_ids[0]], embeddings=[[0.0, 1.0, 0.0]]
    )
    with pytest.raises(FinsightError, match="index_integrity"):
        retriever.retrieve(QueryRequest(question="Revenue?"), context)
