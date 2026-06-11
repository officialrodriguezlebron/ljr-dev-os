import core.resume_parser as parser
from core.models import Profile
from core.sheets_client import SheetsClient


class ProfileAgent:
    def __init__(self, sheets: SheetsClient) -> None:
        self.sheets = sheets

    def get_profile(self) -> Profile:
        identity = parser.get_identity()
        proof_raw = parser.get_proof_points()
        skills = parser.get_skills()
        projects = parser.get_projects()
        gaps = parser.get_gaps()

        try:
            apps = self.sheets.read_tab("APPLICATIONS")
            sent = len(apps)
            replied = sum(1 for r in apps if str(r.get("Replied", "")).lower() == "yes")
            response_rate = replied / sent if sent > 0 else 0.0
            apps_sent = sent
        except Exception:
            apps_sent = 0
            response_rate = 0.0

        try:
            income_rows = self.sheets.find_rows("INCOME", {"Status": "paid"})
            total = 0.0
            for r in income_rows:
                try:
                    total += float(str(r.get("Amount USD", "0")).replace(",", "").strip() or "0")
                except (ValueError, TypeError):
                    pass
            income_current = f"${total:.0f}" if total else "₱0"
        except Exception:
            income_current = "₱0"

        goals = parser.get_goals()
        school_raw = identity.get("School", "FEU-IT — BS CS")
        income_target = goals.get("Monthly Target", "$800/month")

        top_skills = [
            f"{name} ({level})"
            for name, level in skills.items()
            if level == "Advanced"
        ][:5]

        proof_points = [
            f"{p['title'].split('—')[0].strip()}: {p['result']}"
            for p in proof_raw
        ][:4]

        return Profile(
            name=identity.get("Full Name", "Lebron James DG. Rodriguez"),
            school=school_raw,
            income_current=income_current,
            income_target=income_target,
            top_skills=top_skills,
            proof_points=proof_points,
            gaps=[g["name"] for g in gaps[:3]],
            applications_sent=apps_sent,
            response_rate=response_rate,
            active_projects=[p["name"] for p in projects],
        )

    def get_proof_points(self) -> list[str]:
        return [
            f"{p['title'].split('—')[0].strip()}: {p['result']}"
            for p in parser.get_proof_points()
        ]

    def format_telegram(self) -> str:
        return self.get_profile().format_telegram()
