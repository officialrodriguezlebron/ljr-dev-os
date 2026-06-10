import datetime
import logging

import core.resume_parser as parser
from core.groq_client import AIClient as GroqClient
from core.models import LearningPath
from core.sheets_client import SheetsClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Lebron's learning coach.
You create practical, project-based learning paths that result
in portfolio proof within weeks, not months.

Rules:
- Every skill learned must produce something showable
- Free resources only — YouTube, official docs, free courses
- Week 1 = consume, Week 2 = build something, Week 3 = polish + ship
- Proof project must be something a client/employer can click
- Connect to Lebron's existing stack when possible"""

ROADMAP_PROMPT = """Create a {weeks}-week learning roadmap for Lebron.

Current gaps (by market frequency):
{gaps}

Format as a week-by-week plan. Each week: skill focus + deliverable.
End with a portfolio piece that showcases all skills learned."""

PATH_PROMPT = """Create a learning path for: {skill}

Lebron's context:
- {skill_context}
- Learns by building, not watching
- Target: portfolio-ready proof within 2-3 weeks

Include:
1. Best free resources (specific YouTube channels or docs)
2. Week-by-week milestones
3. Proof project idea that connects to his existing work"""


class LearnAgent:
    def __init__(self, sheets: SheetsClient, groq: GroqClient) -> None:
        self.sheets = sheets
        self.groq = groq

    async def create_learning_path(self, skill: str) -> LearningPath:
        try:
            skills = parser.get_skills()
            top = [f"{k} ({v})" for k, v in skills.items() if v in ("Advanced", "Intermediate")][:4]
            skill_context = ", ".join(top) if top else "Shopify Advanced, React/Next.js Intermediate"
        except Exception:
            skill_context = "Shopify Advanced, React/Next.js Intermediate, Python Intermediate"
        raw = await self.groq.chat(
            SYSTEM_PROMPT,
            PATH_PROMPT.format(skill=skill, skill_context=skill_context),
            max_tokens=400,
        )
        return self._parse_path(skill, raw)

    async def generate_roadmap(self, weeks: int = 4) -> str:
        try:
            gap_rows = self.sheets.read_tab("SKILLS")
            gaps_text = "\n".join(
                f"- {r['Skill']} (seen {r.get('Frequency', 0)}x)"
                for r in gap_rows
                if str(r.get("Gap", "")).lower() == "yes"
            )[:800]
        except Exception:
            gaps_text = "- Meta Ads\n- GoHighLevel\n- Google Ads\n- Klaviyo"

        raw = await self.groq.chat(
            SYSTEM_PROMPT,
            ROADMAP_PROMPT.format(weeks=weeks, gaps=gaps_text),
            max_tokens=500,
        )
        return f"🗺️ *{weeks}-Week Learning Roadmap*\n\n{raw}"

    def log_progress(self, skill: str, notes: str) -> None:
        try:
            self.sheets.append_row(
                "LEARNING",
                {
                    "Date": datetime.date.today().isoformat(),
                    "Skill": skill,
                    "Resource": "",
                    "Time (min)": "",
                    "Notes": notes,
                    "Completed": "No",
                },
            )
        except Exception as e:
            logger.error(f"Failed to log progress for '{skill}': {e}")
            raise RuntimeError(f"Could not save learning log: {e}") from e

    def get_log(self) -> str:
        try:
            rows = self.sheets.read_tab("LEARNING")
        except Exception:
            return "Learning log empty or unavailable."
        if not rows:
            return "No learning logged yet. Use /log [skill] [notes] to start."
        recent = rows[-5:]
        lines = ["📚 *Recent Learning Log*\n"]
        for r in reversed(recent):
            lines.append(
                f"• *{r.get('Skill', '?')}* — {r.get('Date', '?')} "
                f"| {r.get('Notes', '')[:60]}"
            )
        return "\n".join(lines)

    def _parse_path(self, skill: str, raw: str) -> LearningPath:
        lines = raw.strip().split("\n")
        resources: list[str] = []
        milestones: list[str] = []
        proof_project = f"Build a {skill} mini-project"

        for line in lines:
            stripped = line.strip().lstrip("0123456789.-) ").strip()
            if not stripped:
                continue
            low = stripped.lower()
            if any(w in low for w in ["youtube", "course", "docs", "resource", "watch", "read"]):
                resources.append(stripped[:80])
            elif any(w in low for w in ["week", "day", "milestone", "build", "create", "ship"]):
                milestones.append(stripped[:80])
            elif any(w in low for w in ["proof", "project", "portfolio", "showcase"]):
                proof_project = stripped[:100]

        return LearningPath(
            skill=skill,
            weeks=3,
            resources=resources[:4] or [f"Search: '{skill} tutorial 2024' on YouTube", f"{skill} official documentation"],
            milestones=milestones[:3] or ["Week 1: Learn fundamentals", "Week 2: Build project", "Week 3: Polish and ship"],
            proof_project=proof_project,
        )
