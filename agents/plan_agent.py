import datetime
from pathlib import Path

import core.resume_parser as parser
from core.groq_client import AIClient as GroqClient
from core.models import Task
from core.sheets_client import SheetsClient

RESUME_PATH = Path("master_resume.md")

PLAN_PROMPT = """Lebron has {hours} hours available.

Current status:
- Applications sent: {app_count}
- Follow-ups due: {followup_count}
- Top skill gaps: {gaps}
- Active projects: {projects}
- Short-term goal: {short_goal}

Create a prioritized task list for today.
Format each task as:
[duration min] | [task title] | [specific action] | [why now]"""

MORNING_PROMPT = """Generate a morning briefing for Lebron.

Date: {date}
Applications sent: {app_count}
Follow-ups due: {followup_count}
Income this month: {income}
Goal: {short_goal}
Top pending action: {top_action}

Format:
- 2-sentence situation summary
- 3 priorities for today (ranked)
- One motivational line based on his actual progress
Keep it under 150 words."""


def _build_system_prompt() -> str:
    try:
        projects = parser.get_projects()
        project_names = ", ".join(p["name"] for p in projects[:4])
        goals = parser.get_goals()
        short_goal = goals.get("Short-term goal", "First remote client by end of June 2026")
        income_target = goals.get("Monthly Target", "$800/month")
    except Exception:
        project_names = "RutaSmart, CareerOS, LJR.devOS"
        short_goal = "First remote client by end of June 2026"
        income_target = "$800/month"

    return f"""You are Lebron's AI executive assistant.

Context:
- BS CS student in final year, thesis passed
- Income target: {income_target}
- Active projects: {project_names}
- Short-term goal: {short_goal}

Prioritization order:
1. Income-generating actions (applications, follow-ups)
2. Thesis compliance if deadline-driven
3. Skill building that closes job market gaps
4. Long-term projects

Rules:
- Give specific tasks, not vague advice
- Each task must have a duration and a concrete action
- Prefer actions that can be completed in one sitting
- Never suggest more tasks than time allows"""


class PlanAgent:
    def __init__(self, sheets: SheetsClient, groq: GroqClient) -> None:
        self.sheets = sheets
        self.groq = groq
        self._system_prompt = _build_system_prompt()

    async def plan_session(self, hours: float) -> list[Task]:
        app_count, followup_count, gaps, projects, short_goal = self._get_context()
        raw = await self.groq.chat(
            self._system_prompt,
            PLAN_PROMPT.format(
                hours=hours,
                app_count=app_count,
                followup_count=followup_count,
                gaps=gaps,
                projects=projects,
                short_goal=short_goal,
            ),
            max_tokens=400,
        )
        return self._parse_tasks(raw)

    async def get_next_action(self) -> str:
        app_count, followup_count, gaps, _, _ = self._get_context()
        if followup_count > 0:
            return f"You have *{followup_count}* follow-up(s) due. Run /followup to see them."
        prompt = f"""What is the single most important thing Lebron should do right now?
        Apps sent: {app_count} | Gaps: {gaps}
        Give one specific action in 2 sentences max."""
        return await self.groq.chat(self._system_prompt, prompt, max_tokens=80)

    async def generate_morning_briefing(self) -> str:
        app_count, followup_count, _, _, short_goal = self._get_context()
        try:
            income_rows = self.sheets.find_rows("INCOME", {"Status": "paid"})
            income = f"${sum(float(r.get('Amount USD', 0)) for r in income_rows):.0f}"
        except Exception:
            income = "₱0"

        top_action = (
            f"{followup_count} follow-ups due"
            if followup_count > 0
            else f"{app_count} applications sent — keep applying"
        )
        raw = await self.groq.chat(
            self._system_prompt,
            MORNING_PROMPT.format(
                date=datetime.date.today().strftime("%A, %B %d"),
                app_count=app_count,
                followup_count=followup_count,
                income=income,
                short_goal=short_goal,
                top_action=top_action,
            ),
            max_tokens=200,
        )
        return f"Morning Brief — {datetime.date.today().strftime('%b %d')}\n\n{raw}"

    def _get_context(self) -> tuple[int, int, str, str, str]:
        app_count = 0
        followup_count = 0

        try:
            apps = self.sheets.read_tab("APPLICATIONS")
            app_count = len(apps)
            today = datetime.date.today()
            for row in apps:
                if str(row.get("Replied", "")).lower() == "yes":
                    continue
                fu_date = str(row.get("Follow-up Date", "")).strip()
                if fu_date:
                    try:
                        if datetime.date.fromisoformat(fu_date) <= today:
                            followup_count += 1
                    except ValueError:
                        pass
        except Exception:
            pass

        # Gaps — Sheets first, resume_parser fallback
        gaps = "Meta Ads, GoHighLevel, Printful"
        try:
            skill_rows = self.sheets.read_tab("SKILLS")
            gap_skills = [
                r.get("Skill", "")
                for r in skill_rows
                if str(r.get("Gap", "")).lower() == "yes"
            ][:3]
            if gap_skills:
                gaps = ", ".join(gap_skills)
        except Exception:
            raw_gaps = parser.get_gaps()
            gaps = ", ".join(g["name"] for g in raw_gaps[:3])

        # Projects and goal from resume_parser
        raw_projects = parser.get_projects()
        projects = ", ".join(p["name"] for p in raw_projects[:4]) if raw_projects else "RutaSmart, CareerOS, LJR.devOS"
        goals = parser.get_goals()
        short_goal = goals.get("Short-term goal", "First remote client by end of June 2026")

        return app_count, followup_count, gaps, projects, short_goal

    def _parse_tasks(self, raw: str) -> list[Task]:
        tasks: list[Task] = []
        for i, line in enumerate(raw.strip().split("\n"), start=1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                try:
                    duration = int("".join(c for c in parts[0] if c.isdigit()) or "30")
                    tasks.append(Task(
                        title=parts[1] if len(parts) > 1 else f"Task {i}",
                        duration_min=duration,
                        reason=parts[3] if len(parts) > 3 else "",
                        action=parts[2] if len(parts) > 2 else "",
                        priority=i,
                    ))
                except (ValueError, IndexError):
                    continue
        return tasks[:5]

    def format_plan_telegram(self, tasks: list[Task]) -> str:
        if not tasks:
            return "Could not generate plan. Try again."
        total_min = sum(t.duration_min for t in tasks)
        lines = [f"*Today's Plan* ({total_min} min)\n"]
        for task in tasks:
            lines.append(task.format_telegram())
            lines.append("")
        return "\n".join(lines)
