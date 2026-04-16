from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from src.models import JobPosting
from src.utils import http_get, canonicalize_url

logger = logging.getLogger(__name__)


_JOB_LIKE_PATH_RE = re.compile(
    r"(/jobs?/|/careers?/|/positions?/|/open(?:ings)?-positions?/|/job-post|/job-openings/|/vacancies/)",
    re.IGNORECASE,
)


def _extract_jobpostings_from_jsonld(doc: Any) -> list[dict]:
    """
    Returns a list of dicts that look like schema.org JobPosting nodes.
    """
    nodes: list[Any] = []
    if isinstance(doc, dict):
        nodes = [doc]
    elif isinstance(doc, list):
        nodes = doc
    else:
        return []

    out: list[dict] = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        ntype = n.get("@type")
        if isinstance(ntype, list):
            types = {str(t).lower() for t in ntype}
        else:
            types = {str(ntype).lower()} if ntype else set()

        if "jobposting" in types:
            out.append(n)
            continue

        graph = n.get("@graph")
        if isinstance(graph, list):
            for g in graph:
                if isinstance(g, dict) and str(g.get("@type", "")).lower() == "jobposting":
                    out.append(g)
    return out


def _jobposting_to_posting(job: dict, *, company_name: str, base_url: str) -> Optional[JobPosting]:
    title = (job.get("title") or job.get("name") or "").strip()
    if not title:
        return None

    url = (job.get("url") or job.get("sameAs") or "").strip()
    if url:
        url = canonicalize_url(urljoin(base_url, url))
    else:
        # some pages only provide an identifier
        identifier = job.get("identifier")
        if isinstance(identifier, dict):
            url = (identifier.get("value") or "").strip()
            if url:
                url = canonicalize_url(urljoin(base_url, url))

    if not url:
        return None

    # Prefer org name from JSON-LD if present
    org = job.get("hiringOrganization")
    company = company_name
    if isinstance(org, dict):
        company = (org.get("name") or company_name).strip() or company_name

    return JobPosting(
        company=company,
        title=title,
        url=url,
        source=f"html:{urlparse(base_url).netloc}",
        collected_at_utc=datetime.now(timezone.utc),
    )


def collect_html_careers(company_name: str, careers_url: str, *, max_links: int = 200) -> list[JobPosting]:
    """
    Best-effort HTML collector:
    1) Parse schema.org JobPosting JSON-LD (most reliable).
    2) Fallback: extract job-like links and use anchor text as title.
    """
    if not careers_url:
        return []

    resp = http_get(careers_url, timeout_s=30)
    soup = BeautifulSoup(resp.text, "html.parser")

    out: list[JobPosting] = []

    # 1) JSON-LD JobPosting extraction
    for script in soup.select('script[type="application/ld+json"]'):
        raw = (script.string or script.get_text() or "").strip()
        if not raw:
            continue
        try:
            doc = json.loads(raw)
        except Exception:
            continue
        for job in _extract_jobpostings_from_jsonld(doc):
            jp = _jobposting_to_posting(job, company_name=company_name, base_url=careers_url)
            if jp:
                out.append(jp)

    # Dedup by URL after JSON-LD
    seen = set()
    deduped: list[JobPosting] = []
    for j in out:
        key = j.url
        if key in seen:
            continue
        seen.add(key)
        deduped.append(j)
    out = deduped

    if out:
        logger.info("html_careers jsonld company=%s collected=%d", company_name, len(out))
        return out

    # 2) Fallback link scraping
    links = soup.select("a[href]")
    candidates: list[tuple[str, str]] = []
    for a in links:
        href = (a.get("href") or "").strip()
        text = (a.get_text(" ", strip=True) or "").strip()
        if not href or not text:
            continue
        if not _JOB_LIKE_PATH_RE.search(href):
            continue
        abs_url = canonicalize_url(urljoin(careers_url, href))
        candidates.append((text, abs_url))
        if len(candidates) >= max_links:
            break

    now = datetime.now(timezone.utc)
    for title, url in candidates:
        out.append(
            JobPosting(
                company=company_name,
                title=title,
                url=url,
                source=f"html_links:{urlparse(careers_url).netloc}",
                collected_at_utc=now,
            )
        )

    # final dedupe by URL
    final: list[JobPosting] = []
    seen2 = set()
    for j in out:
        if j.url in seen2:
            continue
        seen2.add(j.url)
        final.append(j)

    logger.info("html_careers links company=%s collected=%d", company_name, len(final))
    return final

