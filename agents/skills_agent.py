import re

import core.resume_parser as parser


def _normalize_skill(s: str) -> str:
    """Dedup key: lowercase, remove hyphens/spaces. 'e-commerce' -> 'ecommerce'."""
    return re.sub(r"[-\s]+", "", s.lower()).strip()
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
            pct_m = re.search(r"(\d+)%", demand_str)
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

    def update_skill_frequency(self, skills: list[str]) -> list[str]:
        """
        Increments Frequency for each matched skill. Returns names that newly crossed
        the Priority threshold (freq >= 3), sorted by new frequency desc.
        Normalizes skill names to prevent e-commerce/ecommerce duplicates.
        """
        newly_elevated: list[str] = []
        freq_map: dict[str, int] = {}
        try:
            rows = self.sheets.read_tab("SKILLS")
            existing = {_normalize_skill(str(r.get("Skill", ""))): r for r in rows}
            for skill in skills:
                key = _normalize_skill(skill)
                if key in existing:
                    row = existing[key]
                    prev_priority = str(row.get("Priority", "")).lower() == "yes"
                    freq = int(row.get("Frequency", 0) or 0) + 1
                    freq_map[key] = freq
                    updates: dict = {"Frequency": freq}
                    if freq >= 3:
                        updates["Priority"] = "Yes"
                        if not prev_priority:
                            newly_elevated.append(str(row["Skill"]))
                    self.sheets.update_row("SKILLS", "Skill", row["Skill"], updates)
                else:
                    self.sheets.append_row("SKILLS", {
                        "Skill": skill, "Level": "none", "Gap": "Yes",
                        "Frequency": 1, "Priority": "No", "Resource": "",
                        "Completed": "No",
                    })
                    freq_map[key] = 1
        except Exception as e:
            raise RuntimeError(f"Failed to update skill frequency: {e}") from e
        newly_elevated.sort(key=lambda name: -(freq_map.get(_normalize_skill(name), 0)))
        return newly_elevated

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

    def format_skills_compact(self) -> str:
        try:
            rows = self.sheets.read_tab("SKILLS")
        except Exception:
            return "Could not read Skills sheet."
        if not rows:
            return "No skills data. Import from master_resume.md first."

        gaps = [r for r in rows if str(r.get("Gap", "")).lower() in ("yes", "true", "1")]
        gaps_sorted = sorted(gaps, key=lambda r: int(r.get("Frequency", 0) or 0), reverse=True)
        strong = [
            r for r in rows
            if str(r.get("Level", "")).lower() in ("advanced", "experienced", "intermediate")
            and str(r.get("Gap", "")).lower() not in ("yes", "true", "1")
        ]

        lines = ["📚 GAPS (by demand)"]
        for i, g in enumerate(gaps_sorted[:3], 1):
            freq = int(g.get("Frequency", 0) or 0)
            lines.append(f"{i}. {g.get('Skill', '?')} — {freq}x" if freq else f"{i}. {g.get('Skill', '?')} — —")

        if strong:
            lines.append("")
            lines.append("✅ Strong: " + ", ".join(str(r.get("Skill", "")) for r in strong[:5]))

        result = "\n".join(lines).strip()
        return result[:400] if len(result) > 400 else result

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
