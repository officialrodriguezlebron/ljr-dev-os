import datetime
import re
from pathlib import Path

import core.resume_parser as parser
from core.groq_client import AIClient as GroqClient
from core.kyn_engine import KYNEngine
from core.models import ApplicationPackage, KYNResult
from core.sheets_client import SheetsClient

RESUME_PATH = Path("master_resume.md")

SYSTEM_PROMPT = """You are CareerOS — a job application specialist for
Lebron Rodriguez, a Shopify developer and AI VA from the Philippines.

You analyze job posts using the Molongski Method and generate cover letters
that lead with proof, anchor rates, and address gaps honestly.

Rules:
- Lead with one specific proof point (number + outcome)
- Anchor rate at $8-10/hr for Shopify, $7-10/hr for general dev, $5-7/hr for eCommerce VA
- Never say "I am a quick learner" — show learning via proof
- Address gaps head-on: "I'm currently building X, 2-week ramp"
- Max 3 short paragraphs — no walls of text
- Be direct and confident, not desperate"""

COVER_LETTER_PROMPT = """Generate a short, powerful cover letter for this job post.

Profile: {resume}

Job Post:
{post}

KYN Score: {score}/100
Rate Signal: {rate_signal}
Employer Signal: {employer_signal}
Skill Fit: {fit_signal}
Gaps to address: {gaps}

Format:
Subject: [one punchy line]
---
[Cover letter body — max 3 paragraphs, 150 words total]
---
Rate Anchor: [state your rate confidently]"""


class CareerAgent:
    def __init__(self, sheets: SheetsClient, groq: GroqClient) -> None:
        self.sheets = sheets
        self.groq = groq
        self.kyn = KYNEngine()
        self._resume = RESUME_PATH.read_text(encoding="utf-8")

    def score_job(self, post: str) -> KYNResult:
        return self.kyn.score(post)

    def extract_employer_role(self, post: str) -> tuple[str, str]:
        """Best-effort extract employer name and role title from raw job post text."""
        employer = "Unknown"
        role = "Unknown"

        employer_patterns = [
            r"(?:company|employer|client|we are|we're|hi,?\s+i'm|my name is)\s*:?\s*([A-Z][a-zA-Z0-9\s&'.,-]{2,35}?)(?:\.|,|\n|$)",
            r"(?:at|join)\s+([A-Z][a-zA-Z0-9\s&'.]{2,30}?)\s*[,.\n]",
            r"^([A-Z][a-zA-Z0-9\s&'.]{2,30})\s+is\s+(?:looking|hiring|seeking)",
        ]
        for pat in employer_patterns:
            m = re.search(pat, post, re.IGNORECASE | re.MULTILINE)
            if m:
                candidate = m.group(1).strip().rstrip(".,")
                if 2 < len(candidate) < 40 and not candidate.lower().startswith(("i ", "we ", "the ")):
                    employer = candidate
                    break

        role_patterns = [
            r"(?:position|role|title|looking for|hiring a?|need a?)\s*:?\s*([A-Za-z][a-zA-Z\s\-/]{3,45}?)(?:\.|,|\n|$)",
            r"([A-Za-z][a-zA-Z\s\-/]{3,40})\s+(?:needed|wanted|required|role|position)\b",
        ]
        for pat in role_patterns:
            m = re.search(pat, post, re.IGNORECASE | re.MULTILINE)
            if m:
                candidate = m.group(1).strip().rstrip(".,")
                if 3 < len(candidate) < 50:
                    role = candidate
                    break

        return employer[:40], role[:50]

    async def analyze_job(self, post: str) -> ApplicationPackage:
        kyn_result = self.kyn.score(post)

        # Dynamic proof points from master_resume.md
        proof_raw = parser.get_proof_points()
        proof_points = [
            f"{p['title'].split('—')[0].strip()}: {p['result']}"
            for p in proof_raw
        ]

        # Dynamic rate anchor based on job type
        post_lower = post.lower()
        if "shopify" in post_lower:
            rate_anchor_default = parser.get_rate_anchor("shopify")
        elif "ai va" in post_lower or "ai operator" in post_lower:
            rate_anchor_default = parser.get_rate_anchor("ai va")
        elif "tiktok" in post_lower:
            rate_anchor_default = parser.get_rate_anchor("tiktok")
        else:
            rate_anchor_default = parser.get_rate_anchor("ecommerce va")

        prompt = COVER_LETTER_PROMPT.format(
            resume=self._resume[:2000],
            post=post[:1500],
            score=kyn_result.score,
            rate_signal=kyn_result.rate_signal,
            employer_signal=kyn_result.employer_signal,
            fit_signal=kyn_result.fit_signal,
            gaps=", ".join(kyn_result.flags[:3]) or "none",
        )

        raw = await self.groq.chat(SYSTEM_PROMPT, prompt, max_tokens=500)
        lines = raw.strip().split("\n")

        subject = ""
        message_lines = []
        rate_anchor = rate_anchor_default
        in_body = False

        for line in lines:
            if line.lower().startswith("subject:"):
                subject = line.split(":", 1)[1].strip()
            elif line.strip() == "---":
                in_body = not in_body
            elif line.lower().startswith("rate anchor:"):
                rate_anchor = line.split(":", 1)[1].strip()
            elif in_body:
                message_lines.append(line)

        return ApplicationPackage(
            kyn=kyn_result,
            employer_research=kyn_result.employer_signal,
            proof_points=proof_points,
            subject=subject or "Shopify Developer — LuxeWear 95 Lighthouse",
            message="\n".join(message_lines).strip() or raw,
            rate_anchor=rate_anchor,
            gaps=kyn_result.flags,
        )

    async def generate_followup(self, employer: str) -> str:
        prompt = f"""Write a short 2-sentence follow-up message to {employer}.
        Lebron applied 7 days ago. Polite, confident, not desperate.
        End with a clear call to action."""
        return await self.groq.chat(SYSTEM_PROMPT, prompt, max_tokens=100)

    def check_followups(self) -> list[dict]:
        try:
            apps = self.sheets.read_tab("APPLICATIONS")
        except Exception:
            return []
        today = datetime.date.today()
        due = []
        for row in apps:
            if str(row.get("Replied", "")).lower() == "yes":
                continue
            fu_date = str(row.get("Follow-up Date", "")).strip()
            if not fu_date:
                continue
            try:
                if datetime.date.fromisoformat(fu_date) <= today:
                    due.append(row)
            except ValueError:
                continue
        return due

    def format_followups_telegram(self) -> str:
        due = self.check_followups()
        if not due:
            return "No follow-ups due today."
        lines = [f"*{len(due)} follow-up(s) due:*\n"]
        for row in due:
            lines.append(
                f"• *{row.get('Employer', '?')}* — {row.get('Role', '?')} "
                f"({row.get('Platform', '?')}) — sent {row.get('Date', '?')}"
            )
        return "\n".join(lines)

    def format_applications_compact(self) -> str:
        try:
            apps = self.sheets.read_tab("APPLICATIONS")
        except Exception:
            return "Could not read Applications sheet."
        today = datetime.date.today()
        total = len(apps)
        applied = sum(1 for r in apps if str(r.get("Status", "")).lower() in ("applied", "ready to apply"))
        interview = sum(1 for r in apps if "interview" in str(r.get("Status", "")).lower())
        replied_count = sum(1 for r in apps if str(r.get("Replied", "")).lower() == "yes")
        rejected = sum(1 for r in apps if "reject" in str(r.get("Status", "")).lower())

        lines = [f"📊 APPLICATIONS ({total} total)\n"]
        lines.append(f"Applied: {applied} | Interview: {interview} | Replied: {replied_count} | Rejected: {rejected}\n")

        due = self.check_followups()
        if due:
            lines.append("📬 FOLLOW-UPS DUE")
            for row in due[:3]:
                employer = row.get("Employer", "?")
                fu_raw = str(row.get("Follow-up Date", "")).strip()
                try:
                    days = (today - datetime.date.fromisoformat(fu_raw)).days
                    days_str = f"{days}d overdue" if days > 0 else "due today"
                except ValueError:
                    days_str = "check date"
                lines.append(f"• {employer} — {days_str}")
            lines.append("")

        from collections import defaultdict
        p_total: dict = defaultdict(int)
        p_replied: dict = defaultdict(int)
        for row in apps:
            p = str(row.get("Platform", "")).strip()
            if not p:
                continue
            p_total[p] += 1
            if str(row.get("Replied", "")).lower() == "yes":
                p_replied[p] += 1
        if p_total:
            rates = {p: p_replied[p] / p_total[p] * 100 for p in p_total}
            best = max(rates, key=rates.__getitem__)
            lines.append(f"🎯 Best platform: {best} ({rates[best]:.0f}%)")

        result = "\n".join(lines).strip()
        return result[:600] if len(result) > 600 else result

    def get_stats(self) -> str:
        try:
            apps = self.sheets.read_tab("APPLICATIONS")
        except Exception:
            return "Could not read Applications sheet."
        total = len(apps)
        applied = sum(1 for r in apps if str(r.get("Status", "")).lower() == "applied")
        replied = sum(1 for r in apps if str(r.get("Replied", "")).lower() == "yes")
        offers = sum(1 for r in apps if str(r.get("Offer", "")).strip())
        rate = (replied / total * 100) if total > 0 else 0
        return (
            f"*Application Stats*\n\n"
            f"Total sent: {total}\n"
            f"Active applications: {applied}\n"
            f"Replies received: {replied} ({rate:.0f}%)\n"
            f"Offers: {offers}"
        )
