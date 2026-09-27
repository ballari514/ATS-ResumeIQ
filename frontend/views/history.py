import requests
import streamlit as st

from frontend.services import api_client


def _show_backend_error(exc: Exception) -> None:
    if isinstance(exc, requests.ConnectionError):
        st.error("Could not reach the backend. Is it running on port 8000?")
    elif isinstance(exc, requests.HTTPError) and exc.response is not None:
        st.error(f"Backend returned {exc.response.status_code}: {exc.response.text}")
    else:
        st.error(f"Unexpected error: {exc}")


def render() -> None:
    st.title("📊 Analysis History")
    st.markdown("Past analyses saved against your account.")

    access_token = st.session_state.get("access_token")
    if not access_token:
        st.warning("⚠️ Sign in from the sidebar to view your history.")
        return

    try:
        history = api_client.get_history(access_token)
    except requests.RequestException as exc:
        _show_backend_error(exc)
        return

    if not history:
        st.info("No analyses yet for this account. Run an analysis first.")
        if st.button("🎯 Go to Resume Analysis"):
            st.session_state.current_view = "scorer"
            st.rerun()
        return

    st.markdown(f"**Total analyses:** {len(history)}")
    st.markdown("---")

    for idx, entry in enumerate(history):
        filename = entry.get("filename", "resume")
        semantic_score = float(entry.get("ats_score", 0))
        created_at = entry.get("created_at", "")
        analysis = entry.get("analysis_result", {}) or {}
        jd_comparison = analysis.get("jd_comparison") or analysis.get("jd_match_analysis")

        with st.expander(f"📄 {filename} — ATS Score: {semantic_score:.0f}/100 — {created_at}"):
            c1, c2 = st.columns(2)
            with c1:
                st.metric("ATS Score", f"{semantic_score:.0f}/100")
            with c2:
                if jd_comparison:
                    st.metric("JD Match", f"{float(jd_comparison.get('match_percentage', 0)):.0f}%")

            if jd_comparison:
                matched = jd_comparison.get("matched_skills", []) or jd_comparison.get("matched_keywords", []) or []
                missing = jd_comparison.get("missing_skills", []) or jd_comparison.get("missing_keywords", []) or []
                if matched:
                    st.markdown("**Matched Skills**")
                    st.write(", ".join(matched))
                if missing:
                    st.markdown("**Missing Skills**")
                    st.write(", ".join(missing))

            entry_id = entry.get("id")
            if entry_id:
                if st.button("🗑️ Delete", key=f"delete_{idx}"):
                    try:
                        api_client.delete_history_entry(str(entry_id), access_token)
                        st.success("Deleted.")
                        st.rerun()
                    except requests.RequestException as exc:
                        _show_backend_error(exc)
