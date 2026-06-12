# LJR.devOS — AI Team Architecture Blueprint
**Status:** Approved for build | **Version:** 1.0 | **Date:** June 12, 2026
**Authored by:** Claude Code (Chief AI Systems Architect session)

---

## 1. Architecture Overview

```
                       LEBRON (iPhone / Telegram)
                                  |
                       core/telegram_bot.py
                                  |
                       agents/supervisor.py
                                  |
          ┌───────────────────────┼───────────────────────┐
          |                       |                       |
   ┌──────┴──────┐        ┌───────┴──────┐        ┌──────┴──────┐
   |  CAREER OS  |        |  PLANNER OS  |        |   AI TEAM   |
   | career      |        | plan         |        | (7 agents)  |
   | skills      |        | learn        |        |             |
   | profile     |        | calendar     |        |             |
   | overview    |        | overview     |        |             |
   └─────────────┘        └──────────────┘        └──────────────┘
          |                       |                       |
          └───────────────────────┴───────────────────────┘
                                  |
                       ┌──────────┴──────────┐
                       |     core/ layer      |
                       | groq_client.py       |
                       | sheets_client.py     |
                       | calendar_client.py   |
                       | url_fetcher.py       |
                       | resume_parser.py     |
                       └──────────┬──────────┘
                                  |
              ┌───────────────────┼───────────────────┐
              |                   |                   |
       Google Sheets       Google Calendar      Groq/Gemini/
       (data layer)        (scheduling)         Ollama (AI)
```

### The AI Team — 7 Agents

```
┌─────────────────────────────────────────────────────────────────┐
│                         AI TEAM (7 AGENTS)                       │
├───────────────────┬─────────────────────────────────────────────┤
│ architect_agent   │ /idea /ideas                                 │
│ pm_agent          │ /roadmap /prioritize /backlog                │
│ research_agent    │ /research /market /compare                   │
│ analyst_agent     │ /analytics /report /insights                 │
│ backend_agent     │ /backend /api                                │
│ frontend_agent    │ /frontend /ui                                │
│ qa_agent          │ /qa /review /deploycheck                     │
└───────────────────┴─────────────────────────────────────────────┘
```

---

## 2. Agent Interaction Flow

**Principle: No real-time agent-to-agent communication. Google Sheets is the async message bus.**

```
User (Telegram)
    |
    | /command [args]
    v
supervisor.py
    |
    | routes to agent
    v
Agent (reads Sheets + calls Groq)
    |
    | writes output to Sheets (where applicable)
    | returns formatted text
    v
Telegram response
```

### Cross-Agent Data Flow (via Sheets, not direct calls)

```
architect_agent  --writes--> IDEAS tab
                                |
pm_agent         --reads------> IDEAS tab
pm_agent         --writes--> ROADMAP tab, BACKLOG tab
                                |
analyst_agent    --reads------> all tabs (no writes)
research_agent   --writes--> RESEARCH_LOG tab
backend_agent    --reads------> IDEAS tab (for context)
frontend_agent   --reads------> IDEAS tab (for context)
qa_agent         --reads------> PROJECTS tab (for context)
```

**Why this works:** Each agent is independently callable. Lebron orchestrates the flow via commands. No agent waits for another agent to finish.

---

## 3. Folder Structure

```
ljr-dev-os/
├── agents/
│   ├── # EXISTING (no changes unless noted)
│   ├── architect_agent.py      (Sprint 4: minor enhancement)
│   ├── career_agent.py
│   ├── skills_agent.py
│   ├── profile_agent.py
│   ├── plan_agent.py
│   ├── learn_agent.py
│   ├── overview_agent.py
│   ├── calendar_agent.py
│   ├── supervisor.py           (every sprint: add new routes)
│   │
│   ├── # NEW AI TEAM
│   ├── pm_agent.py             (Sprint 1)
│   ├── analyst_agent.py        (Sprint 1)
│   ├── research_agent.py       (Sprint 2)
│   ├── qa_agent.py             (Sprint 2)
│   ├── backend_agent.py        (Sprint 3)
│   └── frontend_agent.py       (Sprint 3)
│
├── core/
│   ├── telegram_bot.py         (every sprint: register new commands)
│   ├── groq_client.py          (no changes)
│   ├── sheets_client.py        (no changes)
│   ├── calendar_client.py      (no changes)
│   ├── kyn_engine.py           (no changes)
│   ├── models.py               (Sprint 1: add RoadmapItem, BacklogItem)
│   ├── resume_parser.py        (no changes)
│   └── url_fetcher.py          (no changes)
│
├── n8n/
│   └── ready/
│       └── weekly_roadmap_briefing.json  (Sprint 4)
│
├── docs/
│   ├── AI_TEAM_BLUEPRINT.md    (this file)
│   ├── PHASE7_ROADMAP.md
│   ├── ARCHITECTURE.md
│   ├── COMMANDS.md
│   └── IPHONE_SHORTCUT.md
│
└── tests/
    ├── test_pm_agent.py         (Sprint 1)
    ├── test_analyst_agent.py    (Sprint 1)
    ├── test_research_agent.py   (Sprint 2)
    └── test_qa_agent.py         (Sprint 2)
```

---

## 4. File-by-File Implementation Plan

### Sprint 1 — Data Foundation

#### `agents/pm_agent.py` (NEW)
```
Class: ProductManagerAgent
Init: sheets: SheetsClient, groq: GroqClient

Methods:
  get_roadmap() -> str
    Reads ROADMAP tab, groups by Sprint, formats as Telegram text
    Shows: Sprint N, Feature, Status, Priority per row
    Max 1000 chars

  prioritize(items: str) -> str
    Takes comma-separated list of backlog items
    Calls Groq with system: PM mindset, output ranked list with reasoning
    Does NOT write to Sheets — returns text only
    max_tokens: 400

  get_backlog() -> str
    Reads BACKLOG tab, groups by Type (feature/bug/research/infra)
    Shows: status, priority, date added
    Max 800 chars

  add_to_backlog(item: str, type: str = "feature") -> str
    Appends row to BACKLOG tab
    Fields: Date, Item, Type, Priority="medium", Source="user",
            Status="backlog", Notes=""
    Returns confirmation string
```

#### `agents/analyst_agent.py` (NEW)
```
Class: DataAnalystAgent
Init: sheets: SheetsClient, groq: GroqClient

Methods:
  get_analytics() -> str
    Reads APPLICATIONS, SKILLS, INCOME, LEARNING_LOG
    Builds compact multi-section summary (no AI, pure aggregation)
    Sections: Applications pipeline, Top skills, Income YTD, Recent learning
    Max 1200 chars

  get_report(subject: str) -> str
    subject = "applications" | "skills" | "income" | "projects" | "learning"
    Reads the relevant tab, computes counts/averages/trends
    Calls Groq for 2-sentence insight on the data
    max_tokens: 200

  get_insights() -> str
    Reads all tabs, passes compact summary to Groq
    System: "You are a career data analyst. Find non-obvious patterns."
    Returns 3-5 bullet insights
    prefer="gemini" (longer synthesis)
    max_tokens: 500
```

#### `core/models.py` additions
```
@dataclass
class RoadmapItem:
    sprint: str
    feature: str
    status: str          # planned | in-progress | done
    priority: int        # 1=high, 2=medium, 3=low
    agent: str           # which AI team agent owns it
    notes: str = ""

@dataclass
class BacklogItem:
    item: str
    type: str            # feature | bug | research | infra
    priority: str        # high | medium | low
    source: str          # user | idea | agent
    status: str          # backlog | in-sprint | done
    date_added: str
    notes: str = ""
```

#### `agents/supervisor.py` additions (Sprint 1)
```
# New imports
from agents.pm_agent import ProductManagerAgent
from agents.analyst_agent import DataAnalystAgent

# Init in __init__
self.pm = ProductManagerAgent(self.sheets, self.ai)
self.analyst = DataAnalystAgent(self.sheets, self.ai)

# New routes in route()
if command == "roadmap":
    return self.pm.get_roadmap()
if command == "prioritize":
    return await self.pm.prioritize(args)
if command == "backlog":
    if args.lower().startswith("add "):
        return self.pm.add_to_backlog(args[4:].strip())
    return self.pm.get_backlog()
if command == "analytics":
    return self.analyst.get_analytics()
if command == "report":
    return await self.analyst.get_report(args or "applications")
if command == "insights":
    return await self.analyst.get_insights()
```

#### `core/telegram_bot.py` additions (Sprint 1)
```
New commands to add to commands list:
"roadmap", "prioritize", "backlog",
"analytics", "report", "insights"
```

---

### Sprint 2 — Intelligence Layer

#### `agents/research_agent.py` (NEW)
```
Class: ResearchAgent
Init: groq: GroqClient, sheets: SheetsClient

Methods:
  research(topic: str) -> str
    If FIRECRAWL_API_KEY set: calls url_fetcher for top result + synthesizes
    Otherwise: calls Groq with web knowledge cutoff caveat
    System: "Research analyst. Find facts, not opinions. Cite uncertainty."
    Logs to RESEARCH_LOG tab: Date, Topic, Summary[:500], Source, Tags
    prefer="gemini" for better synthesis
    max_tokens: 600

  market(niche: str) -> str
    Structured market analysis prompt for niche
    Sections: Market size, Key players, Demand signals, Rate benchmarks,
              Lebron's fit score (1-10), Recommended angle
    Logs to RESEARCH_LOG tab
    prefer="gemini"
    max_tokens: 700

  compare(query: str) -> str
    Parses "A vs B" or "A versus B" from query
    Generates comparison table: criteria, A rating, B rating, verdict
    Does NOT log (comparison is session-specific)
    max_tokens: 500
```

#### `agents/qa_agent.py` (NEW)
```
Class: QAAgent
Init: groq: GroqClient, sheets: SheetsClient

Methods:
  get_test_plan(feature: str) -> str
    Generates structured test plan for a feature
    Sections: Happy path (3-5 cases), Edge cases (2-3), Regression risk
    System: "QA engineer. Write specific, testable cases. No vague steps."
    max_tokens: 500

  review(feature: str) -> str
    Reads recent IDEAS or PROJECTS row matching feature name
    Generates code review checklist: security, performance, error handling,
              edge cases, test coverage gaps
    max_tokens: 400

  deploycheck() -> str
    Static checklist generation (no AI needed)
    Sections:
      Pre-deploy: env vars set, tests passing, no print() debug statements
      Deploy: start.bat runs, bot responds to /start, all commands work
      Post-deploy: monitor logs 5 min, send /overview from phone
    Returns formatted checklist string
    Note: no Groq call — pure logic, always available offline
```

#### `agents/supervisor.py` additions (Sprint 2)
```
from agents.research_agent import ResearchAgent
from agents.qa_agent import QAAgent

self.research = ResearchAgent(self.ai, self.sheets)
self.qa = QAAgent(self.ai, self.sheets)

if command == "research":
    return await self.research.research(args)
if command == "market":
    return await self.research.market(args)
if command == "compare":
    return await self.research.compare(args)
if command == "qa":
    return await self.qa.get_test_plan(args)
if command == "review":
    return await self.qa.review(args)
if command == "deploycheck":
    return self.qa.deploycheck()
```

#### `core/telegram_bot.py` additions (Sprint 2)
```
"research", "market", "compare",
"qa", "review", "deploycheck"
```

---

### Sprint 3 — Engineering Agents

#### `agents/backend_agent.py` (NEW)
```
Class: BackendEngineerAgent
Init: groq: GroqClient, sheets: SheetsClient

Methods:
  get_backend_plan(feature: str) -> str
    Reads matching IDEAS row if exists (for context)
    Generates: API endpoints needed, DB schema changes, Core logic outline,
               Error cases, Ready-to-paste Claude Code prompt
    System: "Senior backend engineer. Python async, Sheets as DB, Groq as AI.
             Output is a Claude Code prompt, not prose."
    prefer="gemini"
    max_tokens: 800

  design_api(endpoint: str) -> str
    Generates REST API spec for a single endpoint
    Output: Method, Path, Auth required, Request schema, Response schema,
            Error codes, Example call
    max_tokens: 400
```

#### `agents/frontend_agent.py` (NEW)
```
Class: FrontendEngineerAgent
Init: groq: GroqClient

Methods:
  get_frontend_plan(feature: str) -> str
    Generates: Screen list, Component breakdown, State/props needed,
               Mobile-first notes, Ready-to-paste Claude Code prompt
    System: "Senior frontend engineer. Next.js, Tailwind, mobile-first.
             Output is a Claude Code prompt, not prose."
    prefer="gemini"
    max_tokens: 800

  design_ui(component: str) -> str
    Generates single component spec
    Output: Purpose, Props, Visual layout (ASCII or description),
            Responsive behavior, Accessibility notes
    max_tokens: 400
```

#### `agents/supervisor.py` additions (Sprint 3)
```
from agents.backend_agent import BackendEngineerAgent
from agents.frontend_agent import FrontendEngineerAgent

self.backend = BackendEngineerAgent(self.ai, self.sheets)
self.frontend = FrontendEngineerAgent(self.ai)

if command == "backend":
    return await self.backend.get_backend_plan(args)
if command == "api":
    return await self.backend.design_api(args)
if command == "frontend":
    return await self.frontend.get_frontend_plan(args)
if command == "ui":
    return await self.frontend.design_ui(args)
```

#### `core/telegram_bot.py` additions (Sprint 3)
```
"backend", "api", "frontend", "ui"
```

---

### Sprint 4 — Integration + RutaSmart Prep

#### `architect_agent.py` enhancement
```
Change: After logging to IDEAS tab, if Status="spec_ready",
        also append a row to BACKLOG tab (Type="feature", Source="idea",
        Status="backlog", Priority="medium")
Effect: /idea flow automatically feeds the PM Agent backlog
```

#### `n8n/ready/weekly_roadmap_briefing.json` (NEW)
```
Trigger: Every Monday 7:00 AM PHT (cron: 0 7 * * 1)
Flow:
  1. Read ROADMAP tab (Google Sheets node, filter Status != "done")
  2. Read BACKLOG tab (Google Sheets node, filter Priority = "high")
  3. Build Prompt node: combine roadmap + backlog into Groq prompt
     "Summarize this week's focus. 3 bullets max. What must ship?"
  4. Call Groq (HTTP Request node, llama-3.3-70b-versatile)
  5. Send to Telegram (owner ID)
```

#### RutaSmart reuse additions
```
ROADMAP tab: add "Project" column (values: ljros | rutasmart)
BACKLOG tab: add "Project" column
RESEARCH_LOG tab: add "Project" column

All agents check Project context from a global config or .env:
  APP_PROJECT=ljros   (default)
  APP_PROJECT=rutasmart  (when running in RutaSmart context)

Analyst Agent: add report types "gps_logs" | "routes" | "stops"
  (these tabs don't exist yet — analyst returns "no data" gracefully)
```

---

## 5. Google Sheets Changes

### New Tabs Required

#### ROADMAP tab
| Column | Type | Notes |
|--------|------|-------|
| Date | date | When item was added |
| Sprint | string | "Sprint 1", "Sprint 2", etc. |
| Feature | string | Short name |
| Status | string | planned / in-progress / done |
| Priority | int | 1=high, 2=medium, 3=low |
| Agent | string | Which AI team agent owns it |
| Project | string | ljros / rutasmart (Sprint 4) |
| Notes | string | Optional |

#### BACKLOG tab
| Column | Type | Notes |
|--------|------|-------|
| Date_Added | date | |
| Item | string | Feature/bug/task description |
| Type | string | feature / bug / research / infra |
| Priority | string | high / medium / low |
| Source | string | user / idea / agent |
| Status | string | backlog / in-sprint / done |
| Project | string | ljros / rutasmart (Sprint 4) |
| Notes | string | |

#### RESEARCH_LOG tab
| Column | Type | Notes |
|--------|------|-------|
| Date | date | |
| Topic | string | Search topic |
| Query | string | Exact query sent |
| Summary | string | First 500 chars of result |
| Source | string | groq / firecrawl / gemini |
| Tags | string | Comma-separated |
| Project | string | ljros / rutasmart (Sprint 4) |

### Existing Tabs — No Schema Changes
IDEAS, APPLICATIONS, SKILLS, PROJECTS, INCOME, LEARNING_LOG, DAILY_LOG
(all used by new agents as read-only, no column additions needed in Sprints 1-3)

---

## 6. Telegram Command Specifications

### Complete Command Map After All 4 Sprints

| Command | Agent | Args | Returns |
|---------|-------|------|---------|
| /roadmap | pm_agent | none | Sprint-by-sprint roadmap from ROADMAP tab |
| /prioritize | pm_agent | [item1, item2, ...] | AI-ranked list with reasoning |
| /backlog | pm_agent | none or "add [item]" | Backlog list or confirmation |
| /analytics | analyst_agent | none | Multi-tab data summary |
| /report | analyst_agent | [subject] | Deep report on one dataset |
| /insights | analyst_agent | none | 3-5 AI-generated pattern insights |
| /research | research_agent | [topic] | Research findings + logged to sheet |
| /market | research_agent | [niche] | Market analysis for a niche |
| /compare | research_agent | [A vs B] | Side-by-side comparison |
| /qa | qa_agent | [feature] | Test plan for a feature |
| /review | qa_agent | [feature] | Code review checklist |
| /deploycheck | qa_agent | none | Deployment readiness checklist |
| /backend | backend_agent | [feature] | Backend plan + Claude Code prompt |
| /api | backend_agent | [endpoint] | Single endpoint spec |
| /frontend | frontend_agent | [feature] | Frontend plan + Claude Code prompt |
| /ui | frontend_agent | [component] | Single component spec |

### Existing Commands (unchanged)
/overview, /applications, /today, /free, /schedule,
/kyn, /analyze, /apply, /followup, /track, /stats,
/me, /projects, /update, /done, /sprint,
/skills, /gaps, /learn, /roadmap (overridden by pm_agent — see below),
/log, /logshow, /plan, /next, /morning, /weekplan, /sprint,
/idea, /ideas, /start, /help

### Conflict resolution: /roadmap
Currently: learn_agent handles /roadmap [weeks] (learning roadmap)
After Sprint 1: pm_agent handles /roadmap (product roadmap)
Resolution: rename learning roadmap command to /learningpath [weeks]
  - Update learn_agent.py route handling
  - Update /help to reflect new command name

---

## 7. n8n Workflow Changes

### Existing Workflows (no changes)
- morning_briefing_v2.json — runs daily, reads APPLICATIONS + PROJECTS

### New Workflow: Sprint 4

#### weekly_roadmap_briefing.json
```
Purpose: Monday morning focus summary
Trigger: Cron — 0 7 * * 1 (Monday 7am PHT = Sunday 11pm UTC)
Nodes:
  1. Cron Trigger
  2. Read ROADMAP (Google Sheets — filter col Status != done)
  3. Read BACKLOG high priority (Google Sheets — filter col Priority = high)
  4. Build Prompt (Set node, static values only, no = prefix)
     prompt = "Week starting [date]. Roadmap items in progress: [list].
               High-priority backlog: [list].
               In 3 bullets: what must ship this week?"
  5. Call Groq (HTTP Request — POST api.groq.com/openai/v1/chat/completions)
     Authorization: Bearer [GROQ_API_KEY] — set in n8n credentials, not inline
  6. Send Telegram (HTTP Request — POST telegram URL)
     chat_id: OWNER_TELEGRAM_ID
     text: "Week of [date]\n[Groq response]"
```

---

## 8. Database / Schema Changes

LJR.devOS uses Google Sheets as its database. No SQL migrations needed.

### Sprint 1 Setup (manual, one-time)
1. Open LJR.devOS Master workbook
2. Add sheet tab: ROADMAP (headers per schema above)
3. Add sheet tab: BACKLOG (headers per schema above)
4. Seed ROADMAP with current sprint items (Sprint 1: pm_agent, analyst_agent)

### Sprint 2 Setup (manual, one-time)
5. Add sheet tab: RESEARCH_LOG (headers per schema above)

### Sprint 4 Setup (manual, one-time)
6. Add "Project" column to ROADMAP, BACKLOG, RESEARCH_LOG
7. Backfill existing rows: Project = "ljros"

### RutaSmart Future Tabs (do not create yet)
When RutaSmart adopts this architecture, add to the SAME workbook:
- GPS_LOGS (route, timestamp, lat, lng, accuracy, filtered)
- STOPS (stop_id, name, lat, lng, route, verified)
- ROUTES (route_id, name, origin, destination, active)
- INCIDENTS (date, route, type, description, resolved)

---

## 9. Sprint-by-Sprint Build Order

### Sprint 1: Data Foundation
**Estimated time:** 2 hours
**Prerequisite:** ROADMAP and BACKLOG tabs created in Sheets

| # | File | Action |
|---|------|--------|
| 1 | core/models.py | Add RoadmapItem + BacklogItem dataclasses |
| 2 | agents/pm_agent.py | New — ProductManagerAgent |
| 3 | agents/analyst_agent.py | New — DataAnalystAgent |
| 4 | agents/supervisor.py | Add PM + Analyst routes, rename /roadmap conflict |
| 5 | agents/learn_agent.py | Rename roadmap method to learning_path |
| 6 | core/telegram_bot.py | Register: roadmap, prioritize, backlog, analytics, report, insights |
| 7 | tests/test_pm_agent.py | Unit tests for get_roadmap, add_to_backlog |
| 8 | tests/test_analyst_agent.py | Unit tests for get_analytics, get_report |

**Sprint 1 acceptance test from phone:**
- /roadmap → shows items from ROADMAP tab
- /backlog → shows items from BACKLOG tab
- /backlog add "build pm_agent" → row appears in BACKLOG tab
- /analytics → multi-section data summary
- /report applications → pipeline report
- /insights → 3-5 AI pattern bullets

---

### Sprint 2: Intelligence Layer
**Estimated time:** 2 hours
**Prerequisite:** Sprint 1 complete, RESEARCH_LOG tab created

| # | File | Action |
|---|------|--------|
| 1 | agents/research_agent.py | New — ResearchAgent |
| 2 | agents/qa_agent.py | New — QAAgent |
| 3 | agents/supervisor.py | Add Research + QA routes |
| 4 | core/telegram_bot.py | Register: research, market, compare, qa, review, deploycheck |
| 5 | tests/test_research_agent.py | Unit tests (mock Groq call) |
| 6 | tests/test_qa_agent.py | Unit tests for deploycheck (no Groq) |

**Sprint 2 acceptance test from phone:**
- /research shopify headless 2026 → structured findings, logged to RESEARCH_LOG
- /market ecommerce va philippines → market analysis
- /compare groq vs gemini → comparison table
- /qa "rate anchor fix" → test plan with happy path and edge cases
- /review "overview agent" → code review checklist
- /deploycheck → full checklist, no Groq needed

---

### Sprint 3: Engineering Agents
**Estimated time:** 2 hours
**Prerequisite:** Sprint 2 complete

| # | File | Action |
|---|------|--------|
| 1 | agents/backend_agent.py | New — BackendEngineerAgent |
| 2 | agents/frontend_agent.py | New — FrontendEngineerAgent |
| 3 | agents/supervisor.py | Add Backend + Frontend routes |
| 4 | core/telegram_bot.py | Register: backend, api, frontend, ui |

**Sprint 3 acceptance test from phone:**
- /backend "add user onboarding flow" → API design + Claude Code prompt
- /api /users/profile → endpoint spec
- /frontend "job card component" → component spec + Claude Code prompt
- /ui dashboard → screen layout description
- All outputs are copy-pasteable into a Claude Code session

---

### Sprint 4: Integration + RutaSmart Prep
**Estimated time:** 2 hours
**Prerequisite:** Sprint 3 complete

| # | File | Action |
|---|------|--------|
| 1 | agents/architect_agent.py | On spec_ready, auto-append to BACKLOG tab |
| 2 | n8n/ready/weekly_roadmap_briefing.json | New n8n workflow |
| 3 | All agents | Add Project column support (read APP_PROJECT from env) |
| 4 | docs/COMMANDS.md | Update full command list |
| 5 | CLAUDE.md | Update Current Status to v1.4 Phase 7 COMPLETE |

**Sprint 4 acceptance test:**
- /idea "add dark mode" → spec logged to IDEAS AND auto-appended to BACKLOG
- Monday 7am: Telegram receives weekly roadmap briefing
- APP_PROJECT=rutasmart in .env → all agents scope data to rutasmart rows

---

## 10. Acceptance Criteria Per Agent

### 1. Architect Agent (existing, Sprint 4 enhancement)
- [ ] /idea [description] returns spec_ready with full spec OR needs_clarification with targeted questions
- [ ] /ideas returns list of all IDEAS tab entries with date and status
- [ ] IDEAS tab: row logged correctly (Date, Idea, Status=captured, Problem, Solution, Acceptance Criteria, Claude Code Prompt)
- [ ] Sprint 4: spec_ready items auto-append to BACKLOG tab
- [ ] Skill hints embedded in generated Claude Code prompts

### 2. Product Manager Agent (Sprint 1)
- [ ] /roadmap returns formatted sprints from ROADMAP tab (empty if tab is empty, not an error)
- [ ] /prioritize [items] returns AI-ranked list, reasoning visible, under 400 tokens
- [ ] /backlog returns items grouped by type
- [ ] /backlog add [item] writes row to BACKLOG with correct Date and Status=backlog
- [ ] Upsert behavior: /backlog add for existing item updates priority, does not duplicate

### 3. Research Agent (Sprint 2)
- [ ] /research [topic] returns structured findings with source caveat if Groq only
- [ ] /market [niche] returns market analysis with rate benchmark and fit score
- [ ] /compare [A vs B] returns side-by-side comparison, no em dashes
- [ ] All research/market results logged to RESEARCH_LOG tab
- [ ] compare does NOT log (session-specific, not persistent)
- [ ] Works without FIRECRAWL_API_KEY (degrades gracefully to Groq knowledge)

### 4. Data Analyst Agent (Sprint 1)
- [ ] /analytics returns data from at least 3 tabs in one response
- [ ] /report applications returns application pipeline stats (total, by status, by platform)
- [ ] /report skills returns skill gap analysis (frequency, priority count)
- [ ] /insights returns 3-5 non-obvious patterns from combined data
- [ ] /analytics and /report work when Groq is down (pure aggregation, no AI required)
- [ ] /insights degrades gracefully if Groq is down (returns "AI unavailable — use /analytics for raw data")

### 5. Backend Engineer Agent (Sprint 3)
- [ ] /backend [feature] returns: endpoints needed, DB changes, core logic outline, Claude Code prompt
- [ ] /api [endpoint] returns: method, path, auth, request schema, response schema, errors, example
- [ ] Generated Claude Code prompts include ljros-conventions + code-reviewer skill hints
- [ ] Output is under 1500 chars (fits Telegram message without splitting)
- [ ] Does not hallucinate existing code — qualifies with "implement" framing, not "here is the code"

### 6. Frontend Engineer Agent (Sprint 3)
- [ ] /frontend [feature] returns: screen list, component breakdown, state/props, mobile-first notes, Claude Code prompt
- [ ] /ui [component] returns: purpose, props, layout description, responsive behavior
- [ ] Generated Claude Code prompts include frontend-design + ui-ux-pro-max + vercel-react-best-practices hints
- [ ] Output is under 1500 chars
- [ ] Mobile-first constraint explicitly stated in every output

### 7. QA/DevOps Agent (Sprint 2)
- [ ] /qa [feature] returns: 3-5 happy path cases, 2-3 edge cases, regression risk assessment
- [ ] /review [feature] returns: security check, performance check, error handling check, test gap list
- [ ] /deploycheck returns complete checklist without calling Groq (offline-safe)
- [ ] /deploycheck checklist covers: env vars, bot response, all commands smoke test, log monitoring
- [ ] All outputs are actionable checklists, not prose descriptions

---

## 11. RutaSmart Reuse Plan

### What Gets Reused Unchanged
- All 7 agent files (zero modification)
- core/ layer (groq_client, sheets_client, calendar_client, url_fetcher)
- n8n workflow patterns (same node types, different data sources)
- Telegram bot structure

### What Gets Extended
- analyst_agent.py: add report types gps_logs, routes, stops (new `if subject == "gps_logs"` branch)
- research_agent.py: add RutaSmart research prompts (transportation, LTFRB, route analysis)
- pm_agent.py: ROADMAP/BACKLOG filtered by Project="rutasmart"

### What Gets Added for RutaSmart Only
- core/rutasmart_client.py: GPS log processor, stop matcher, route analyzer
- New Sheets tabs: GPS_LOGS, STOPS, ROUTES, INCIDENTS (see schema above)
- agents/rutasmart_agent.py: domain-specific commands (/routes, /stops, /coverage, /incident)

### Migration Path
```
1. Set APP_PROJECT=rutasmart in .env (or runtime context)
2. Add RutaSmart tabs to same workbook OR new workbook + new GOOGLE_SHEETS_ID
3. All 7 AI Team agents work immediately with RutaSmart data
4. Add rutasmart_agent.py for domain-specific analysis
5. No changes to existing LJR.devOS agents
```

---

## 12. /help Section Update (Post Sprint 4)

```
*AI TEAM:*
`/roadmap` — product roadmap by sprint
`/prioritize [items]` — AI-ranked priority
`/backlog` — full backlog list
`/analytics` — data overview all tabs
`/report [subject]` — deep report on one dataset
`/insights` — AI pattern analysis
`/research [topic]` — research findings
`/market [niche]` — market analysis
`/compare [A vs B]` — side-by-side comparison
`/backend [feature]` — backend plan + Claude Code prompt
`/api [endpoint]` — endpoint spec
`/frontend [feature]` — frontend plan + Claude Code prompt
`/ui [component]` — component spec
`/qa [feature]` — test plan
`/review [feature]` — code review checklist
`/deploycheck` — deployment readiness
```

---

## Build Trigger

**Do not start Sprint 1 until:**
- [ ] RutaSmart thesis defense complete (June 20)
- [ ] ROADMAP and BACKLOG tabs created in LJR.devOS Master workbook
- [ ] This blueprint reviewed and confirmed by Lebron

**When ready, paste this into a new Claude Code session:**

> "Build LJR.devOS AI Team Sprint 1 per docs/AI_TEAM_BLUEPRINT.md.
> Build agents/pm_agent.py + agents/analyst_agent.py + all supporting changes.
> Use ljros-conventions + code-reviewer."
