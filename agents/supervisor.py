import logging

from agents.career_agent import CareerAgent
from agents.learn_agent import LearnAgent
from agents.plan_agent import PlanAgent
from agents.profile_agent import ProfileAgent
from agents.skills_agent import SkillsAgent
from core.groq_client import AIClient
from core.sheets_client import SheetsClient

logger = logging.getLogger(__name__)


class SupervisorAgent:
    def __init__(self) -> None:
        sheets = SheetsClient()
        groq = AIClient()

        self.career = CareerAgent(sheets, groq)
        self.skills = SkillsAgent(sheets, groq)
        self.profile = ProfileAgent(sheets)
        self.plan = PlanAgent(sheets, groq)
        self.learn = LearnAgent(sheets, groq)
        self.sheets = sheets

    async def route(self, command: str, args: str) -> str:
        logger.info(f"Routing: {command} | args: {args[:60]}")

        try:
            return await self._dispatch(command, args)
        except Exception as e:
            logger.error(f"Error in {command}: {e}", exc_info=True)
            return f"❌ Error in `{command}`: {e}\n\nTry again or check logs."

    async def _dispatch(self, command: str, args: str) -> str:
        # Career commands
        if command == "kyn":
            result = self.career.score_job(args)
            return result.format_telegram()

        if command == "analyze":
            if len(args) < 50:
                return "⚠️ Paste the full job post after /analyze"
            pkg = await self.career.analyze_job(args)
            return pkg.format_telegram()

        if command == "apply":
            if len(args) < 50:
                return "⚠️ Paste the full job post after /apply"
            pkg = await self.career.analyze_job(args)
            return f"📧 *Application Package*\n\n{pkg.format_telegram()}"

        if command == "followup":
            return self.career.format_followups_telegram()

        if command == "stats":
            return self.career.get_stats()

        if command == "track":
            parts = args.split("|")
            if len(parts) < 3:
                return "Format: /track Platform | Employer | Role | KYN | Status"
            self.sheets.append_row(
                "APPLICATIONS",
                {
                    "Date": __import__("datetime").date.today().isoformat(),
                    "Platform": parts[0].strip(),
                    "Employer": parts[1].strip(),
                    "Role": parts[2].strip(),
                    "KYN": parts[3].strip() if len(parts) > 3 else "",
                    "Status": parts[4].strip() if len(parts) > 4 else "applied",
                    "Notes": "",
                    "Follow-up Date": "",
                    "Replied": "No",
                    "Offer": "",
                },
            )
            return f"✅ Tracked: *{parts[1].strip()}* — {parts[2].strip()}"

        # Profile commands
        if command == "me":
            return self.profile.format_telegram()

        if command == "projects":
            try:
                rows = self.sheets.read_tab("PROJECTS")
                if not rows:
                    return "Projects sheet empty. Add projects via Sheets."
                lines = ["📁 *Projects*\n"]
                for r in rows:
                    status_emoji = {"done": "✅", "in progress": "🔨", "paused": "⏸️"}.get(
                        str(r.get("Status", "")).lower(), "◈"
                    )
                    lines.append(
                        f"{status_emoji} *{r.get('Project', '?')}* — "
                        f"{r.get('Status', '?')} | Next: {r.get('Next Task', '?')}"
                    )
                return "\n".join(lines)
            except Exception:
                return "📁 *Projects*\n• RutaSmart — Compliance mode\n• CareerOS — v3 complete\n• LJR.devOS — In progress"

        # Skills commands
        if command == "skills":
            return self.skills.format_skills_telegram()

        if command == "gaps":
            return self.skills.format_gaps_telegram()

        # Learning commands
        if command == "learn":
            if not args.strip():
                return "Usage: /learn [skill name]"
            path = await self.learn.create_learning_path(args.strip())
            return path.format_telegram()

        if command == "roadmap":
            weeks = int(args.strip()) if args.strip().isdigit() else 4
            return await self.learn.generate_roadmap(weeks)

        if command == "log":
            parts = args.split(" ", 1)
            if len(parts) < 2:
                return "Usage: /log [skill] [notes]"
            self.learn.log_progress(parts[0], parts[1])
            return f"✅ Logged progress on *{parts[0]}*"

        if command == "logshow":
            return self.learn.get_log()

        # Planning commands
        if command == "plan":
            hours = self.plan.parse_duration(args.strip()) if args.strip() else 2.0
            tasks = await self.plan.plan_session(hours)
            return self.plan.format_plan_telegram(tasks)

        if command == "next":
            return await self.plan.get_next_action()

        if command == "morning":
            return await self.plan.generate_morning_briefing()

        # System
        if command in ("start", "help"):
            return self._help_text()

        return f"❓ Unknown command: `/{command}`\n\n{self._help_text()}"

    def _help_text(self) -> str:
        return (
            "🤖 *LJR.devOS* — Lebron's AI Operating System\n\n"
            "*Career:*\n"
            "`/kyn [post]` — KYN score\n"
            "`/analyze [post]` — Full analysis + cover letter\n"
            "`/apply [post]` — Application package\n"
            "`/followup` — Follow-ups due today\n"
            "`/track Platform|Employer|Role|KYN|Status` — Log application\n"
            "`/stats` — Application stats\n\n"
            "*Profile:*\n"
            "`/me` — Your full profile\n"
            "`/projects` — All projects\n\n"
            "*Skills:*\n"
            "`/skills` — All skills\n"
            "`/gaps` — Top skill gaps\n\n"
            "*Learning:*\n"
            "`/learn [skill]` — Learning path\n"
            "`/roadmap [weeks]` — Multi-week roadmap\n"
            "`/log [skill] [notes]` — Log progress\n"
            "`/logshow` — View learning log\n\n"
            "*Planning:*\n"
            "`/plan [hours]` — Plan your session\n"
            "`/next` — Next best action\n"
            "`/morning` — Morning briefing"
        )
