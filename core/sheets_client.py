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
}


class SheetsClient:
    def __init__(self) -> None:
        self._gc: gspread.Client | None = None
        self._sheet: gspread.Spreadsheet | None = None
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
        return sheet.worksheet(TABS.get(tab, tab))

    def read_tab(self, tab: str) -> list[dict[str, Any]]:
        ws = self._tab(tab)
        records = ws.get_all_records()
        logger.debug(f"Read {len(records)} rows from {tab}")
        return records

    def append_row(self, tab: str, data: dict[str, Any]) -> None:
        ws = self._tab(tab)
        headers = ws.row_values(1)
        row = [str(data.get(h, "")) for h in headers]
        ws.append_row(row, value_input_option="USER_ENTERED")
        logger.debug(f"Appended row to {tab}")

    def update_row(
        self,
        tab: str,
        match_col: str,
        match_val: str,
        updates: dict[str, Any],
    ) -> bool:
        ws = self._tab(tab)
        headers = ws.row_values(1)
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
