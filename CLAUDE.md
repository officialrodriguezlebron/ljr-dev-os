# LJR.devOS — System State

> Full reference for new Claude Code sessions. Read this entire file before touching any code.
> Last updated: 2026-06-15 | Version: v2.0 Phase 7 COMPLETE + Dashboard

---

## System Identity

- **Owner:** Lebron James DG. Rodriguez (Filipino freelancer, FEU-IT BS CS, Dean's List)
- **What:** Personal AI operating system — Telegram bot for career, skills, daily planning, and client (LazySun) ecommerce work
- **Primary interface:** Telegram bot (owner-only, locked to Telegram ID 5135239563)
- **AI runtime:** Groq `llama-3.3-70b-versatile` → Gemini 2.0 Flash → Claude Sonnet 4.6 → Ollama `deepseek-r1:8b`
- **Data layer:** Google Sheets (LJR.devOS Master workbook, ID in `LJROS_SHEETS_ID` env var)
- **Run command:** `python -m core.telegram_bot` (Telegram only) or `python core/run_all.py` (Telegram + API)
- **HTTP API:** `core/api_server.py` — FastAPI on port 8000, `POST /run`, `GET /health`, `GET /commands`
- **Web dashboard:** `https://ynitos.vercel.app` — Next.js, Tailscale IP `100.116.49.59:8000`
- **Combined launcher:** `python core/run_all.py` — shares one `SupervisorAgent` between Telegram + HTTP

---

## File Map

```
ljr-dev-os/
├── CLAUDE.md                      ← YOU ARE HERE
├── master_resume.md               ← Single source of truth for Lebron's resume data
├── .env                           ← All credentials (never commit)
├── requirements.txt
├── start.bat                      ← Windows startup script
├── google-credentials.json        ← Service account key (gitignored)
│
├── core/
│   ├── telegram_bot.py            ← Entry point. ConversationHandler for /apply. Photo handler.
│   ├── groq_client.py             ← AIClient: 4-provider chain + gemini_vision() for images
│   ├── kyn_engine.py              ← Pure KYN scoring logic — no AI calls, no side effects
│   ├── models.py                  ← Dataclasses: KYNResult, ApplicationPackage, SkillGap, Task, LearningPath, Profile
│   ├── sheets_client.py           ← SheetsClient: read_tab, append_row, update_row, find_rows
│   ├── schedule_engine.py         ← Reads ljr-brain/wiki/concepts/base-schedule.md, fills flex blocks
│   ├── url_fetcher.py             ← Firecrawl API → httpx+BS4 fallback
│   ├── knowledge_client.py        ← Phase 7: read/write va-work/knowledge/ for learning loop
│   ├── calendar_client.py         ← Google Calendar API v3 wrapper (PHT timezone)
│   └── resume_parser.py           ← Parses master_resume.md sections (IDENTITY, SKILLS, PROOF POINTS, etc.)
│
├── agents/
│   ├── supervisor.py              ← Routes ALL commands. Holds session caches (_last_kyn, _last_output).
│   │
│   ├── — Daily OS —
│   ├── career_agent.py            ← /kyn /analyze /apply /followup /stats — KYN + Molongski cover letters
│   ├── skills_agent.py            ← /skills /gaps — frequency tracking, gap detection
│   ├── profile_agent.py           ← /me — profile card from Sheets + resume
│   ├── plan_agent.py              ← /plan /next /morning /weekplan /sprint
│   ├── learn_agent.py             ← /learn /roadmap /log /logshow
│   ├── overview_agent.py          ← /overview — single-screen daily dashboard
│   ├── calendar_agent.py          ← /free /schedule — wraps CalendarClient
│   ├── reply_agent.py             ← /reply — 3 tone variants, reads wiki/people/ context
│   ├── architect_agent.py         ← /idea /ideas — generates Claude Code specs as JSON
│   │
│   └── — Phase 7: Ecommerce AI Team —
│   ├── pdp_agent.py               ← /pdp — 9-section Shopify PDP (LazySun voice, Gemini preferred)
│   ├── photo_qa_agent.py          ← /photoreview + Telegram photo → Gemini vision QA
│   ├── tiktok_agent.py            ← /tiktok — TikTok Shop title/hashtags/keywords
│   ├── meta_ads_agent.py          ← /meta — 4 creative angles, ASC structure, budget tiers
│   ├── content_calendar_agent.py  ← /contentcal — 4-week calendar, email↔social sync
│   ├── email_audit_agent.py       ← /emailaudit — 5-flow audit, KISS Jordan-update sentences
│   ├── reel_content_agent.py      ← /reel — second-by-second script + CapCut instructions
│   └── toggl_agent.py             ← /toggl /hours /togglreport — Toggl Track API v9 (httpx Basic auth)
│
├── docs/
│   ├── PHASE7_ROADMAP.md
│   ├── AI_TEAM_BLUEPRINT.md
│   └── N8N_SETUP.md
│
└── n8n/                           ← 5 workflow JSONs (Morning Briefing, Follow-ups, Skills Extractor, Calendar, Income)
```

---

## All Telegram Commands

### Daily OS
| Command | Agent | What it does |
|---------|-------|-------------|
| `/overview` | OverviewAgent | Single-screen: apps count + follow-ups + active projects + top skill gap |
| `/today` | ScheduleEngine | Fixed class blocks + flex blocks by priority (LazySun > RutaSmart > LJR.devOS) |
| `/adjust [text]` | ScheduleEngine + Groq | Recompute remaining day after an adjustment |
| `/reply [msg]` | ReplyAgent | 3 tone variants (Direct/Clarifying/Warm-professional). Reads wiki/people/ context |
| `/applications` | CareerAgent | Compact pipeline: applied/interview/replied counts |
| `/free` | CalendarAgent | Free slots ≥30min today (Google Calendar, PHT timezone) |
| `/schedule [N]` | CalendarAgent | Next N days (default 3) |

### Career Pipeline
| Command | Agent | What it does |
|---------|-------|-------------|
| `/apply [url\|text]` | ConversationHandler | Full pipeline: KYN + cover letter → YES/NO/EDIT confirm gate → logs to APPLICATIONS |
| `/analyze [url\|text]` | CareerAgent | Quick: KYN + cover letter + auto-log to APPLICATIONS (no confirm gate) |
| `/kyn [post]` | KYNEngine | Score only — rate/employer/fit/pakwan. No AI call. |
| `/followup` | CareerAgent | Follow-ups due today (Follow-up Date ≤ today, not yet replied) |
| `/track [platform] [employer] [role] [kyn] [status]` | Supervisor | Upsert APPLICATIONS row |
| `/stats` | CareerAgent | Application stats by platform and status |

### Profile & Projects
| Command | Agent | What it does |
|---------|-------|-------------|
| `/me` | ProfileAgent | Profile card: skills, income, proof points, active projects |
| `/projects` | Supervisor + Sheets | All projects + next tasks from PROJECTS tab |
| `/update [project] [field] [value]` | Supervisor + Sheets | Update PROJECTS field |
| `/done [project] [new next task]` | Supervisor + Sheets | Mark current task done, set next |
| `/sprint` | PlanAgent | Sprint board view |

### Skills & Learning
| Command | Agent | What it does |
|---------|-------|-------------|
| `/skills` | SkillsAgent | Compact skills list with levels |
| `/gaps` | SkillsAgent | Top skill gaps sorted by frequency |
| `/learn [skill]` | LearnAgent | Learning path: resources + milestones + proof project |
| `/roadmap [weeks]` | LearnAgent | Multi-week roadmap (default 4 weeks) |
| `/log` *(no args)* | KnowledgeClient | Save last ecommerce output to va-work/knowledge/tasks/ |
| `/log [skill] [notes]` | LearnAgent | Log learning progress to LEARNING LOG tab |
| `/logshow` | LearnAgent | View learning log |

### Planning
| Command | Agent | What it does |
|---------|-------|-------------|
| `/plan [hours] [energy]` | PlanAgent | Session task list. energy = high\|medium\|low |
| `/next` | PlanAgent | Single next best action |
| `/morning` | PlanAgent | Morning briefing summary |
| `/weekplan` | PlanAgent | AI-generated Mon-Fri plan |

### Build (Architect)
| Command | Agent | What it does |
|---------|-------|-------------|
| `/idea [desc]` | ArchitectAgent | Turns rough idea into Claude Code ready-to-paste spec. Logs to IDEAS tab. |
| `/ideas` | Supervisor + Sheets | List all captured ideas from IDEAS tab |

### Phase 7 — Ecommerce AI Team (LazySun)
| Command | Agent | What it does |
|---------|-------|-------------|
| `/pdp [info]` | PdpAgent | 9-section Shopify PDP (title, anchor, description, benefits, sizing, FAQ, SEO ×2, shot list) |
| `/pdp revision: [info]` | PdpAgent | Revision mode — update only what changed |
| Send photo in chat | PhotoQaAgent | Gemini vision QA: PASS/NEEDS REVISION/FAIL + tool-specific fix steps |
| `/photoreview [url] [context]` | PhotoQaAgent | Same QA via image URL |
| `/tiktok [info]` | TiktokAgent | TikTok Shop: title ≤60 chars, 10 hashtags, 7 keywords, sync/attribution flags |
| `/meta [info]` | MetaAdsAgent | Meta ads: ASC structure, 4 creative angles (pain/outcome/social proof/identity), AOV budget tier |
| `/contentcal [brief]` | ContentCalendarAgent | 4-week calendar table, email↔social sync check, [DRAFT] flags for unconfirmed items |
| `/emailaudit [info]` | EmailAuditAgent | 5-flow audit (Welcome/Cart/Post-Purchase/Win-Back/Browse Abandon) + KISS Jordan-update format |
| `/reel [brief]` | ReelContentAgent | Second-by-second script, CapCut edit steps, sound rec, caption, b-roll list |
| `/feedback [notes]` | Supervisor | Save final version → extract lesson → append to jordan-feedback.md + lessons-learned.md |

### Time Tracking
| Command | Agent | What it does |
|---------|-------|-------------|
| `/toggl [desc] [Xmin]` | TogglAgent | Log time entry to Toggl Track. Duration defaults to 30min. |
| `/hours` | TogglAgent | This week's hours vs 20hr target + per-day breakdown + pace |
| `/togglreport` | TogglAgent | Jordan-ready weekly summary grouped by task |

---

## Data Layer — Google Sheets Tabs

All ops go through `core/sheets_client.py`. Tab names are aliased in the `TABS` dict.

| Tab | Alias | Key Columns | Used By |
|-----|-------|-------------|---------|
| PROFILE | PROFILE | (imported from master_resume) | profile_agent |
| SKILLS | SKILLS | Skill, Category, Level, Priority, Frequency, Gap, Resource | skills_agent, overview_agent, plan_agent |
| PROJECTS | PROJECTS | Project, Status, Next Task, Deadline, Priority, Notes | supervisor, plan_agent |
| APPLICATIONS | APPLICATIONS | Date, Platform, Employer, Role, KYN Score, Status, Notes, Follow-up Date, Replied, Offer | career_agent, supervisor, telegram_bot |
| LEARNING LOG | LEARNING | Skill, Date, Notes, Duration | learn_agent |
| INCOME | INCOME | Date, Client, Project, Amount USD, Currency, Status, Notes | profile_agent, plan_agent |
| DAILY LOG | DAILY | (plan_agent writes daily logs) | plan_agent |
| WEEKLY PLANNER | WEEKLY PLANNER | (weekplan output) | plan_agent |
| IDEAS | IDEAS | Date, Idea, Status, Problem, Solution, Acceptance Criteria, Claude Code Prompt | architect_agent, supervisor |

**SheetsClient behavior:**
- `read_tab(tab)` → `list[dict]` (all rows as dicts keyed by header)
- `append_row(tab, data)` → appends using column headers (safe: missing cols become `""`)
- `update_row(tab, match_col, match_val, updates)` → first matching row, returns `bool`
- `find_rows(tab, filters)` → filtered list
- Auto-creates missing tabs (adds worksheet with 1000 rows, 20 cols)
- Caches worksheet objects and headers per session

---

## AI Client — `core/groq_client.py`

```python
ai = AIClient()

# Standard text call
result = await ai.chat(system, user, max_tokens=400, prefer="groq")
# prefer options: "groq" | "gemini" | "claude" | "ollama"
# Chain: preferred → groq → gemini → claude → ollama (skips unconfigured)

# Vision call (Gemini only — no fallback)
result = await ai.gemini_vision(system, prompt, image_bytes, mime_type="image/jpeg", max_tokens=600)

# JSON extraction (tries groq, falls back to gemini)
data = await ai.extract_json(system, user)

# Status check
print(ai.get_status())  # "Groq ✅ | Gemini ✅ | Claude ❌ no key | Ollama ✅"
```

**Models (class vars, never hardcode in agents):**
- `groq_model = "llama-3.3-70b-versatile"`
- `gemini_model = "gemini-2.0-flash"`
- `claude_model = "claude-sonnet-4-6"`
- `ollama_model = os.getenv("OLLAMA_MODEL", "deepseek-r1:8b")`

**When to use which `prefer`:**
- Short outputs, routing, scoring → `prefer="groq"` (fastest, default)
- Long outputs (PDPs, calendars, cover letters, roadmaps) → `prefer="gemini"`
- Final polish on high-stakes outputs (KYN ≥70) → `prefer="claude"` (only if key set)
- Vision (photo QA) → `ai.gemini_vision()` directly (no prefer param)

---

## KYN Engine — `core/kyn_engine.py`

Pure Python scoring — no AI, no side effects. Called by `career_agent.score_job()`.

**Score breakdown (100 pts total):**
- Rate (40pts): ≥$7/hr=40, ≥$5=30, ≥$3=15, <$3=0, unstated=10
- Employer (30pts): Strong=30, Moderate=20, Unclear=15, Weak=5
- Fit (30pts): ≥5 skills=30, ≥3=20, ≥1=10, 0=0
- Pakwan penalty: -20pts if exploitation phrases detected

**Verdicts:**
- `apply` (≥60, pakwan pass, rate stated)
- `ask_questions` (40-59, or rate not stated)
- `skip` (pakwan fail, or rate <$3)

**Hidden instruction detection:** Regex finds "start your message with X" patterns.

---

## External Directories (read by agents at runtime)

### `C:\Users\HomePC\ljr-brain\` — Obsidian vault
- `wiki/concepts/base-schedule.md` — academic timetable (ScheduleEngine reads this to find fixed class blocks)
- `wiki/people/jordan-haddadi.md` — Jordan Haddadi context (ReplyAgent reads on /reply)
- `wiki/people/mark.md` — Mark context (ReplyAgent)
- `wiki/projects/lazysun.md` — LazySun project context (ReplyAgent reads first 600 chars)
- `wiki/hot.md` — 500-char current situation snapshot (ReplyAgent reads)
- `wiki/context/current-focus.md` — What Lebron is focused on this week
- `wiki/context/operating-principles.md` — How Lebron works, communication rules
- `wiki/daily/YYYY-MM-DD.md` — Daily notes

**Env var:** `BRAIN_PATH` (default: `C:\Users\HomePC\ljr-brain`)

### `C:\Users\HomePC\va-work\` — LazySun client work
- `.agents/product-marketing.md` — LazySun brand context: vintage/heritage menswear, Portland ME, 25-40 buyer, NEVER "luxury/premium/elevated"
- `.agents/skills/` — marketingskills library (44 skills: ad-creative, copywriting, cro, emails, social, etc.) — Phase 7 agents embed knowledge from these
- `.claude/skills/lazysun/pdp-update/SKILL.md` — LazySun-specific PDP instructions
- `knowledge/jordan-feedback.md` — Jordan's feedback (populated by /feedback)
- `knowledge/lessons-learned.md` — Extracted lessons (populated by /feedback)
- `knowledge/winners/` — Winning output examples (manually added .md files)
- `knowledge/tasks/YYYY-MM-DD-[agent]/` — Saved task outputs (/log saves here)

**Env var:** `VA_WORK_PATH` (default: `C:\Users\HomePC\va-work`)

---

## Phase 7 — Knowledge Loop

Every ecommerce agent (pdp, photo_qa, tiktok, meta_ads, content_calendar, email_audit, reel_content) calls `build_knowledge_context()` from `core/knowledge_client.py` before generating. This injects Jordan's feedback + lessons + winning examples into the system prompt.

**Loop:**
1. Agent generates output → ends with "Reply `/log` to save"
2. `/log` (no args) → `supervisor._last_output` → `knowledge_client.save_task()` → `va-work/knowledge/tasks/YYYY-MM-DD-[agent]/`
3. `/feedback [notes]` → saves `final-version.md` → Groq extracts LESSON + JORDAN_FEEDBACK → appends to `lessons-learned.md` + `jordan-feedback.md`
4. Next time any agent runs, it reads those files as context

**Session cache in supervisor:**
```python
self._last_output: dict | None = None
# {"agent": "pdp", "request": "...", "output": "..."}
```

---

## Environment Variables

| Variable | Required | Used By | Notes |
|----------|----------|---------|-------|
| `TELEGRAM_TOKEN` | YES | telegram_bot.py | Bot crashes without this |
| `GROQ_API_KEY` | YES | groq_client.py | Primary AI provider |
| `GOOGLE_CREDENTIALS_PATH` | YES | sheets_client.py, calendar_client.py | Path to service account JSON |
| `LJROS_SHEETS_ID` | YES | sheets_client.py | Google Sheets workbook ID |
| `GOOGLE_SHEETS_ID` | YES | (same as above, legacy alias) | |
| `GOOGLE_CALENDAR_ID` | YES | calendar_client.py | Calendar ID (email format) |
| `GEMINI_API_KEY` | YES for vision/long outputs | groq_client.py | MUST be from aistudio.google.com (AIzaSy... format). NOT the same as GOOGLE_API_KEY. |
| `GOOGLE_API_KEY` | Partial | groq_client.py fallback | Used if GEMINI_API_KEY empty — but may be wrong key type |
| `FIRECRAWL_API_KEY` | Optional | url_fetcher.py | Falls back to BS4 if missing |
| `ANTHROPIC_API_KEY` | Optional | groq_client.py | Claude fallback — not currently set |
| `OLLAMA_URL` | Optional | groq_client.py | Default: http://localhost:11434 |
| `OLLAMA_MODEL` | Optional | groq_client.py | Default: deepseek-r1:8b |
| `BRAIN_PATH` | Optional | schedule_engine.py, reply_agent.py | Default: C:\Users\HomePC\ljr-brain |
| `VA_WORK_PATH` | Optional | all Phase 7 agents | Default: C:\Users\HomePC\va-work |
| `TOGGL_API_TOKEN` | Optional | toggl_agent.py | Not yet set — /toggl fails gracefully |
| `TOGGL_LAZYSUN_PROJECT_ID` | Optional | toggl_agent.py | Project ID for LazySun entries |
| `TOGGL_WORKSPACE_ID` | Optional | toggl_agent.py | Auto-fetched from API if missing |
| `OWNER_TELEGRAM_ID` | YES | telegram_bot.py | 5135239563 — owner lock |
| `LJROS_API_KEY` | YES for HTTP API | api_server.py | Dashboard auth header `X-API-Key` |
| `LJROS_API_PORT` | Optional | run_all.py | Default: 8000 |
| `LJROS_API_TIMEOUT` | Optional | api_server.py | Seconds before 504, default: 60 |
| `LJROS_CORS_ORIGINS` | Optional | api_server.py | Comma-separated origins. Default: `*`. Set to `https://ynitos.vercel.app` |

**CRITICAL:** `GEMINI_API_KEY` must be a Gemini API key from Google AI Studio (starts with `AIzaSy...`). `GOOGLE_API_KEY` in current `.env` is a Google Cloud key — different thing. Set `GEMINI_API_KEY` separately for `/photoreview`, photo QA, and Gemini fallback to work.

---

## Supervisor Session Caches

`agents/supervisor.py` holds two session caches between commands:

```python
self._last_kyn: dict[str, int] = {}
# {"last": 75} — last KYN score from /analyze, used by /track as default

self._last_output: dict | None = None
# {"agent": "pdp", "request": "...", "output": "..."}
# Set by every Phase 7 agent call. Read by /log (no args).
```

---

## ConversationHandler — `/apply` Flow

Located in `core/telegram_bot.py`. The `/apply` command is handled by a multi-state ConversationHandler — it does NOT route through `supervisor._dispatch()`.

**States:**
- `AWAITING_CONFIRM (0)` → User replies YES/NO/EDIT
  - YES → log status="applied" to APPLICATIONS → END
  - NO → log status="skipped" → END
  - EDIT → → `AWAITING_EDIT (1)`
- `AWAITING_EDIT (1)` → User sends edited cover letter → log status="applied", notes="edited cover letter" → END
- `TIMEOUT (600s)` → log status="pending-decision" → END
- `/cancel` → clears user_data → END

Context stored in `context.user_data`: `apply_pkg`, `apply_employer`, `apply_role`, `apply_platform`.

---

## Code Rules (Non-Negotiable)

### AI
- Default `prefer="groq"`. Use `prefer="gemini"` for outputs >400 tokens.
- Never hardcode model names in agent files — use `ai.groq_model`, `ai.gemini_model` etc.
- The chain handles fallbacks — don't add try/except around `ai.chat()` calls.

### Paths
- Always guard file reads with `.exists()` before `.read_text()`.
- Use `Path(os.getenv("BRAIN_PATH", r"C:\Users\HomePC\ljr-brain"))` pattern.
- Never hardcode absolute paths directly in agent logic.

### Agents
- All public methods must return `str` — Telegram reply is a string, `None` responses break the bot.
- Supervisor catches all exceptions in `route()` and formats them as error strings.
- New agents: no `__init__` args needed (no sheets, no groq — passed at call time).
- Phase 7 agents all end output with "Reply `/log` to save this to knowledge base".

### Sheets
- Use `SheetsClient` only via supervisor's `self.sheets` — don't instantiate in agents.
- Column names are case-sensitive and must match sheet headers exactly.
- APPLICATIONS columns: `Date, Platform, Employer, Role, KYN Score, Status, Notes, Follow-up Date, Replied, Offer`

### Git
- Conventional commits: `feat:`, `fix:`, `chore:`, `docs:`
- Run from repo root: `python -m core.telegram_bot`

---

## LazySun Brand Rules (for Phase 7 agents)

- **Never use:** luxury, premium, elevated, curated, timeless, effortless
- **Tone:** specific, unhurried, story-first, peer-level — the shop has a POV
- **Audience:** Men 25-40, vintage/heritage Americana, buys on story not trend
- **Known bug:** Meta descriptions don't auto-update in Shopify. Affected: Hoodie-Acorn ($198→$168 price change), Saturday Pants Blue + Black (stale price). Always flag in PDP meta outputs.
- **Photo standard:** Hero = pure white RGB(255,255,255), product 70-85% frame fill, 2048×2048px
- **VA rate:** $400/mo trial, 20hrs/week. Track via `/toggl`.

---

## Current Status — v2.0 Phase 7 COMPLETE + Dashboard (2026-06-15)

- **Bot:** Live, polling, owner-locked to 5135239563
- **AI:** Groq ✅ | Gemini (text) ✅ via GOOGLE_API_KEY fallback | Gemini (vision) ⚠️ GEMINI_API_KEY not set | Claude ❌ | Ollama ✅
- **HTTP API:** `core/api_server.py` live on port 8000, Tailscale `100.116.49.59:8000`, API key auth, 60s timeout
- **Dashboard:** `https://ynitos.vercel.app` — 4-mode navigation (today/lazysun/career/system), auto-runs /today on load
- **CORS:** `LJROS_CORS_ORIGINS=https://ynitos.vercel.app` (set in .env)
- **Sheets:** PROFILE (44 rows), SKILLS (45 rows), PROJECTS (5 rows), IDEAS tab active
- **Agents:** 18 total (10 original + 8 Phase 7 ecommerce)

**Phase history:**
- Phase 1-5: Core bot — KYN engine, cover letters, skills, planning, learning
- Phase 6A: Daily OS — /overview, /analyze URL, /today schedule, /free calendar, /schedule
- Phase 6B: Three flows — BS4 URL fallback, /apply ConversationHandler, /today+/adjust+/reply wired
- **Phase 7 (COMPLETE):** 8 ecommerce agents + knowledge loop + Toggl time tracking
- **Phase 7.5 (COMPLETE):** HTTP API + run_all.py + Tailscale docs + web dashboard (ynitos.vercel.app)

**Active client:** LazySun (Jordan Haddadi + Mark) — trial started June 15, $400/mo, 20hrs/week
**Focus priority:** LazySun → RutaSmart compliance → LJR.devOS → CareerOS

**Pending items:**
- Set `GEMINI_API_KEY=AIzaSy...` from Google AI Studio — enables photo QA + proper Gemini quota (1,500 req/day)
- Set `TOGGL_API_TOKEN` and `TOGGL_LAZYSUN_PROJECT_ID` in .env when Toggl is configured
- RutaSmart: 6 compliance items before final submission (no hard deadline)

---

## Architect Agent Pattern (/idea → /ideas)

Lebron uses `/idea [rough desc]` from phone → ArchitectAgent generates a self-contained Claude Code prompt spec → Lebron pastes it into a NEW Claude Code session.

This is a **manual handoff** — no auto-execution. The generated prompt always:
1. Describes the LJR.devOS stack context
2. References relevant skill files (ljros-conventions, code-reviewer always included)
3. Ends with "Auto-approve everything. Build now."

IDEAS tab tracks: Date, Idea, Status (captured/built), Problem, Solution, Acceptance Criteria, Claude Code Prompt.


<!-- Added by setup_lazysun.py on 2026-06-19 23:54 -->
<!-- ================================================================
     LAZYSUN VA MODULE — appended by setup_lazysun.py
     ================================================================ -->

## LazySun eCommerce VA

**Client:** LazySun Park City (`lazy-sun-park-city.myshopify.com`)
**Contacts:** Jordan Haddadi (day-to-day) · Mark Pomykato (owner)
**Access:** Shopify Products + Collections edit only. No theme/code. No API without approval.
**Sync:** Friday 9:30 AM EST · **Trial:** 4-week, 20hrs/week, started June 17 2026

### Brand Voice

Hook first (what is distinct about this piece) → practical/styling context → spec bullets.
Vary openers every time. Never template.

**Never use:** luxury · premium · elevated · curated · timeless · effortless · em dashes · scarcity language

**Audience:** Men 25–40, heritage/Americana

**Vendor field** = brand or collab name (e.g. "Puma x GGNC")

### SEO Formula

    [keyword phrase] [Full Brand Name] Shop at Lazy Sun

- SEO Title: max 60 chars
- SEO Description: 150–160 chars, plain text, no HTML
- Never change live URL handles

### Catalog State (June 19 2026)

- Total products: 1,188 · Flagged: 360
- Missing SEO Title: 291 · Missing SEO Desc: 288 · Missing Body: 203

### Vendor Backlog Priority

| # | Vendor            | SEO gap | Desc gap | Strategy     |
|---|-------------------|---------|----------|--------------|
| 1 | Gramicci          | 46      | 7        | SEO-only     |
| 2 | Kestin            | 11      | 0        | SEO-only     |
| 3 | Wythe             | 8       | 0        | SEO-only     |
| 4 | Snow Peak         | 10      | 1        | SEO-only     |
| 5 | Deep Cuts Vintage | 68      | 75       | Full PDP     |
| 6 | Lazy Sun          | 27      | 67       | Full PDP     |
| 7 | Lazy Sun Vintage  | 25      | 20       | Full PDP     |
| 8 | Vintage MLB       | 21      | 10       | Full PDP     |

### Slash Commands

`/lazysun-audit`   → run gap audit on products_export_1.csv, print vendor summary
`/lazysun-seo`     → generate SEO title + meta desc for a vendor batch
`/lazysun-pdp`     → generate full body copy + SEO for a vendor batch
`/lazysun-status`  → print backlog progress

### Working Files

| File | Location |
|------|----------|
| Full catalog export | `output/products_export_1.csv` |
| Flagged products | `output/audit_gaps.csv` |
| Generated SEO (review) | `output/proposed_seo_[vendor].csv` |
| Generated PDP (review) | `output/proposed_pdp_[vendor].csv` |

<!-- END LAZYSUN VA MODULE -->
