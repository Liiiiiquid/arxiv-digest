#!/usr/bin/env python3
"""Local web UI for browsing and starring arxiv-digest papers."""

import csv
import io
import json
import os

from flask import Flask, jsonify, request, Response

from config import Config
from database import Database

app = Flask(__name__)
cfg = Config.from_env()


def _db() -> Database:
    return Database(cfg.db_path)


# ── HTML shell ────────────────────────────────────────────────────────────────

_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>arxiv-digest</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, sans-serif; background: #f5f5f5; color: #222; }}
  header {{ background: #1a1a2e; color: #fff; padding: 1rem 1.5rem;
            display: flex; align-items: center; gap: 1rem; }}
  header h1 {{ font-size: 1.2rem; font-weight: 600; flex: 1; }}
  header a {{ color: #adf; text-decoration: none; font-size: .9rem; }}
  header a:hover {{ text-decoration: underline; }}
  .tabs {{ display: flex; gap: 0; background: #eee; border-bottom: 2px solid #ddd; }}
  .tab {{ padding: .6rem 1.5rem; cursor: pointer; font-size: .9rem;
          border: none; background: none; color: #555; }}
  .tab.active {{ background: #fff; border-bottom: 2px solid #1a1a2e;
                 color: #1a1a2e; font-weight: 600; margin-bottom: -2px; }}
  .list {{ max-width: 860px; margin: 1.5rem auto; padding: 0 1rem; }}
  .card {{ background: #fff; border-radius: 8px; padding: 1.1rem 1.3rem;
           margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.08); }}
  .card-title {{ font-size: 1rem; font-weight: 600; margin-bottom: .3rem; }}
  .card-title a {{ color: #1a0dab; text-decoration: none; }}
  .card-title a:hover {{ text-decoration: underline; }}
  .card-meta {{ font-size: .8rem; color: #777; margin-bottom: .5rem; }}
  .card-abstract {{ font-size: .88rem; line-height: 1.55; color: #444; }}
  .star-btn {{ float: right; background: none; border: none; font-size: 1.3rem;
               cursor: pointer; padding: 0 0 0 .5rem; line-height: 1; }}
  .empty {{ text-align: center; color: #999; padding: 3rem; }}
</style>
</head>
<body>
<header>
  <h1>arxiv-digest</h1>
  <a href="/export/json" download="starred.json">⬇ JSON</a>
  &nbsp;
  <a href="/export/csv" download="starred.csv">⬇ CSV</a>
</header>
<div class="tabs">
  <button class="tab {all_active}" onclick="show('all')">All recent</button>
  <button class="tab {starred_active}" onclick="show('starred')">Starred ★</button>
</div>
<div id="all" class="list" style="display:{all_display}">{all_html}</div>
<div id="starred" class="list" style="display:{starred_display}">{starred_html}</div>
<script>
function show(tab) {{
  document.getElementById('all').style.display = tab==='all' ? '' : 'none';
  document.getElementById('starred').style.display = tab==='starred' ? '' : 'none';
  document.querySelectorAll('.tab').forEach((t,i) =>
    t.classList.toggle('active', (i===0) === (tab==='all')));
}}
async function toggleStar(btn, arxivId) {{
  const res = await fetch('/star/' + arxivId, {{method: 'POST'}});
  const data = await res.json();
  btn.textContent = data.starred ? '★' : '☆';
  btn.title = data.starred ? 'Unstar' : 'Star';
}}
</script>
</body>
</html>"""


def _card(p: dict) -> str:
    star = "★" if p.get("starred") else "☆"
    abstract = (p["abstract"] or "")[:400]
    if len(p["abstract"] or "") > 400:
        abstract += "…"
    return f"""<div class="card">
  <div class="card-title">
    <button class="star-btn" title="{'Unstar' if p.get('starred') else 'Star'}"
            onclick="toggleStar(this,'{p['arxiv_id']}')">{star}</button>
    <a href="{p['url']}" target="_blank">{p['title']}</a>
  </div>
  <div class="card-meta">{p['authors']} &mdash; {(p['published'] or '')[:10]}</div>
  <div class="card-abstract">{abstract}</div>
</div>"""


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
def index():
    tab = request.args.get("tab", "all")
    db = _db()
    all_papers = db.get_recent_papers()
    starred = db.get_starred_papers()
    db.close()

    all_html = "".join(_card(p) for p in all_papers) or '<p class="empty">No papers yet — run main.py first.</p>'
    starred_html = "".join(_card(p) for p in starred) or '<p class="empty">No starred papers yet. Click ☆ on any paper.</p>'

    return _PAGE.format(
        all_active="active" if tab != "starred" else "",
        starred_active="active" if tab == "starred" else "",
        all_display="none" if tab == "starred" else "",
        starred_display="" if tab == "starred" else "none",
        all_html=all_html,
        starred_html=starred_html,
    )


@app.post("/star/<arxiv_id>")
def star(arxiv_id: str):
    db = _db()
    new_state = db.toggle_star(arxiv_id)
    db.close()
    return jsonify(starred=new_state)


@app.get("/export/json")
def export_json():
    db = _db()
    papers = db.get_starred_papers()
    db.close()
    return Response(
        json.dumps(papers, indent=2, ensure_ascii=False),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=starred.json"},
    )


@app.get("/export/csv")
def export_csv():
    db = _db()
    papers = db.get_starred_papers()
    db.close()
    buf = io.StringIO()
    fields = ["arxiv_id", "title", "authors", "published", "url", "abstract"]
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(papers)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=starred.csv"},
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Open http://localhost:{port} in your browser  (Ctrl-C to stop)")
    app.run(debug=False, port=port, use_reloader=False)
