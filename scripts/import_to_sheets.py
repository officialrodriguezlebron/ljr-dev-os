"""
Imports CSV data files into LJR.devOS Master Google Sheet.

Files:
  skills_data.csv   -> SKILLS tab
  projects_data.csv -> PROJECTS tab
  profile_data.csv  -> PROFILE tab

Run from repo root:
    python scripts/import_to_sheets.py
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.sheets_client import SheetsClient


def load_csv(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def import_skills(sheets: SheetsClient, rows: list[dict]) -> int:
    batch = [
        {
            "Skill": row["Skill"],
            "Level": row["Level"],
            "Gap": row["Gap"],
            "Frequency": int(row.get("Frequency", 0) or 0),
            "Priority": row.get("Priority", "No"),
            "Resource": row.get("Resource", ""),
            "Completed": row.get("Completed", "No"),
            "Category": row.get("Category", ""),
            "Notes": row.get("Notes", ""),
        }
        for row in rows
    ]
    return sheets.batch_append_rows("SKILLS", batch)


def import_projects(sheets: SheetsClient, rows: list[dict]) -> int:
    batch = [
        {
            "Project": row["Project"],
            "Status": row["Status"],
            "Next Task": row["Next Task"],
            "Deadline": row["Deadline"],
            "Priority": row.get("Priority", ""),
            "GitHub": row.get("GitHub", ""),
            "Blocked By": row.get("Blocked By", ""),
            "Stack": row.get("Stack", ""),
            "Description": row.get("Description", ""),
            "Proof": row.get("Proof", ""),
        }
        for row in rows
    ]
    return sheets.batch_append_rows("PROJECTS", batch)


def import_profile(sheets: SheetsClient, rows: list[dict]) -> int:
    batch = [
        {
            "Field": row["Field"],
            "Value": row["Value"],
            "Last Updated": row.get("Last Updated", ""),
            "Category": row.get("Category", ""),
        }
        for row in rows
    ]
    return sheets.batch_append_rows("PROFILE", batch)


def clear_tab(sheets: SheetsClient, tab: str) -> None:
    """Clear all data from a tab (keeps the sheet, removes all content)."""
    ws = sheets._tab(tab)
    ws.clear()
    sheets._header_cache.pop(tab, None)
    print(f"      [CLEAR] {tab} tab wiped")


def main() -> dict[str, int]:
    print("\nLJR.devOS - Sheets Data Import")
    print("=" * 44)

    sheets = SheetsClient()
    counts: dict[str, int] = {}

    # Clear any existing data first (handles re-runs with stale/empty rows)
    print("\n[0/3] Clearing existing data...")
    for tab in ("SKILLS", "PROJECTS", "PROFILE"):
        clear_tab(sheets, tab)

    print("\n[1/3] Importing skills_data.csv -> SKILLS tab...")
    n = import_skills(sheets, load_csv("skills_data.csv"))
    counts["SKILLS"] = n
    print(f"      [OK] {n} skills imported")

    print("\n[2/3] Importing projects_data.csv -> PROJECTS tab...")
    n = import_projects(sheets, load_csv("projects_data.csv"))
    counts["PROJECTS"] = n
    print(f"      [OK] {n} projects imported")

    print("\n[3/3] Importing profile_data.csv -> PROFILE tab...")
    n = import_profile(sheets, load_csv("profile_data.csv"))
    counts["PROFILE"] = n
    print(f"      [OK] {n} profile rows imported")

    print("\n" + "=" * 44)
    print("Import complete.")
    return counts


if __name__ == "__main__":
    main()
