import re
from typing import Any, Dict, List


def filter_papers(
    papers: List[Dict[str, Any]], keywords: List[str]
) -> List[Dict[str, Any]]:
    """Keep papers whose title or abstract matches any keyword (regex, case-insensitive)."""
    patterns = [re.compile(re.escape(k.strip()), re.IGNORECASE) for k in keywords if k.strip()]
    if not patterns:
        return papers
    return [p for p in papers if _matches(p, patterns)]


def _matches(paper: Dict[str, Any], patterns: List[re.Pattern]) -> bool:
    text = f"{paper['title']} {paper['abstract']}"
    return any(pat.search(text) for pat in patterns)
