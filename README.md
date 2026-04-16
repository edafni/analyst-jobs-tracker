## Analyst Jobs Tracker (Tel Aviv) — Free, daily Google Sheet updates

Collects new **Analyst** job postings (Data/BI/Product/Business/Financial Analyst) for **Tel Aviv, Israel** from **free sources** (job boards + company career pages), deduplicates them, computes a simple **fit score** (based on your CV), and appends only new rows to a Google Sheet.

### Sources included (free)
- **Company ATS feeds**: Greenhouse + Lever (recommended: stable JSON)
- **Optional**: Remotive free API (remote jobs; can be filtered to Israel)
- **Optional**: DuckDuckGo HTML SERP discovery (disabled by default; best-effort)

### What you get in Google Sheets
Spreadsheet name: **`Analyst Jobs Tracker`**

Columns:
- **Company**
- **Job Title**
- **Link**
- **Status** (default: `New`)
- **Timestamp** (UTC ISO format)
- **Score** (higher = better match)

---

## Setup (one-time)

### 1) Create the Google Sheet
1. Create a Google Sheet named **`Analyst Jobs Tracker`**
2. In row 1, create headers exactly:
   - `Company`, `Job Title`, `Link`, `Status`, `Timestamp`, `Score`

### 2) Create Google credentials (Service Account)
1. Go to Google Cloud Console → create a project
2. Enable **Google Sheets API**
3. Create a **Service Account**
4. Create a **JSON key** and download it
5. Share your Google Sheet with the **service account email** (Editor)

### 3) Local run (optional)
Create a virtualenv and install deps:

```bash
cd "/Users/dafni/AI/analyst-jobs-tracker"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export GOOGLE_SERVICE_ACCOUNT_JSON="$(cat /path/to/service-account.json)"
python -m src.pipeline
```

Notes:
- If you see network/proxy errors locally, that’s environment-specific. GitHub Actions typically works fine.
- To enable optional DuckDuckGo discovery:
  - `export ENABLE_DDG=1`

### 4) GitHub Actions (daily automation)
1. Push this folder to a GitHub repo
2. Repo → Settings → Secrets and variables → Actions → New repository secret
   - Name: `GOOGLE_SERVICE_ACCOUNT_JSON`
   - Value: paste the full JSON key contents
   - Name: `ANALYST_JOBS_SPREADSHEET_ID`
   - Value: the spreadsheet id from your sheet URL (the long string between `/d/` and `/edit`)
3. Actions will run daily and append new jobs.

---

## Configuration

### Companies list
Edit `config/companies.yaml` to add/adjust companies and their careers pages.

Recommended approach: add companies that use **Greenhouse** or **Lever** and provide the `org` identifier.

### Keywords / scoring
Edit `src/scoring.py` to tune weights (SQL/Python/experimentation/product analytics/Amplitude/Looker/Tableau + fintech/payments boost).

