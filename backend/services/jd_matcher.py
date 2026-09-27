"""
JD ↔ Resume Matcher

Skill matching is conservative and evidence-based.

Matching sources:
    1. Explicit resume skills
    2. Explicit project evidence
    3. Explicit work-experience evidence
    4. Explicit education/coursework evidence

Overall semantic similarity is calculated separately and is NOT used
to invent individual skill matches.
"""

import re
from typing import Dict, List, Tuple

import numpy as np
from rapidfuzz import fuzz


# ============================================================================
# SKILL ALIASES
# ============================================================================

SKILL_ALIASES = {
    "oop": "object oriented programming",
    "o.o.p": "object oriented programming",
    "object oriented programming": "object oriented programming",
    "object-oriented programming": "object oriented programming",

    "dsa": "data structures and algorithms",
    "data structures & algorithms": "data structures and algorithms",
    "data structures and algorithms": "data structures and algorithms",
    "data structures algorithms": "data structures and algorithms",
    "data structures and algorithm": "data structures and algorithms",

    "dbms": "database management systems",
    "database management system": "database management systems",
    "database management systems": "database management systems",

    "ml": "machine learning",
    "machine learning": "machine learning",

    "dl": "deep learning",
    "deep learning": "deep learning",

    "cv": "computer vision",
    "computer vision": "computer vision",

    "nlp": "natural language processing",
    "natural language processing": "natural language processing",

    "ai": "artificial intelligence",
    "artificial intelligence": "artificial intelligence",

    "sklearn": "scikit learn",
    "scikit-learn": "scikit learn",
    "scikit learn": "scikit learn",

    "rest api": "rest apis",
    "rest apis": "rest apis",
    "restful api": "rest apis",
    "restful apis": "rest apis",

    "js": "javascript",
    "javascript": "javascript",

    "ts": "typescript",
    "typescript": "typescript",

    "postgres": "postgresql",
    "postgresql": "postgresql",

    "amazon web services": "aws",
    "aws": "aws",

    "google cloud platform": "gcp",
    "gcp": "gcp",

    "microsoft azure": "azure",
    "azure": "azure",
}


# ============================================================================
# NORMALIZATION
# ============================================================================

def _normalize(text: str) -> str:
    """Normalize a skill phrase for comparison."""

    if not text:
        return ""

    text = str(text).strip().lower()

    text = text.replace("&", " and ")
    text = text.replace("-", " ")
    text = text.replace("/", " ")

    # Keep + and # for C++ and C#.
    text = re.sub(r"[^a-z0-9+#.\s]", " ", text)

    text = text.replace(".", "")

    text = re.sub(r"\s+", " ", text).strip()

    return SKILL_ALIASES.get(text, text)


def _clean_skill_list(skills) -> List[str]:
    """Clean and deduplicate skill names."""

    if not skills:
        return []

    cleaned = []
    seen = set()

    for skill in skills:

        if skill is None:
            continue

        skill = str(skill).strip()

        if not skill:
            continue

        normalized = _normalize(skill)

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(normalized)
        cleaned.append(skill)

    return cleaned


# ============================================================================
# PROJECT + EXPERIENCE EVIDENCE
# ============================================================================

def _build_resume_evidence(
    projects: List[Dict] = None,
    experience_entries: List[Dict] = None,
) -> List[str]:
    """
    Build evidence from projects and work experience.
    """

    evidence = []

    projects = projects or []
    experience_entries = experience_entries or []

    # ----------------------------------------------------------------------
    # Projects
    # ----------------------------------------------------------------------

    for project in projects:

        if not isinstance(project, dict):
            continue

        parts = []

        title = project.get("title")
        description = project.get("description")
        technologies = project.get("technologies", [])

        if title:
            parts.append(str(title))

        if description:
            parts.append(str(description))

        if technologies:

            if isinstance(technologies, list):
                parts.extend(
                    str(item)
                    for item in technologies
                    if item
                )
            else:
                parts.append(str(technologies))

        if parts:
            evidence.append(" ".join(parts))

    # ----------------------------------------------------------------------
    # Experience
    # ----------------------------------------------------------------------

    for experience in experience_entries:

        if not isinstance(experience, dict):
            continue

        parts = []

        job_title = experience.get("job_title")
        company = experience.get("company")
        description = experience.get("description")
        duration = experience.get("duration")

        if job_title:
            parts.append(str(job_title))

        if company:
            parts.append(str(company))

        if description:
            parts.append(str(description))

        if duration:
            parts.append(str(duration))

        if parts:
            evidence.append(" ".join(parts))

    return evidence


# ============================================================================
# EDUCATION / COURSEWORK EVIDENCE
# ============================================================================

def _build_education_evidence(
    education_entries=None,
) -> List[str]:
    """
    Extract only coursework/subject information from education.

    We intentionally DO NOT use:
        - degree names
        - college names
        - university names
        - graduation years
        - CGPA

    This prevents qualifications such as "B.Tech" from becoming
    technical skill matches.

    Supported possible parser fields include:
        coursework
        courses
        subjects
        relevant_coursework
        modules
        academic_subjects
        description
        details
    """

    evidence = []

    if not education_entries:
        return evidence

    # Normalize a single education dictionary into a list.
    if isinstance(education_entries, dict):
        education_entries = [education_entries]

    # If parser returned strings, accept them as coursework evidence.
    if isinstance(education_entries, str):
        education_entries = [education_entries]

    for education in education_entries:

        # --------------------------------------------------------------
        # String education entry
        # --------------------------------------------------------------

        if isinstance(education, str):
            evidence.append(education)
            continue

        if not isinstance(education, dict):
            continue

        coursework_fields = [
            "coursework",
            "courses",
            "subjects",
            "relevant_coursework",
            "modules",
            "academic_subjects",
            "description",
            "details",
        ]

        parts = []

        for field in coursework_fields:

            value = education.get(field)

            if not value:
                continue

            if isinstance(value, list):

                parts.extend(
                    str(item)
                    for item in value
                    if item
                )

            else:
                parts.append(str(value))

        if parts:
            evidence.append(" ".join(parts))

    return evidence


# ============================================================================
# EXPLICIT TEXT MATCH
# ============================================================================

def _phrase_in_text(
    skill: str,
    text: str,
) -> bool:
    """
    Check whether a skill is explicitly mentioned in evidence.

    Examples:

        Python in "Built models using Python"       → True
        Git in "Used GitHub"                         → False
        C++ in "Implemented algorithms in C++"       → True
    """

    if not skill or not text:
        return False

    skill_normalized = _normalize(skill)
    text_normalized = _normalize(text)

    if not skill_normalized or not text_normalized:
        return False

    pattern = (
        r"(?<![a-z0-9])"
        + re.escape(skill_normalized)
        + r"(?![a-z0-9])"
    )

    return re.search(
        pattern,
        text_normalized,
    ) is not None


# ============================================================================
# EXPLICIT SKILL MATCH
# ============================================================================

def _explicit_skill_match(
    jd_skill: str,
    resume_skills: List[str],
) -> Tuple[bool, str]:
    """
    Match a JD skill against explicitly extracted resume skills.

    Matching:
        1. Exact normalized match
        2. Known alias
        3. Very high-confidence fuzzy match for longer phrases

    No loose semantic matching is used here.
    """

    jd_normalized = _normalize(jd_skill)

    if not jd_normalized:
        return False, ""

    for resume_skill in resume_skills:

        resume_normalized = _normalize(resume_skill)

        if not resume_normalized:
            continue

        # Exact.
        if jd_normalized == resume_normalized:
            return True, resume_skill

        # Known alias.
        jd_alias = SKILL_ALIASES.get(
            jd_normalized,
            jd_normalized,
        )

        resume_alias = SKILL_ALIASES.get(
            resume_normalized,
            resume_normalized,
        )

        if jd_alias == resume_alias:
            return True, resume_skill

        # Conservative fuzzy matching.
        if (
            len(jd_normalized) >= 8
            and len(resume_normalized) >= 8
        ):

            ratio = fuzz.token_set_ratio(
                jd_normalized,
                resume_normalized,
            )

            if ratio >= 96:
                return True, resume_skill

    return False, ""


# ============================================================================
# SKILL MATCHING
# ============================================================================

def _match_skills(
    jd_skills: List[str],
    resume_skills: List[str],
    projects: List[Dict] = None,
    experience_entries: List[Dict] = None,
    education_entries=None,
    embedder=None,
) -> Tuple[List[str], List[str], Dict[str, Dict]]:
    """
    Match actual JD skills against resume evidence.

    Individual skill matching does NOT use semantic similarity.

    Evidence sources:
        - Resume skills
        - Projects
        - Experience
        - Education/coursework
    """

    jd_skills = _clean_skill_list(
        jd_skills
    )

    resume_skills = _clean_skill_list(
        resume_skills
    )

    project_experience_evidence = _build_resume_evidence(
        projects=projects,
        experience_entries=experience_entries,
    )

    education_evidence = _build_education_evidence(
        education_entries
    )

    # Combine evidence sources.
    all_evidence = (
        project_experience_evidence
        + education_evidence
    )

    matched_skills = []
    missing_skills = []
    evidence_map = {}

    for jd_skill in jd_skills:

        # ==============================================================
        # LEVEL 1
        # Explicit resume skill
        # ==============================================================

        explicit_match, matched_resume_skill = (
            _explicit_skill_match(
                jd_skill,
                resume_skills,
            )
        )

        if explicit_match:

            matched_skills.append(
                jd_skill
            )

            evidence_map[jd_skill] = {
                "type": "explicit_skill",
                "matched_with": matched_resume_skill,
                "confidence": 1.0,
            }

            continue

        # ==============================================================
        # LEVEL 2
        # Explicit project / experience / coursework evidence
        # ==============================================================

        matched_evidence = None
        evidence_type = None

        # First check project / experience.
        for evidence_item in project_experience_evidence:

            if _phrase_in_text(
                jd_skill,
                evidence_item,
            ):

                matched_evidence = evidence_item
                evidence_type = "resume_evidence"
                break

        # Then check education/coursework.
        if matched_evidence is None:

            for evidence_item in education_evidence:

                if _phrase_in_text(
                    jd_skill,
                    evidence_item,
                ):

                    matched_evidence = evidence_item
                    evidence_type = "education_coursework"
                    break

        if matched_evidence is not None:

            matched_skills.append(
                jd_skill
            )

            evidence_map[jd_skill] = {
                "type": evidence_type,
                "matched_with": matched_evidence,
                "confidence": 0.95,
            }

            continue

        # ==============================================================
        # LEVEL 3
        # No reliable evidence
        # ==============================================================

        missing_skills.append(
            jd_skill
        )

        evidence_map[jd_skill] = {
            "type": "not_demonstrated",
            "matched_with": "",
            "confidence": 0.0,
        }

    return (
        matched_skills,
        missing_skills,
        evidence_map,
    )


# ============================================================================
# OVERALL SEMANTIC SIMILARITY
# ============================================================================

def calculate_semantic_similarity(
    resume_text: str,
    jd_text: str,
    embedder,
) -> float:
    """
    Calculate document-level semantic similarity.

    Returns a decimal between 0 and 1.

    Example:
        0.60 = 60%
    """

    if (
        not resume_text
        or not jd_text
        or not embedder
    ):
        return 0.0

    try:

        embeddings = embedder.encode(
            [
                resume_text,
                jd_text,
            ],
            convert_to_numpy=True,
        )

        embeddings = np.asarray(
            embeddings
        )

        if (
            embeddings.ndim != 2
            or len(embeddings) != 2
        ):
            return 0.0

        resume_embedding = embeddings[0]
        jd_embedding = embeddings[1]

        resume_norm = np.linalg.norm(
            resume_embedding
        )

        jd_norm = np.linalg.norm(
            jd_embedding
        )

        if (
            resume_norm == 0
            or jd_norm == 0
        ):
            return 0.0

        similarity = float(
            np.dot(
                resume_embedding,
                jd_embedding,
            )
            / (
                resume_norm
                * jd_norm
            )
        )

        return max(
            0.0,
            min(
                1.0,
                similarity,
            ),
        )

    except Exception:
        return 0.0


# ============================================================================
# OVERALL MATCH PERCENTAGE
# ============================================================================

def calculate_match_percentage(
    matched_count: int,
    total_jd_skills: int,
    semantic_similarity: float,
) -> float:
    """
    Overall match score:

        80% → skill coverage
        20% → document-level semantic similarity
    """

    if total_jd_skills > 0:

        skill_ratio = (
            matched_count
            / total_jd_skills
        )

    else:
        skill_ratio = 0.0

    semantic_similarity = max(
        0.0,
        min(
            1.0,
            semantic_similarity,
        ),
    )

    score = (
        (
            skill_ratio
            * 0.80
        )
        +
        (
            semantic_similarity
            * 0.20
        )
    ) * 100

    return round(
        score,
        2,
    )


# ============================================================================
# PUBLIC FUNCTION
# ============================================================================

def compare_resume_with_jd(
    resume_text: str,
    resume_keywords: List[str],
    resume_skills: List[str],
    jd_text: str,
    jd_keywords: List[str],
    embedder,
    nlp=None,
    jd_skills: List[str] = None,
    projects: List[Dict] = None,
    experience_entries: List[Dict] = None,
    education_entries=None,
) -> Dict:
    """
    Compare resume with JD.

    Only `jd_skills` controls matched/missing skill analysis.

    Resume/JD keywords are deliberately NOT treated as skill gaps.
    """

    jd_skills = _clean_skill_list(
        jd_skills or []
    )

    resume_skills = _clean_skill_list(
        resume_skills or []
    )

    (
        matched_skills,
        missing_skills,
        evidence_map,
    ) = _match_skills(
        jd_skills=jd_skills,
        resume_skills=resume_skills,
        projects=projects,
        experience_entries=experience_entries,
        education_entries=education_entries,
        embedder=embedder,
    )

    # Overall semantic similarity.
    semantic_similarity = calculate_semantic_similarity(
        resume_text=resume_text,
        jd_text=jd_text,
        embedder=embedder,
    )

    # Overall match percentage.
    match_percentage = calculate_match_percentage(
        matched_count=len(
            matched_skills
        ),
        total_jd_skills=len(
            jd_skills
        ),
        semantic_similarity=semantic_similarity,
    )

    # Skill coverage percentage.
    if jd_skills:

        skill_match_ratio = (
            len(matched_skills)
            / len(jd_skills)
        ) * 100

    else:

        skill_match_ratio = 0.0

    # We intentionally do not populate these.
    #
    # Generic JD terms such as:
    #     internship
    #     documentation
    #     bachelor's degree
    #     academic project
    #     develop applications
    #
    # should not appear as missing skills.
    matched_keywords = []
    missing_keywords = []

    return {
        "match_percentage": match_percentage,

        # Decimal expected by the current UI.
        # Example: 0.60 → 60%
        "semantic_similarity": round(
            semantic_similarity,
            4,
        ),

        "matched_skills": matched_skills,

        "missing_skills": missing_skills,

        # Backward compatibility.
        "skills_gap": missing_skills,

        "matched_keywords": matched_keywords,

        "missing_keywords": missing_keywords,

        "total_jd_skills": len(
            jd_skills
        ),

        "matched_skill_count": len(
            matched_skills
        ),

        "missing_skill_count": len(
            missing_skills
        ),

        "skill_match_ratio": round(
            skill_match_ratio,
            2,
        ),

        "evidence": evidence_map,
    }