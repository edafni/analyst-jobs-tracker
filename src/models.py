from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class JobPosting:
    company: str
    title: str
    url: str
    city: Optional[str]
    source: str
    collected_at_utc: datetime

