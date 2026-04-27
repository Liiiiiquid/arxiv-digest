# arxiv-digest

Fetches recent papers from the arxiv API, filters them by keyword, stores results
in a local SQLite database, and sends an HTML digest by email.
Also generates a browsable `digest.html` you can open directly in your browser.

## Project layout

```
arxiv-digest/
├── main.py          # entry point (fetch → filter → email → webhook)
├── serve.py         # local web UI for starring / exporting papers
├── config.py        # reads all settings from environment variables
├── fetcher.py       # arxiv Atom API → list of papers
├── filter.py        # keyword filtering
├── database.py      # SQLite: store, deduplicate, star, clean up
├── emailer.py       # HTML digest builder + SMTP sender
├── webhook.py       # optional webhook notification
├── html_writer.py   # generates digest.html after each run
├── scheduler.py     # weekly cleanup helper
├── requirements.txt
├── .env.example     # copy to .env and fill in your secrets
└── README.md
```

## Quick start

### 1. Create a virtual environment

```bash
cd arxiv-digest
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure your settings

```bash
cp .env.example .env
```

Open `.env` and fill in the values (see the sections below for details).

### 3. Dry-run — fetch and filter without sending email

```bash
python main.py --dry-run
```

You should see something like:

```
2026-04-27 08:00:00 INFO     Fetching from arxiv …
2026-04-27 08:00:02 INFO     Fetched 100 paper(s)
2026-04-27 08:00:02 INFO     12 paper(s) match keywords
2026-04-27 08:00:02 INFO     12 new (unseen) paper(s)
2026-04-27 08:00:02 INFO     [dry-run] Would send: '[arxiv-digest] 12 new paper(s)' → ['you@example.com']
2026-04-27 08:00:02 INFO     digest.html updated
2026-04-27 08:00:02 INFO     Done (dry-run)
```

### 4. Real run

```bash
python main.py
```

A `digest.html` file is also created in the project folder after every run —
open it in any browser, no server needed.

### 5. Schedule with cron (daily at 08:00)

```bash
crontab -e
```

Add this line (replace the path):

```
0 8 * * * cd /path/to/arxiv-digest && .venv/bin/python main.py >> digest.log 2>&1
```

---

## Choosing your arxiv categories

Set `ARXIV_CATEGORIES` to a comma-separated list of category codes.
Browse the full list at <https://arxiv.org/category_taxonomy>.

Common examples:

| Field | Category code |
|---|---|
| Condensed matter — mesoscale | `cond-mat.mes-hall` |
| Condensed matter — quantum gases | `cond-mat.quant-gas` |
| Optics / photonics | `physics.optics` |
| Quantum physics | `quant-ph` |
| High energy physics — theory | `hep-th` |
| Machine learning | `cs.LG` |
| Computer vision | `cs.CV` |

Multiple categories:

```
ARXIV_CATEGORIES=cond-mat.mes-hall,cond-mat.quant-gas,physics.optics
```

## Choosing your keywords

Set `KEYWORDS` to a comma-separated list of plain-text terms.
A paper matches if **any** keyword appears in its title or abstract
(case-insensitive).

```
KEYWORDS=topological,polariton,photonic crystal,Bose-Einstein condensate
```

Tips:
- Use multi-word phrases: `photonic crystal` matches the exact phrase.
- Broad terms (`topological`) catch more; narrow terms (`Chern insulator`) are more precise.
- Start broad with `--dry-run`, then tighten the list until the daily volume feels right.

## All configuration variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ARXIV_CATEGORIES` | yes | — | Comma-separated arxiv category codes |
| `KEYWORDS` | yes | — | Comma-separated filter terms |
| `MAX_RESULTS` | no | `100` | Max papers fetched per run (arxiv API limit: 2000) |
| `EMAIL_MAX_PAPERS` | no | `50` | Max papers in a single email; extras noted at the bottom |
| `SMTP_HOST` | yes | — | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | no | `587` | STARTTLS port |
| `SMTP_USER` | yes | — | Your email login |
| `SMTP_PASSWORD` | yes | — | **App Password**, not your account password |
| `EMAIL_FROM` | yes | — | Sender address |
| `EMAIL_TO` | yes | — | Comma-separated recipient addresses |
| `WEBHOOK_URL` | no | `` | POST new papers here (Slack, n8n, etc.) — leave blank to skip |
| `DB_PATH` | no | `arxiv_digest.db` | SQLite file path |
| `RETENTION_DAYS` | no | `7` | Delete papers older than this many days |

**Gmail users:** create an App Password at <https://myaccount.google.com/apppasswords>
(requires 2-Step Verification enabled). Use the 16-character code as `SMTP_PASSWORD`.

---

## CLI options

```
python main.py              # normal run — email new papers only
python main.py --dry-run    # fetch and filter, print results, send nothing
python main.py --resend     # re-send all matched papers, not just new ones
```

## Local web UI

```bash
python serve.py
# then open http://localhost:8080
```

- **All recent** tab — browse papers, click ☆ to star
- **Starred ★** tab — view your starred papers
- **⬇ JSON / ⬇ CSV** — export starred papers

## digest.html (no server needed)

Every `main.py` run regenerates `digest.html` in the project folder.
Open it in any browser:

- Search by title or author
- Star papers (saved in browser localStorage)
- Export starred list as JSON

---

## How it works

1. **Fetch** — queries the arxiv Atom API sorted by submission date.
2. **Filter** — keeps papers matching at least one keyword in title or abstract.
3. **Deduplicate** — already-seen `arxiv_id`s are skipped; only new papers are emailed.
4. **Email** — sends an HTML digest capped at `EMAIL_MAX_PAPERS`; overflow is noted in the email footer.
5. **Webhook** — optional JSON POST to notify an external service.
6. **Cleanup** — deletes rows older than `RETENTION_DAYS` on every run.
7. **digest.html** — regenerated from the full DB after each run.
