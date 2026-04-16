from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.models import JobPosting
from src.utils import http_get, canonicalize_url

logger = logging.getLogger(__name__)


def collect_lever(org: str, company_name: str) -> list[JobPosting]:
    """
    Lever postings API (public):
    https://api.lever.co/v0/postings/{org}?mode=json
    """
    api_url = f"https://api.lever.co/v0/postings/{org}"
    resp = http_get(api_url, timeout_s=30, headers={"Accept": "application/json"})
    data = resp.json()

    now = datetime.now(timezone.utc)
    out: list[JobPosting] = []
    for job in data or []:
        title = (job.get("text") or "").strip()
        categories = job.get("categories") or {}
        city = None
        if isinstance(categories, dict):
            city = (categories.get("location") or "").strip() or None
        host = (job.get("hostedUrl") or "").strip()
        if not host:
            host = (job.get("applyUrl") or "").strip()
        url = canonicalize_url(host)
        if not title or not url:
            continue
        out.append(
            JobPosting(
                company=company_name,
                title=title,
                url=url,
                city=city,
                source=f"lever:{org}",
                collected_at_utc=now,
            )
        )
    logger.info("lever org=%s collected=%d", org, len(out))
    return out

