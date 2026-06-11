import datetime
import logging
import re
import shlex

from agents.architect_agent import ArchitectAgent
from agents.career_agent import CareerAgent
from agents.overview_agent import OverviewAgent
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
        self.architect = ArchitectAgent()
        self.overview = OverviewAgent()
        self.sheets = sheets
        self.ai = groq

        # Session cache: last KYN score from /analyze (keyed by "last")
        self._last_kyn: dict[str, int] = {}

    async def route(self, command: str, args: str) -> str:
        logger.info(f"Routing: {command} | args: {args[:60]}")
        try:
            return await self._dispatch(command, args)
        except Exception as e:
            logger.error(f"Error in {command}: {e}", exc_info=True)
            return f"Error in `{command}`: {e}\n\nTry again or check logs."

    async def _dispatch(self, command: str, args: str) -> str:
        # ── Daily dashboard ────────────────────────────────────────────
        if command == "overview":
            return self.overview.get_overview(self.sheets)

        if command == "applications":
            return self.career.format_applications_compact()

        # ── Career commands ────────────────────────────────────────────
        if command == "kyn":
            result = self.career.score_job(args)
            return result.format_telegram()

        if command == "analyze":
            if len(args) < 50:
                return "Paste the full job post after /analyze"
            pkg = await self.career.analyze_job(args)

            # Cache KYN score for /track
            self._last_kyn["last"] = pkg.kyn.score

            # Auto-log to APPLICATIONS with status "ready to apply"
            employer, role = self.career.extract_employer_role(args)
            today = datetime.date.today()
            try:
                self.sheets.append_row("APPLICATIONS", {
                    "Date": today.isoformat(),
                    "Platform": "analyzed",
                    "Employer": employer,
                    "Role": role,
                    "KYN Score": str(pkg.kyn.score),
                    "Status": "ready to apply",
                    "Notes": pkg.kyn.verdict,
                    "Follow-up Date": (today + datetime.timedelta(days=5)).isoformat(),
                    "Replied": "No",
                    "Offer": "",
                })
            except Exception as e:
                logger.warning(f"Auto-log failed for /analyze: {e}")

            # Update skill frequency from matched skills
            if pkg.kyn.matched_skills:
                try:
                    self.skills.update_skill_frequency(pkg.kyn.matched_skills)
                except Exception as e:
                    logger.warning(f"Skill frequency update failed: {e}")

            return pkg.format_telegram()

        if command == "apply":
            if len(args) < 50:
                return "Paste the full job post after /apply"
            pkg = await self.career.analyze_job(args)
            return f"*Application Package*\n\n{pkg.format_telegram()}"

        if command == "followup":
            return self.career.format_followups_telegram()

        if command == "stats":
            return self.career.get_stats()

        if command == "track":
            try:
                parts = shlex.split(args)
            except ValueError:
                parts = args.split()

            if len(parts) < 3:
                return (
                    "*Usage:* /track [platform] [employer] [role] [kyn\\_score] [status]\n"
                    "Example: `/track OLJ LazySun VA 75 applied`\n"
                    "Example: `/track OLJ \"Tech Corp\" \"Shopify Dev\"`\n\n"
                    "KYN score and status are optional — uses last /analyze score if available."
                )

            platform = parts[0]
            employer = parts[1]
            role = parts[2]
            kyn_score = parts[3] if len(parts) > 3 else str(self._last_kyn.get("last", ""))
            status = parts[4] if len(parts) > 4 else "applied"
            today = datetime.date.today()

            # Upsert: update existing row if Employer + Role match
            existing = self.sheets.find_rows("APPLICATIONS", {"Employer": employer, "Role": role})
            if existing:
                self.sheets.update_row("APPLICATIONS", "Employer", employer, {
                    "Status": status,
                    "KYN Score": kyn_score,
                    "Platform": platform,
                })
                return f"Updated: *{employer}* — {role} → {status}"

            self.sheets.append_row("APPLICATIONS", {
                "Date": today.isoformat(),
                "Platform": platform,
                "Employer": employer,
                "Role": role,
                "KYN Score": kyn_score,
                "Status": status,
                "Notes": "",
                "Follow-up Date": (today + datetime.timedelta(days=5)).isoformat(),
                "Replied": "No",
                "Offer": "",
            })
            return f"Tracked: *{employer}* — {role} | KYN: {kyn_score or 'N/A'} | Status: {status}"

        # ── Profile commands ───────────────────────────────────────────
        if command == "me":
            return self.profile.format_telegram()

        if command == "projects":
            try:
                rows = self.sheets.read_tab("PROJECTS")
                if not rows:
                    return "Projects sheet empty. Add projects via Sheets."
                lines = ["*Projects*\n"]
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
                return "*Projects*\n• RutaSmart — Compliance mode\n• CareerOS — v3 complete\n• LJR.devOS — In progress"

        if command == "update":
            try:
                parts = shlex.split(args)
            except ValueError:
                parts = args.split()
            if len(parts) < 3:
                return (
                    "*Usage:* /update [project] [field] [value]\n"
                    "Example: `/update LJR.devOS \"Next Task\" \"wire weekplan\"`\n"
                    "Fields: Status, Next Task, Deadline, Priority, Notes"
                )
            project = parts[0]
            field = parts[1]
            value = " ".join(parts[2:])
            updated = self.sheets.update_row("PROJECTS", "Project", project, {field: value})
            if updated:
                return f"Updated *{project}*: {field} = {value}"
            return f"Project '{project}' not found. Use /projects to see exact names."

        if command == "done":
            try:
                parts = shlex.split(args)
            except ValueError:
                parts = args.split()
            if not parts:
                return (
                    "*Usage:* /done [project] [optional: new next task]\n"
                    "Example: `/done LJR.devOS \"start /weekplan\"`\n"
                    "Marks current task done and sets the next one (or clears it)."
                )
            project = parts[0]
            new_next = " ".join(parts[1:]) if len(parts) > 1 else ""

            rows = self.sheets.find_rows("PROJECTS", {"Project": project})
            if not rows:
                return f"Project '{project}' not found. Use /projects to see exact names."

            current_next = rows[0].get("Next Task", "(no task set)")
            self.sheets.update_row("PROJECTS", "Project", project, {"Next Task": new_next})

            msg = f"Done: *{current_next}*\nProject: {project}"
            if new_next:
                msg += f"\nNext up: {new_next}"
            else:
                msg += "\nNext task cleared. Set with /update [project] \"Next Task\" [task]"
            return msg

        # ── Skills commands ────────────────────────────────────────────
        if command == "skills":
            return self.skills.format_skills_compact()

        if command == "gaps":
            return self.skills.format_gaps_telegram()

        # ── Learning commands ──────────────────────────────────────────
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
            return f"Logged progress on *{parts[0]}*"

        if command == "logshow":
            return self.learn.get_log()

        # ── Planning commands ──────────────────────────────────────────
        if command == "plan":
            raw = args.strip().lower()
            # Parse optional energy level at the end: /plan 2h high
            energy = "medium"
            for level in ("high", "medium", "low"):
                if re.search(rf"\b{level}\b", raw):
                    energy = level
                    raw = re.sub(rf"\b{level}\b", "", raw).strip()
                    break
            hours = self.plan.parse_duration(raw) if raw else 2.0
            tasks = await self.plan.plan_session(hours, energy=energy)
            return self.plan.format_plan_telegram(tasks, energy=energy)

        if command == "next":
            return await self.plan.get_next_action()

        if command == "morning":
            return await self.plan.generate_morning_briefing()

        if command == "weekplan":
            return await self.plan.generate_weekplan()

        if command == "sprint":
            return self.plan.generate_sprint_view()

        # ── Architect commands ─────────────────────────────────────────
        if command == "idea":
            if not args.strip():
                return (
                    "*Usage:* /idea [description]\n"
                    "Example: `/idea Add /platforms command to show reply rates by platform`"
                )
            result = await self.architect.process_idea(args.strip(), self.ai)
            return self._format_idea_result(result, args.strip())

        if command == "ideas":
            return self._format_ideas_list()

        # ── System ─────────────────────────────────────────────────────
        if command in ("start", "help"):
            return self._help_text()

        return f"Unknown command: `/{command}`\n\n{self._help_text()}"

    def _help_text(self) -> str:
        return (
            "*LJR.devOS* — Lebron's AI Operating System\n\n"
            "*📱 DAILY:*\n"
            "`/overview` — your day in one screen\n"
            "`/applications` — application pipeline\n"
            "`/skills` — skill gaps and strengths\n\n"
            "*Career:*\n"
            "`/kyn [post]` — KYN score\n"
            "`/analyze [post]` — Full analysis + cover letter (auto-logs)\n"
            "`/apply [post]` — Application package\n"
            "`/followup` — Follow-ups due today\n"
            "`/track [platform] [employer] [role] [kyn] [status]`\n"
            "`/stats` — Application stats\n\n"
            "*Projects:*\n"
            "`/projects` — All projects + next tasks\n"
            "`/update [project] [field] [value]` — Update a project field\n"
            "`/done [project] [new next task]` — Mark task done, set next\n"
            "`/sprint` — Sprint board view\n\n"
            "*🏗️ BUILD:*\n"
            "`/idea [description]` — Turn an idea into a Claude Code spec\n"
            "`/ideas` — See all captured ideas\n\n"
            "*Skills:*\n"
            "`/skills` — All skills\n"
            "`/gaps` — Top skill gaps\n\n"
            "*Learning:*\n"
            "`/learn [skill]` — Learning path\n"
            "`/roadmap [weeks]` — Multi-week roadmap\n"
            "`/log [skill] [notes]` — Log progress\n"
            "`/logshow` — View learning log\n\n"
            "*Planning:*\n"
            "`/plan [hours] [energy: high/medium/low]` — Session plan\n"
            "`/weekplan` — AI-generated Mon-Fri plan\n"
            "`/next` — Next best action\n"
            "`/morning` — Morning briefing"
        )

    def _format_idea_result(self, result: dict, original_idea: str) -> str:
        status = result.get("status", "error")

        if status == "needs_clarification":
            questions = result.get("questions", [])
            if not questions:
                return "Unclear idea — please add more detail and try again."
            lines = ["A few questions before I spec this out:\n"]
            for i, q in enumerate(questions[:3], 1):
                lines.append(f"{i}. {q}")
            lines.append(
                f"\nReply with: `/idea {original_idea[:40]} -- [your answers]`"
            )
            return "\n".join(lines)

        if status == "spec_ready":
            problem = result.get("problem", "")
            solution = result.get("solution", "")
            criteria = result.get("acceptance_criteria", [])
            prompt = result.get("claude_code_prompt", "")

            # Log to IDEAS tab
            try:
                self.sheets.append_row("IDEAS", {
                    "Date": datetime.date.today().isoformat(),
                    "Idea": original_idea[:200],
                    "Status": "captured",
                    "Problem": problem,
                    "Solution": solution,
                    "Acceptance Criteria": " | ".join(criteria),
                    "Claude Code Prompt": prompt[:1000],
                })
            except Exception as e:
                logger.warning(f"IDEAS tab log failed: {e}")

            criteria_lines = "\n".join(f"• {c}" for c in criteria)
            return (
                "*IDEA SPECCED*\n\n"
                f"*Problem:* {problem}\n"
                f"*Solution:* {solution}\n\n"
                f"*Acceptance Criteria:*\n{criteria_lines}\n\n"
                f"*Paste this into Claude Code:*\n```\n{prompt}\n```\n\n"
                "Logged to IDEAS tab. Run /ideas to see all captured ideas."
            )

        # error
        return result.get("message", "Could not process idea, try rephrasing")

    def _format_ideas_list(self) -> str:
        try:
            rows = self.sheets.read_tab("IDEAS")
        except Exception as e:
            logger.error(f"IDEAS read failed: {e}")
            return "Could not read IDEAS tab."

        if not rows:
            return "No ideas captured yet. Use /idea [description] to spec one."

        captured = [r for r in rows if str(r.get("Status", "")).lower() == "captured"]
        built = [r for r in rows if str(r.get("Status", "")).lower() == "built"]
        other = [r for r in rows if r not in captured and r not in built]

        lines = [f"*CAPTURED IDEAS* ({len(rows)} total)\n"]

        if captured:
            lines.append("*Not yet built:*")
            for r in captured:
                date = r.get("Date", "?")
                idea = str(r.get("Idea", ""))[:60]
                lines.append(f"- {date} — {idea}")
            lines.append("")

        if built:
            lines.append("*Built:*")
            for r in built:
                date = r.get("Date", "?")
                idea = str(r.get("Idea", ""))[:60]
                lines.append(f"- {date} — {idea}")
            lines.append("")

        if other:
            lines.append("*Other:*")
            for r in other:
                date = r.get("Date", "?")
                idea = str(r.get("Idea", ""))[:60]
                status = r.get("Status", "?")
                lines.append(f"- {date} [{status}] — {r.get('Idea', '')[:60]}")

        return "\n".join(lines).strip()
