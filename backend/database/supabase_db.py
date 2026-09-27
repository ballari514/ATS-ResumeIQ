import logging
import httpx
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict

logger = logging.getLogger('ats_resume_scorer')

from backend.core.config import SUPABASE_URL, SUPABASE_KEY


class SupabaseNotConfiguredError(RuntimeError):
    """Raised when SUPABASE_URL / SUPABASE_KEY (service role) are missing.

    Previously, a missing config silently produced an empty history list or
    a silently-dropped save — which looked exactly like "you have no history
    yet" even after running several analyses. Raising here lets callers
    decide what to do (log loudly, or surface a real error to the user)
    instead of masking the problem as an empty state.
    """


def _get_headers() -> Dict[str, str]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise SupabaseNotConfiguredError(
            "Supabase is not configured on the backend — set SUPABASE_URL and "
            "SUPABASE_KEY (the Supabase project's *service_role* key, not the "
            "anon key) in the backend's .env file. History cannot be saved or "
            "loaded until this is set."
        )
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


async def save_analysis(user_id: str, filename: str, analysis_result: Dict) -> Optional[str]:
    try:
        headers = _get_headers()
    except SupabaseNotConfiguredError as exc:
        logger.error(f"Cannot save analysis history: {exc}")
        return None

    def _json_default(o):
        if hasattr(o, 'model_dump'):
            return o.model_dump()
        return str(o)
    serializable_result = json.loads(json.dumps(analysis_result, default=_json_default))

    doc = {
        "user_id": user_id,
        "filename": filename,
        "ats_score": serializable_result.get("ats_score", 0),
        "keyword_match": serializable_result.get("keyword_match", 0),
        "missing_keywords": serializable_result.get("missing_keywords", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "analysis_result": serializable_result,
    }

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=doc)
            response.raise_for_status()
            data = response.json()
            if data and len(data) > 0:
                inserted_id = str(data[0].get("id"))
                logger.info(f"Saved analysis for user {user_id}: {inserted_id}")
                return inserted_id
            logger.warning(
                "Supabase insert returned no rows — check that the 'analyses' "
                "table exists (see supabase/schema.sql) and that SUPABASE_KEY "
                "is the service_role key."
            )
            return None
    except httpx.HTTPStatusError as exc:
        logger.error(
            f"Failed to save analysis to Supabase: {exc.response.status_code} "
            f"{exc.response.text}"
        )
        return None
    except Exception as exc:
        logger.error(f"Failed to save analysis to Supabase: {exc}")
        return None


async def get_user_history(user_id: str) -> List[Dict]:
    # Deliberately NOT caught here — a config error should surface to the
    # route handler as a real error, not look like "no history yet".
    headers = _get_headers()

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"

    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers=headers,
            params={
                "user_id": f"eq.{user_id}",
                "order": "created_at.desc"
            }
        )
        if response.status_code >= 400:
            logger.error(f"SUPABASE DEBUG STATUS: {response.status_code}")
            logger.error(f"SUPABASE DEBUG RESPONSE: {response.text}")
        response.raise_for_status()
        docs = response.json()

        results = []
        for doc in docs:
            results.append({
                "id": str(doc.get("id")),
                "filename": doc.get("filename", "resume"),
                "resume_name": doc.get("filename", "resume"),
                "job_title": "Software Engineer",
                "ats_score": doc.get("ats_score", 0),
                "keyword_match": doc.get("keyword_match", 0),
                "missing_keywords": doc.get("missing_keywords", []),
                "date": doc.get("created_at", ""),
                "created_at": doc.get("created_at", ""),
                "analysis_result": doc.get("analysis_result", {}),
            })
        return results


async def delete_analysis(analysis_id: str, user_id: str) -> bool:
    headers = _get_headers()

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"

    async with httpx.AsyncClient() as client:
        response = await client.delete(
            url,
            headers=headers,
            params={
                "id": f"eq.{analysis_id}",
                "user_id": f"eq.{user_id}"
            }
        )
        response.raise_for_status()
        return True
