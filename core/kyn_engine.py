import re
from typing import Optional
from core.models import KYNResult

LEBRON_SKILLS = {
    "shopify", "liquid", "html", "css", "javascript", "js",
    "tiktok shop", "tiktok", "shopee", "facebook live", "fb live",
    "claude", "chatgpt", "cursor", "midjourney", "ai",
    "n8n", "zapier", "heygen", "synthesia",
    "react", "next.js", "nextjs", "python", "fastapi",
    "postgresql", "postgres", "git", "github", "canva",
    "customer service", "seo", "cro", "conversion",
    "google analytics", "google workspace", "google sheets",
    "ecommerce", "e-commerce", "dropshipping", "print on demand",
    "typescript", "tailwind", "vercel",
}

PAKWAN_PHRASES = [
    "right pay for the right person",
    "competitive salary",
    "unlimited earning potential",
    "not payable",
    "penalty",
    "will be deducted",
    "for exposure",
    "build your portfolio",
    "unpaid trial",
    "test task",
    "no pay for training",
]

STRONG_EMPLOYER_SIGNALS = [
    "registered business",
    "established company",
    "years in business",
    "ceo", "founder", "director",
    "we have a team",
    "full-time",
    "long-term",
]

WEAK_EMPLOYER_SIGNALS = [
    "small business owner",
    "just starting",
    "startup",
    "first time hiring",
    "budget is flexible",
    "let me know your rate",
]

RATE_PATTERN = re.compile(
    r"""
    (?:
        \$\s?(\d+(?:\.\d+)?)\s?(?:/\s?hr|/\s?hour|per\s+hour|hourly)
        |
        usd\s?(\d+(?:\.\d+)?)\s?(?:/\s?hr|/\s?hour|per\s+hour)?
        |
        (\d+(?:\.\d+)?)\s?(?:usd|dollars?)\s?(?:/\s?hr|per\s+hour)?
        |
        \$\s?(\d+)\s?-\s?\$?\s?(\d+)\s?(?:/\s?hr|/\s?hour|per\s+hour)
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

MONTHLY_PATTERN = re.compile(
    r"\$\s?(\d{3,5})\s?(?:/\s?month|per\s+month|monthly|/mo)",
    re.IGNORECASE,
)

HIDDEN_PATTERN = re.compile(
    r'(?:start|begin|open)\s+(?:your|the)\s+(?:message|application|cover letter|reply)\s+with\s+["\']?(\w[\w\s]+)["\']?',
    re.IGNORECASE,
)
HIDDEN_PATTERN2 = re.compile(
    r'(?:mention|include|write|put|use)\s+["\']?([A-Z][a-zA-Z\s]{2,30})["\']?\s+(?:at the (?:top|start|beginning)|in your (?:message|application))',
    re.IGNORECASE,
)


class KYNEngine:
    def score(self, post: str) -> KYNResult:
        post_lower = post.lower()
        flags: list[str] = []

        rate = self._extract_rate(post)
        rate_signal = self._rate_signal(rate, flags)

        employer_signal = self._employer_signal(post_lower)
        fit_signal, fit_score = self._fit_signal(post_lower)
        pakwan_pass, pakwan_flags = self._pakwan_test(post_lower)
        flags.extend(pakwan_flags)
        hidden = self._hidden_instruction(post)

        score = self._calculate_score(rate, employer_signal, fit_score, pakwan_pass)
        verdict = self._verdict(score, pakwan_pass, rate)

        return KYNResult(
            score=score,
            verdict=verdict,
            rate_signal=rate_signal,
            employer_signal=employer_signal,
            fit_signal=fit_signal,
            pakwan_pass=pakwan_pass,
            flags=flags,
            hidden_instruction=hidden,
            rate_usd_hourly=rate,
        )

    def _extract_rate(self, post: str) -> Optional[float]:
        m = RATE_PATTERN.search(post)
        if m:
            groups = [g for g in m.groups() if g is not None]
            if len(groups) == 2:
                low, high = float(groups[0]), float(groups[1])
                return (low + high) / 2
            return float(groups[0])

        m2 = MONTHLY_PATTERN.search(post)
        if m2:
            monthly_usd = float(m2.group(1))
            return round(monthly_usd / 160, 2)

        return None

    def _rate_signal(self, rate: Optional[float], flags: list[str]) -> str:
        if rate is None:
            return "Rate not stated — ask before applying"
        if rate < 3.0:
            flags.append(f"Rate too low: ${rate:.2f}/hr (minimum $5)")
            return f"🔴 ${rate:.2f}/hr — below minimum"
        if rate < 5.0:
            flags.append(f"Rate borderline: ${rate:.2f}/hr")
            return f"🟡 ${rate:.2f}/hr — negotiate up"
        if rate < 7.0:
            return f"🟢 ${rate:.2f}/hr — acceptable"
        return f"✅ ${rate:.2f}/hr — strong"

    def _employer_signal(self, post_lower: str) -> str:
        strong_count = sum(1 for s in STRONG_EMPLOYER_SIGNALS if s in post_lower)
        weak_count = sum(1 for s in WEAK_EMPLOYER_SIGNALS if s in post_lower)

        if strong_count >= 2:
            return "Strong — established employer"
        if strong_count == 1:
            return "Moderate — some credibility signals"
        if weak_count >= 2:
            return "Weak — new/small employer, proceed carefully"
        return "Unclear — do employer research"

    def _fit_signal(self, post_lower: str) -> tuple[str, int]:
        matched = sum(1 for skill in LEBRON_SKILLS if skill in post_lower)
        total_words = len(post_lower.split())

        if matched >= 5:
            return f"High fit — {matched} matching skills", 30
        if matched >= 3:
            return f"Good fit — {matched} matching skills", 20
        if matched >= 1:
            return f"Partial fit — {matched} matching skill(s)", 10
        return "Low fit — few matching skills", 0

    def _pakwan_test(self, post_lower: str) -> tuple[bool, list[str]]:
        flags = []
        for phrase in PAKWAN_PHRASES:
            if phrase in post_lower:
                flags.append(f"Pakwan phrase: '{phrase}'")
        return len(flags) == 0, flags

    def _hidden_instruction(self, post: str) -> Optional[str]:
        for pattern in (HIDDEN_PATTERN, HIDDEN_PATTERN2):
            m = pattern.search(post)
            if m:
                return m.group(1).strip()
        return None

    def _calculate_score(
        self,
        rate: Optional[float],
        employer_signal: str,
        fit_score: int,
        pakwan_pass: bool,
    ) -> int:
        score = 0

        # Rate (40 points)
        if rate is None:
            score += 10
        elif rate >= 7.0:
            score += 40
        elif rate >= 5.0:
            score += 30
        elif rate >= 3.0:
            score += 15
        else:
            score += 0

        # Employer (30 points)
        if "Strong" in employer_signal:
            score += 30
        elif "Moderate" in employer_signal:
            score += 20
        elif "Weak" in employer_signal:
            score += 5
        else:
            score += 15

        # Fit (30 points — from fit_score passed in)
        score += fit_score

        # Pakwan penalty
        if not pakwan_pass:
            score = max(0, score - 20)

        return min(100, score)

    def _verdict(self, score: int, pakwan_pass: bool, rate: Optional[float]) -> str:
        if not pakwan_pass:
            return "skip"
        if rate is not None and rate < 3.0:
            return "skip"
        if rate is None:
            return "ask_questions"
        if score >= 60:
            return "apply"
        if score >= 40:
            return "ask_questions"
        return "skip"
