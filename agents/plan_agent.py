import datetime
from pathlib import Path

from core.groq_client import GroqClient
from core.models import Task
from core.sheets_client import SheetsClient

RESUME_PATH = Path("master_resume.md")

SYSTEM_PROMPT = """You are Lebron's AI executive assistant.

Context:
- BS CS student in final compliance phase (thesis passed)
- Building CareerOS for freelance income
- Income target: $800/month, current: ₱0
- Active projects: RutaSmart (compliance), CareerOS, LJR.devOS

Prioritization order:
1. Thesis compliance (deadline-driven)
2. Income-generating actions (applications, follow-ups)
3. Skill building that closes job market gaps
4. Long-term projects (LJR.devOS)

Rules:
- Give specific tasks, not vague advice
- Each task must have a duration and a concrete action
- Prefer actions that can be completed in one sitting
- Never suggest more tasks than time allows"""

PLAN_PROMPT = """Lebron has {hours} hours available.

Current status from data:
- Applications sent: {app_count}
- Follow-ups due: {followup_count}
- Top skill gaps: {gaps}
- Active projects: RutaSmart compliance, CareerOS, LJR.devOS
- Thesis compliance: In progress

Create a prioritized task list for today.
Format each task as:
[duration min] | [task title] | [specific action] | [why now]"""

MORNING_PROMPT = """Generate a morning briefing for Lebron.

Date: {date}
Applications sent: {app_count}
Follow-ups due: {followup_count}
Income this month: {income}
Top pending action: {top_action}

Format:
- 2-sentence situation summary
- 3 priorities for today (ranked)
- One motivational line based on his actual progress
Keep it under 150 words."""


class PlanAgent:
    def __init__(self, sheets: SheetsClient, groq: GroqClient) -> None:
        self.sheets = sheets
        self.groq = groq

    async def plan_session(self, hours: float) -> list[Task]:
        app_count, followup_count, gaps = self._get_context()

        raw = await self.groq.chat(
            SYSTEM_PROMPT,
            PLAN_PROMPT.format(
                hours=hours,
                app_count=app_count,
                followup_count=followup_count,
                gaps=gaps,
            ),
            max_tokens=400,
        )
        return self._parse_tasks(raw)

    async def get_next_action(self) -> str:
        app_count, followup_count, gaps = self._get_context()

        if followup_count > 0:
            return f"📬 You have *{followup_count}* follow-up(s) due. Run /followup to see them."

        prompt = f"""What is the single most important thing Lebron should do right now?
        Apps sent: {app_count} | Gaps: {gaps}
        Give one specific action in 2 sentences max."""

        return await self.groq.chat(SYSTEM_PROMPT, prompt, max_tokens=80)

    async def generate_morning_briefing(self) -> str:
        app_count, followup_count, _ = self._get_context()

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
            SYSTEM_PROMPT,
            MORNING_PROMPT.format(
                date=datetime.date.today().strftime("%A, %B %d"),
                app_count=app_count,
                followup_count=followup_count,
                income=income,
                top_action=top_action,
            ),
            max_tokens=200,
        )
        return f"☀️ *Morning Brief — {datetime.date.today().strftime('%b %d')}*\n\n{raw}"

    def _get_context(self) -> tuple[int, int, str]:
        app_count = 0
        followup_count = 0
        gaps = "Meta Ads, GoHighLevel, Klaviyo"

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

        try:
            skill_rows = self.sheets.read_tab("SKILLS")
            gap_skills = [
                r["Skill"]
                for r in skill_rows
                if str(r.get("Gap", "")).lower() == "yes"
            ][:3]
            if gap_skills:
                gaps = ", ".join(gap_skills)
        except Exception:
            pass

        return app_count, followup_count, gaps

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
                    tasks.append(
                        Task(
                            title=parts[1] if len(parts) > 1 else f"Task {i}",
                            duration_min=duration,
                            reason=parts[3] if len(parts) > 3 else "",
                            action=parts[2] if len(parts) > 2 else "",
                            priority=i,
                        )
                    )
                except (ValueError, IndexError):
                    continue
        return tasks[:5]

    def format_plan_telegram(self, tasks: list[Task]) -> str:
        if not tasks:
            return "Could not generate plan. Try again."
        total_min = sum(t.duration_min for t in tasks)
        lines = [f"📋 *Today's Plan* ({total_min} min)\n"]
        for task in tasks:
            lines.append(task.format_telegram())
            lines.append("")
        return "\n".join(lines)
