import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List

log = logging.getLogger(__name__)


def send_digest(papers: List[Dict[str, Any]], cfg, dry_run: bool = False, overflow: int = 0):
    subject = f"[arxiv-digest] {len(papers)} new paper(s)"
    if overflow:
        subject += f" (+{overflow} more)"

    if dry_run:
        log.info("[dry-run] Would send: '%s' → %s", subject, cfg.email_to)
        for p in papers:
            log.info("[dry-run]   %s | %s", p["arxiv_id"], p["title"])
        return

    html = _build_html(papers, overflow)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg.email_from
    msg["To"] = ", ".join(cfg.email_to)
    msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(cfg.smtp_user, cfg.smtp_password)
        smtp.sendmail(cfg.email_from, cfg.email_to, msg.as_string())

    log.info("Email sent to %s (%d papers)", cfg.email_to, len(papers))


def _build_html(papers: List[Dict[str, Any]], overflow: int = 0) -> str:
    items = "\n".join(_item_html(p) for p in papers)
    overflow_note = ""
    if overflow:
        overflow_note = (
            f'<p style="margin-top:1.5em;color:#888;font-size:.9em;">'
            f'<em>+ {overflow} more paper(s) matched but were not included in this email. '
            f'Open <strong>digest.html</strong> locally or run <code>python main.py --resend</code> '
            f'with a higher <code>EMAIL_MAX_PAPERS</code> to see all.</em></p>'
        )
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>arxiv digest</title></head>
<body style="font-family:sans-serif;max-width:760px;margin:auto;padding:1.5em;color:#222;">
  <h2 style="border-bottom:1px solid #ddd;padding-bottom:.5em;">
    arxiv digest &mdash; {len(papers)} new paper(s)
  </h2>
  <ul style="list-style:none;padding:0;">
{items}
  </ul>
{overflow_note}
</body>
</html>"""


def _item_html(p: Dict[str, Any]) -> str:
    abstract = p["abstract"][:400] + ("…" if len(p["abstract"]) > 400 else "")
    return f"""    <li style="margin-bottom:2em;padding-bottom:1em;border-bottom:1px solid #eee;">
      <a href="{p['url']}" style="font-size:1.05em;font-weight:bold;color:#1a0dab;">{p['title']}</a><br>
      <span style="color:#555;font-size:.9em;">{p['authors']}</span><br>
      <span style="color:#888;font-size:.85em;">{p['published'][:10]}</span>
      <p style="margin:.5em 0 0;font-size:.92em;line-height:1.5;">{abstract}</p>
    </li>"""
