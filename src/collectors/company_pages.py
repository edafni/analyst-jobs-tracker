from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

import yaml

from src.collectors.greenhouse import collect_greenhouse
from src.collectors.lever import collect_lever
from src.models import JobPosting

logger = logging.getLogger(__name__)


def load_company_config(config_path: Union[str, Path]) -> list[dict]:
    p = Path(config_path)
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return list(data.get("companies", []) or [])


def collect_company_pages(config_path: Union[str, Path]) -> list[JobPosting]:
    companies = load_company_config(config_path)
    out: list[JobPosting] = []

    for c in companies:
        name = (c.get("name") or "").strip()
        ctype = (c.get("type") or "").strip().lower()
        org = (c.get("org") or "").strip()

        if not name or not ctype:
            continue

        try:
            if ctype == "greenhouse" and org:
                out.extend(collect_greenhouse(org=org, company_name=name))
            elif ctype == "lever" and org:
                out.extend(collect_lever(org=org, company_name=name))
            else:
                logger.info("Skipping unsupported company config (type=%s, org=%s): %s", ctype, org, name)
        except Exception:
            logger.exception("Company collector failed: %s", name)

    logger.info("company_pages collected=%d", len(out))
    return out

