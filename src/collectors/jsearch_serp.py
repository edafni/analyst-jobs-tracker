from __future__ import annotations

import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from src.models import JobPosting
from src.utils import http_get, canonicalize_url

logger = logging.getLogger(__name__)


def collect_duckduckgo_serp(*, query: str) -> list[JobPosting]:
    """
    Free SERP fallback using DuckDuckGo HTML results. This is best-effort:
    - No guarantees on stability
    - Might get blocked if you run it too aggressively

    We use it to discover job posting URLs across multiple domains without a paid API.
    Then we do a shallow parse to try to extract title/company from the result title.
    """
    params = {"q": query, "t": "h_", "ia": "web"}
    url = f"https://duckduckgo.com/html/?{urlencode(params)}"
    resp = http_get(url, timeout_s=30)
    soup = BeautifulSoup(resp.text, "html.parser")

    now = datetime.now(timezone.utc)
    out: list[JobPosting] = []
    for a in soup.select("a.result__a"):
        href = a.get("href") or ""
        title_text = (a.get_text(" ", strip=True) or "").strip()
        if not href or not title_text:
            continue

        # DuckDuckGo HTML sometimes returns a redirect URL; keep as-is but canonicalize.
        job_url = canonicalize_url(href)

        # Very rough parsing: split "Title - Company" patterns.
        company = "Unknown"
        job_title = title_text
        if " - " in title_text:
            parts = [p.strip() for p in title_text.split(" - ") if p.strip()]
            if len(parts) >= 2:
                job_title = parts[0]
                company = parts[1]

        out.append(
            JobPosting(
                company=company,
                title=job_title,
                url=job_url,
                source="duckduckgo",
                collected_at_utc=now,
            )
        )

    logger.info("duckduckgo collected=%d", len(out))
    return out

