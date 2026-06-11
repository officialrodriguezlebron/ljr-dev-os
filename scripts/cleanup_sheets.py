"""One-time cleanup: fix APPLICATIONS and INCOME tab headers, create WEEKLY PLANNER."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from core.sheets_client import SheetsClient


def clean_tab(wb, tab_name: str, headers: list[str]) -> None:
    try:
        ws = wb.worksheet(tab_name)
        print(f"  Found '{tab_name}', clearing all data...")
    except Exception:
        print(f"  '{tab_name}' not found, creating...")
        ws = wb.add_worksheet(title=tab_name, rows=1000, cols=len(headers) + 2)
    ws.clear()
    ws.append_row(headers, value_input_option="USER_ENTERED")
    print(f"  Done — {len(headers)} headers written, 0 data rows.")


def ensure_tab(wb, tab_name: str, headers: list[str]) -> None:
    try:
        wb.worksheet(tab_name)
        print(f"  '{tab_name}' already exists, skipping.")
    except Exception:
        ws = wb.add_worksheet(title=tab_name, rows=100, cols=len(headers) + 2)
        ws.append_row(headers, value_input_option="USER_ENTERED")
        print(f"  '{tab_name}' created with {len(headers)} headers.")


def main() -> None:
    print("LJR.devOS — Sheet Cleanup")
    print("=" * 40)

    client = SheetsClient()
    wb = client._connect()

    print("\n[1] Cleaning APPLICATIONS tab...")
    clean_tab(wb, "APPLICATIONS", [
        "Date", "Platform", "Employer", "Role", "KYN Score",
        "Status", "Notes", "Follow-up Date", "Replied", "Offer",
    ])

    print("\n[2] Cleaning INCOME tab...")
    clean_tab(wb, "INCOME", [
        "Month", "Client", "Role", "Amount USD", "Status", "Notes",
    ])

    print("\n[3] Ensuring WEEKLY PLANNER tab...")
    ensure_tab(wb, "WEEKLY PLANNER", [
        "Week_Start", "Plan_Text", "Projects_Covered", "Generated_At",
    ])

    client._ws_cache.clear()
    client._header_cache.clear()

    print("\n" + "=" * 40)
    print("Cleanup complete.")
    print("  APPLICATIONS: 10 headers, 0 rows")
    print("  INCOME: 6 headers, 0 rows")
    print("  WEEKLY PLANNER: created or already existed")


if __name__ == "__main__":
    main()
