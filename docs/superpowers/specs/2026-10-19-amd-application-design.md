# AMD financial-document RAG application

The human asked to finish development for AMD and then authorized using our
judgment with the existing document. The goal is a working financial-document
RAG application. This narrows the current delivery to AMD_2022_10K, using its
existing 121-page source and complete fixed-chunk index; the original six-company
evaluation remains separate and incomplete.

Build on the existing Python, LangChain, Chroma, Nebius and Claude service.
Streamlit is the presentation layer. Show the actual filing, reporting period and
coverage before asking questions. Users can browse extracted PDF pages offline,
ask independent questions, inspect evidence quotes with one-based PDF pages,
follow official filing links, and download an answer with its provenance.

Opening or rerunning the app makes no provider requests. Live answers require the
explicit live-answers switch and use the existing shared budget, current rate
cards, deadlines and phase 3 sublimit. Repeated matching questions reuse a durable
receipt; an interrupted or uncertain request cannot be automatically repurchased.
Replay verifies source/index/config/request identity, checksum and citation text.
The UI shows answered, partial, abstention and operational-error outcomes without
inventing metrics. Unknown usage remains unknown. Errors shown in the UI are safe
messages; raw provider exceptions and credentials never cross that boundary.

No gold annotations are read by the app. Company/document filters are explicit
and locked to the displayed AMD filing. The existing notebook remains byte-for-
byte intact. No changes to original PDFs, existing budget authority, existing
spend/reservations, source manifest, frozen benchmark splits or baseline index
identity. No push, merge, deployment or full-corpus benchmark is authorized.

Design call: a quiet analyst workspace with a white reading canvas, pale blue
sidebar (#edf3fa), dark navy text (#172b4d), blue actions (#245fc7), neutral rules
(#dce4ef) and amber partial/error notices. System sans-serif for controls and a
Georgia heading give the reading area hierarchy. Left-aligned question and answer
remain central; source browsing is a separate tab. Avoid unmeasured financial
headline numbers and decorative dashboards.

Acceptance: real AMD index opens offline; guarded live answer or clear operational
error is exercised once; repeat/reload has no provider dispatch; source quotes and
page labels are correct; Streamlit tests cover startup, submit, rerun, cached
answer, abstention and safe error; full keyless suite, Ruff, lock, package build
and synthetic smoke are reported. An independent final review checks the slice.
