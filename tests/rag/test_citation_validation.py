"""Only supplied exact source intervals can become application-owned citations."""

import importlib

import pytest

from finsight.contracts.generation import DraftAnswer, DraftClaim, DraftReference
from finsight.runtime.errors import FinsightError


def validator():
    assert importlib.util.find_spec("finsight.citations.validation"), "Missing citation validation"
    return importlib.import_module("finsight.citations.validation").validate_draft


def test_valid_claim_resolves_original_source(citation_setup):
    packet, pages, draft, usage = citation_setup
    answer = validator()(draft, packet, pages, usage)
    assert answer.status == "answered"
    assert answer.citations[0].page_index == 0
    assert answer.citations[0].source == packet.slices[0].source
    assert answer.answer_text == "Revenue was 100 in 2022. [1]"
    assert answer.usage == usage


@pytest.mark.parametrize(
    "identity,quote",
    [("unsupplied", "Revenue 100"), ("a" * 64, "Revenue 125"), ("a" * 64, "invented quote")],
)
def test_real_quote_on_wrong_year_span_or_unsupplied_id_rejected(citation_setup, identity, quote):
    packet, pages, _, usage = citation_setup
    draft = DraftAnswer(
        status="answered",
        claims=[
            DraftClaim(
                text="Untrusted success text",
                references=[DraftReference(evidence_id=identity, quote=quote)],
            )
        ],
    )
    with pytest.raises(FinsightError, match="citation_validation_failed") as error:
        validator()(draft, packet, pages, usage)
    assert "Untrusted success text" not in str(error.value)


def test_every_claim_requires_reference(citation_setup):
    packet, pages, draft, usage = citation_setup
    claim = draft.claims[0].model_copy(update={"references": ()})
    with pytest.raises(FinsightError, match="citation_validation_failed"):
        validator()(draft.model_copy(update={"claims": (claim,)}), packet, pages, usage)


def test_partial_requires_missing_part_limitations(citation_setup):
    packet, pages, draft, usage = citation_setup
    with pytest.raises(FinsightError, match="citation_validation_failed"):
        validator()(draft.model_copy(update={"status": "partial"}), packet, pages, usage)
    partial = draft.model_copy(
        update={"status": "partial", "limitations": ("2023 evidence absent",)}
    )
    assert validator()(partial, packet, pages, usage).status == "partial"


def test_abstention_carries_no_fact_citations_or_calculation(citation_setup):
    packet, pages, _, usage = citation_setup
    answer = validator()(
        DraftAnswer(status="insufficient_evidence", limitations=("missing facts",)),
        packet,
        pages,
        usage,
    )
    assert answer.citations == () and answer.calculation is None
    assert not answer.answer_text


def test_quote_cannot_cross_inserted_gap(citation_setup):
    from finsight.contracts import SourceSpan

    packet, pages, draft, usage = citation_setup
    item = packet.slices[0]
    retained = item.model_copy(
        update={
            "source_spans": (
                SourceSpan(page_index=0, char_start=0, char_end=4),
                SourceSpan(page_index=0, char_start=18, char_end=25),
            ),
            "text": "2022\n[gap]\n" + item.text[18:25],
        }
    )
    packet = packet.model_copy(update={"slices": (retained,)})
    reference = DraftReference(evidence_id=retained.evidence_id, quote=retained.text)
    draft = draft.model_copy(
        update={"claims": (DraftClaim(text="Untrusted claim", references=(reference,)),)}
    )
    with pytest.raises(FinsightError, match="citation_validation_failed"):
        validator()(draft, packet, pages, usage)
