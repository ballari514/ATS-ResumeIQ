from typing import Any, Dict, List
import streamlit as st


def display_strengths(strengths: List[str]) -> None:
    st.markdown("### 💪 Strengths")
    if not strengths:
        st.info("No specific strengths were detected from the current analysis.")
        return
    for item in strengths:
        st.markdown(f"- {item}")


def display_critical_issues(analysis: Dict[str, Any]) -> None:
    critical = analysis.get("critical_issues") or []
    summary = analysis.get("issues_summary") or []

    if not critical and not summary:
        st.success("### ✅ No Major Issues Found")
        st.markdown("Your resume doesn't have any urgent issues. Nice work.")
        return

    st.markdown("### ⚠️ Areas for Improvement")
    st.warning("These are the main areas that may reduce the resume score or job match.")

    for item in critical:
        st.markdown(f"- {item}")

    extra = [s for s in summary if s not in critical]
    if extra:
        with st.expander("📋 Additional flagged items", expanded=False):
            for item in extra:
                st.markdown(f"- {item}")
