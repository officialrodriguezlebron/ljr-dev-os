# LJR.devOS — Agent Memory

## System Identity
- **Owner:** Lebron James DG. Rodriguez
- **What:** Personal AI operating system — career intelligence, skills tracking, daily planning
- **Primary interface:** Telegram bot
- **AI runtime:** Groq → Gemini → Claude → Ollama (priority fallback chain)
- **Data layer:** Google Sheets (LJR.devOS Master workbook)
- **Automation:** n8n (self-hosted, Windows)
- **Frontend:** Next.js 16 static site (Vercel) — separate concern

## Repos
- `ljr-dev-os` — THIS REPO (Next.js portfolio + Python agent system)
- `tempo` — CareerOS v3 bot (separate, older system)

## Architecture

```
iPhone / Telegram
       ↓
core/telegram_bot.py       ← Receives all commands
       ↓
agents/supervisor.py       ← Routes to correct agent
       ↓
┌──────────────────────────────────────────┐
│           Specialized Agents             │
├─────────────────┬────────────────────────┤
│ career_agent.py │ KYN scoring, cover ltrs│
│ skills_agent.py │ gaps, learning paths   │
│ profile_agent.py│ /me, profile data      │
│ plan_agent.py   │ /plan, /next, /morning │
│ learn_agent.py  │ /learn, /roadmap, /log │
└─────────────────┴────────────────────────┘
       ↓
┌──────────────────────────────────────────┐
│           Core Layer                     │
├─────────────────┬────────────────────────┤
│ kyn_engine.py   │ Pure logic KYN scorer  │
│ groq_client.py  │ AI with fallbacks      │
│ sheets_client.py│ All Google Sheets ops  │
│ models.py       │ Typed dataclasses      │
└─────────────────┴────────────────────────┘
       ↓
┌──────────────────────────────────────────┐
│         Google Sheets (Data Layer)       │
│ PROFILE · SKILLS · PROJECTS             │
│ APPLICATIONS · LEARNING LOG             │
│ INCOME · DAILY LOG                      │
└──────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────┐
│         n8n (Automation Layer)           │
│ Morning Briefing  · Follow-up Reminders  │
│ Skills Extractor  · Interview Calendar   │
│ Income Tracker                           │
└──────────────────────────────────────────┘
```

## Owner Profile (Quick Ref)
- FEU-IT BS CS, Dean's List, thesis passed Mar 7 2026
- Top skills: Shopify Advanced, TikTok Shop Advanced, CRO Advanced
- Income target: $800/month | Current: ₱0
- Active projects: RutaSmart, CareerOS, LuxeWear, LJR.devOS
- Target roles: Remote Shopify Dev, eCommerce specialist

## Agent Responsibilities

| Agent | Handles | Tools Used |
|-------|---------|------------|
| supervisor | All routing | All agents |
| career_agent | /kyn /analyze /apply /followup | kyn_engine, groq, sheets |
| skills_agent | /gaps /skills | sheets, groq |
| profile_agent | /me /projects | sheets, master_resume |
| plan_agent | /plan /next /morning | sheets, groq |
| learn_agent | /learn /roadmap /log | sheets, groq |

## Rules (Non-Negotiable)

### AI Provider Rules
- **Default:** Groq (`llama-3.3-70b-versatile`) — fastest, 14,400 req/day free
- **Long outputs (cover letters, roadmaps):** Gemini 2.0 Flash — use `prefer="gemini"`
- **KYN score ≥ 70 final polish:** Claude Sonnet 4.6 — use `prefer="claude"` only if ANTHROPIC_API_KEY set
- **Last resort / offline:** Ollama `deepseek-r1:8b` — auto-fallback, no config needed
- Always use `ai.chat(system, user, prefer="groq")` — the chain handles fallbacks automatically
- Never hardcode model names in agent files — they live in `AIClient` class vars
- Check `ai.get_status()` for current provider availability

### Build Rules
- Auto-approve all file writes
- Prefer automation (n8n) over custom code
- Prefer Sheets over databases
- Never hardcode owner data — read from master_resume.md
- All agents read master_resume.md on init

### Code Rules
- Python 3.11+, async/await throughout
- Type hints on all functions
- No silent failures — log and re-raise
- `.env` for all credentials, never in code
- Run from repo root: `python -m core.telegram_bot`

### Git Rules
- Conventional commits: feat:, fix:, chore:, docs:
- Push after every working feature

## Architect Agent (/idea, /ideas)

Workflow: Lebron sends `/idea [rough description]` from phone. Architect Agent either asks clarifying questions or produces a full spec + ready-to-paste Claude Code prompt with relevant skill hints embedded.

This is a **MANUAL HANDOFF** system — Lebron copies the generated prompt and pastes it into a SEPARATE Claude Code session himself. There is no auto-execution.

IDEAS tab in LJR.devOS Master sheet tracks: Date, Idea, Status (captured/built), Problem, Solution, Acceptance Criteria, Claude Code Prompt.

When building features for LJR.devOS itself going forward, prefer:
**think of idea → /idea on phone → get spec → paste into Claude Code → build → mark IDEAS row as "built" manually.**

Skill hints auto-embedded in generated prompts:
- Always: ljros-conventions + code-reviewer
- UI/frontend work: + frontend-design + ui-ux-pro-max
- React/Next.js: + vercel-react-best-practices
- Website auditing/scraping: + browser-use
- New feature with unclear approach: + brainstorming

Deferred features (CEO Agent, QA Agent, Claude Code Bridge, GitHub PR automation): see docs/PHASE7_ROADMAP.md for documented trigger conditions.

## Build Order

| # | File | Status |
|---|------|--------|
| 1 | CLAUDE.md | ✅ |
| 2 | master_resume.md | ✅ |
| 3 | .env | ✅ |
| 4 | requirements.txt | ✅ |
| 5 | core/models.py | ✅ |
| 6 | core/kyn_engine.py | ✅ |
| 7 | core/groq_client.py (AIClient, 4 providers) | ✅ |
| 8 | core/sheets_client.py | ✅ |
| 9 | agents/profile_agent.py | ✅ |
| 10 | agents/skills_agent.py | ✅ |
| 11 | agents/career_agent.py | ✅ |
| 12 | agents/learn_agent.py | ✅ |
| 13 | agents/plan_agent.py | ✅ |
| 14 | agents/supervisor.py | ✅ |
| 15 | core/telegram_bot.py | ✅ |
| 16 | start.bat | ✅ |
| 17-21 | n8n/*.json (5 workflows) | ✅ |
| 22 | n8n/N8N_SETUP.md | ✅ |
| 23-25 | docs/*.md | ✅ |

## Current Status — v1.4 Phase 6A COMPLETE (June 12, 2026)
- **Bot:** Live and polling — token active, owner lock on ID 5135239563
- **AI:** Groq ✅ Gemini ✅ Claude ❌ (no key) Ollama ✅
- **Sheets:** Connected — PROFILE (44 rows), SKILLS (45 rows), PROJECTS (5 rows), IDEAS tab active
- **Agents:** 10 total — supervisor, career, skills, profile, plan, learn, architect, overview, calendar + analyst/pm blueprinted
- **Phase 6A (Daily OS):** COMPLETE
  - 6A-1: /overview, /applications, compact /skills (overview_agent.py)
  - 6A-2: /analyze [url] via Firecrawl, CURRENT FOCUS in /me, new-priority skill notification
  - 6A-3a: /today, /free, /schedule via Google Calendar API (calendar_agent.py, calendar_client.py)
  - 6A-3b: Calendar write/NLU — deferred, spec in PHASE7_ROADMAP.md
- **Career:** Molongski Method fully encoded in SYSTEM_PROMPT + COVER_LETTER_PROMPT
  - KISS spine, Tips/reciprocity technique, Calendar Method for CTAs, wink guidance
  - Rate anchor fix: pre-injected into prompt, no AI drift possible
- **AI Team Blueprint:** docs/AI_TEAM_BLUEPRINT.md — 7 agents, 4 sprints, full spec
  - pm_agent, analyst_agent, research_agent, qa_agent, backend_agent, frontend_agent
  - Build trigger: after June 20 thesis defense
  - Sheets changes needed: ROADMAP, BACKLOG, RESEARCH_LOG tabs
- **Calendar setup needed:** share with careeros-bot@careeros-498909.iam.gserviceaccount.com + GOOGLE_CALENDAR_ID in .env
- **Active lead:** Jordan + Mark @ LazySun — intro call invite in inbox (June 8, unaccepted — reply needed)
- **Next focus:** RutaSmart thesis defense June 20 → reply LazySun → AI Team Sprint 1 after defense.
