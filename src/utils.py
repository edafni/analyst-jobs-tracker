from __future__ import annotations

import logging
import re
from typing import Optional, Dict
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


@retry(
    reraise=True,
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((requests.RequestException,)),
)
def http_get(url: str, *, timeout_s: int = 20, headers: Optional[Dict[str, str]] = None) -> requests.Response:
    hdrs: Dict[str, str] = {
        "User-Agent": "Mozilla/5.0 (compatible; AnalystJobsTracker/1.0; +https://example.invalid)",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        **(headers or {}),
    }
    resp = requests.get(url, headers=hdrs, timeout=timeout_s)
    resp.raise_for_status()
    return resp


def canonicalize_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return u

    parsed = urlparse(u)
    # Drop fragments and common tracking query params.
    q = [(k, v) for (k, v) in parse_qsl(parsed.query, keep_blank_values=True)]
    drop_keys_re = re.compile(r"^(utm_|ref|source|fbclid|gclid|yclid|mc_cid|mc_eid)", re.IGNORECASE)
    q2 = [(k, v) for (k, v) in q if not drop_keys_re.search(k)]

    cleaned = parsed._replace(fragment="", query=urlencode(q2, doseq=True))
    return urlunparse(cleaned)


def dedupe_key(company: str, title: str, url: str) -> str:
    if url:
        return canonicalize_url(url)
    return f"{(company or '').strip().lower()}::{(title or '').strip().lower()}"

