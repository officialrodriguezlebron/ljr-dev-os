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
    for row in rows:
        sheets.append_row("SKILLS", {
            "Skill": row["Skill"],
            "Level": row["Level"],
            "Gap": row["Gap"],
            "Frequency": int(row.get("Frequency", 0) or 0),
            "Priority": row.get("Priority", "No"),
            "Resource": row.get("Resource", ""),
            "Completed": row.get("Completed", "No"),
            "Category": row.get("Category", ""),
            "Notes": row.get("Notes", ""),
        })
    return len(rows)


def import_projects(sheets: SheetsClient, rows: list[dict]) -> int:
    for row in rows:
        sheets.append_row("PROJECTS", {
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
        })
    return len(rows)


def import_profile(sheets: SheetsClient, rows: list[dict]) -> int:
    for row in rows:
        sheets.append_row("PROFILE", {
            "Field": row["Field"],
            "Value": row["Value"],
            "Last Updated": row.get("Last Updated", ""),
            "Category": row.get("Category", ""),
        })
    return len(rows)


def main() -> dict[str, int]:
    print("\nLJR.devOS — Sheets Data Import")
    print("=" * 44)

    sheets = SheetsClient()
    counts: dict[str, int] = {}

    print("\n[1/3] Importing skills_data.csv -> SKILLS tab...")
    skills_rows = load_csv("skills_data.csv")
    n = import_skills(sheets, skills_rows)
    counts["SKILLS"] = n
    print(f"      [OK] {n} skills imported")

    print("\n[2/3] Importing projects_data.csv -> PROJECTS tab...")
    project_rows = load_csv("projects_data.csv")
    n = import_projects(sheets, project_rows)
    counts["PROJECTS"] = n
    print(f"      [OK] {n} projects imported")

    print("\n[3/3] Importing profile_data.csv -> PROFILE tab...")
    profile_rows = load_csv("profile_data.csv")
    n = import_profile(sheets, profile_rows)
    counts["PROFILE"] = n
    print(f"      [OK] {n} profile rows imported")

    print("\n" + "=" * 44)
    print("Import complete.")
    return counts


if __name__ == "__main__":
    main()
