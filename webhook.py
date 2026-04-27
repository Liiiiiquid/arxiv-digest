import logging
from typing import Any, Dict, List
import requests

log = logging.getLogger(__name__)


def notify_webhook(papers: List[Dict[str, Any]], cfg, dry_run: bool = False):
    if not cfg.webhook_url:
        log.debug("WEBHOOK_URL not set, skipping")
        return

    payload = {
        "count": len(papers),
        "papers": [
            {"arxiv_id": p["arxiv_id"], "title": p["title"], "url": p["url"]}
            for p in papers
        ],
    }

    if dry_run:
        log.info("[dry-run] Would POST %d paper(s) to %s", len(papers), cfg.webhook_url)
        return

    resp = requests.post(cfg.webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    log.info("Webhook notified (%s): %d paper(s)", cfg.webhook_url, len(papers))
