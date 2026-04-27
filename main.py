#!/usr/bin/env python3
"""arxiv-digest: fetch, filter, store, and email arxiv papers."""

import argparse
import logging
import sys

from config import Config
from database import Database
from emailer import send_digest
from fetcher import fetch_papers
from filter import filter_papers
from html_writer import generate as generate_html
from scheduler import cleanup_old_papers
from webhook import notify_webhook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


def run(dry_run: bool = False, resend: bool = False):
    cfg = Config.from_env()
    db = Database(cfg.db_path)

    try:
        log.info("Fetching from arxiv (categories=%s, max=%d)…",
                 cfg.arxiv_categories, cfg.max_results)
        papers = fetch_papers(cfg.arxiv_categories, cfg.max_results)
        log.info("Fetched %d paper(s)", len(papers))

        filtered = filter_papers(papers, cfg.keywords)
        log.info("%d paper(s) match keywords", len(filtered))

        new_papers = db.store_new_papers(filtered)
        log.info("%d new (unseen) paper(s)", len(new_papers))

        # --resend sends all filtered papers regardless of whether they're new
        to_send = filtered if resend else new_papers

        if resend:
            log.info("--resend: sending all %d matched paper(s)", len(to_send))

        if to_send:
            overflow = max(0, len(to_send) - cfg.email_max_papers)
            capped = to_send[:cfg.email_max_papers]
            if overflow:
                log.info("Capping email at %d papers (%d more in digest.html)",
                         cfg.email_max_papers, overflow)
            send_digest(capped, cfg, dry_run=dry_run, overflow=overflow)
            if not dry_run:
                db.mark_email_sent([p["arxiv_id"] for p in capped])

            notify_webhook(to_send, cfg, dry_run=dry_run)
            if not dry_run:
                db.mark_webhook_sent([p["arxiv_id"] for p in to_send])
        else:
            log.info("No new papers — use --resend to send anyway")

        cleanup_old_papers(db, cfg.retention_days)

        html_path = generate_html(db.get_recent_papers())
        log.info("digest.html updated (%s)", html_path)

    finally:
        db.close()

    log.info("Done%s", " (dry-run)" if dry_run else "")


def main():
    parser = argparse.ArgumentParser(
        description="Fetch arxiv papers, filter by keyword, email digest."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and filter without sending email or webhook",
    )
    parser.add_argument(
        "--resend",
        action="store_true",
        help="Send digest for all matched papers, not just new ones",
    )
    args = parser.parse_args()

    try:
        run(dry_run=args.dry_run, resend=args.resend)
    except KeyError as e:
        log.error("Missing required env var: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
