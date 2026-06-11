import datetime
import logging
import re

import core.resume_parser as parser

logger = logging.getLogger(__name__)
from core.groq_client import AIClient as GroqClient
from core.models import Task
from core.sheets_client import SheetsClient

PLAN_PROMPT = """Lebron has exactly {minutes} minutes available ({hours_label}).
Budget cap: {budget_min} minutes (90% of available — leave buffer).
{energy_directive}

Situation:
- Overdue follow-ups (>5 days, no reply): {followup_count}
- Applications sent total: {app_count}
- Top skill gaps: {gaps}
- Active projects and next tasks: {projects}
- Goal: {short_goal}

Priority order (STRICT — follow this exactly):
1. Overdue follow-ups if any exist (5 min each)
2. Apply to a new high-KYN job via /analyze (10 min per application)
3. RutaSmart thesis revision task (60-90 min if budget allows)
4. Learn top skill gap — one focused tutorial (30 min)
5. Project next task from active projects (15-30 min)

Task duration rules:
- Follow up one employer: 5 min
- Apply to one job (/analyze + send): 10 min
- RutaSmart revision: 60 min
- Watch one skill tutorial: 30 min
- Project task (small): 15 min
- Project task (medium): 30 min

CRITICAL: Total task minutes MUST NOT exceed {budget_min} minutes.
Stop adding tasks once the budget is filled.

Format each task exactly like this (pipe-separated, no extra text):
[duration_min] | [task title] | [exact action to take] | [why this now]

Example:
10 | Apply to Shopify Dev role | Run /analyze on the job post then send message | Closes income gap fastest
30 | Meta Ads tutorial | Watch Meta Blueprint Module 1 on blueprint.facebook.com | 40% of target jobs need this"""

WEEKPLAN_PROMPT = """Generate a Monday-Friday work plan for Lebron.

Active projects and next tasks: {projects}
Open applications tracked: {app_count}
Follow-ups due: {followup_count}
Top skill gaps to close: {gaps}
Goal this week: {short_goal}

Format (exactly — one line per day):
MON: [primary task] ({{duration}}min)
TUE: [primary task] ({{duration}}min)
WED: [primary task] ({{duration}}min)
THU: [primary task] ({{duration}}min)
FRI: [primary task] ({{duration}}min)
Theme: [one-line weekly theme]

Rules:
- ONE primary task per day (highest value for that day)
- Mix income-generating tasks (apply/follow-up) with building tasks
- Friday = review + prep for next week
- Keep each day under 3 hours"""

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

You plan sessions to the minute. You never suggest more work than fits the budget.
You always prioritize income-generating tasks first."""


class PlanAgent:
    def __init__(self, sheets: SheetsClient, groq: GroqClient) -> None:
        self.sheets = sheets
        self.groq = groq
        self._system_prompt = _build_system_prompt()

    @staticmethod
    def parse_duration(raw: str) -> float:
        """
        Parse user input into hours (float).
        "2 hours" → 2.0
        "2h" → 2.0
        "30 min" → 0.5
        "90" → 1.5  (bare number = minutes if <=120, hours if >120 is ambiguous → treat as hours)
        "1.5" → 1.5
        """
        raw = raw.lower().strip()
        # explicit minutes
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:min(?:ute)?s?)", raw)
        if m:
            return float(m.group(1)) / 60
        # explicit hours
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:h(?:our)?s?)", raw)
        if m:
            return float(m.group(1))
        # bare number
        m = re.search(r"(\d+(?:\.\d+)?)", raw)
        if m:
            val = float(m.group(1))
            # treat bare numbers <=5 as hours, >5 as minutes
            return val if val <= 5 else val / 60
        return 2.0

    async def plan_session(self, hours: float, energy: str = "medium") -> list[Task]:
        minutes = round(hours * 60)
        budget_min = round(minutes * 0.9)
        hours_label = f"{hours:.0f}h" if hours == int(hours) else f"{hours:.1f}h"

        energy_directives = {
            "high": "ENERGY: HIGH — dive straight into the hardest, highest-value task. Full focus mode.",
            "medium": "ENERGY: MEDIUM — balance focus work with lighter tasks. Start with one high-value task.",
            "low": "ENERGY: LOW — admin tasks only. ONLY schedule: follow-ups (5 min each), /stats check (5 min), /logshow review (5 min). Skip building and deep-focus tasks entirely.",
        }
        energy_directive = energy_directives.get(energy.lower(), energy_directives["medium"])

        app_count, followup_count, gaps, projects, short_goal = self._get_context()

        raw = await self.groq.chat(
            self._system_prompt,
            PLAN_PROMPT.format(
                minutes=minutes,
                hours_label=hours_label,
                budget_min=budget_min,
                energy_directive=energy_directive,
                app_count=app_count,
                followup_count=followup_count,
                gaps=gaps,
                projects=projects,
                short_goal=short_goal,
            ),
            max_tokens=500,
        )
        return self._parse_tasks(raw, budget_min)

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
            total = 0.0
            for r in income_rows:
                try:
                    total += float(str(r.get("Amount USD", "0")).replace(",", "").strip() or "0")
                except (ValueError, TypeError):
                    pass
            income = f"${total:.0f}"
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
                        applied_date = datetime.date.fromisoformat(str(row.get("Date", "")).strip())
                        days_since = (today - applied_date).days
                        if days_since >= 5 and datetime.date.fromisoformat(fu_date) <= today:
                            followup_count += 1
                    except (ValueError, TypeError):
                        pass
        except Exception:
            pass

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

        try:
            project_rows = self.sheets.read_tab("PROJECTS")
            project_parts = [
                f"{r.get('Project', '?')} → {r.get('Next Task', 'TBD')}"
                for r in project_rows
                if str(r.get("Status", "")).lower() != "done"
            ]
            projects = "; ".join(project_parts) or "No active projects"
        except Exception:
            raw_projects = parser.get_projects()
            projects = ", ".join(p["name"] for p in raw_projects[:4]) if raw_projects else "RutaSmart, CareerOS, LJR.devOS"
        goals = parser.get_goals()
        short_goal = goals.get("Short-term goal", "First remote client by end of June 2026")

        return app_count, followup_count, gaps, projects, short_goal

    def _parse_tasks(self, raw: str, budget_min: int = 999) -> list[Task]:
        tasks: list[Task] = []
        used_min = 0
        for i, line in enumerate(raw.strip().split("\n"), start=1):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("Example"):
                continue
            parts = [p.strip() for p in line.split("|")]
            if len(parts) < 3:
                continue
            try:
                duration = int("".join(c for c in parts[0] if c.isdigit()) or "30")
                if duration <= 0 or duration > 180:
                    continue
                # Stop adding tasks once budget is filled
                if used_min + duration > budget_min:
                    break
                tasks.append(Task(
                    title=parts[1] if len(parts) > 1 else f"Task {i}",
                    duration_min=duration,
                    action=parts[2] if len(parts) > 2 else "",
                    reason=parts[3] if len(parts) > 3 else "",
                    priority=i,
                ))
                used_min += duration
            except (ValueError, IndexError):
                continue
        return tasks

    def format_plan_telegram(self, tasks: list[Task], energy: str = "medium") -> str:
        if not tasks:
            return "Could not generate plan. Try again."
        total_min = sum(t.duration_min for t in tasks)
        h, m = divmod(total_min, 60)
        time_str = f"{h}h {m}m" if h else f"{m}m"
        energy_tag = {"high": "Full Focus", "medium": "Balanced", "low": "Low Energy"}.get(energy.lower(), "")
        header = f"*Today's Plan* ({time_str}" + (f" — {energy_tag}" if energy_tag else "") + ")\n"
        lines = [header]
        for task in tasks:
            lines.append(task.format_telegram())
            lines.append("")
        return "\n".join(lines)

    async def generate_weekplan(self) -> str:
        app_count, followup_count, gaps, projects, short_goal = self._get_context()
        raw = await self.groq.chat(
            self._system_prompt,
            WEEKPLAN_PROMPT.format(
                projects=projects,
                app_count=app_count,
                followup_count=followup_count,
                gaps=gaps,
                short_goal=short_goal,
            ),
            max_tokens=300,
        )
        week_start = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())

        try:
            self.sheets.append_row("WEEKLY PLANNER", {
                "Week_Start": week_start.isoformat(),
                "Plan_Text": raw[:1000],
                "Projects_Covered": projects[:100],
                "Generated_At": datetime.datetime.now().isoformat(timespec="minutes"),
            })
        except Exception as e:
            logger.warning(f"Could not save weekplan to sheet: {e}")

        return f"*Week of {week_start.strftime('%b %d')}*\n\n{raw}"

    def generate_sprint_view(self) -> str:
        try:
            rows = self.sheets.read_tab("PROJECTS")
        except Exception as e:
            logger.error(f"Could not read PROJECTS: {e}")
            return "Could not read Projects sheet."

        this_week: list[str] = []
        next_week: list[str] = []
        backlog: list[str] = []

        for r in rows:
            status = str(r.get("Status", "")).lower()
            priority = str(r.get("Priority", "")).lower()
            name = r.get("Project", "?")
            next_task = r.get("Next Task", "TBD")
            if status == "done":
                continue
            line = f"• *{name}*: {next_task}"
            if status == "in progress" or priority == "high":
                this_week.append(line)
            elif priority in ("medium", "normal"):
                next_week.append(line)
            else:
                backlog.append(line)

        lines = ["*Sprint Board*\n"]
        if this_week:
            lines.append("*THIS WEEK:*")
            lines.extend(this_week)
            lines.append("")
        if next_week:
            lines.append("*NEXT WEEK:*")
            lines.extend(next_week)
            lines.append("")
        if backlog:
            lines.append("*BACKLOG:*")
            lines.extend(backlog)

        if not (this_week or next_week or backlog):
            return "No active projects in sprint board. Add projects to the PROJECTS tab."

        return "\n".join(lines)
