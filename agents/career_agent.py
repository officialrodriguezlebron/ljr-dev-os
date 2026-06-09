import datetime
from pathlib import Path

from core.groq_client import GroqClient
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
- Anchor rate at $7-10/hr for Shopify, $5-7/hr for eCommerce VA
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

    async def analyze_job(self, post: str) -> ApplicationPackage:
        kyn_result = self.kyn.score(post)

        proof_points = [
            "LuxeWear: 95 Lighthouse, 100 SEO, 12 CRO features — zero base theme",
            "Unicharm: TikTok Shop ops, 500+ concurrent viewers, 30% sales lift",
            "VXI: 93.88% CSAT, 80-100 tickets/day, 120% quota exceeded",
            "RutaSmart: React 18 + FastAPI thesis, defense passed Mar 7 2026",
            "CareerOS: 14+ Telegram commands, KYN engine, Sheets pipeline",
        ]

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
        rate_anchor = "$7-10/hr depending on scope"
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
            follow_up_date = str(row.get("Follow-up Date", "")).strip()
            if not follow_up_date:
                continue
            try:
                due_date = datetime.date.fromisoformat(follow_up_date)
                if due_date <= today:
                    due.append(row)
            except ValueError:
                continue
        return due

    def format_followups_telegram(self) -> str:
        due = self.check_followups()
        if not due:
            return "✅ No follow-ups due today."
        lines = [f"📬 *{len(due)} follow-up(s) due:*\n"]
        for row in due:
            lines.append(
                f"• *{row.get('Employer', '?')}* — {row.get('Role', '?')} "
                f"({row.get('Platform', '?')}) — sent {row.get('Date', '?')}"
            )
        return "\n".join(lines)

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
            f"📊 *Application Stats*\n\n"
            f"Total sent: {total}\n"
            f"Active applications: {applied}\n"
            f"Replies received: {replied} ({rate:.0f}%)\n"
            f"Offers: {offers}\n"
        )
