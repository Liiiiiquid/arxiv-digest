import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List
import logging

log = logging.getLogger(__name__)

_CREATE = """
CREATE TABLE IF NOT EXISTS papers (
    arxiv_id     TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    authors      TEXT NOT NULL,
    abstract     TEXT,
    url          TEXT,
    published    TEXT,
    fetched_at   TEXT NOT NULL,
    email_sent   INTEGER DEFAULT 0,
    webhook_sent INTEGER DEFAULT 0,
    starred      INTEGER DEFAULT 0
)
"""


class Database:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(_CREATE)
        # migrate existing databases that predate the starred column
        try:
            self.conn.execute("ALTER TABLE papers ADD COLUMN starred INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        self.conn.commit()

    def store_new_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        new = []
        now = datetime.utcnow().isoformat()
        for p in papers:
            try:
                self.conn.execute(
                    """INSERT INTO papers
                       (arxiv_id, title, authors, abstract, url, published, fetched_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (p["arxiv_id"], p["title"], p["authors"],
                     p["abstract"], p["url"], p["published"], now),
                )
                new.append(p)
            except sqlite3.IntegrityError:
                pass  # already seen
        self.conn.commit()
        return new

    def mark_email_sent(self, arxiv_ids: List[str]):
        self.conn.executemany(
            "UPDATE papers SET email_sent = 1 WHERE arxiv_id = ?",
            [(aid,) for aid in arxiv_ids],
        )
        self.conn.commit()

    def mark_webhook_sent(self, arxiv_ids: List[str]):
        self.conn.executemany(
            "UPDATE papers SET webhook_sent = 1 WHERE arxiv_id = ?",
            [(aid,) for aid in arxiv_ids],
        )
        self.conn.commit()

    def get_recent_papers(self, limit: int = 200) -> List[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM papers ORDER BY fetched_at DESC LIMIT ?", (limit,)
        )
        return [dict(row) for row in cur.fetchall()]

    def toggle_star(self, arxiv_id: str) -> bool:
        """Flip starred flag; return the new state."""
        cur = self.conn.execute(
            "SELECT starred FROM papers WHERE arxiv_id = ?", (arxiv_id,)
        )
        row = cur.fetchone()
        if row is None:
            return False
        new_val = 0 if row["starred"] else 1
        self.conn.execute(
            "UPDATE papers SET starred = ? WHERE arxiv_id = ?", (new_val, arxiv_id)
        )
        self.conn.commit()
        return bool(new_val)

    def get_starred_papers(self) -> List[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT * FROM papers WHERE starred = 1 ORDER BY published DESC"
        )
        return [dict(row) for row in cur.fetchall()]

    def delete_older_than(self, days: int) -> int:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        cur = self.conn.execute(
            "DELETE FROM papers WHERE fetched_at < ?", (cutoff,)
        )
        self.conn.commit()
        return cur.rowcount

    def close(self):
        self.conn.close()
