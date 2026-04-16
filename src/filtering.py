import re


ANALYST_TITLE_RE = re.compile(
    r"\b("
    r"data analyst|product analyst|business analyst|bi analyst|"
    r"financial analyst|analytics analyst|marketing analyst|"
    r"risk analyst|fraud analyst|operations analyst"
    r")\b",
    re.IGNORECASE,
)

EXCLUDE_TITLE_RE = re.compile(
    r"\b("
    r"soc analyst|security analyst|cyber|threat|incident response|"
    r"qa analyst|test analyst|support analyst|"
    r"laboratory|lab analyst"
    r")\b",
    re.IGNORECASE,
)


def is_relevant_analyst_role(title: str) -> bool:
    t = (title or "").strip()
    if not t:
        return False
    if EXCLUDE_TITLE_RE.search(t):
        return False
    return bool(ANALYST_TITLE_RE.search(t) or re.search(r"\banalyst\b", t, re.IGNORECASE))

