"""Human claim labels bind to the exact generated claim and displayed evidence."""

import csv
from pathlib import Path

from finsight.runtime.errors import FinsightError

FIELDS = [
    "question_id",
    "arm",
    "trace_id",
    "claim_index",
    "claim_fingerprint",
    "question",
    "claim_text",
    "source_quotes",
    "verdict",
    "reviewer",
    "notes",
]


def csv_text(value):
    text = str(value)
    return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) else text


def review_rows(run):
    return [
        dict(
            question_id=record.question_id,
            arm=record.arm,
            trace_id=record.trace_id,
            claim_index=str(claim.index),
            claim_fingerprint=claim.fingerprint,
            question=record.question,
            claim_text=claim.text,
            source_quotes="\n\n".join(c.source_quote for c in record.answer.citations),
            verdict="",
            reviewer="",
            notes="",
        )
        for record in run.records
        for claim in record.claims
    ]


def write_review(run, path: Path):
    # Never erase the human's work when refreshing a report.
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows({k: csv_text(v) for k, v in row.items()} for row in review_rows(run))


def read_review(run, path: Path | None):
    if path is None:
        return {}
    expected = {
        (r["question_id"], r["arm"], r["trace_id"], r["claim_index"]): r for r in review_rows(run)
    }
    labels, seen = {}, set()
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != FIELDS:
                raise ValueError("Review columns changed")
            for row in reader:
                if set(row) != set(FIELDS) or any(v is None for v in row.values()):
                    raise ValueError("Malformed review row")
                key = tuple(row[k] for k in FIELDS[:4])
                if key in seen or key not in expected:
                    raise ValueError("Unknown or duplicate claim")
                seen.add(key)
                original = expected[key]
                for field in FIELDS[4:8]:
                    if row[field] != csv_text(original[field]):
                        raise ValueError("Reviewed evidence changed")
                if not row["verdict"].strip():
                    continue
                if row["verdict"] not in {"supported", "unsupported", "uncertain"} or not (
                    row["reviewer"].strip() and row["notes"].strip()
                ):
                    raise ValueError("Explicit reviewer, verdict and notes required")
                labels[key] = row["verdict"]
    except (ValueError, OSError, KeyError, TypeError):
        raise FinsightError("evaluation_review_integrity") from None
    return labels
