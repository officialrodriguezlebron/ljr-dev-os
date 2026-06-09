# LJR.devOS — Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INTERFACES                             │
│                                                                 │
│   Telegram Bot          iPhone Shortcuts        Web Dashboard   │
│   (primary)             (quick triggers)        (Next.js)       │
└────────────┬────────────────────┬───────────────────────────────┘
             │                    │
             ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                   core/telegram_bot.py                          │
│   Receives commands → validates owner → routes to supervisor    │
│   Auto-KYN: long text without /command → instant KYN score      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  agents/supervisor.py                           │
│   Routes all commands to the correct specialized agent          │
│   Handles errors, formats responses for Telegram               │
└────┬──────────┬──────────┬──────────┬──────────┬───────────────┘
     │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼
┌─────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ career  │ │ skills │ │profile │ │  plan  │ │ learn  │
│ _agent  │ │ _agent │ │ _agent │ │ _agent │ │ _agent │
│         │ │        │ │        │ │        │ │        │
│/kyn     │ │/skills │ │/me     │ │/plan   │ │/learn  │
│/analyze │ │/gaps   │ │/projects│ │/next  │ │/roadmap│
│/apply   │ │        │ │        │ │/morning│ │/log    │
│/followup│ │        │ │        │ │        │ │        │
│/track   │ │        │ │        │ │        │ │        │
│/stats   │ │        │ │        │ │        │ │        │
└────┬────┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
     │          │          │          │          │
     └──────────┴──────────┴──────────┴──────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
┌─────────────────────────┐   ┌─────────────────────────────┐
│    core/groq_client.py  │   │   core/sheets_client.py     │
│                         │   │                             │
│  Groq (primary)         │   │  Read/write all 7 tabs:     │
│  → Gemini (fallback)    │   │  PROFILE, SKILLS, PROJECTS  │
│  → Ollama (local)       │   │  APPLICATIONS, LEARNING LOG │
└─────────────────────────┘   │  INCOME, DAILY LOG          │
                               └─────────────────────────────┘
                                             │
                                             ▼
                               ┌─────────────────────────────┐
                               │   Google Sheets             │
                               │   LJR.devOS Master          │
                               └─────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    n8n (Automation Layer)                       │
│                                                                 │
│  morning_briefing    → 7am PHT → Groq → Telegram               │
│  followup_reminder   → 9am PHT → Sheets filter → Telegram       │
│  skills_extractor    → Webhook → Groq → Sheets update          │
│  interview_calendar  → Webhook → Google Calendar → Telegram     │
│  income_tracker      → Webhook → Sheets → Progress bar → TG    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    core/kyn_engine.py                          │
│                    (No AI needed — pure logic)                  │
│                                                                 │
│  Rate extraction (regex)    → $X/hr signal                     │
│  Employer signal analysis   → Strong/Moderate/Weak             │
│  Skill fit (LEBRON_SKILLS)  → High/Good/Partial/Low            │
│  Pakwan test (phrase list)  → Pass/Fail                        │
│  Hidden instruction detect  → Found/None                       │
│  → KYNResult (score 0-100, verdict: apply/ask/skip)            │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow: /analyze Command

```
User sends: /analyze [job post]
      ↓
telegram_bot.py → supervisor.route("analyze", job_post)
      ↓
career_agent.analyze_job(post)
      ↓
kyn_engine.score(post)        → KYNResult (pure logic, instant)
      ↓
groq_client.chat(system, prompt)   → Cover letter text
      ↓
ApplicationPackage assembled
      ↓
Format as Telegram markdown
      ↓
User receives: KYN score + cover letter + rate anchor
```

## Agent Responsibilities

| Agent | Owns | Never touches |
|-------|------|---------------|
| career_agent | APPLICATIONS tab, KYN scoring, cover letters | SKILLS, INCOME |
| skills_agent | SKILLS tab | APPLICATIONS |
| profile_agent | PROFILE tab, master_resume.md read | Writing to sheets |
| plan_agent | DAILY LOG, reads all tabs | Writing to SKILLS |
| learn_agent | LEARNING LOG tab | APPLICATIONS, INCOME |

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Interface | Telegram Bot API | Mobile-first, free, instant |
| Agents | Python 3.11 + async | Simple, readable, no overhead |
| AI | Groq (llama-3.3-70b) | Fastest free inference |
| Fallback AI | Gemini 1.5 Flash | Free tier, reliable |
| Local AI | Ollama (llama3) | Offline capability |
| Data | Google Sheets | Free, visual, shareable |
| Automation | n8n (self-hosted) | No code for scheduling/webhooks |
| Frontend | Next.js 16 (Vercel) | Portfolio + planning dashboard |
