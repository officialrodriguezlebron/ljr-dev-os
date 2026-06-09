from core.groq_client import GroqClient
from core.models import SkillGap
from core.sheets_client import SheetsClient

SYSTEM_PROMPT = """You are Lebron's skills strategist.
You track which skills appear in job markets and recommend
learning priorities based on market demand vs current skill gaps.
Be specific — give real resources (YouTube channels, courses, docs).
Lebron learns by doing. Every resource must lead to a portfolio piece."""


class SkillsAgent:
    def __init__(self, sheets: SheetsClient, groq: GroqClient) -> None:
        self.sheets = sheets
        self.groq = groq

    def get_skills(self) -> list[dict]:
        try:
            return self.sheets.read_tab("SKILLS")
        except Exception:
            return []

    def get_gaps(self) -> list[SkillGap]:
        try:
            rows = self.sheets.read_tab("SKILLS")
        except Exception:
            return self._default_gaps()

        gaps = []
        for row in rows:
            gap_val = str(row.get("Gap", "")).lower()
            if gap_val in ("yes", "true", "1"):
                gaps.append(
                    SkillGap(
                        name=str(row.get("Skill", "")),
                        frequency=int(row.get("Frequency", 0) or 0),
                        priority=str(row.get("Priority", "")).lower() == "yes",
                        resource=str(row.get("Resource", "TBD")),
                        current_level=str(row.get("Level", "none")),
                    )
                )
        gaps.sort(key=lambda g: (-g.frequency, not g.priority))
        return gaps or self._default_gaps()

    def update_skill_frequency(self, skills: list[str]) -> None:
        try:
            rows = self.sheets.read_tab("SKILLS")
            existing = {str(r.get("Skill", "")).lower(): r for r in rows}

            for skill in skills:
                key = skill.lower()
                if key in existing:
                    freq = int(existing[key].get("Frequency", 0) or 0) + 1
                    self.sheets.update_row(
                        "SKILLS", "Skill", existing[key]["Skill"], {"Frequency": freq}
                    )
                else:
                    self.sheets.append_row(
                        "SKILLS",
                        {
                            "Skill": skill,
                            "Level": "none",
                            "Gap": "Yes",
                            "Frequency": 1,
                            "Priority": "No",
                            "Resource": "",
                            "Completed": "No",
                        },
                    )
        except Exception as e:
            raise RuntimeError(f"Failed to update skill frequency: {e}") from e

    def format_gaps_telegram(self) -> str:
        gaps = self.get_gaps()
        if not gaps:
            return "No skill gaps found in Sheets. Add some via /track."
        lines = [f"📊 *Top Skill Gaps* ({len(gaps)} total)\n"]
        for gap in gaps[:6]:
            lines.append(gap.format_telegram())
        return "\n".join(lines)

    def format_skills_telegram(self) -> str:
        rows = self.get_skills()
        if not rows:
            return "Skills sheet empty. Import from master_resume.md first."
        strong = [r for r in rows if str(r.get("Level", "")).lower() in ("advanced", "intermediate")]
        learning = [r for r in rows if str(r.get("Level", "")).lower() in ("beginner", "learning", "none")]
        lines = [f"⚡ *Skills ({len(rows)} tracked)*\n"]
        lines.append(f"*Strong ({len(strong)}):* " + " · ".join(str(r["Skill"]) for r in strong[:6]))
        lines.append(f"*Learning ({len(learning)}):* " + " · ".join(str(r["Skill"]) for r in learning[:5]))
        return "\n".join(lines)

    def _default_gaps(self) -> list[SkillGap]:
        return [
            SkillGap("Meta Ads", 12, True, "Meta Blueprint free course", "beginner"),
            SkillGap("GoHighLevel", 8, True, "GHL YouTube — Official Channel", "none"),
            SkillGap("Klaviyo", 6, False, "Klaviyo Academy (free)", "none"),
            SkillGap("Google Ads", 5, False, "Google Skillshop", "none"),
            SkillGap("Printful", 3, False, "Printful Help Center", "none"),
        ]
