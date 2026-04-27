import logging
from database import Database

log = logging.getLogger(__name__)


def cleanup_old_papers(db: Database, retention_days: int):
    deleted = db.delete_older_than(retention_days)
    if deleted:
        log.info("Cleaned up %d paper(s) older than %d day(s)", deleted, retention_days)
