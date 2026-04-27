import xml.etree.ElementTree as ET
from typing import Any, Dict, List
import logging
import requests

log = logging.getLogger(__name__)

_API = "http://export.arxiv.org/api/query"
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
}


def fetch_papers(categories: List[str], max_results: int = 100) -> List[Dict[str, Any]]:
    query = " OR ".join(f"cat:{c.strip()}" for c in categories)
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    log.debug("GET %s params=%s", _API, params)
    resp = requests.get(_API, params=params, timeout=30)
    resp.raise_for_status()
    return _parse(resp.text)


def _parse(xml_text: str) -> List[Dict[str, Any]]:
    root = ET.fromstring(xml_text)
    papers = []
    for entry in root.findall("atom:entry", _NS):
        raw_id = _text(entry, "atom:id")
        arxiv_id = raw_id.split("/abs/")[-1]
        title = " ".join(_text(entry, "atom:title").split())
        abstract = " ".join(_text(entry, "atom:summary").split())
        published = _text(entry, "atom:published")
        url = raw_id  # canonical abs URL
        authors = ", ".join(
            a.find("atom:name", _NS).text
            for a in entry.findall("atom:author", _NS)
            if a.find("atom:name", _NS) is not None
        )
        papers.append(dict(
            arxiv_id=arxiv_id,
            title=title,
            abstract=abstract,
            published=published,
            url=url,
            authors=authors,
        ))
    return papers


def _text(elem, tag: str) -> str:
    child = elem.find(tag, _NS)
    return child.text.strip() if child is not None and child.text else ""
