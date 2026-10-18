import json

import pytest

from finsight.evaluation.benchmark import load_benchmark


def test_actual_schema_names_and_nullable_fields(benchmark_fixture):
    path, corpus, _ = benchmark_fixture
    cases = load_benchmark(path, corpus)
    assert len(cases) == 52 and len({c.financebench_id for c in cases}) == 52
    assert all(isinstance(c.financebench_id, str) for c in cases)
    assert sum(c.question_reasoning is None for c in cases) == 22
    assert cases[0].evidence[0].evidence_page_num == 0
    assert cases[0].justification is None


@pytest.mark.parametrize(
    "change",
    ["duplicate", "unknown_doc", "negative_page", "past_end", "numeric_id", "wrong_company"],
)
def test_bad_benchmark_references_fail(change, benchmark_fixture):
    path, corpus, rows = benchmark_fixture
    if change == "duplicate":
        rows.append(rows[0])
    elif change == "unknown_doc":
        rows[0]["doc_name"] = "missing"
    elif change == "negative_page":
        rows[0]["evidence"][0]["evidence_page_num"] = -1
    elif change == "past_end":
        rows[0]["evidence"][0]["evidence_page_num"] = 2
    elif change == "numeric_id":
        rows[0]["financebench_id"] = 10
    else:
        rows[0]["company"] = "Boeing"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    with pytest.raises(ValueError):
        load_benchmark(path, corpus)
