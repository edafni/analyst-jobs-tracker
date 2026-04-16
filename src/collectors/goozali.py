from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from src.models import JobPosting
from src.utils import canonicalize_url

logger = logging.getLogger(__name__)


DEFAULT_GOOZALI_AIRTABLE_URL = "https://airtable.com/appwewqLk7iUY4azc/shrQBuWjXd0YgPqV6/tblnk93ouV3B2ce9b"


def _norm(s: str) -> str:
    return (s or "").strip()


def collect_goozali() -> list[JobPosting]:
    """
    Goozali job openings table is hosted as a public Airtable shared view.
    Airtable does not provide a stable, unauthenticated CSV/JSON endpoint, so we use Playwright
    to render the public view and scrape visible rows.

    Env:
      - GOOZALI_AIRTABLE_URL: override the shared view URL
      - GOOZALI_MAX_ROWS: max number of rows to scrape (default 300)
    """
    url = os.environ.get("GOOZALI_AIRTABLE_URL", "").strip() or DEFAULT_GOOZALI_AIRTABLE_URL
    max_rows = int(os.environ.get("GOOZALI_MAX_ROWS", "300").strip() or "300")
    timeout_ms = int(os.environ.get("GOOZALI_TIMEOUT_MS", "180000").strip() or "180000")

    now = datetime.now(timezone.utc)
    out: list[JobPosting] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="Asia/Jerusalem",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        page = context.new_page()

        # Airtable can be slow; retry once with a fresh page.
        for attempt in range(2):
            try:
                page.goto(url, wait_until="load", timeout=timeout_ms)
                content = page.content()
                if "browser version is not supported" in content.lower():
                    logger.warning("goozali airtable blocked (browser not supported) url=%s", url)
                    browser.close()
                    return []

                # Wait for something grid-like to appear
                page.wait_for_selector('[role="grid"], [role="table"], [role="columnheader"]', timeout=timeout_ms)
                break
            except PlaywrightTimeoutError:
                if attempt == 0:
                    logger.warning("goozali playwright timeout (retrying) url=%s", url)
                    page.close()
                    page = context.new_page()
                    continue
                logger.warning("goozali playwright timeout url=%s", url)
                browser.close()
                return []

        # Extract column headers
        headers = page.eval_on_selector_all(
            '[role="columnheader"]',
            "els => els.map(e => (e.textContent || '').trim()).filter(Boolean)",
        )
        headers_norm = [_norm(h).lower() for h in headers]

        def idx_for(keys: list[str]) -> Optional[int]:
            for k in keys:
                for i, h in enumerate(headers_norm):
                    if k in h:
                        return i
            return None

        company_i = idx_for(["company", "employer"])
        title_i = idx_for(["job title", "title", "position", "role"])
        link_i = idx_for(["link", "url", "apply"])
        city_i = idx_for(["location", "city", "region", "area"])

        # Fallback when header extraction fails: assume common order.
        if company_i is None or title_i is None or link_i is None:
            company_i, title_i, link_i = 0, 1, 2

        # Scrape rows (visible in DOM). Airtable virtualizes; we scroll down to load more.
        rows_seen = 0
        last_count = -1
        for _ in range(50):  # scroll attempts
            rows = page.query_selector_all('[role="row"]')
            # Skip header row(s)
            data_rows = []
            for r in rows:
                cells = r.query_selector_all('[role="gridcell"]')
                if not cells:
                    continue
                data_rows.append(cells)

            for cells in data_rows:
                if rows_seen >= max_rows:
                    break
                def cell_text(i: int) -> str:
                    if i < 0 or i >= len(cells):
                        return ""
                    return _norm(cells[i].inner_text())

                company = cell_text(company_i)
                title = cell_text(title_i)

                # Link might be in a cell as <a>
                link = ""
                if 0 <= link_i < len(cells):
                    a = cells[link_i].query_selector("a[href]")
                    if a:
                        link = _norm(a.get_attribute("href") or "")
                    if not link:
                        link = cell_text(link_i)

                city = cell_text(city_i) if city_i is not None else ""

                if not (company and title and link):
                    continue

                out.append(
                    JobPosting(
                        company=company,
                        city=city or None,
                        title=title,
                        url=canonicalize_url(urljoin(url, link)),
                        source="goozali",
                        collected_at_utc=now,
                    )
                )
                rows_seen += 1

            if rows_seen >= max_rows:
                break

            if rows_seen == last_count:
                break
            last_count = rows_seen

            # Scroll the grid to load more rows
            page.mouse.wheel(0, 2000)
            page.wait_for_timeout(500)

        browser.close()

    logger.info("goozali collected=%d", len(out))
    return out

