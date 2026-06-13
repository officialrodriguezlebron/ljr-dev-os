import datetime
import logging
import re
import shlex

from agents.architect_agent import ArchitectAgent
from agents.calendar_agent import CalendarAgent
from agents.career_agent import CareerAgent
from agents.overview_agent import OverviewAgent
from agents.learn_agent import LearnAgent
from agents.plan_agent import PlanAgent
from agents.profile_agent import ProfileAgent
from agents.reply_agent import ReplyAgent
from agents.skills_agent import SkillsAgent
from agents.content_calendar_agent import ContentCalendarAgent
from agents.email_audit_agent import EmailAuditAgent
from agents.meta_ads_agent import MetaAdsAgent
from agents.pdp_agent import PdpAgent
from agents.photo_qa_agent import PhotoQaAgent
from agents.reel_content_agent import ReelContentAgent
from agents.tiktok_agent import TiktokAgent
from agents.toggl_agent import TogglAgent
from core.groq_client import AIClient
from core.knowledge_client import KnowledgeClient
from core.schedule_engine import ScheduleEngine
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
        self.calendar = CalendarAgent()
        self.overview = OverviewAgent()
        self.reply = ReplyAgent()
        self.schedule_engine = ScheduleEngine()
        self.sheets = sheets
        self.ai = groq

        # Phase 7 — ecommerce AI team
        self.pdp = PdpAgent()
        self.photo_qa = PhotoQaAgent()
        self.tiktok_shop = TiktokAgent()
        self.meta_ads = MetaAdsAgent()
        self.content_cal = ContentCalendarAgent()
        self.email_audit = EmailAuditAgent()
        self.reel = ReelContentAgent()
        self.toggl = TogglAgent()
        self._knowledge = KnowledgeClient()

        # Session caches
        self._last_kyn: dict[str, int] = {}
        self._last_output: dict | None = None  # Last ecommerce agent output for /log

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

        if command == "today":
            return self.schedule_engine.get_today_schedule()

        if command == "adjust":
            if not args.strip():
                return (
                    "*Usage:* /adjust [what's changing]\n"
                    "Examples:\n"
                    "`/adjust in commute til noon`\n"
                    "`/adjust sleep early tonight, wrap up by 9PM`\n"
                    "`/adjust push LazySun block to tomorrow`"
                )
            return await self.schedule_engine.adjust_schedule(args.strip(), self.ai)

        if command == "free":
            return self.calendar.get_free_slots()

        if command == "schedule":
            days = int(args.strip()) if args.strip().isdigit() else 3
            return self.calendar.get_schedule(days=days)

        # ── Career commands ────────────────────────────────────────────
        if command == "kyn":
            result = self.career.score_job(args)
            return result.format_telegram()

        if command == "analyze":
            raw_input = args.strip()

            # URL detection — fetch via Firecrawl if input is a URL
            from core.url_fetcher import detect_platform, fetch_job_post, is_fetch_error, is_url
            detected_platform = "analyzed"
            if is_url(raw_input):
                detected_platform = detect_platform(raw_input)
                fetched = await fetch_job_post(raw_input)
                if is_fetch_error(fetched):
                    from core.url_fetcher import fetch_error_message
                    return fetch_error_message(fetched)
                job_text = fetched
            else:
                job_text = raw_input

            if len(job_text) < 50:
                return "Paste the full job post after /analyze (or a valid job URL)"

            pkg = await self.career.analyze_job(job_text)

            # Cache KYN score for /track
            self._last_kyn["last"] = pkg.kyn.score

            # Auto-log to APPLICATIONS
            employer, role = self.career.extract_employer_role(job_text)
            today = datetime.date.today()
            try:
                self.sheets.append_row("APPLICATIONS", {
                    "Date": today.isoformat(),
                    "Platform": detected_platform,
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

            # Update skill frequency + detect newly elevated skills
            newly_elevated: list[str] = []
            if pkg.kyn.matched_skills:
                try:
                    newly_elevated = self.skills.update_skill_frequency(pkg.kyn.matched_skills)
                except Exception as e:
                    logger.warning(f"Skill frequency update failed: {e}")

            response = pkg.format_telegram()

            # Weak-skill flag (primary requirement is a known weak area)
            flag = self.career.check_weak_skill_flag(job_text)
            if flag:
                response += f"\n\n{flag}"

            # New priority skill notification — show max 2, summarize overflow
            if newly_elevated:
                shown = newly_elevated[:2]
                overflow = len(newly_elevated) - len(shown)
                for skill in shown:
                    response += (
                        f"\n\n📚 New priority skill: *{skill}* now appears in 3+ analyzed jobs. "
                        f"Run `/learn {skill}` for a learning path."
                    )
                if overflow > 0:
                    response += f"\n+{overflow} more priority skills elevated — run `/gaps` to see all."

            return response

        if command == "apply":
            raw_input = args.strip()
            from core.url_fetcher import detect_platform, fetch_job_post, is_fetch_error, is_url
            if is_url(raw_input):
                fetched = await fetch_job_post(raw_input)
                if is_fetch_error(fetched):
                    from core.url_fetcher import fetch_error_message
                    return fetch_error_message(fetched)
                job_text = fetched
            else:
                job_text = raw_input
            if len(job_text) < 50:
                return "Paste the full job post after /apply (or a valid job URL)"
            pkg = await self.career.analyze_job(job_text)
            return f"*Application Package*\n\n{pkg.format_telegram()}"

        if command == "reply":
            if not args.strip():
                return (
                    "*Usage:* /reply [paste message content]\n"
                    "Example: `/reply Hi Lebron, are you ready for Monday? — Jordan`"
                )
            return await self.reply.draft_reply(args.strip(), self.ai)

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
            if not args.strip():
                # Phase 7: save last ecommerce output to knowledge base
                if not self._last_output:
                    return (
                        "Nothing to log. Run an ecommerce command first (`/pdp`, `/meta`, `/tiktok`, `/reel`, etc.)\n"
                        "Or: `/log [skill] [notes]` to log learning progress"
                    )
                task_dir = self._knowledge.save_task(
                    self._last_output["agent"],
                    self._last_output["request"],
                    self._last_output["output"],
                )
                return (
                    f"Saved to knowledge base: `{task_dir.name}`\n"
                    f"Reply `/feedback [your notes]` to record what worked."
                )
            # Legacy: /log [skill] [notes] for learning
            parts = args.split(" ", 1)
            if len(parts) < 2:
                return "Usage: `/log [skill] [notes]` or `/log` (no args) to save last ecommerce output"
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

        # ── Phase 7: Ecommerce AI Team ─────────────────────────────────
        if command == "pdp":
            if not args.strip():
                return (
                    "*Usage:* `/pdp [product info]`\n"
                    "Include: product name, price, material, key story/reference\n"
                    "Add `revision:` prefix to revise existing copy."
                )
            is_revision = args.strip().lower().startswith("revision:")
            info = args.strip()[9:].strip() if is_revision else args.strip()
            result = await self.pdp.write_pdp(info, self.ai, is_revision=is_revision)
            self._last_output = {"agent": "pdp", "request": args.strip(), "output": result}
            return result

        if command == "photoreview":
            if not args.strip():
                return "*Usage:* `/photoreview [image url] [optional context]`"
            parts = args.strip().split(" ", 1)
            url = parts[0]
            context_note = parts[1] if len(parts) > 1 else ""
            if not url.startswith(("http://", "https://")):
                return "Provide a direct image URL (ending in .jpg/.png etc.). Or send a photo in chat for Telegram review."
            result = await self.photo_qa.review_from_url(url, context_note, self.ai)
            self._last_output = {"agent": "photo_qa", "request": args.strip(), "output": result}
            return result

        if command == "tiktok":
            if not args.strip():
                return (
                    "*Usage:* `/tiktok [product info]`\n"
                    "Include: product name, price, key detail, own-label or brand name"
                )
            result = await self.tiktok_shop.write_listing(args.strip(), self.ai)
            self._last_output = {"agent": "tiktok", "request": args.strip(), "output": result}
            return result

        if command == "meta":
            if not args.strip():
                return (
                    "*Usage:* `/meta [product info]`\n"
                    "Include: product name, price, key benefit, AOV (for budget tier)"
                )
            result = await self.meta_ads.write_ads(args.strip(), self.ai)
            self._last_output = {"agent": "meta_ads", "request": args.strip(), "output": result}
            return result

        if command == "contentcal":
            if not args.strip():
                return (
                    "*Usage:* `/contentcal [brief]`\n"
                    "Include: month, active products, any email campaigns planned"
                )
            result = await self.content_cal.build_calendar(args.strip(), self.ai)
            self._last_output = {"agent": "content_cal", "request": args.strip(), "output": result}
            return result

        if command == "emailaudit":
            brief = args.strip() or "No existing flow info — assume standard Shopify Email defaults."
            result = await self.email_audit.audit(brief, self.ai)
            self._last_output = {"agent": "email_audit", "request": brief, "output": result}
            return result

        if command == "reel":
            if not args.strip():
                return (
                    "*Usage:* `/reel [brief]`\n"
                    "Include: product/subject, platform (Reels/TikTok), tone, any specific moment to capture"
                )
            result = await self.reel.write_reel(args.strip(), self.ai)
            self._last_output = {"agent": "reel", "request": args.strip(), "output": result}
            return result

        if command == "toggl":
            if not args.strip():
                return (
                    "*Usage:* `/toggl [task description] [optional: Xmin]`\n"
                    "Examples:\n"
                    "`/toggl Updated PDP copy for Saturday Pants`\n"
                    "`/toggl Jordan call 45min`"
                )
            # Parse optional duration
            parts = args.rsplit(" ", 1)
            duration_min = 30
            desc = args.strip()
            if len(parts) == 2 and parts[1].lower().endswith("min") and parts[1][:-3].isdigit():
                duration_min = int(parts[1][:-3])
                desc = parts[0].strip()
            return await self.toggl.log_time(desc, duration_min)

        if command == "hours":
            return await self.toggl.get_hours()

        if command == "togglreport":
            return await self.toggl.get_report()

        if command == "feedback":
            if not args.strip():
                return (
                    "*Usage:* `/feedback [your notes on what worked / what to change]`\n"
                    "Run after reviewing AI output — saves final version + extracts lessons."
                )
            agent_name = self._last_output["agent"] if self._last_output else "unknown"
            self._knowledge.save_final(agent_name, args.strip())

            extract_prompt = f"""Extract actionable lessons from this creative feedback.

Feedback: {args.strip()}

Output EXACTLY (no extra text):
LESSON: [one specific, reusable lesson for future work]
JORDAN_FEEDBACK: [any "avoid X" or "prefer Y" pattern Jordan expressed, or NONE]"""

            extracted = await self.ai.chat(
                "You extract concise lessons from creative work feedback. Be specific.",
                extract_prompt,
                max_tokens=150,
            )

            lesson = ""
            jordan_fb = ""
            for line in extracted.splitlines():
                if line.startswith("LESSON:"):
                    lesson = line.replace("LESSON:", "").strip()
                elif line.startswith("JORDAN_FEEDBACK:") and "none" not in line.lower():
                    jordan_fb = line.replace("JORDAN_FEEDBACK:", "").strip()

            if lesson:
                self._knowledge.append_lesson(lesson)
            if jordan_fb:
                self._knowledge.append_jordan_feedback(jordan_fb)

            msg = "Feedback saved."
            if lesson:
                msg += f"\nLesson noted: _{lesson}_"
            if jordan_fb:
                msg += f"\nJordan preference: _{jordan_fb}_"
            return msg

        # ── System ─────────────────────────────────────────────────────
        if command in ("start", "help"):
            return self._help_text()

        return f"Unknown command: `/{command}`\n\n{self._help_text()}"

    def _help_text(self) -> str:
        return (
            "*LJR.devOS* — Lebron's AI Operating System\n\n"
            "*📱 DAILY:*\n"
            "`/overview` — your day in one screen\n"
            "`/today` — today's schedule (fixed + flex blocks)\n"
            "`/adjust [text]` — mid-day schedule adjustment\n"
            "`/reply [message]` — draft 3 tone variants for any message\n"
            "`/applications` — application pipeline\n"
            "`/free` — free slots ≥30min (Google Calendar)\n"
            "`/schedule` — next 3 days calendar view\n\n"
            "*Career:*\n"
            "`/apply [url or post]` — Full pipeline + confirm gate (logs to Sheets)\n"
            "`/analyze [url or post]` — Quick analysis + cover letter (auto-logs)\n"
            "`/kyn [post]` — KYN score only\n"
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
            "`/morning` — Morning briefing\n\n"
            "*🛍️ ECOMMERCE AI TEAM:*\n"
            "`/pdp [product info]` — Write full Shopify PDP (9 sections)\n"
            "`/photoreview [url]` — QA product photo (PASS/NEEDS REVISION/FAIL)\n"
            "`/tiktok [product info]` — TikTok Shop title, hashtags, keywords\n"
            "`/meta [product info]` — Meta ads (4 angles, ASC structure)\n"
            "`/contentcal [brief]` — 4-week content calendar\n"
            "`/emailaudit [flow info]` — Audit 5 email flows\n"
            "`/reel [brief]` — Reel/TikTok script + CapCut instructions\n\n"
            "*⏱️ TIME TRACKING:*\n"
            "`/toggl [description] [Xmin]` — Log time to Toggl\n"
            "`/hours` — This week's hours vs 20hr target\n"
            "`/togglreport` — Jordan-ready weekly summary\n\n"
            "*📚 KNOWLEDGE LOOP:*\n"
            "`/log` — Save last ecommerce output to knowledge base\n"
            "`/log [skill] [notes]` — Log learning progress\n"
            "`/feedback [notes]` — Record what worked, extract lessons"
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
