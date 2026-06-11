"""
Parses master_resume.md — single source of truth for all agents.
All functions re-read the file on each call so edits propagate without restart.
"""
import re
from pathlib import Path
from typing import Optional

RESUME_PATH = Path("master_resume.md")


def _text() -> str:
    return RESUME_PATH.read_text(encoding="utf-8")


def get_identity() -> dict[str, str]:
    """Returns the IDENTITY table as {field: value}."""
    text = _text()
    m = re.search(r"## IDENTITY\n\n\|.*?\|\n\|.*?\|\n(.*?)(?=\n---)", text, re.DOTALL)
    if not m:
        return {}
    result: dict[str, str] = {}
    for line in m.group(1).strip().split("\n"):
        if "|" in line and "---" not in line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) == 2 and parts[0]:
                result[parts[0]] = parts[1]
    return result


def get_proof_points() -> list[dict]:
    """
    Returns list of dicts:
      {title, summary, result, bullets}
    One dict per ### block inside ## PROOF POINTS.
    """
    text = _text()
    m = re.search(r"## PROOF POINTS\n(.*?)(?=\n## [A-Z])", text, re.DOTALL)
    if not m:
        return _default_proof_points()
    section = m.group(1)
    blocks = re.split(r"\n### ", "\n" + section)
    points: list[dict] = []
    for block in blocks:
        if not block.strip() or block.strip().startswith("<!--"):
            continue
        lines = block.strip().split("\n")
        title = lines[0].strip()
        if not title or title.startswith("<!--"):
            continue
        bullets = [
            l.strip().lstrip("- ").strip()
            for l in lines[1:]
            if l.strip().startswith("-") and not l.strip().startswith("---")
        ]
        if not bullets:
            continue
        # Prefer "Results:" line, then a line with numbers/metrics, then last bullet
        result_line = (
            next((b for b in bullets if "Results:" in b or "Result:" in b), None)
            or next((b for b in bullets if any(c.isdigit() for c in b)), None)
            or bullets[-1]
        )
        result_clean = re.sub(r"\*+", "", result_line).replace("Results:", "").strip(" :")
        points.append({
            "title": title,
            "summary": bullets[0] if bullets else "",
            "result": result_clean,
            "bullets": bullets,
        })
    return points or _default_proof_points()


def get_skills() -> dict[str, str]:
    """Returns {skill_name: level} for all skills in ## SKILLS tables."""
    text = _text()
    m = re.search(r"## SKILLS\n(.*?)(?=\n---|\n## [A-Z])", text, re.DOTALL)
    if not m:
        return {}
    skills: dict[str, str] = {}
    for line in m.group(1).split("\n"):
        if "|" in line and "---" not in line and "Skill" not in line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) == 2 and parts[0] and parts[1]:
                skills[parts[0]] = parts[1]
    return skills


def get_gaps() -> list[dict]:
    """
    Returns list of dicts:
      {name, market_demand, priority, resource}
    from ## KNOWN SKILL GAPS table.
    """
    text = _text()
    m = re.search(r"## KNOWN SKILL GAPS\n(.*?)(?=\n---|\n## [A-Z])", text, re.DOTALL)
    if not m:
        return _default_gaps()
    gaps: list[dict] = []
    for line in m.group(1).split("\n"):
        if "|" in line and "---" not in line and "Skill" not in line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) >= 4 and parts[0]:
                gaps.append({
                    "name": parts[0],
                    "market_demand": parts[1],
                    "priority": parts[2],
                    "resource": parts[3],
                })
    return gaps or _default_gaps()


def get_rate_anchor(role_type: str = "shopify") -> str:
    """Returns the rate string for a role type from ## RATE ANCHORS."""
    text = _text()
    m = re.search(r"## RATE ANCHORS\n(.*?)(?=\n---|\n## [A-Z])", text, re.DOTALL)
    if not m:
        return "$7-10/hr"
    role_lower = role_type.lower()
    for line in m.group(1).split("\n"):
        if "|" in line and "---" not in line and "Role" not in line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) == 2:
                key = parts[0].lower()
                if any(kw in key for kw in role_lower.split()):
                    return parts[1]
    return "$7-10/hr"


def get_projects() -> list[dict]:
    """Returns list of project dicts from ## PROJECTS section."""
    text = _text()
    m = re.search(r"## PROJECTS\n(.*?)(?=\n---|\n## [A-Z])", text, re.DOTALL)
    if not m:
        return _default_projects()
    section = m.group(1)
    blocks = re.split(r"\n### ", "\n" + section)
    projects: list[dict] = []
    for block in blocks:
        if not block.strip():
            continue
        lines = block.strip().split("\n")
        name_line = lines[0].strip()
        name_m = re.match(r"(.+?)\s*\((.+?)\)", name_line)
        name = name_m.group(1).strip() if name_m else name_line
        status = name_m.group(2).strip() if name_m else "Unknown"
        details: dict[str, str] = {}
        for line in lines[1:]:
            stripped = line.strip().lstrip("- ")
            if ": " in stripped:
                k, v = stripped.split(": ", 1)
                details[k.strip()] = v.strip()
        projects.append({"name": name, "status": status, **details})
    return projects or _default_projects()


def get_current_focus() -> dict[str, str]:
    """Returns {field: value} from ## CURRENT FOCUS & GOALS table."""
    text = _text()
    m = re.search(
        r"## CURRENT FOCUS & GOALS\n\n\|.*?\|\n\|.*?\|\n(.*?)(?=\n---|\n## |\Z)",
        text,
        re.DOTALL,
    )
    if not m:
        return {}
    result: dict[str, str] = {}
    for line in m.group(1).strip().split("\n"):
        if "|" in line and "---" not in line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) == 2 and parts[0]:
                result[parts[0]] = parts[1]
    return result


def get_goals() -> dict[str, str]:
    """Returns {field: value} from ## INCOME & GOALS table."""
    text = _text()
    m = re.search(r"## INCOME & GOALS\n\n\|.*?\|\n\|.*?\|\n(.*?)(?=\n---|\n## |\Z)", text, re.DOTALL)
    if not m:
        return {}
    result: dict[str, str] = {}
    for line in m.group(1).strip().split("\n"):
        if "|" in line and "---" not in line:
            parts = [p.strip() for p in line.strip("|").split("|")]
            if len(parts) == 2 and parts[0]:
                result[parts[0]] = parts[1]
    return result


# ── Fallbacks (used when resume section is missing / can't be parsed) ──────────

def _default_proof_points() -> list[dict]:
    return [
        {
            "title": "LuxeWear — Custom Shopify Theme",
            "summary": "Built fully custom Shopify theme from scratch",
            "result": "95 Lighthouse, 100 SEO, 12 CRO features",
            "bullets": ["Built fully custom Shopify theme", "95 Performance, 100 SEO (Lighthouse)"],
        },
        {
            "title": "Unicharm Philippines — TikTok Shop",
            "summary": "Managed TikTok Shop Seller Center end-to-end",
            "result": "500+ viewers/session, 30% sales lift",
            "bullets": ["Managed TikTok Shop Seller Center", "500+ consistent viewers per session"],
        },
        {
            "title": "VXI Global Solutions — Customer Service",
            "summary": "Handled 80-100 support tickets daily",
            "result": "93.88% CSAT, exceeded quota by 120%",
            "bullets": ["80-100 support tickets daily", "93.88% CSAT throughout tenure"],
        },
    ]


def _default_gaps() -> list[dict]:
    return [
        {"name": "Meta Ads Manager", "market_demand": "40% of target jobs", "priority": "HIGH", "resource": "Meta Blueprint (free)"},
        {"name": "GoHighLevel (GHL)", "market_demand": "30% of target jobs", "priority": "HIGH", "resource": "GHL Free Trial"},
        {"name": "Printful / POD", "market_demand": "20% of target jobs", "priority": "MEDIUM", "resource": "Printful Docs"},
    ]


def _default_projects() -> list[dict]:
    return [
        {"name": "RutaSmart", "status": "In Progress"},
        {"name": "CareerOS", "status": "Active"},
        {"name": "LJR.devOS", "status": "Building"},
        {"name": "LuxeWear", "status": "Complete"},
    ]
