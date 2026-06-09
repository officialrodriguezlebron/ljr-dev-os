# LJR.devOS — Personal AI Operating System

## Identity
- **Owner:** Lebron James DG. Rodriguez
- **What:** Unified personal OS — career intelligence, skills tracking, project hub, daily planning
- **Repo:** github.com/officialrodriguezlebron/ljr-dev-os (THIS repo)
- **Related repo:** github.com/officialrodriguezlebron/tempo (CareerOS lives here)
- **Stack:** Next.js 14 + Tailwind CSS (static site on Vercel)
- **Data sources:** IDENTITY.md, projects.md, goals.md (all in this repo, parsed at build time)
- **Automation:** n8n workflows, iPhone Shortcuts, Telegram bot (all in tempo repo)

## Architecture

```
ljr-dev-os/                    ← THIS REPO (portfolio + planning)
├── app/                       ← Next.js pages
│   └── page.tsx               ← Portfolio home page
├── components/portfolio/      ← UI components
├── lib/                       ← Parsers (read markdown at build time)
│   ├── parse-identity.ts
│   ├── parse-projects.ts
│   └── types.ts
├── IDENTITY.md                ← Single source of truth: who Lebron is
├── projects.md                ← All projects with proof points
├── goals.md                   ← Current goals + weekly tasks
├── CLAUDE.md                  ← This file
├── .claude/agents/            ← Agent role definitions
└── .claude/commands/          ← Slash commands

tempo/                         ← SEPARATE REPO (CareerOS bot + automation)
├── careeros/bot/              ← Telegram bot (v3, 14+ commands)
├── careeros/lib/              ← profile_reader, skills_brain
├── careeros/master_resume.md  ← Resume data (stays here)
├── careeros/n8n/              ← n8n workflow JSONs
└── careeros/data/             ← Runtime data (gitignored)
```

## Rules (Non-negotiable)

### Git
- Conventional commits: feat:, fix:, docs:, chore:, refactor:, test:
- Push after every commit
- Feature branches for new modules: feat/portfolio, feat/planner

### Code
- TypeScript strict mode — no `any` types
- Tailwind CSS only — no custom CSS files unless absolutely necessary
- Static site — NO Supabase, NO runtime API calls, NO client-side fetching
- Data parsed from markdown at build time via getStaticProps or generateStaticParams
- Component naming: PascalCase
- File naming: kebab-case

### Design System
- Dark mode: bg-gray-950 body, bg-gray-900 cards
- Text: text-gray-100 primary, text-gray-400 secondary
- Accent: emerald-500 (links, badges, hover states)
- Font: system (font-sans), font-mono for code/tags
- No shadows deeper than shadow-sm
- No border-radius larger than rounded-lg
- No gradients, no heavy animations
- Mobile-first: max-w-5xl container, px-4 on mobile

### Agent Team Rules
- Each agent owns specific files — no shared editing
- QA must verify build passes before approving
- Max 3-5 agents per team
- Always shut down agents cleanly

## Build Order

| # | Module | Status | Branch |
|---|--------|--------|--------|
| 1 | Foundation (IDENTITY + goals + projects + agents) | ✅ Done | main |
| 2 | Portfolio Site (static, employer-facing) | 🔨 Next | feat/portfolio |
| 3 | n8n Workflows (morning brief, weekly, job alerts) | ⏳ Queued | — (in tempo repo) |
| 4 | AI Planner page | ⏳ Queued | feat/planner |

## Key Files

| File | Purpose | Editable? |
|------|---------|-----------|
| IDENTITY.md | Who Lebron is — skills, experience, proof points | Yes (update as career grows) |
| projects.md | All projects with status and proof | Yes (add new projects) |
| goals.md | Current month/week goals | Yes (update weekly) |
| CLAUDE.md | This file — system context | Yes (update after each session) |
| lib/parse-identity.ts | Parses IDENTITY.md into typed objects | Rarely |
| lib/parse-projects.ts | Parses projects.md into typed objects | Rarely |

## Current Status
- Foundation: ✅ Slash commands, goals, projects created
- Portfolio: Not started
- Still needed: IDENTITY.md content, agent definitions, CLAUDE.md
- Next: Complete setup (steps 1-3), then build portfolio (Prompt 2)

## @references
- See IDENTITY.md for full profile, skills, proof points
- See projects.md for project data
- See goals.md for current priorities
- See .claude/agents/ for team role definitions
- See .claude/commands/ for reusable slash commands
