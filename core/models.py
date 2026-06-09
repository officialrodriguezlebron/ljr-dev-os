from dataclasses import dataclass, field
from typing import Optional


@dataclass
class KYNResult:
    score: int
    verdict: str  # "apply" | "skip" | "ask_questions"
    rate_signal: str
    employer_signal: str
    fit_signal: str
    pakwan_pass: bool
    flags: list[str]
    hidden_instruction: Optional[str]
    rate_usd_hourly: Optional[float]

    def format_telegram(self) -> str:
        verdict_emoji = {"apply": "✅", "ask_questions": "⚠️", "skip": "❌"}.get(
            self.verdict, "❓"
        )
        pakwan_emoji = "✅" if self.pakwan_pass else "🚩"
        flags_text = "\n".join(f"  • {f}" for f in self.flags) if self.flags else "  None"
        rate_text = f"${self.rate_usd_hourly:.2f}/hr" if self.rate_usd_hourly else "Not stated"
        hidden_text = f"\n🕵️ *Hidden:* `{self.hidden_instruction}`" if self.hidden_instruction else ""

        return (
            f"*KYN Score: {self.score}/100* {verdict_emoji}\n\n"
            f"💰 *Rate:* {rate_text} — {self.rate_signal}\n"
            f"🏢 *Employer:* {self.employer_signal}\n"
            f"🎯 *Fit:* {self.fit_signal}\n"
            f"🍱 *Pakwan Pass:* {pakwan_emoji}\n\n"
            f"🚩 *Flags:*\n{flags_text}"
            f"{hidden_text}\n\n"
            f"*Verdict: {self.verdict.replace('_', ' ').upper()}*"
        )


@dataclass
class ApplicationPackage:
    kyn: KYNResult
    employer_research: str
    proof_points: list[str]
    subject: str
    message: str
    rate_anchor: str
    gaps: list[str]

    def format_telegram(self) -> str:
        proofs = "\n".join(f"• {p}" for p in self.proof_points[:3])
        gaps_text = ", ".join(self.gaps) if self.gaps else "None identified"
        return (
            f"{self.kyn.format_telegram()}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 *Subject:* {self.subject}\n\n"
            f"*Proof Points Used:*\n{proofs}\n\n"
            f"*Rate Anchor:* {self.rate_anchor}\n"
            f"*Gaps to Address:* {gaps_text}\n\n"
            f"*Message:*\n{self.message}"
        )


@dataclass
class SkillGap:
    name: str
    frequency: int
    priority: bool
    resource: str
    current_level: str = "none"

    def format_telegram(self) -> str:
        priority_emoji = "🔴" if self.priority else "🟡"
        return f"{priority_emoji} *{self.name}* — seen {self.frequency}x | {self.resource}"


@dataclass
class Task:
    title: str
    duration_min: int
    reason: str
    action: str
    priority: int

    def format_telegram(self) -> str:
        return (
            f"*{self.priority}. {self.title}* ({self.duration_min} min)\n"
            f"   Why: {self.reason}\n"
            f"   → {self.action}"
        )


@dataclass
class LearningPath:
    skill: str
    weeks: int
    resources: list[str]
    milestones: list[str]
    proof_project: str

    def format_telegram(self) -> str:
        resources_text = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(self.resources))
        milestones_text = "\n".join(f"  Week {i+1}: {m}" for i, m in enumerate(self.milestones))
        return (
            f"📚 *{self.skill} Learning Path ({self.weeks} weeks)*\n\n"
            f"*Resources:*\n{resources_text}\n\n"
            f"*Milestones:*\n{milestones_text}\n\n"
            f"*Proof Project:* {self.proof_project}"
        )


@dataclass
class Profile:
    name: str
    school: str
    income_current: str
    income_target: str
    top_skills: list[str]
    proof_points: list[str]
    gaps: list[str]
    applications_sent: int
    response_rate: float
    active_projects: list[str]

    def format_telegram(self) -> str:
        skills_text = " · ".join(self.top_skills[:5])
        proofs_text = "\n".join(f"• {p}" for p in self.proof_points[:3])
        projects_text = " · ".join(self.active_projects)
        return (
            f"👤 *{self.name}*\n"
            f"🎓 {self.school}\n\n"
            f"💰 Income: {self.income_current} → {self.income_target}\n"
            f"📊 Applications: {self.applications_sent} sent | "
            f"{self.response_rate:.0%} response rate\n\n"
            f"⚡ *Top Skills:* {skills_text}\n\n"
            f"🏆 *Proof:*\n{proofs_text}\n\n"
            f"🔨 *Building:* {projects_text}"
        )
