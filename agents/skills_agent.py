import core.resume_parser as parser
from core.groq_client import AIClient as GroqClient
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
            rows = self.sheets.read_tab("SKILLS")
            if rows:
                return rows
        except Exception:
            pass
        # Fall back to resume_parser
        skills = parser.get_skills()
        return [{"Skill": k, "Level": v, "Gap": "No"} for k, v in skills.items()]

    def get_gaps(self) -> list[SkillGap]:
        # Try Sheets first (has frequency data from real job scans)
        try:
            rows = self.sheets.read_tab("SKILLS")
            if rows:
                gaps = []
                for row in rows:
                    if str(row.get("Gap", "")).lower() in ("yes", "true", "1"):
                        gaps.append(SkillGap(
                            name=str(row.get("Skill", "")),
                            frequency=int(row.get("Frequency", 0) or 0),
                            priority=str(row.get("Priority", "")).lower() == "yes",
                            resource=str(row.get("Resource", "TBD")),
                            current_level=str(row.get("Level", "none")),
                        ))
                gaps.sort(key=lambda g: (-g.frequency, not g.priority))
                if gaps:
                    return gaps
        except Exception:
            pass

        # Fall back to resume_parser.get_gaps()
        return self._gaps_from_resume()

    def _gaps_from_resume(self) -> list[SkillGap]:
        raw = parser.get_gaps()
        result = []
        for g in raw:
            demand_str = g.get("market_demand", "0%")
            pct_m = __import__("re").search(r"(\d+)%", demand_str)
            freq = int(pct_m.group(1)) if pct_m else 0
            result.append(SkillGap(
                name=g["name"],
                frequency=freq,
                priority=g.get("priority", "").upper() == "HIGH",
                resource=g.get("resource", "TBD"),
                current_level="none",
            ))
        result.sort(key=lambda g: (-g.frequency, not g.priority))
        return result

    def update_skill_frequency(self, skills: list[str]) -> None:
        try:
            rows = self.sheets.read_tab("SKILLS")
            existing = {str(r.get("Skill", "")).lower(): r for r in rows}
            for skill in skills:
                key = skill.lower()
                if key in existing:
                    freq = int(existing[key].get("Frequency", 0) or 0) + 1
                    self.sheets.update_row("SKILLS", "Skill", existing[key]["Skill"], {"Frequency": freq})
                else:
                    self.sheets.append_row("SKILLS", {
                        "Skill": skill, "Level": "none", "Gap": "Yes",
                        "Frequency": 1, "Priority": "No", "Resource": "",
                        "Completed": "No",
                    })
        except Exception as e:
            raise RuntimeError(f"Failed to update skill frequency: {e}") from e

    def format_gaps_telegram(self) -> str:
        # Try Sheets with frequency data first
        try:
            rows = self.sheets.read_tab("SKILLS")
            if rows:
                gaps = [r for r in rows if str(r.get("Gap", "")).lower() in ("yes", "true", "1")]
                if gaps:
                    lines = [f"📊 *Top Skill Gaps* ({len(gaps)} total)\n"]
                    for g in gaps[:6]:
                        freq = int(g.get("Frequency", 0) or 0)
                        priority = str(g.get("Priority", "")).lower() == "yes"
                        emoji = "🔴" if priority else "🟡"
                        resource = str(g.get("Resource", "TBD"))
                        freq_str = f"{freq}% of target jobs" if freq else "market demand tracked"
                        lines.append(f"{emoji} *{g['Skill']}* — {freq_str} | {resource}")
                    return "\n".join(lines)
        except Exception:
            pass

        # Fall back to resume_parser with market demand strings
        raw = parser.get_gaps()
        if not raw:
            return "No skill gaps found. Check master_resume.md."
        lines = [f"📊 *Top Skill Gaps* ({len(raw)} total)\n"]
        for g in raw[:6]:
            priority = g.get("priority", "").upper() == "HIGH"
            emoji = "🔴" if priority else "🟡"
            lines.append(
                f"{emoji} *{g['name']}* — {g['market_demand']} | {g['resource']}"
            )
        return "\n".join(lines)

    def format_skills_telegram(self) -> str:
        rows = self.get_skills()
        if not rows:
            return "Skills sheet empty. Import from master_resume.md first."
        strong = [r for r in rows if str(r.get("Level", "")).lower() in ("advanced", "intermediate", "experienced")]
        learning = [r for r in rows if str(r.get("Level", "")).lower() in ("beginner", "learning", "none")]
        gaps = [r for r in rows if str(r.get("Gap", "")).lower() in ("yes", "true", "1")]
        lines = [f"⚡ *Skills ({len(rows)} tracked)*\n"]
        if strong:
            lines.append(f"*Strong ({len(strong)}):* " + " · ".join(str(r.get("Skill", r.get("Skill", ""))) for r in strong[:8]))
        if learning:
            lines.append(f"*Learning ({len(learning)}):* " + " · ".join(str(r.get("Skill", "")) for r in learning[:5]))
        if gaps:
            lines.append(f"*Gaps ({len(gaps)}):* " + " · ".join(str(r.get("Skill", "")) for r in gaps[:5]))
        return "\n".join(lines)
