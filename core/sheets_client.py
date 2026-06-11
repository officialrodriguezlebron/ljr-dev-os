import logging
import os
from typing import Any

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()
logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

TABS = {
    "PROFILE": "PROFILE",
    "SKILLS": "SKILLS",
    "PROJECTS": "PROJECTS",
    "APPLICATIONS": "APPLICATIONS",
    "LEARNING": "LEARNING LOG",
    "INCOME": "INCOME",
    "DAILY": "DAILY LOG",
    "WEEKLY PLANNER": "WEEKLY PLANNER",
    "IDEAS": "IDEAS",
}


class SheetsClient:
    def __init__(self) -> None:
        self._gc: gspread.Client | None = None
        self._sheet: gspread.Spreadsheet | None = None
        self._ws_cache: dict[str, gspread.Worksheet] = {}
        self._header_cache: dict[str, list[str]] = {}
        self.sheets_id = os.getenv("LJROS_SHEETS_ID", "")
        self.creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "google-credentials.json")

    def _connect(self) -> gspread.Spreadsheet:
        if self._sheet is None:
            creds = Credentials.from_service_account_file(self.creds_path, scopes=SCOPES)
            self._gc = gspread.authorize(creds)
            self._sheet = self._gc.open_by_key(self.sheets_id)
        return self._sheet

    def _tab(self, tab: str) -> gspread.Worksheet:
        sheet = self._connect()
        tab_name = TABS.get(tab, tab)
        if tab_name in self._ws_cache:
            return self._ws_cache[tab_name]
        all_ws = sheet.worksheets()
        logger.debug(f"[sheets] Looking for '{tab_name}' in {[ws.title for ws in all_ws]}")
        for ws in all_ws:
            if ws.title.lower() == tab_name.lower():
                self._ws_cache[tab_name] = ws
                return ws
        logger.info(f"[sheets] Creating missing tab: {tab_name}")
        new_ws = sheet.add_worksheet(title=tab_name, rows=1000, cols=20)
        self._ws_cache[tab_name] = new_ws
        return new_ws

    def _headers(self, tab: str) -> list[str]:
        if tab not in self._header_cache:
            ws = self._tab(tab)
            self._header_cache[tab] = ws.row_values(1)
        return self._header_cache[tab]

    def read_tab(self, tab: str) -> list[dict[str, Any]]:
        ws = self._tab(tab)
        records = ws.get_all_records()
        logger.debug(f"Read {len(records)} rows from {tab}")
        return records

    def append_row(self, tab: str, data: dict[str, Any]) -> None:
        ws = self._tab(tab)
        headers = self._headers(tab)
        row = [str(data.get(h, "")) for h in headers]
        ws.append_row(row, value_input_option="USER_ENTERED")
        logger.debug(f"Appended row to {tab}")

    def batch_append_rows(self, tab: str, rows_data: list[dict[str, Any]]) -> int:
        """Append multiple rows in a single API call. Use this for bulk imports."""
        if not rows_data:
            return 0
        ws = self._tab(tab)
        headers = self._headers(tab)
        if not headers:
            # Tab is empty — write the header row first
            headers = list(rows_data[0].keys())
            ws.append_row(headers, value_input_option="USER_ENTERED")
            self._header_cache[tab] = headers
            logger.info(f"[sheets] Wrote headers to empty tab '{tab}': {headers}")
        rows = [[str(r.get(h, "")) for h in headers] for r in rows_data]
        ws.append_rows(rows, value_input_option="USER_ENTERED")
        logger.debug(f"Batch appended {len(rows)} rows to {tab}")
        return len(rows)

    def update_row(
        self,
        tab: str,
        match_col: str,
        match_val: str,
        updates: dict[str, Any],
    ) -> bool:
        ws = self._tab(tab)
        headers = self._headers(tab)
        if match_col not in headers:
            logger.error(f"Column '{match_col}' not in {tab}")
            return False

        col_idx = headers.index(match_col) + 1
        col_values = ws.col_values(col_idx)

        for i, val in enumerate(col_values[1:], start=2):
            if str(val).strip() == str(match_val).strip():
                for col_name, new_val in updates.items():
                    if col_name in headers:
                        col_pos = headers.index(col_name) + 1
                        ws.update_cell(i, col_pos, str(new_val))
                logger.debug(f"Updated row in {tab} where {match_col}={match_val}")
                return True

        logger.warning(f"No row found in {tab} where {match_col}={match_val}")
        return False

    def find_rows(self, tab: str, filters: dict[str, Any]) -> list[dict[str, Any]]:
        rows = self.read_tab(tab)
        result = []
        for row in rows:
            if all(str(row.get(k, "")).lower() == str(v).lower() for k, v in filters.items()):
                result.append(row)
        return result

    def get_cell(self, tab: str, row: int, col: str) -> str:
        ws = self._tab(tab)
        headers = ws.row_values(1)
        if col not in headers:
            return ""
        col_idx = headers.index(col) + 1
        return ws.cell(row, col_idx).value or ""

    def get_summary(self, tab: str) -> dict[str, int]:
        rows = self.read_tab(tab)
        return {"total": len(rows)}
