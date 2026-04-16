from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.models import JobPosting
from src.utils import http_get, canonicalize_url

logger = logging.getLogger(__name__)


def collect_greenhouse(org: str, company_name: str) -> list[JobPosting]:
    """
    Greenhouse job board JSON endpoint (public):
    https://boards-api.greenhouse.io/v1/boards/{org}/jobs
    """
    api_url = f"https://boards-api.greenhouse.io/v1/boards/{org}/jobs"
    resp = http_get(api_url, timeout_s=30, headers={"Accept": "application/json"})
    data = resp.json()

    now = datetime.now(timezone.utc)
    out: list[JobPosting] = []
    for job in data.get("jobs", []) or []:
        title = (job.get("title") or "").strip()
        abs_url = canonicalize_url(job.get("absolute_url") or "")
        if not title or not abs_url:
            continue
        out.append(
            JobPosting(
                company=company_name,
                title=title,
                url=abs_url,
                source=f"greenhouse:{org}",
                collected_at_utc=now,
            )
        )
    logger.info("greenhouse org=%s collected=%d", org, len(out))
    return out

