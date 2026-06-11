import datetime
import logging
from typing import Any

logger = logging.getLogger(__name__)


class OverviewAgent:
    def get_overview(self, sheets: Any) -> str:
        today = datetime.date.today()
        date_str = today.strftime("%a, %b") + " " + str(today.day)
        parts = [f"📊 TODAY — {date_str}\n"]

        # Applications block
        try:
            apps = sheets.read_tab("APPLICATIONS")
            applied = sum(1 for r in apps if str(r.get("Status", "")).lower() in ("applied", "ready to apply"))
            interview = sum(1 for r in apps if "interview" in str(r.get("Status", "")).lower())
            replied = sum(1 for r in apps if str(r.get("Replied", "")).lower() == "yes")

            followups_due = 0
            for row in apps:
                if str(row.get("Replied", "")).lower() == "yes":
                    continue
                fu_raw = str(row.get("Follow-up Date", "")).strip()
                if not fu_raw:
                    continue
                try:
                    if datetime.date.fromisoformat(fu_raw) <= today:
                        followups_due += 1
                except ValueError:
                    continue

            parts.append(f"Applications: {applied} applied | {interview} interview | {replied} replied")
            parts.append(f"Follow-ups due: {followups_due}\n")

            lazysun = [
                r for r in apps
                if "jordan" in str(r.get("Employer", "")).lower()
                or "lazysun" in str(r.get("Employer", "")).lower()
            ]
            if lazysun and not any(str(r.get("Replied", "")).lower() == "yes" for r in lazysun):
                parts.append("⚠️ LazySun: awaiting reply\n")
        except Exception as e:
            logger.warning(f"Overview: apps read failed: {e}")
            parts.append("Applications: unavailable\n")

        # Active projects block (top 2)
        try:
            projects = sheets.read_tab("PROJECTS")
            active = [r for r in projects if str(r.get("Status", "")).lower() not in ("done", "paused")][:2]
            for r in active:
                name = str(r.get("Project", "?"))
                task = str(r.get("Next Task", "TBD"))[:40]
                parts.append(f"🚀 {name}: {task}")
            if active:
                parts.append("")
        except Exception as e:
            logger.warning(f"Overview: projects read failed: {e}")

        # Top skill gap
        try:
            skills = sheets.read_tab("SKILLS")
            gaps = [r for r in skills if str(r.get("Gap", "")).lower() in ("yes", "true", "1")]
            gaps_sorted = sorted(gaps, key=lambda r: int(r.get("Frequency", 0) or 0), reverse=True)
            if gaps_sorted:
                top = gaps_sorted[0]
                freq = top.get("Frequency", "?")
                parts.append(f"📚 Top gap: {top.get('Skill', '?')} ({freq}x)")
        except Exception as e:
            logger.warning(f"Overview: skills read failed: {e}")

        result = "\n".join(parts).strip()
        return result[:800] if len(result) > 800 else result
