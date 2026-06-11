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

## Energy Pattern Learning (deep version)
**Status:** Basic version shipped (`/plan [time] [energy: high/medium/low]`)
The deep version (auto-detecting energy from usage patterns, time of day, etc.) is deferred.
**Revisit if:** Manual energy input becomes annoying after 2+ weeks of daily use.
