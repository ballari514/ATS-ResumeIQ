import json
import os
import urllib.error
import urllib.request
from typing import Dict, List, Optional


def generate_llm_resume_suggestions(
    matched_skills: List[str],
    missing_skills: List[str],
) -> List[Dict]:
    """Generate personalized resume suggestions using Groq."""

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return []

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    prompt = f"""
You are an AI resume improvement assistant.

The resume-JD matching system has already calculated these results:

Matched skills:
{json.dumps(matched_skills, ensure_ascii=False)}

Missing / not demonstrated skills:
{json.dumps(missing_skills, ensure_ascii=False)}

Generate up to 3 concise, actionable resume suggestions.

Your suggestions must:
1. Be based ONLY on the supplied skills.
2. Never claim that the candidate has a skill that is listed as missing.
3. Suggest a resume section, bullet-point improvement, or rewording opportunity.
4. If a missing skill is important, suggest where the candidate could mention
   it ONLY if they genuinely have that experience.
5. Do not change or recalculate any score.
6. Do not mention ATS score, semantic score, or matching calculations.
7. Do not give generic advice unrelated to the supplied skills.

Return ONLY valid JSON in this exact format:
[
  {{
    "title": "Short suggestion title",
    "suggestion": "Actionable suggestion",
    "type": "llm_resume_suggestion"
  }}
]
"""

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a resume improvement assistant. "
                    "Return only valid JSON."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }

    request = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

        generated_text = (
            result.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        if not generated_text:
            return []

        generated_text = generated_text.strip()

        if generated_text.startswith("```"):
            generated_text = generated_text.replace("```json", "", 1)
            generated_text = generated_text.replace("```", "")
            generated_text = generated_text.strip()

        parsed = json.loads(generated_text)

        if not isinstance(parsed, list):
            return []

        suggestions = []

        for item in parsed[:3]:
            if not isinstance(item, dict):
                continue

            title = str(item.get("title", "")).strip()
            suggestion = str(item.get("suggestion", "")).strip()

            if title and suggestion:
                suggestions.append({
                    "icon": "🤖",
                    "title": title,
                    "suggestion": suggestion,
                    "type": "llm_resume_suggestion",
                })

        return suggestions

    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
        ValueError,
    ):
        return []


def generate_jd_recommendations(
    jd_comparison: Optional[Dict],
) -> List[Dict]:
    """
    Generate actionable resume recommendations.

    Existing rule-based recommendations are preserved.
    Groq is additionally used for personalized resume suggestions.

    This function does not modify or recalculate matching or scoring.
    """

    if not jd_comparison:
        return []

    recommendations = []

    matched_skills = jd_comparison.get("matched_skills", []) or []
    missing_skills = jd_comparison.get("missing_skills", []) or []

    matched_lower = {
        str(skill).lower()
        for skill in matched_skills
    }

    missing_lower = {
        str(skill).lower()
        for skill in missing_skills
    }

    def add_recommendation(
        title: str,
        suggestion: str,
        rec_type: str,
    ):
        recommendations.append({
            "icon": "💡",
            "title": title,
            "suggestion": suggestion,
            "type": rec_type,
        })

    ml_skills = {
        "machine learning",
        "deep learning",
        "ml",
        "dl",
    }

    if matched_lower.intersection(ml_skills):
        add_recommendation(
            "Strengthen ML project evidence",
            "For your strongest ML project, mention the model used and an evaluation metric such as accuracy, F1-score, MAE, RMSE, or R² when available.",
            "project_evidence",
        )

    if (
        "rest apis" in missing_lower
        or "rest api" in missing_lower
    ):
        add_recommendation(
            "Strengthen API experience",
            "If you have built or consumed an API, explicitly describe the REST API, endpoint, or backend functionality in your project or experience section.",
            "api",
        )

    if (
        "git" in missing_lower
        and "github" in matched_lower
    ):
        add_recommendation(
            "Clarify version-control experience",
            "Your resume mentions GitHub but does not provide sufficient evidence for Git. If you genuinely used Git for version control, mention it explicitly.",
            "version_control",
        )

    if "docker" in missing_lower:
        add_recommendation(
            "Consider adding containerization experience",
            "If Docker is relevant to your target role, gain hands-on experience through a genuine project and describe how you used it.",
            "docker",
        )

    cloud_skills = {
        "aws",
        "gcp",
        "azure",
        "cloud platforms",
    }

    missing_cloud = [
        skill
        for skill in cloud_skills
        if skill in missing_lower
    ]

    if missing_cloud:
        add_recommendation(
            "Consider relevant cloud experience",
            f"If cloud skills are important for the target role, gain genuine hands-on experience with {missing_cloud[0].upper()} through a project before listing it.",
            "cloud",
        )

    if "data visualization" in missing_lower:
        add_recommendation(
            "Strengthen data-visualization evidence",
            "If you have created charts or visual analysis in a project, explicitly mention the visualization tools and what insights you produced.",
            "data_visualization",
        )

    if (
        "feature engineering" in missing_lower
        and (
            "machine learning" in matched_lower
            or "ml" in matched_lower
        )
    ):
        add_recommendation(
            "Document feature-engineering work",
            "If you performed feature selection, transformation, encoding, scaling, or other feature-engineering steps, describe them in the relevant ML project.",
            "feature_engineering",
        )

    llm_recommendations = generate_llm_resume_suggestions(
        matched_skills=[
            str(skill)
            for skill in matched_skills
        ],
        missing_skills=[
            str(skill)
            for skill in missing_skills
        ],
    )

    recommendations.extend(llm_recommendations)

    unique = []
    seen = set()

    for rec in recommendations:
        key = rec["suggestion"].strip().lower()

        if key not in seen:
            seen.add(key)
            unique.append(rec)

    return unique[:5]
