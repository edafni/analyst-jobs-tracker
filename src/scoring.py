import re
from typing import Optional


WEIGHTS = {
    # Core strengths from CV
    "sql": 6,
    "python": 6,
    "experiment": 5,  # experiment/experimentation/A-B
    "ab_test": 5,
    "metrics": 4,
    "kpi": 4,
    "instrumentation": 4,
    "tracking": 4,
    "taxonomy": 3,
    "amplitude": 4,
    "looker": 3,
    "tableau": 3,
    "bi": 2,
    "dashboard": 2,
    # Domain alignment
    "fintech": 3,
    "payments": 3,
    "wallet": 2,
    "banking": 2,
    # Light seniority signal
    "senior": 1,
    "lead": 1,
    "principal": 1,
}


def score_job(title: str, text: Optional[str] = None) -> int:
    haystack = " ".join([title or "", text or ""]).lower()

    score = 0
    if re.search(r"\bsql\b", haystack):
        score += WEIGHTS["sql"]
    if re.search(r"\bpython\b", haystack):
        score += WEIGHTS["python"]

    if re.search(r"\b(a/?b|ab)\s*test", haystack) or "a/b" in haystack:
        score += WEIGHTS["ab_test"]
    if re.search(r"\bexperiment", haystack):
        score += WEIGHTS["experiment"]

    if re.search(r"\bmetrics?\b", haystack):
        score += WEIGHTS["metrics"]
    if re.search(r"\bkpi\b|\bkpis\b", haystack):
        score += WEIGHTS["kpi"]

    if re.search(r"\binstrumentation\b", haystack):
        score += WEIGHTS["instrumentation"]
    if re.search(r"\btracking\b", haystack):
        score += WEIGHTS["tracking"]
    if re.search(r"\btaxonomy\b", haystack):
        score += WEIGHTS["taxonomy"]

    if re.search(r"\bamplitude\b", haystack):
        score += WEIGHTS["amplitude"]
    if re.search(r"\blooker\b", haystack):
        score += WEIGHTS["looker"]
    if re.search(r"\btableau\b", haystack):
        score += WEIGHTS["tableau"]
    if re.search(r"\bbi\b|\bbusiness intelligence\b", haystack):
        score += WEIGHTS["bi"]
    if re.search(r"\bdashboards?\b", haystack):
        score += WEIGHTS["dashboard"]

    if re.search(r"\bfintech\b", haystack):
        score += WEIGHTS["fintech"]
    if re.search(r"\bpayments?\b", haystack):
        score += WEIGHTS["payments"]
    if re.search(r"\bwallet\b", haystack):
        score += WEIGHTS["wallet"]
    if re.search(r"\bbanking\b", haystack):
        score += WEIGHTS["banking"]

    if re.search(r"\bsenior\b", haystack):
        score += WEIGHTS["senior"]
    if re.search(r"\blead\b", haystack):
        score += WEIGHTS["lead"]
    if re.search(r"\bprincipal\b", haystack):
        score += WEIGHTS["principal"]

    return int(score)

