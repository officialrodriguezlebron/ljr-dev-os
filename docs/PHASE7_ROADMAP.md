# Phase 7+ — Deferred Features

These were part of the original "AI software company" vision but are deferred. Each has a specific trigger condition for when to revisit — not "never," but "not yet."

## CEO Agent
**Status:** Not built — deemed redundant
**Reason:** `/plan`, `/next`, and `/sprint` already provide prioritization and project-selection logic. A second AI layer deciding "what to build next" duplicates this.
**Revisit if:** `/plan` output consistently feels wrong/unhelpful after 2+ weeks of real use.

## QA Agent / Research Agent (as separate agents)
**Status:** Not built — deemed redundant
**Reason:** code-reviewer skill handles QA during Claude Code sessions. Research is just a follow-up `/idea` or direct question in a Claude Code session with context7/brave-search MCPs already connected.
**Revisit if:** code-reviewer skill proves insufficient for catching real bugs across 5+ shipped features.

## Claude Code Bridge (auto-execution)
**Status:** Not built — explicitly deferred for security
**Reason:** An agent that autonomously writes code and opens PRs from a phone command, with no review step, is a meaningful security and quality risk. The manual paste step (`/idea` → copy → paste into Claude Code) takes ~10 seconds and provides a critical human checkpoint.
**Revisit if:** `/idea` volume exceeds ~5/week AND the manual paste step becomes the actual bottleneck (verified, not assumed) AND a security review of auto-execution has been done.

## GitHub PR Automation
**Status:** Not built
**Depends on:** Claude Code Bridge (above). Same trigger conditions.

## Calendar Write / NLU (6A-3b)
**Status:** Not built — read-only shipped in 6A-3a (June 12, 2026)
**Reason:** Read-only (/today, /free, /schedule) covers the core need. Write support adds complexity (intent parsing, conflict detection, undo flows) with unclear daily value until read commands prove useful.
**Trigger:** `/today`, `/free`, or `/schedule` used daily for 7 consecutive days without issues. NOT MET YET — just shipped.

### Spec (ready to build when trigger is met)

**Approach:** Simple regex intent parsing — NOT full NLU, NOT AI for parsing.

**Commands (all via free-text message to bot, not slash commands):**
- `"Add interview tomorrow at 2pm"`
- `"Move study session to 7pm"`
- `"Cancel the 9am class"`

**Intent extraction pattern:**
1. Action: `add|create` / `move|reschedule` / `cancel|delete` — first word match
2. Time: regex for `HH:MM`, `H:MMam/pm`, relative day (`today|tomorrow|monday...`)
3. Event name: remaining text after stripping action + time tokens

**Confirmation step (REQUIRED — never skip):**
```
📅 Add: Interview · Tomorrow 2:00 PM
Confirm? Reply /yes or /no
```
Store pending action in memory (dict on supervisor, keyed by user_id). On `/yes` write to Calendar API. On `/no` discard. Pending action expires after 5 minutes.

**New files needed:**
- `core/calendar_writer.py` — `create_event()`, `delete_event()`, `move_event()` using `calendar.events().insert/delete/patch`
- `core/intent_parser.py` — regex-based intent extraction, returns `IntentResult(action, event_name, date, time)` dataclass

**Changes to existing files:**
- `agents/calendar_agent.py` — add `parse_and_confirm()` and `execute_confirmed()` methods
- `agents/supervisor.py` — handle `/yes` and `/no` commands, route free-text through intent parser when message looks like a calendar command (starts with add/move/cancel)
- `.env` — change Calendar scope from `calendar.readonly` to `calendar` (requires re-sharing or updating service account permissions)

**Scope constraint:** Only write to the calendar ID in `GOOGLE_CALENDAR_ID`. Never read or write other calendars.

## Energy Pattern Learning (deep version)
**Status:** Basic version shipped (`/plan [time] [energy: high/medium/low]`)
The deep version (auto-detecting energy from usage patterns, time of day, etc.) is deferred.
**Revisit if:** Manual energy input becomes annoying after 2+ weeks of daily use.
