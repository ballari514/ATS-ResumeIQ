from typing import Any, Dict

import streamlit as st

from frontend.components.score_display import display_overall_score, display_score_breakdown
from frontend.components.jd_comparison import display_jd_comparison


def display_jd_recommendations(analysis: Dict[str, Any]) -> None:
    """Display evidence-based JD recommendations."""
    recommendations = analysis.get("jd_recommendations", [])

    if not recommendations:
        return

    st.markdown("---")
    st.markdown("### 💡 Recommendations")

    for rec in recommendations:
        title = rec.get("title", "")
        suggestion = rec.get("suggestion", "")

        if title and suggestion:
            st.markdown(f"**{title}**")
            st.markdown(f"→ {suggestion}")
        elif suggestion:
            st.markdown(f"→ {suggestion}")


def display_candidate_information(analysis: Dict[str, Any]) -> None:
    """Display extracted candidate information using the existing dashboard layout."""
    name = analysis.get("candidate_name", "")
    email = analysis.get("email", "")
    phone = analysis.get("phone", "")
    education = analysis.get("education", [])
    years = analysis.get("years_of_experience", 0.0)

    if not any([name, email, phone, education, years]):
        return

    st.markdown("### 👤 Candidate Information")

    cols = st.columns(3)

    if name:
        cols[0].markdown(f"**Name**\n{name}")

    if email:
        cols[1].markdown(f"**Email**\n{email}")

    if phone:
        cols[2].markdown(f"**Phone**\n{phone}")

    # Education
    if education:
        education_items = []

        for item in education:
            if isinstance(item, dict):
                degree = item.get("degree", "")
                institution = item.get("institution", "")
                year = item.get("year", "")

                value = " — ".join(
                    x for x in [degree, institution, year] if x
                )

                if value:
                    education_items.append(value)

        if education_items:
            st.markdown("**Education:**")
            for item in education_items:
                st.markdown(f"- {item}")

    # Years of Experience
    if years is not None:
        try:
            years_value = float(years)

            if years_value > 0:
                experience_text = f"{years_value:g} years"
            else:
                experience_text = "No experience"

        except (TypeError, ValueError):
            experience_text = str(years)

        st.markdown(
            f"**Years of Experience:** {experience_text}"
        )


def display_results_dashboard(analysis: Dict[str, Any]) -> None:
    """Render the concise analysis results without changing backend scoring."""
    display_candidate_information(analysis)
    st.markdown("---")
    display_overall_score(analysis)
    st.markdown("---")

    display_score_breakdown(analysis)

    jd_comparison = analysis.get("jd_comparison") or analysis.get("jd_match_analysis")

    if jd_comparison:
        st.markdown("---")
        display_jd_comparison(jd_comparison)

        display_jd_recommendations(analysis)
