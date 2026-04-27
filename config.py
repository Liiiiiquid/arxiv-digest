import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # arxiv
    arxiv_categories: List[str]
    keywords: List[str]
    max_results: int

    # email
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    email_from: str
    email_to: List[str]

    # webhook
    webhook_url: str

    # storage
    db_path: str
    retention_days: int

    # email cap
    email_max_papers: int

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            arxiv_categories=os.environ["ARXIV_CATEGORIES"].split(","),
            keywords=os.environ["KEYWORDS"].split(","),
            max_results=int(os.getenv("MAX_RESULTS", "100")),
            smtp_host=os.environ["SMTP_HOST"],
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_user=os.environ["SMTP_USER"],
            smtp_password=os.environ["SMTP_PASSWORD"],
            email_from=os.environ["EMAIL_FROM"],
            email_to=os.environ["EMAIL_TO"].split(","),
            webhook_url=os.getenv("WEBHOOK_URL", ""),
            db_path=os.getenv("DB_PATH", "arxiv_digest.db"),
            retention_days=int(os.getenv("RETENTION_DAYS", "7")),
            email_max_papers=int(os.getenv("EMAIL_MAX_PAPERS", "50")),
        )
