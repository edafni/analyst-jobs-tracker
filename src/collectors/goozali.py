from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse, parse_qs

import pandas as pd

from src.models import JobPosting
from src.utils import http_get, canonicalize_url

logger = logging.getLogger(__name__)


GOOZALI_URLS = [
    "https://en.goozali.com/",
    "https://www.goozali.com/",
    "https://test.goozali.com/",
]


_GOOGLE_SHEETS_RE = re.compile(r"https?://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)", re.IGNORECASE)


def _extract_google_sheet_id(html: str) -> Optional[str]:
    m = _GOOGLE_SHEETS_RE.search(html or "")
    return m.group(1) if m else None


def _google_sheet_csv_url(sheet_id: str) -> str:
    # Public CSV export endpoint
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"


def _guess_col(df: pd.DataFrame, needles: list[str]) -> Optional[str]:
    cols = list(df.columns)
    lowered = {c: str(c).strip().lower() for c in cols}
    for n in needles:
        for c in cols:
            if n in lowered[c]:
                return c
    return None


def collect_goozali() -> list[JobPosting]:
    """
    Best-effort Goozali collector.

    Goozali pages often embed a public table (e.g., Google Sheet). We:
    1) fetch candidate Goozali URLs
    2) detect a Google Sheets id in the HTML
    3) download CSV export and parse rows
    """
    sheet_id = None
    for u in GOOZALI_URLS:
        try:
            resp = http_get(u, timeout_s=30)
        except Exception:
            logger.info("goozali fetch failed url=%s", u)
            continue
        sid = _extract_google_sheet_id(resp.text)
        if sid:
            sheet_id = sid
            logger.info("goozali detected google_sheet_id=%s from url=%s", sid, u)
            break

    if not sheet_id:
        logger.info("goozali no embedded google sheet detected")
        return []

    csv_url = _google_sheet_csv_url(sheet_id)
    resp = http_get(csv_url, timeout_s=30, headers={"Accept": "text/csv"})
    df = pd.read_csv(pd.io.common.BytesIO(resp.content))
    if df.empty:
        return []

    # Heuristic column mapping
    title_col = _guess_col(df, ["title", "position", "role", "job"])
    company_col = _guess_col(df, ["company", "employer"])
    link_col = _guess_col(df, ["link", "url", "apply"])
    city_col = _guess_col(df, ["city", "location", "region", "area"])

    if not (title_col and company_col and link_col):
        logger.warning(
            "goozali csv missing expected columns. cols=%s title=%s company=%s link=%s city=%s",
            list(df.columns),
            title_col,
            company_col,
            link_col,
            city_col,
        )
        return []

    now = datetime.now(timezone.utc)
    out: list[JobPosting] = []
    for _, row in df.iterrows():
        title = str(row.get(title_col, "")).strip()
        company = str(row.get(company_col, "")).strip()
        link = str(row.get(link_col, "")).strip()
        if not title or not company or not link:
            continue
        if link.lower() in {"nan", "none"}:
            continue
        city = None
        if city_col:
            v = row.get(city_col)
            if v is not None and str(v).strip().lower() not in {"nan", "none"}:
                city = str(v).strip() or None

        out.append(
            JobPosting(
                company=company,
                city=city,
                title=title,
                url=canonicalize_url(link),
                source="goozali",
                collected_at_utc=now,
            )
        )

    logger.info("goozali collected=%d", len(out))
    return out

