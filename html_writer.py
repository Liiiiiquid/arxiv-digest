"""Generate a self-contained digest.html from recent DB papers."""

import json
from typing import Any, Dict, List

_TEMPLATE = """<!DOCTYPE html>
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
  header span {{ font-size: .8rem; color: #aaa; }}
  .toolbar {{ display: flex; gap: .5rem; align-items: center;
              padding: .7rem 1.5rem; background: #fff; border-bottom: 1px solid #ddd; }}
  .toolbar button {{ padding: .4rem .9rem; border: 1px solid #ccc; border-radius: 4px;
                     cursor: pointer; font-size: .85rem; background: #fff; }}
  .toolbar button:hover {{ background: #f0f0f0; }}
  .toolbar input {{ padding: .4rem .7rem; border: 1px solid #ccc; border-radius: 4px;
                    font-size: .85rem; width: 220px; }}
  .tab-label {{ font-size: .85rem; color: #555; margin-left: auto; }}
  .list {{ max-width: 860px; margin: 1.2rem auto; padding: 0 1rem; }}
  .card {{ background: #fff; border-radius: 8px; padding: 1.1rem 1.3rem;
           margin-bottom: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,.08);
           display: flex; gap: .8rem; }}
  .card.hidden {{ display: none; }}
  .star-btn {{ background: none; border: none; font-size: 1.4rem;
               cursor: pointer; flex-shrink: 0; padding-top: .1rem; line-height: 1; }}
  .card-body {{ flex: 1; min-width: 0; }}
  .card-title {{ font-size: .98rem; font-weight: 600; margin-bottom: .25rem; }}
  .card-title a {{ color: #1a0dab; text-decoration: none; }}
  .card-title a:hover {{ text-decoration: underline; }}
  .card-meta {{ font-size: .78rem; color: #888; margin-bottom: .4rem; }}
  .card-abstract {{ font-size: .87rem; line-height: 1.55; color: #444; }}
  .empty {{ text-align: center; color: #aaa; padding: 3rem; }}
  #exportBtn {{ margin-left: auto; }}
</style>
</head>
<body>
<header>
  <h1>arxiv-digest</h1>
  <span>Generated {generated}</span>
</header>
<div class="toolbar">
  <button onclick="setView('all')">All ({total})</button>
  <button onclick="setView('starred')">Starred ★</button>
  <input type="search" id="search" placeholder="Search title / author…" oninput="applyFilters()">
  <button id="exportBtn" onclick="exportStarred()">⬇ Export starred (JSON)</button>
</div>
<div id="list" class="list"></div>

<script>
const PAPERS = {papers_json};
const LS_KEY = 'arxiv_digest_starred';

function loadStarred() {{
  try {{ return new Set(JSON.parse(localStorage.getItem(LS_KEY) || '[]')); }}
  catch {{ return new Set(); }}
}}
function saveStarred(s) {{
  localStorage.setItem(LS_KEY, JSON.stringify([...s]));
}}

let starred = loadStarred();
// Seed from DB-starred state on first visit to this digest version
PAPERS.forEach(p => {{ if (p.db_starred) starred.add(p.arxiv_id); }});
saveStarred(starred);

let currentView = 'all';
let currentSearch = '';

function setView(v) {{ currentView = v; applyFilters(); }}

function applyFilters() {{
  currentSearch = document.getElementById('search').value.toLowerCase();
  const list = document.getElementById('list');
  list.innerHTML = '';
  const visible = PAPERS.filter(p => {{
    const matchView = currentView === 'all' || starred.has(p.arxiv_id);
    const matchSearch = !currentSearch ||
      p.title.toLowerCase().includes(currentSearch) ||
      p.authors.toLowerCase().includes(currentSearch);
    return matchView && matchSearch;
  }});
  if (!visible.length) {{
    list.innerHTML = '<p class="empty">No papers found.</p>';
    return;
  }}
  visible.forEach(p => list.appendChild(makeCard(p)));
}}

function makeCard(p) {{
  const isStarred = starred.has(p.arxiv_id);
  const abstract = p.abstract.length > 400 ? p.abstract.slice(0,400) + '…' : p.abstract;
  const div = document.createElement('div');
  div.className = 'card';
  div.dataset.id = p.arxiv_id;
  div.innerHTML = `
    <button class="star-btn" title="${{isStarred ? 'Unstar':'Star'}}"
            onclick="toggleStar('${{p.arxiv_id}}',this)">${{isStarred ? '★':'☆'}}</button>
    <div class="card-body">
      <div class="card-title"><a href="${{p.url}}" target="_blank">${{p.title}}</a></div>
      <div class="card-meta">${{p.authors}} &mdash; ${{p.published.slice(0,10)}}</div>
      <div class="card-abstract">${{abstract}}</div>
    </div>`;
  return div;
}}

function toggleStar(id, btn) {{
  if (starred.has(id)) {{ starred.delete(id); btn.textContent = '☆'; btn.title = 'Star'; }}
  else {{ starred.add(id); btn.textContent = '★'; btn.title = 'Unstar'; }}
  saveStarred(starred);
  if (currentView === 'starred') applyFilters();
}}

function exportStarred() {{
  const data = PAPERS.filter(p => starred.has(p.arxiv_id));
  const blob = new Blob([JSON.stringify(data, null, 2)], {{type:'application/json'}});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = 'starred.json'; a.click();
}}

applyFilters();
</script>
</body>
</html>"""


def generate(papers: List[Dict[str, Any]], output_path: str = "digest.html"):
    from datetime import datetime

    # rename db column so JS can read it unambiguously
    js_papers = [
        {**p, "db_starred": bool(p.get("starred", 0))}
        for p in papers
    ]
    papers_json = json.dumps(js_papers, ensure_ascii=False)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = _TEMPLATE.format(
        generated=generated,
        total=len(papers),
        papers_json=papers_json,
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path
