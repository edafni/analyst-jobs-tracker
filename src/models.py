from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class JobPosting:
    company: str
    title: str
    url: str
    source: str
    collected_at_utc: datetime

