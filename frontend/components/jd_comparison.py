from typing import Any, Dict, Optional

import streamlit as st


def display_jd_comparison(jd_comparison: Optional[Dict[str, Any]]) -> None:
    if not jd_comparison:
        return  # caller decides whether to render the section at all

    st.markdown("### 🎯 Resume–Job Description Match")

    match_pct = float(jd_comparison.get("match_percentage", 0))
    semantic = float(jd_comparison.get("semantic_similarity", 0))
    matched_skills = jd_comparison.get("matched_skills", []) or []
    missing_skills = jd_comparison.get("missing_skills", []) or jd_comparison.get("skills_gap", []) or []
    matched_keywords = jd_comparison.get("matched_keywords", []) or []
    missing_keywords = jd_comparison.get("missing_keywords", []) or []

    top_l, top_r = st.columns(2)
    with top_l:
        st.metric("Match Percentage", f"{match_pct:.0f}%")
        st.progress(min(max(match_pct / 100.0, 0.0), 1.0))
        st.metric("Semantic Similarity", f"{semantic * 100:.0f}%")
        st.progress(min(max(semantic, 0.0), 1.0))
    with top_r:
        st.markdown("**✅ Matched skills**")
        st.markdown(", ".join(matched_skills[:15]) if matched_skills else "_No explicit skill matches yet_")
        if matched_keywords:
            st.caption("Matched JD keywords: " + ", ".join(matched_keywords[:10]))

    st.markdown("---")
    bot_l, bot_r = st.columns(2)
    with bot_l:
        st.markdown("**⚠️ Missing / not demonstrated skills**")
        if missing_skills:
            for skill in missing_skills[:10]:
                st.markdown(f"- {skill}")
        else:
            st.markdown("_No explicit skill gaps detected_")
        if missing_keywords:
            st.caption("Other missing JD terms: " + ", ".join(missing_keywords[:8]))
    with bot_r:
        st.markdown("**🧩 What this means**")
        if missing_skills:
            st.markdown(" These are JD requirements for which sufficient evidence was not found in the resume, projects, experience, or coursework")
        else:
            st.markdown("The explicit skills extracted from the JD are supported by evidence in the resume, projects, experience, or coursework.")
