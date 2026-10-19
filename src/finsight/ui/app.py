"""Streamlit presentation only; requests cross the typed application boundary."""

import json

import streamlit as st
from pydantic import ValidationError

from finsight.contracts import Answer
from finsight.runtime.errors import FinsightError
from finsight.ui.workspace import open_workspace

ERRORS = {
    "paid_not_authorized": "Enable live answers for a new question. Saved answers reopen for free.",
    "credentials_missing": "Add the Nebius and Anthropic keys to the local .env file.",
    "rate_expired": "Refresh the expired price cards before using live answers.",
    "rate_unavailable": "Verified price cards are missing. Follow the README setup.",
    "budget_exceeded": "Testing funds are exhausted. Saved answers and pages remain available.",
    "budget_integrity": "The testing ledger needs inspection. Live requests are paused.",
    "index_incomplete": "The AMD index is not ready. Follow the AMD setup in the README.",
    "index_integrity": "The AMD index could not be verified. Inspect the local index files.",
    "source_integrity": "The AMD source could not be verified. Check the local source setup.",
    "tokenizer_unavailable": "The pinned tokenizer is missing. Follow the README setup.",
    "tokenizer_integrity": (
        "The tokenizer cache is unreadable or invalid. Check setup and Windows file permissions."
    ),
    "experiment_interrupted": (
        "This question has an interrupted request. Inspect its receipt before retrying; "
        "no new call was made."
    ),
    "experiment_replay_integrity": (
        "The saved answer no longer matches verified evidence. Inspect its receipt before retrying."
    ),
    "experiment_pilot_scope": "This workspace answers questions from the AMD 2022 Form 10-K only.",
    "index_busy": "Another request is in progress. Wait for it to finish, then reopen the answer.",
    "question_token_limit": "Shorten your question and try again.",
    "provider_timeout": "The provider timed out. No automatic repurchase will occur.",
}


def safe_error(exc) -> str:
    code = exc.code if isinstance(exc, FinsightError) else "internal_error"
    return ERRORS.get(
        code, "The request could not be completed. Inspect the local trace before retrying."
    )


def _answer(result):
    answer = Answer.model_validate(result["answer"])
    if answer.status == "error":
        st.error(safe_error(FinsightError(answer.error.code)))
    elif answer.status == "insufficient_evidence":
        st.warning("The filing does not provide enough evidence to answer this question.")
    elif answer.status == "partial":
        st.warning("Partial answer: some requested information could not be verified.")
    else:
        st.success("Answer with source citations")
    if answer.answer_text:
        st.text(answer.answer_text)
    for limitation in answer.limitations:
        st.text(limitation)
    if answer.calculation:
        calculation = answer.calculation
        st.text(f"Calculation: {calculation.expression} = {calculation.result} {calculation.unit}")
    for i, evidence in enumerate(answer.citations, 1):
        page = evidence.page_index + 1
        with st.expander(f"[{i}] {evidence.source.doc_name} · PDF page {page}", expanded=True):
            # Document and model text remain text; never interpolate them into HTML.
            st.text(evidence.source_quote)
            if evidence.source.source_url:
                st.link_button(
                    "Open filing at cited page", f"{evidence.source.source_url}#page={page}"
                )
    usage = answer.usage
    latency = "unknown" if usage.latency_ms is None else f"{usage.latency_ms / 1000:.1f} s"
    cost = "unknown" if usage.cost_usd is None else f"${usage.cost_usd:.6f}"
    tokens = (
        "unknown"
        if usage.input_tokens is None or usage.output_tokens is None
        else f"{usage.input_tokens:,} in / {usage.output_tokens:,} out"
    )
    prefix = "Saved answer · no new provider calls" if result["replay"] else "Original request"
    st.caption(f"{prefix} · {latency} · Cost {cost} · Tokens {tokens}")
    st.caption(f"Trace: {result['trace_id']}")
    st.download_button(
        "Download answer and citations",
        json.dumps(result, ensure_ascii=False, indent=2),
        file_name="finsight-amd-answer.json",
        mime="application/json",
        on_click="ignore",
    )


def render(workspace):
    st.set_page_config(page_title="FinSight · AMD", page_icon="📑", layout="wide")
    st.markdown(
        "<style>.block-container{max-width:1120px;padding-top:2.5rem}"
        "h1{font-family:Georgia,serif;font-weight:500;color:#172b4d}"
        "[data-testid=stSidebar]{background:#edf3fa}"
        "[data-testid=stTextArea] textarea{font-size:1.05rem}"
        "button:focus-visible,a:focus-visible{outline:3px solid #245fc7;outline-offset:3px}"
        "</style>",
        unsafe_allow_html=True,
    )
    document = workspace.document
    scope = workspace.lab.corpus.source_fingerprint
    if st.session_state.get("scope") != scope:
        st.session_state["scope"] = scope
        st.session_state.pop("result", None)
    with st.sidebar:
        st.title("FinSight")
        st.write("Financial document intelligence")
        st.divider()
        st.subheader("Your source")
        st.write("**Advanced Micro Devices**")
        st.write(f"{document.fiscal_period} Form 10-K")
        st.caption(
            f"{document.page_count:,} PDF pages · {workspace.chunk_count:,} indexed passages"
        )
        if document.source_url:
            st.link_button("Open original filing", str(document.source_url))
        st.divider()
        live = st.toggle("Enable live answers", key="live", value=False)
        st.caption(
            "New answers use the existing testing credits. "
            "Reopening a saved answer makes no new provider calls."
        )
        st.caption(
            "Questions are answered independently from this filing. "
            "Include the reporting year in comparisons."
        )
    st.title("Read the numbers. Check the evidence.")
    st.write("Ask about AMD’s financial performance and accounting in its 2022 annual filing.")
    questions, source = st.tabs(["Ask the filing", "Explore source pages"])
    with questions:
        with st.form("question_form"):
            st.text_area(
                "Your financial question",
                key="question",
                height=110,
                max_chars=2500,
                placeholder="What was AMD’s revenue in 2022, and how did it compare with 2021?",
            )
            submitted = st.form_submit_button("Ask AMD", key="ask", type="primary")
        st.caption("Try: What was AMD revenue in 2022? · What were the main operating segments?")
        if not submitted and "result" in st.session_state:
            try:
                st.session_state["result"] = workspace.ask(
                    st.session_state["answered_question"], allow_paid=False
                )
            except Exception as exc:
                st.session_state.pop("result", None)
                st.error(safe_error(exc))
        if submitted:
            question = st.session_state["question"].strip()
            # A failed/new submission must not leave a previous answer under its question.
            st.session_state.pop("result", None)
            if not question:
                st.info("Enter a financial question to get started.")
            else:
                try:
                    with st.spinner("Reading evidence from the filing…"):
                        result = workspace.ask(question, allow_paid=live)
                    st.session_state["result"] = result
                    st.session_state["answered_question"] = question
                except FinsightError as exc:
                    message = safe_error(exc)
                    if exc.code == "paid_not_authorized":
                        st.info(message)
                    else:
                        st.error(message)
                except ValidationError:
                    st.error("Enter a question within the supported length and scope.")
                except Exception:
                    st.error(safe_error(None))
        if "result" in st.session_state:
            st.subheader("Answer")
            st.text(st.session_state["answered_question"])
            _answer(st.session_state["result"])
    with source:
        number = st.number_input(
            "PDF page",
            min_value=1,
            max_value=document.page_count,
            value=1,
            step=1,
            key="page",
        )
        st.caption(
            "PDF page numbers start at 1 and can differ from the printed report page labels."
        )
        try:
            page = workspace.page(number)
            if page.table_diagnostics:
                st.warning("The extractor reported limitations on this page:")
                for diagnostic in page.table_diagnostics:
                    st.text(diagnostic)
            if page.text:
                st.text(page.text)
            else:
                st.info(
                    "No text was extracted from this page. Open the original filing to inspect it."
                )
            if document.source_url:
                st.link_button("Open this PDF page", f"{document.source_url}#page={number}")
        except Exception as exc:
            st.error(safe_error(exc))


def main():
    workspace = None
    try:
        workspace = open_workspace()
        render(workspace)
    except Exception as exc:
        st.title("FinSight · AMD")
        st.error(safe_error(exc))
        st.info(
            "See the AMD application setup in README.md. "
            "Starting the app does not buy embeddings or answers."
        )
    finally:
        if workspace is not None:
            workspace.close()
