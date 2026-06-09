import re
from pathlib import Path

from core.models import Profile
from core.sheets_client import SheetsClient

RESUME_PATH = Path("master_resume.md")

SYSTEM_PROMPT = """You are Lebron's personal profile manager.
You maintain an accurate, up-to-date view of who Lebron is,
what he has built, and where he stands in his career journey.
Be concise and factual. Use exact numbers from his proof points."""


class ProfileAgent:
    def __init__(self, sheets: SheetsClient) -> None:
        self.sheets = sheets
        self._resume: str = RESUME_PATH.read_text(encoding="utf-8")

    def get_profile(self) -> Profile:
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
            current_month_income = sum(
                float(r.get("Amount USD", 0)) for r in income_rows
            )
            income_current = f"${current_month_income:.0f}" if current_month_income else "₱0"
        except Exception:
            income_current = "₱0"

        top_skills = self._extract_section("Advanced")[:5]
        proof_points = self._extract_proof_points()[:4]
        projects = self._extract_projects()

        return Profile(
            name="Lebron James DG. Rodriguez",
            school="FEU-IT — BS CS, Dean's List",
            income_current=income_current,
            income_target="$800/month",
            top_skills=top_skills,
            proof_points=proof_points,
            gaps=self._extract_section("Learning")[:3],
            applications_sent=apps_sent,
            response_rate=response_rate,
            active_projects=projects,
        )

    def get_proof_points(self) -> list[str]:
        return self._extract_proof_points()

    def format_telegram(self) -> str:
        return self.get_profile().format_telegram()

    def _extract_section(self, section_name: str) -> list[str]:
        lines = self._resume.split("\n")
        in_section = False
        items: list[str] = []
        for line in lines:
            if f"### {section_name}" in line:
                in_section = True
                continue
            if in_section:
                if line.startswith("###") or line.startswith("##"):
                    break
                stripped = line.strip().lstrip("- ").strip()
                if stripped and not stripped.startswith("#"):
                    # Take only the skill name before the colon
                    skill = stripped.split(":")[0].strip()
                    if skill:
                        items.append(skill)
        return items

    def _extract_proof_points(self) -> list[str]:
        proof_blocks = re.findall(
            r"### (.+?)\n(.*?)(?=###|\Z)", self._resume, re.DOTALL
        )
        points = []
        for title, body in proof_blocks:
            if "proof" in title.lower() or any(
                kw in body.lower() for kw in ["lighthouse", "csat", "viewers", "silhouette"]
            ):
                continue
            lines = [l.strip().lstrip("- ").strip() for l in body.strip().split("\n") if l.strip().startswith("-")]
            if lines:
                points.append(f"{title}: {lines[0]}")
        return points[:6]

    def _extract_projects(self) -> list[str]:
        m = re.search(r"## ACTIVE PROJECTS\n(.*?)(?=\n##|\Z)", self._resume, re.DOTALL)
        if not m:
            return ["RutaSmart", "CareerOS", "LuxeWear", "LJR.devOS"]
        lines = [l.strip().lstrip("- ").split(":")[0].strip() for l in m.group(1).split("\n") if l.strip().startswith("-")]
        return lines or ["RutaSmart", "CareerOS", "LuxeWear", "LJR.devOS"]
