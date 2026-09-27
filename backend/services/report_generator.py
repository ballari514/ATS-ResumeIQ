import os
from datetime import datetime
from zoneinfo import ZoneInfo
from jinja2 import Environment, FileSystemLoader
from typing import Dict

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), '..', 'templates')
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))


def format_date(value, fmt='%B %d, %Y at %I:%M %p'):
    """Convert an ISO timestamp string to a human-readable date string."""
    if not value:
        return ''
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return dt.strftime(fmt)
    except Exception:
        return value


env.filters['format_date'] = format_date


def generate_html_reports(analysis_data: Dict) -> Dict[str, str]:
    """Render the current Resume-JD summary report."""
    now = datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()

    candidate_name = (
        analysis_data.get('candidate_name')
        or analysis_data.get('name')
        or ''
    )
    email = analysis_data.get('email') or ''
    phone = analysis_data.get('phone') or ''

    education = (
        analysis_data.get('education')
        or analysis_data.get('education_details')
        or ''
    )

    experience_months = analysis_data.get('experience_months')
    if experience_months is not None and float(experience_months) > 0:
        years_of_experience = round(float(experience_months) / 12, 1)
    else:
        years_of_experience = 'No experience'

    overall_score = (
        analysis_data.get('ATS_score', 0)
        or analysis_data.get('ats_score', 0)
    )

    jd_raw = (
        analysis_data.get('jd_match_analysis')
        or analysis_data.get('jd_comparison')
        or {}
    )

    if hasattr(jd_raw, 'model_dump'):
        jd_raw = jd_raw.model_dump()

    recommendations = analysis_data.get('jd_recommendations', []) or []

    context = {
        'timestamp': now,
        'candidate_name': candidate_name,
        'email': email,
        'phone': phone,
        'education': education,
        'years_of_experience': years_of_experience,
        'overall_score': overall_score,
        'jd_analysis': jd_raw,
        'recommendations': recommendations,
    }

    return {
        'summary': env.get_template('summary.html').render(**context),
    }
