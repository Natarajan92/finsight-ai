# ADR 0002: Source-only extraction and evaluation-private benchmark preparation

- Status: accepted for Phase 1 under human approval P1-004, 2026-10-18.
- Context: six approved companies, 53 canonical filings, 52 benchmark questions,
  immutable original files, Windows development, keyless Linux/Windows CI.

## Decision

Use pinned PyMuPDF 1.28.2 / MuPDF 1.28.2 for inspection, original-order text, and
block geometry. Keep raw text unchanged and prove block offsets against it. Prefer
explicit diagnostics over guessed reading order, numeric cleanup, or table cells.
Image-only pages retain their identity and receive a coverage-gap diagnostic;
OCR remains a separate decision. Extractor `phase1-v2` invalidates older envelopes
when image-only detection is introduced.

The offline document-information join builds a portable, hash-verified manifest.
Runtime extraction accepts only that manifest and original PDF bytes. Contracts use
only Pydantic/standard library; runtime imports cannot load evaluation. A validated
`load_cached` boundary lets offline auditing inspect frozen pages without private
cache parsing or annotation-guided re-extraction.

Keep benchmark questions/answers/justifications/page annotations in `evaluation`.
Freeze 36 development / 16 holdout IDs using seed 42, company quotas, and feasible
reasoning coverage. Store membership and fingerprints only in public split files.
Gold changes cannot affect PDF-derived content, and exact-quote checks are restricted
to development after the split freezes. All four future arms share question sets
and the full corpus; holdout is one later campaign after configuration freeze.

## Alternatives and consequences

- Document-grouped splitting was not selected by the human; shared filings are
  disclosed, so results concern unseen questions rather than unseen documents.
- Embedding QA JSON, oracle document filters, gold-passage injection, and silently
  inferring metadata are excluded by the project contract.
- Structured table reconstruction and OCR would add validation/dependency work.
  Nine scanned Amcor appendix pages remain explicit text-coverage gaps. None is
  an annotated evidence page; no benchmark performance is inferred from that fact.
- PyMuPDF use was explicitly approved; retain the repository license and record
  third-party terms separately. No commercial license purchase or relicensing
  action is part of this phase.

## Documentation used

The official documentation explicitly covers 1.28.2. Implementation follows its
[text extraction description](https://pymupdf.readthedocs.io/en/latest/app1.html),
[Page API](https://pymupdf.readthedocs.io/en/latest/page.html), and
[Document API](https://pymupdf.readthedocs.io/en/latest/document.html).
The earlier ContextHub guide covered 1.27.2; it was preliminary context, not the
authority for version-specific calls. See also the
[third-party license notice](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright).
