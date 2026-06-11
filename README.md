# LJR.devOS

Personal AI operating system for Lebron James DG. Rodriguez.

## What it does

LJR.devOS knows who you are, what you're building, and what to do next. Send it a job post and it scores it in seconds. Ask for a plan and it gives you a time-budgeted session. It tracks every application, skill gap, and learning session — all in Google Sheets, all accessible from your phone via Telegram.

- **KYN Engine** — scores job posts by rate, employer quality, and skill fit
- **Career Agent** — generates cover letters anchored to your real proof points
- **Plan Agent** — builds time-budgeted work sessions (respects your available hours)
- **Skills Agent** — tracks gaps by market frequency from real job scans
- **Learn Agent** — creates project-based learning paths with portfolio deliverables
- **Profile Agent** — your full profile, proof points, and project status on demand

## Commands

| Command | What it does |
|---------|-------------|
| `/kyn [job post]` | KYN score: rate, employer, fit, pakwan check |
| `/analyze [job post]` | Full analysis + cover letter (auto-logs to APPLICATIONS, updates skill frequency) |
| `/apply [job post]` | Application package ready to send |
| `/followup` | Follow-ups due today (5+ days, no reply) |
| `/track [platform] [employer] [role] [kyn] [status]` | Log or update an application (upserts by employer+role) |
| `/stats` | Application stats: sent, replies, offers |
| `/me` | Your full profile snapshot |
| `/projects` | All active projects and next tasks |
| `/update [project] [field] [value]` | Update any project field (e.g. `Next Task`, `Status`) |
| `/done [project] [new next task]` | Mark current task done and set the next one |
| `/sprint` | Sprint board view: This Week / Next Week / Backlog |
| `/skills` | All tracked skills by level |
| `/gaps` | Top skill gaps ranked by market demand |
| `/learn [skill]` | 3-week project-based learning path |
| `/roadmap [weeks]` | Multi-week learning roadmap |
| `/log [skill] [notes]` | Log a learning session |
| `/logshow` | Recent learning log |
| `/plan [hours] [energy: high/medium/low]` | Time-budgeted session plan (e.g. `/plan 2h high`) |
| `/weekplan` | AI-generated Monday-Friday plan from live project data |
| `/next` | Single most important action right now |
| `/morning` | Morning briefing with priorities |
| `/help` | All commands |

## Architecture

```
iPhone / Telegram
       |
core/telegram_bot.py       <- Receives all commands (owner-only lock)
       |
agents/supervisor.py       <- Routes to correct agent
       |
+------------------+------------------+
| career_agent.py  | skills_agent.py  |
| profile_agent.py | plan_agent.py    |
| learn_agent.py   |                  |
+------------------+------------------+
       |
+------------------+------------------+
| core/groq_client.py  (AIClient)     |
| Groq -> Gemini -> Claude -> Ollama  |
+------------------+------------------+
       |
+------------------+------------------+
| core/sheets_client.py               |
| PROFILE | SKILLS | PROJECTS         |
| APPLICATIONS | LEARNING LOG         |
| INCOME | DAILY LOG                  |
+------------------+------------------+
       |
n8n (self-hosted Windows)
- Morning Briefing  - Follow-up Reminders
- Skills Extractor  - Interview Calendar
- Income Tracker
```

## Setup

### Prerequisites
- Python 3.11+
- Google Cloud service account with Sheets + Drive access
- Groq API key (free at console.groq.com)
- Telegram bot token (from @BotFather)

### 1. Clone and install

```bash
git clone https://github.com/yourusername/ljr-dev-os.git
cd ljr-dev-os
pip install -r requirements.txt
```

### 2. Configure .env

```env
TELEGRAM_TOKEN=your_bot_token
OWNER_TELEGRAM_ID=your_telegram_user_id
GROQ_API_KEY=your_groq_key
GOOGLE_API_KEY=your_gemini_key
LJROS_SHEETS_ID=your_google_sheets_id
GOOGLE_CREDENTIALS_PATH=google-credentials.json
OLLAMA_URL=http://localhost:11434
```

### 3. Add credentials

Place your Google service account JSON at `google-credentials.json` in the repo root.
Share your Google Sheet with the service account email.

### 4. Seed data

```bash
python scripts/seed_data.py
```

This imports `skills_data.csv`, `projects_data.csv`, and `profile_data.csv` into your Sheets workbook. Idempotent — safe to re-run.

### 5. Start the bot

```bash
start.bat
# or
python -m core.telegram_bot
```

### 6. Test

Send `/start` to your bot on Telegram.

## AI Provider Chain

| Provider | Model | When used | Free tier |
|----------|-------|-----------|-----------|
| Groq | llama-3.3-70b-versatile | Default (fastest) | 14,400 req/day |
| Gemini | gemini-2.0-flash | Long outputs | 1,500 req/day |
| Claude | claude-sonnet-4-6 | High-quality polish | Pay-per-use |
| Ollama | deepseek-r1:8b | Local fallback | Unlimited |

The chain falls back automatically. If Groq fails, it tries Gemini, then Claude, then Ollama.

## Data Layer (Google Sheets)

| Tab | What's stored |
|-----|--------------|
| PROFILE | Identity fields, proof points, bio |
| SKILLS | All skills with level, gap flag, frequency (auto-updated by /analyze) |
| PROJECTS | Active projects, status, next task (editable via /update, /done) |
| APPLICATIONS | Every job application tracked (auto-logged by /analyze, upserted by /track) |
| LEARNING LOG | Learning sessions and notes |
| INCOME | Income records and payment status |
| DAILY LOG | Daily activity log |
| WEEKLY PLANNER | AI-generated Mon-Fri plans (written by /weekplan) |

## n8n Automation

Five workflows run on a self-hosted n8n instance (Windows):

1. **Morning Briefing** — sends `/morning` output to Telegram at 8am
2. **Follow-up Reminders** — checks for overdue applications daily
3. **Skills Extractor** — extracts skills from job posts, updates Sheets
4. **Interview Calendar** — syncs interview dates to Google Calendar
5. **Income Tracker** — logs payments and updates running total

Setup instructions: `n8n/N8N_SETUP.md`

## File Structure

```
ljr-dev-os/
  agents/
    supervisor.py       <- Routes all commands
    career_agent.py     <- KYN scoring, cover letters
    skills_agent.py     <- Gaps, skill tracking
    profile_agent.py    <- Profile, proof points
    plan_agent.py       <- Session planning, morning brief
    learn_agent.py      <- Learning paths, roadmaps
  core/
    telegram_bot.py     <- Bot entrypoint, owner-only lock
    groq_client.py      <- AIClient with 4-provider chain
    sheets_client.py    <- All Google Sheets operations
    kyn_engine.py       <- Pure-logic KYN scorer
    resume_parser.py    <- Parses master_resume.md
    models.py           <- Typed dataclasses
  scripts/
    seed_data.py        <- Idempotent data seeder
    import_to_sheets.py <- CSV bulk importer
  n8n/                  <- Workflow JSON exports
  master_resume.md      <- Single source of truth for owner data
  start.bat             <- Windows launcher with pre-flight checks
```

## Status

v1.1 — June 11, 2026

- 6 agents operational — 23 commands
- Google Sheets integration live (PROFILE: 44 rows, SKILLS: 45 rows, PROJECTS: 5 rows)
- 4-provider AI fallback (Groq + Gemini + Claude + Ollama)
- n8n morning briefing active
- Owner-only Telegram lock on user ID
- All owner data sourced from `master_resume.md` — no hardcoded values
- Full data loop: /analyze auto-logs to APPLICATIONS + updates skill frequency
- Energy-aware planning: `/plan 2h high` / `/plan 1h low`
- Project Hub: `/update`, `/done`, `/sprint`, `/weekplan`
- APPLICATIONS and INCOME tabs clean — correct 10/6 headers
