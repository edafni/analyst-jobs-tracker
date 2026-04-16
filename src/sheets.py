from __future__ import annotations

import json
import logging
import os
from typing import Iterable

import gspread
from google.oauth2.service_account import Credentials
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


SHEET_TITLE = "Analyst Jobs Tracker"
WORKSHEET_TITLE = "Analyst Jobs Tracker"
HEADERS = ["Company", "Job Title", "Link", "Status", "Timestamp", "Score"]


def _get_service_account_json() -> dict:
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise RuntimeError("Missing env var GOOGLE_SERVICE_ACCOUNT_JSON")
    return json.loads(raw)


def get_client() -> gspread.Client:
    info = _get_service_account_json()
    creds = Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    return gspread.authorize(creds)


def open_or_create_tracker_sheet(client: gspread.Client) -> gspread.Spreadsheet:
    try:
        return client.open(SHEET_TITLE)
    except gspread.SpreadsheetNotFound:
        logger.warning("Spreadsheet not found; creating: %s", SHEET_TITLE)
        return client.create(SHEET_TITLE)


def open_or_create_worksheet(spreadsheet: gspread.Spreadsheet) -> gspread.Worksheet:
    try:
        ws = spreadsheet.worksheet(WORKSHEET_TITLE)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(title=WORKSHEET_TITLE, rows=2000, cols=len(HEADERS))
    ensure_headers(ws)
    return ws


def ensure_headers(ws: gspread.Worksheet) -> None:
    first_row = ws.row_values(1)
    if [c.strip() for c in first_row] == HEADERS:
        return
    if first_row:
        logger.warning("Worksheet has unexpected headers; overwriting row 1 with expected headers.")
    ws.update("A1", [HEADERS])


def read_existing_links(ws: gspread.Worksheet) -> set[str]:
    # Find the Link column by header name
    headers = ws.row_values(1)
    if not headers:
        ensure_headers(ws)
        headers = ws.row_values(1)
    try:
        link_idx = headers.index("Link") + 1  # 1-based
    except ValueError:
        ensure_headers(ws)
        headers = ws.row_values(1)
        link_idx = headers.index("Link") + 1

    col_vals = ws.col_values(link_idx)
    # Skip header
    return {v.strip() for v in col_vals[1:] if v and v.strip()}


@retry(reraise=True, stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
def append_rows(ws: gspread.Worksheet, rows: Iterable[list]) -> None:
    rows_list = list(rows)
    if not rows_list:
        return
    ws.append_rows(rows_list, value_input_option="USER_ENTERED")

