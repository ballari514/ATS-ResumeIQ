import hashlib
import json
from typing import Optional

import requests
import streamlit as st

from frontend.services import api_client
from frontend.components.dashboard import display_results_dashboard


def _analysis_fingerprint(analysis: dict) -> str:
    """
    Stable hash of an analysis result. Used to guarantee the PDF download
    button can never hand out bytes generated from a different (older)
    analysis than the one currently on screen.
    """
    return hashlib.sha256(
        json.dumps(analysis, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _read_jd(jd_file, jd_text: str) -> str:
    """
    Turn whatever the user provided into a plain JD string for the backend.

    For .txt files we decode in-process — that's a trivial operation, no need
    for a backend round-trip. For PDF/DOCX, we'd need the backend's parser;
    we don't have a public endpoint for that, so we ask the user to paste text
    instead for non-txt JDs.
    """
    if jd_text:
        return jd_text.strip()
    if jd_file is None:
        return ""
    if jd_file.name.lower().endswith(".txt"):
        return jd_file.getvalue().decode("utf-8", errors="ignore")
    st.warning(
        "Job description files must be `.txt` for now — paste the JD text instead "
        "if you have a PDF or DOCX."
    )
    return ""


def _show_backend_error(exc: Exception) -> None:
    """Translate a `requests` exception into a friendly Streamlit error."""
    if isinstance(exc, requests.ConnectionError):
        st.error("Could not reach the backend. Is `uvicorn backend.main:app` running on port 8000?")
    elif isinstance(exc, requests.Timeout):
        st.error("The backend took too long to respond. Try a smaller resume or check the server logs.")
    elif isinstance(exc, requests.HTTPError) and exc.response is not None:
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except ValueError:
            detail = exc.response.text
        st.error(f"Backend returned {exc.response.status_code}: {detail}")
    else:
        st.error(f"Unexpected error: {exc}")


def _render_upload_area(analysis_mode: str):
    """Two-column upload widgets. Returns (resume_file, jd_file, jd_text)."""
    left, right = st.columns(2)

    with left:
        st.markdown("### 📄 Upload Resume")
        resume_file = st.file_uploader(
            "Choose your resume file",
            type=["pdf", "doc", "docx"],
            help="Supported: PDF, DOC, DOCX (max 5 MB)",
            key="resume_upload",
        )
        if resume_file:
            st.success(f"✅ {resume_file.name} ({resume_file.size / 1024:.1f} KB)")

    jd_file: Optional[object] = None
    jd_text = ""

    with right:
        if analysis_mode == "Job Description Comparison":
            st.markdown("### 📋 Job Description")
            jd_method = st.radio(
                "Input method:",
                ["Paste Text", "Upload .txt File"],
                horizontal=True,
                key="jd_input_method",
            )
            if jd_method == "Upload .txt File":
                jd_file = st.file_uploader(
                    "Choose JD file (.txt only)",
                    type=["txt"],
                    key="jd_upload",
                )
                if jd_file:
                    st.success(f"✅ {jd_file.name}")
            else:
                jd_text = st.text_area(
                    "Paste job description text:",
                    height=200,
                    placeholder="Paste the JD here...",
                    key="jd_text",
                )
                if jd_text:
                    st.success(f"✅ {len(jd_text)} characters")
        else:
            st.markdown("### 📋 Job Description")

    return resume_file, jd_file, jd_text


def _render_export_buttons(analysis: dict) -> None:
    st.markdown("### 📥 Export Results")
    c1, c2 = st.columns(2)

    current_fp = _analysis_fingerprint(analysis)

    # If the cached PDF was generated from a different analysis than the one
    # currently on screen (e.g. the user re-ran the analysis), drop it — a
    # stale PDF must never be offered for download.
    if st.session_state.get("scorer_pdf_for") not in (None, current_fp):
        st.session_state.pop("scorer_pdf_bytes", None)
        st.session_state.pop("scorer_pdf_for", None)

    with c1:
        if st.button("📑 Generate PDF Report", use_container_width=True, type="primary"):
            try:
                with st.spinner("Generating PDF on backend..."):
                    pdf_bytes = api_client.generate_pdf(
                        analysis,
                        access_token=st.session_state["access_token"],
                    )
                st.session_state["scorer_pdf_bytes"] = pdf_bytes
                st.session_state["scorer_pdf_for"] = current_fp
            except requests.RequestException as exc:
                _show_backend_error(exc)

        if (
            "scorer_pdf_bytes" in st.session_state
            and st.session_state.get("scorer_pdf_for") == current_fp
        ):
            st.download_button(
                "⬇️ Download PDF",
                data=st.session_state["scorer_pdf_bytes"],
                file_name="ats_resume_report.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="download_pdf_report",
            )



def render() -> None:
    st.title("📄 AI Resume Screener & Job Matcher")
    st.markdown("Upload your resume and provide the target job description for a 1-to-1 match analysis.")

    st.markdown("---")

    analysis_mode = "Job Description Comparison"

    st.markdown("---")

    resume_file, jd_file, jd_text = _render_upload_area(analysis_mode)

    # If the person swaps in a different resume file, any previously
    # generated analysis/PDF belongs to the old file — drop it immediately
    # rather than risk it being shown/downloaded alongside the new upload.
    if resume_file is not None:
        current_upload_id = (resume_file.name, resume_file.size)
        if st.session_state.get("scorer_upload_id") not in (None, current_upload_id):
            st.session_state.pop("scorer_analysis", None)
            st.session_state.pop("scorer_pdf_bytes", None)
            st.session_state.pop("scorer_pdf_for", None)
        st.session_state["scorer_upload_id"] = current_upload_id

    st.markdown("---")

    if not resume_file:
        st.info("👆 Upload your resume to begin.")
        # If we have a prior result in session, render it again.
        if st.session_state.get("scorer_analysis"):
            display_results_dashboard(st.session_state["scorer_analysis"])
        return

    access_token = st.session_state.get("access_token")
    if not access_token:
        st.warning("⚠️ Sign in from the sidebar to analyze a resume.")
        return

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        analyze = st.button("🚀 Analyze Resume", use_container_width=True, type="primary")

    if not analyze:
        # Re-show previous result on rerun (e.g. after PDF generation).
        if st.session_state.get("scorer_analysis"):
            display_results_dashboard(st.session_state["scorer_analysis"])
            _render_export_buttons(st.session_state["scorer_analysis"])
        return

    # Fresh analysis — drop any cached PDF/result.
    st.session_state.pop("scorer_pdf_bytes", None)
    st.session_state.pop("scorer_analysis", None)

    job_description = _read_jd(jd_file, jd_text) if analysis_mode == "Job Description Comparison" else ""

    try:
        with st.spinner("Analyzing your resume... this can take 10–30 seconds."):
            analysis = api_client.analyze_resume(
                resume_file=resume_file,
                access_token=access_token,
                job_description=job_description,
            )
    except requests.RequestException as exc:
        _show_backend_error(exc)
        return

    st.session_state["scorer_analysis"] = analysis
    st.success("✅ Analysis complete!")
    display_results_dashboard(analysis)
    _render_export_buttons(analysis)
