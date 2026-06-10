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

## Current Status
- **Bot:** Live and polling — token active, owner lock on ID 5135239563
- **AI:** Groq ✅ Gemini ✅ Claude ❌ (no key) Ollama ✅
- **Sheets:** Connected — PROFILE (44 rows), SKILLS (45 rows), PROJECTS (5 rows) seeded
- **Agents:** All 5 read from master_resume.md via core/resume_parser.py
- **plan_agent:** Time-budget enforced — /plan 2h returns exactly ≤108 min of tasks
- **sheets_client:** Worksheet + header caching — no more 429 rate limit errors
- **scripts/seed_data.py:** Idempotent seed + row-count verification working
- **MCPs:** github ✅ context7 ✅ | Google Gmail/Calendar/Drive — run /mcp to authenticate
- **Next:** Authenticate Google MCPs (/mcp) → test /me /skills /gaps /plan 2h end to end
