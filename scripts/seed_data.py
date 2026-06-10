"""
Seeds LJR.devOS Google Sheets on first launch, then verifies row counts.

Run from repo root:
    python scripts/seed_data.py

Safe to run multiple times — skips import if PROFILE tab already has ≥40 rows.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.import_to_sheets import main as run_import
from core.sheets_client import SheetsClient

EXPECTED = {
    "PROFILE": 44,
    "SKILLS": 45,
    "PROJECTS": 5,
}


def already_seeded(sheets: SheetsClient) -> bool:
    try:
        rows = sheets.read_tab("PROFILE")
        return len(rows) >= 40
    except Exception:
        return False


def verify(sheets: SheetsClient) -> bool:
    print("\nVerification")
    print("-" * 44)
    all_ok = True
    for tab, expected in EXPECTED.items():
        try:
            rows = sheets.read_tab(tab)
            actual = len(rows)
            ok = actual >= expected
            status = "OK" if ok else "WARN"
            check = "[OK]" if ok else "[--]"
            print(f"  {check} {tab} tab: {actual} rows (expected >= {expected})")
            if not ok:
                all_ok = False
        except Exception as e:
            print(f"  [ERR] {tab} tab: {e}")
            all_ok = False
    return all_ok


def main() -> None:
    print("\nLJR.devOS — Seed & Verify")
    print("=" * 44)

    sheets = SheetsClient()

    if already_seeded(sheets):
        print("\n[SKIP] PROFILE tab already has data. Skipping import.")
        print("       (Delete all rows from PROFILE tab to re-seed.)\n")
    else:
        print("\n[RUN] Starting data import...")
        run_import()

    ok = verify(sheets)

    print("\n" + "=" * 44)
    if ok:
        print("READY — All tabs populated. Run start.bat to launch bot.")
    else:
        print("INCOMPLETE — Some tabs may be missing rows.")
        print("Fix: Copy google-credentials.json to repo root, then re-run.")


if __name__ == "__main__":
    main()
