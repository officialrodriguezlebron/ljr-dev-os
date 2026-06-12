import datetime
import re
from pathlib import Path

import core.resume_parser as parser
from core.groq_client import AIClient as GroqClient
from core.kyn_engine import KYNEngine
from core.models import ApplicationPackage, KYNResult
from core.sheets_client import SheetsClient

RESUME_PATH = Path("master_resume.md")

SYSTEM_PROMPT = """You are CareerOS, a job application specialist for Lebron Rodriguez.
You apply the Molongski Method: Intentional Freelancing, not "Basta Basta" (random, thoughtless action).

Lebron: Shopify developer and AI VA from the Philippines, targeting remote roles on OLJ, Upwork, and LinkedIn.
Business mindset: he is offering expertise, not asking for a favor.

WRITING RULES (non-negotiable):
- No em dashes. Commas, periods, or simple connectors only.
- No "Dear Hiring Manager." No "I am writing to express my interest."
- No vague openers about industry trends or competitive markets.
- NEVER write any of these phrases or close variants:
    "resonates with my skills/experience"
    "I am confident that"
    "I am excited to" or "excited about the opportunity"
    "I believe I would be a great fit"
    "my expertise can help"
    "hardworking," "dedicated," "detail-oriented"
    "Please find attached my resume"
    "In today's competitive market"
    "passionate about"
- Every sentence must be inseparable from THIS specific post. If a sentence could be copied
  into a different job application unchanged, it is too generic and must be rewritten.
- Rate is always pre-supplied. USE IT EXACTLY. Never round, substitute, or invent a different number.
- Tone: confident, peer-level, direct. Talking to a business partner, not an authority.
- On OLJ/Upwork casual posts: ending with "wink" is fine as a pattern interrupt.
  On formal/corporate posts: skip it.

SELF-CHECK (run this before outputting):
Read your draft. Remove the company name and job-specific details mentally.
Could this letter work for a completely different job? If yes, the Hook and Bridge are still
too generic. Rewrite them until they are inseparable from this specific post."""

COVER_LETTER_PROMPT = """Write a Molongski-Method cover letter for this job post.

PROFILE:
{resume}

JOB POST:
{post}

KYN ANALYSIS:
Score: {score}/100
Rate Signal: {rate_signal}
Employer Signal: {employer_signal}
Skill Fit: {fit_signal}
Gaps: {gaps}
Rate: {rate_anchor}. USE THIS EXACT RATE. Never write a different number.

STEP 1: REASON SILENTLY before writing anything.
Work through these 4 questions about THIS specific post:
  Q1. What is the ONE most specific, concrete detail in this post?
      (a tool name, a number, a deliverable, a phrase that reveals what they actually care about)
  Q2. What is the underlying operational problem behind their stated need?
      (not "they need a VA" but the actual pain causing that need: scaling chaos, catalog inconsistency,
       owner doing everything manually, etc.)
  Q3. Which ONE of Lebron's proof points most directly solves that problem?
      (specific project plus specific result, not generic "Shopify experience")
  Q4. What is ONE free, concrete insight about their situation that only someone who actually
      understands their domain and read this post would say?

STEP 2: WRITE using only what that reasoning produced.

HOOK (first 1-2 sentences):
  MUST reference the specific detail from Q1. Quote their phrase, name their tool, or state
  their exact need back to them. Never open with generalities. Lead with what Lebron can do
  for THEM in their specific situation.

BRIDGE (1-2 sentences):
  Connect the proof point from Q3 directly to the problem from Q2.
  Format: "I did [specific thing] for [specific project], which resulted in [specific outcome/number]."
  One story, tightly connected to the Hook. No resume dump.

VALUE/TIP (1-2 sentences):
  Give away the insight from Q4. It must sound like something only someone who read this post
  and knows this domain would say. This shifts Lebron from applicant to expert advisor.

GAPS (1 sentence, include ONLY if a real gap exists for this specific role):
  "Currently building [X] skills, two-week ramp to full proficiency."
  If there is no gap, omit this section entirely. Do not write a filler gaps sentence.

RATE:
  "My rate for this is {rate_anchor}." Use rate_anchor verbatim. No rounding, no substitution.

CTA (Calendar Method):
  Offer exactly 2 specific time slots. Never "available anytime" or "let me know your schedule."
  Format: "Free [Day] [time] or [Day] [time] for a quick call?"

SIGN-OFF:
  Warm, brief. Match the formality level of the post.
  "wink" acceptable on casual OLJ/Upwork posts. Skip on formal posts.

OUTPUT (this exact format, do not change the delimiters):
Subject: [one punchy, benefit-focused subject line, no "Application for"]
---
[cover letter body, max 200 words, no em dashes, components in order: Hook, Bridge, Value/Tip, Gaps if needed, Rate, CTA, Sign-off]
---
Rate Anchor: {rate_anchor}"""


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
            rate_anchor=rate_anchor_default,
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

    def check_weak_skill_flag(self, post: str) -> str | None:
        """
        Returns a warning string if the job's PRIMARY requirement is a known weak skill,
        else None. 'Primary' = appears in the opening 300 chars OR mentioned 3+ times.
        """
        post_lower = post.lower()
        opening = post_lower[:300]

        weak_groups = [
            (
                "mobile app development",
                ["mobile app", "mobile developer", "mobile development",
                 "react native", "flutter", "ios dev", "android dev", "ios app", "android app"],
            ),
            (
                "Meta Ads / Facebook Ads",
                ["meta ads", "facebook ads", "facebook advertising", "instagram ads",
                 "paid social", "fb ads"],
            ),
            (
                "Cloud / DevOps",
                ["devops engineer", "cloud engineer", "cloud infrastructure",
                 "kubernetes", "docker swarm", "aws engineer", "azure engineer", "gcp engineer"],
            ),
        ]

        for label, keywords in weak_groups:
            for kw in keywords:
                if kw in opening or post_lower.count(kw) >= 3:
                    return (
                        f"⚠️ Note: this role's primary requirement ({label}) is outside "
                        f"your current strengths — consider if worth the application time"
                    )
        return None

    async def generate_followup(self, employer: str) -> str:
        prompt = f"""Write a Molongski follow-up message to {employer}.
Lebron applied 7 days ago and has not heard back.

Rules:
- Under 80 words total
- Brief, professional, forward-looking — zero desperation
- Reference the specific role applied to if known from the employer name
- Add one line of new value (a relevant insight, a quick result, or a genuine observation)
- End with a clear, low-friction question
- No em dashes
- No "I just wanted to check in" or "I know you are busy"

Subject line plus message body."""
        return await self.groq.chat(SYSTEM_PROMPT, prompt, max_tokens=150)

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
