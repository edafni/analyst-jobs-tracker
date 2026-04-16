from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import pandas as pd

from src.collectors.company_pages import collect_company_pages
from src.collectors.jsearch_serp import collect_duckduckgo_serp
from src.collectors.remotive import collect_remotive
from src.filtering import is_relevant_analyst_role
from src.logging_utils import setup_logging
from src.models import JobPosting
from src.scoring import score_job
from src.sheets import get_client, open_tracker_sheet, open_or_create_worksheet, read_existing_links, append_rows
from src.utils import canonicalize_url

logger = logging.getLogger(__name__)


DEFAULT_LOCATION_QUERY = "Tel Aviv Israel"


def collect_all() -> list[JobPosting]:
    jobs: list[JobPosting] = []

    # Company ATS (lever/greenhouse) from config
    jobs.extend(collect_company_pages("config/companies.yaml"))

    # Free API source (may be remote)
    if os.environ.get("ENABLE_REMOTIVE", "1").strip() == "1":
        try:
            jobs.extend(collect_remotive(location_hint="israel", query="analyst"))
        except Exception:
            logger.exception("Remotive collector failed")

    # Optional free SERP discovery (disabled by default; enable explicitly)
    if os.environ.get("ENABLE_DDG", "0").strip() == "1":
        q = os.environ.get("DDG_QUERY", f'("data analyst" OR "product analyst" OR "bi analyst" OR "business analyst") "{DEFAULT_LOCATION_QUERY}"')
        try:
            jobs.extend(collect_duckduckgo_serp(query=q))
        except Exception:
            logger.exception("DuckDuckGo collector failed")

    return jobs


def to_rows(jobs: list[JobPosting]) -> list[list]:
    now_iso = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    rows: list[list] = []
    for j in jobs:
        rows.append(
            [
                j.company,
                j.city or "",
                j.title,
                canonicalize_url(j.url),
                "New",
                now_iso,
                score_job(j.title),
            ]
        )
    return rows


def main() -> int:
    setup_logging(os.environ.get("LOG_LEVEL", "INFO"))

    logger.info("Starting collection")
    collected = collect_all()
    logger.info("Collected total=%d", len(collected))

    # Filter relevant analyst roles
    filtered = [j for j in collected if is_relevant_analyst_role(j.title)]
    logger.info("Filtered relevant=%d", len(filtered))

    # Normalize and dedupe within-run by URL
    df = pd.DataFrame(
        [
            {
                "company": j.company,
                "city": j.city,
                "title": j.title,
                "url": canonicalize_url(j.url),
                "source": j.source,
                "collected_at": j.collected_at_utc,
            }
            for j in filtered
        ]
    )
    if df.empty:
        logger.info("No jobs after filtering")
        return 0

    df = df.dropna(subset=["url"]).drop_duplicates(subset=["url"])
    jobs = [
        JobPosting(
            company=row["company"],
            title=row["title"],
            url=row["url"],
            city=row.get("city"),
            source=row["source"],
            collected_at_utc=row["collected_at"],
        )
        for _, row in df.iterrows()
    ]
    logger.info("Deduped within run=%d", len(jobs))

    # Sheets: open, read existing links, append only new
    client = get_client()
    ss = open_tracker_sheet(client)
    ws = open_or_create_worksheet(ss)
    logger.info("Writing to worksheet title=%s", ws.title)

    existing = read_existing_links(ws)
    logger.info("Existing links in sheet=%d", len(existing))
    existing_canon = {canonicalize_url(u) for u in existing}

    new_jobs = [j for j in jobs if canonicalize_url(j.url) not in existing_canon]
    logger.info("New jobs to append=%d", len(new_jobs))

    rows = to_rows(new_jobs)
    append_rows(ws, rows)
    logger.info("Appended rows=%d", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

