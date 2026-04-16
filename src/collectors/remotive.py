from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from src.models import JobPosting
from src.utils import canonicalize_url

logger = logging.getLogger(__name__)


def collect_remotive(*, location_hint: str = "israel", query: str = "analyst") -> list[JobPosting]:
    """
    Remotive provides a free JSON API (remote jobs). We include it because it can yield Israel-related roles,
    but it may be remote-only. You can disable it later if you want strict Tel Aviv only.
    """
    url = "https://remotive.com/api/remote-jobs"
    params = {"search": query}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    now = datetime.now(timezone.utc)
    out: list[JobPosting] = []
    for job in data.get("jobs", []) or []:
        title = (job.get("title") or "").strip()
        company = (job.get("company_name") or "").strip()
        job_url = canonicalize_url(job.get("url") or "")
        candidate_loc = (job.get("candidate_required_location") or "").lower()

        if location_hint and location_hint.lower() not in candidate_loc:
            continue

        if title and company and job_url:
            out.append(
                JobPosting(
                    company=company,
                    title=title,
                    url=job_url,
                    source="remotive",
                    collected_at_utc=now,
                )
            )
    logger.info("remotive collected=%d", len(out))
    return out

