import os
import json 
import logging
from typing import Dict

from groq import Groq

logger=logging.getLogger('ats_resume_scorer')


GROQ_MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')

_client=None

def _get_client()->Groq:
    global _client
    if _client is None:
        api_key=os.getenv('GROQ_API_KEY')

        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        _client=Groq(api_key=api_key)
        #_ before client is a convention to indicate that this variable is intended for internal use within the module and should not be accessed directly from outside the module. It helps to avoid naming conflicts and makes it clear that this variable is not part of the public API of the module.
    return _client

RESUME_SYSTEM_PROMPT = (
    "You are a resume parser. Extract information from the resume "
    "and return ONLY a valid JSON object. No explanation, no markdown."
)

RESUME_USER_PROMPT = """Extract the following from this resume and return as JSON:
{{
  "name": "full name",
  "email": "email address",
  "phone": "phone number",
  "linkedin": "LinkedIn URL if present, otherwise null",
  "github": "GitHub URL if present, otherwise null",
  "professional_summary": "the full text of the Summary, Profile, About Me, Objective, or Professional Summary section at the top of the resume. Copy the ENTIRE paragraph exactly as written. If no such section exists, return an empty string.",
  "skills": ["list", "of", "skills"],
  "experience": [
    {{
      "job_title": "",
      "company": "",
      "start_date": "",
      "end_date": "",
      "duration_months": 0,
      "description": ""
    }}
  ],
  "education": [
    {{
      "degree": "",
      "institution": "",
      "year": ""
    }}
  ],
  "certifications": ["list of certifications"],
  "projects": [
    {{
      "title": "project name",
      "description": "what the project does and how it was built",
      "technologies": ["tech", "used"]
    }}
  ],
  "action_verbs": ["strong action verbs used in bullet points, e.g. developed, implemented, designed"],
  "keywords": ["important keywords and phrases from the resume for ATS matching"]
}}

Important instructions:
- For duration_months, calculate the number of months between start_date and end_date. If end_date is "Present" or "Current", calculate from start_date to now.
- For skills, extract ALL technical and soft skills mentioned anywhere in the resume.
- For action_verbs, find verbs that start bullet points or describe achievements.
- For keywords, extract noun phrases and technical terms relevant to ATS matching.
- Return ONLY valid JSON. No markdown code fences, no explanation.

Resume Text:
{raw_text}"""

def _call_groq(client:Groq, system_prompt:str, user_prompt:str)->str:

    response=client.chat.completions.create(
        model=GROQ_MODEL, 
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        #temperature means how much randomness to introduce into the model's responses. A temperature of 0.0 means the model will always choose the most likely next word, leading to more deterministic and focused outputs. Higher temperatures (e.g., 0.7) would make the model's responses more varied and creative, but potentially less accurate or relevant.
        temperature=0.0,
        max_tokens=4096 #roughly 3000 words, which is more than enough for a resume or job description
    )

    return response.choices[0].message.content.strip()

def _try_parse_json(text: str) -> dict | None:

    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):

        # Remove opening fence (```json or ```)
        first_newline = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
        cleaned = cleaned[first_newline + 1:]
        # Remove closing fence
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    
def parse_resume(raw_text: str)->Dict:

    client=_get_client()
    prompt=RESUME_USER_PROMPT.format(raw_text=raw_text)
    #.raw_text=raw_text is a placeholder in the RESUME_USER_PROMPT string that will be replaced with the actual resume text when the prompt is formatted. This allows the prompt to dynamically include the specific resume content that needs to be parsed.
    raw_response=_call_groq(client, RESUME_SYSTEM_PROMPT, prompt)
    result = _try_parse_json(raw_response)

    if result is not None:
        return _validate_resume_result(result)

    logger.warning("Groq resume parse: first attempt returned invalid JSON, retrying...")
    strict_prompt = (
        "Your previous response was not valid JSON. "
        "Return ONLY the raw JSON object, no markdown, no explanation, no code fences.\n\n"
        + prompt
    )
    raw_response = _call_groq(client, RESUME_SYSTEM_PROMPT, strict_prompt)
    result = _try_parse_json(raw_response)
    if result is not None:
        return _validate_resume_result(result)

    raise ValueError(
        f"Groq returned unparseable response after retry. Raw response:\n{raw_response[:500]}"
    )
    
JD_SYSTEM_PROMPT = (
    "You are an expert job-description parser for an explainable AI "
    "resume-to-job matching system. Extract only information explicitly "
    "supported by the job description. Return ONLY a valid JSON object. "
    "Never invent skills or requirements. Keep skills separate from "
    "job titles, education, experience, responsibilities, and generic ATS keywords."
)


JD_USER_PROMPT = """Analyze the following job description and return JSON in exactly this structure:

{{
  "job_title": "",
  "required_skills": [],
  "preferred_skills": [],
  "experience_required": "",
  "education_required": "",
  "key_responsibilities": [],
  "keywords": []
}}

IMPORTANT RULES FOR SKILL EXTRACTION:

1. "required_skills" must contain ONLY genuine skills explicitly required
   by the job description.

2. "preferred_skills" must contain ONLY genuine skills explicitly described
   as preferred, desirable, nice-to-have, bonus, or optional.

3. A skill can be:
   - Programming language
   - Framework
   - Library
   - Software/tool
   - Database technology
   - Cloud technology
   - Technical concept
   - Engineering methodology
   - Professional/soft skill when explicitly required
   - Domain-specific technical skill

4. Examples of valid skills:
   Python
   Java
   SQL
   C++
   JavaScript
   React
   Django
   TensorFlow
   PyTorch
   Scikit-learn
   Docker
   Kubernetes
   AWS
   Azure
   Git
   GitHub
   REST APIs
   Machine Learning
   Deep Learning
   Computer Vision
   Natural Language Processing
   Data Structures and Algorithms
   Object-Oriented Programming
   Database Management
   Problem Solving
   Communication
   Analytical Skills

5. Normalize obvious abbreviations or equivalent names where appropriate:
   - OOP → Object-Oriented Programming
   - DSA → Data Structures and Algorithms
   - DBMS → Database Management Systems
   - ML → Machine Learning
   - DL → Deep Learning
   - NLP → Natural Language Processing
   - CV → Computer Vision
   - REST API / RESTful API → REST APIs

6. DO NOT put any of the following into required_skills or preferred_skills:
   - Job titles
   - Company names
   - Degree names
   - Educational qualifications
   - Years of experience
   - Locations
   - Salary information
   - Job responsibilities
   - Complete sentences
   - Generic phrases such as "develop applications"
   - "work with the team"
   - "maintain software"
   - "write clean code"
   - "document results"
   - "build solutions"
   unless the phrase itself is a clearly identifiable skill.

7. Example:

   Job description:
   "We are looking for a Junior ML Engineer with Python, SQL,
   TensorFlow and strong problem-solving skills. The candidate
   should have a B.Tech degree and will develop ML models,
   work with databases and collaborate with the team."

   Correct extraction:

   required_skills:
   ["Python", "SQL", "TensorFlow", "Machine Learning", "Problem Solving"]

   education_required:
   "B.Tech"

   key_responsibilities:
   [
     "Develop ML models",
     "Work with databases",
     "Collaborate with the team"
   ]

   Incorrect extraction would be:
   ["Junior ML Engineer", "B.Tech", "develop ML models",
    "work with databases", "collaborate with the team"]

8. "keywords" may contain broader ATS-relevant terms, but keywords MUST NOT
   be treated as skills by the skill-matching engine.

9. Do not infer a skill merely because another skill is related to it.
   For example:
   - Docker does NOT automatically mean Kubernetes.
   - GitHub does NOT automatically mean Git.
   - TensorFlow does NOT automatically mean Deep Learning.
   - SQL does NOT automatically mean PostgreSQL.
   Related technologies may be useful evidence, but they are not identical skills.

10. If a requirement is ambiguous, do not invent or guess. Put it in the
    appropriate non-skill field or omit it.

11. Keep each skill as a concise canonical skill name rather than a sentence.

12. Return ONLY valid JSON. No markdown. No explanation.

Job Description:
{raw_text}"""

def parse_job_description(raw_text: str) -> Dict:
    client = _get_client()
    prompt = JD_USER_PROMPT.format(raw_text=raw_text)

    raw_response = _call_groq(client, JD_SYSTEM_PROMPT, prompt)
    result = _try_parse_json(raw_response)
    if result is not None:
        return _validate_jd_result(result)

    #works if result is None, meaning the first attempt to parse the JSON failed. In that case, it logs a warning and retries with a stricter prompt that emphasizes returning only valid JSON. If the second attempt also fails, it raises a ValueError with the raw response for debugging.
    logger.warning("Groq JD parse: first attempt returned invalid JSON, retrying...")
    strict_prompt = (
        "Your previous response was not valid JSON. "
        "Return ONLY the raw JSON object, no markdown, no explanation, no code fences.\n\n"
        + prompt
    )
    raw_response = _call_groq(client, JD_SYSTEM_PROMPT, strict_prompt)
    result = _try_parse_json(raw_response)
    if result is not None:
        return _validate_jd_result(result)

    raise ValueError(
        f"Groq returned unparseable response after retry. Raw response:\n{raw_response[:500]}"
    )

#it will make sure, that the parse json has all the valid fields we expect
def _validate_jd_result(result: dict) -> dict:
    
    defaults = {
        "job_title": "",
        "required_skills": [],
        "preferred_skills": [],
        "experience_required": "",
        "education_required": "",
        "key_responsibilities": [],
        "keywords": [],
    }

    for key, default in defaults.items():
        if key not in result or result[key] is None:
            result[key] = default

        #isInstance checks if the default value is a list and if the corresponding value in the result is not a list. If the result value is not a list, it replaces it with the default list. This ensures that all expected fields are present and have the correct data type, preventing potential errors in downstream processing.
        if isinstance(default, list) and not isinstance(result[key], list):
            result[key] = default

    return result


#to make sure the parse json has all the valid json fields
def _validate_resume_result(result: dict) -> dict:

    defaults = {
        "name": "",
        "email": None,
        "phone": None,
        "linkedin": None,
        "github": None,
        "professional_summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "certifications": [],
        "projects": [],
        "action_verbs": [],
        "keywords": [],
    }
    for key, default in defaults.items():
        if key not in result or result[key] is None:
            result[key] = default
            
        # Ensure list fields are actually lists
        if isinstance(default, list) and not isinstance(result[key], list):
            result[key] = default

    #Validate experience entries
    for exp in result.get("experience", []):
        if not isinstance(exp, dict):
            continue
        exp.setdefault("job_title", "")
        exp.setdefault("company", "")
        exp.setdefault("start_date", "")
        exp.setdefault("end_date", "")
        exp.setdefault("duration_months", 0)
        exp.setdefault("description", "")
        #Ensure duration_months is an int
        try:
            exp["duration_months"] = int(exp["duration_months"])
        except (ValueError, TypeError):
            exp["duration_months"] = 0

    #Validate project entries
    for proj in result.get("projects", []):
        if not isinstance(proj, dict):
            continue
        proj.setdefault("title", "")
        proj.setdefault("description", "")
        proj.setdefault("technologies", [])

    return result


