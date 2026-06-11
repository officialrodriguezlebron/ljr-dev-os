# LJR.devOS Conventions

Trigger: any work on agents/, core/, or supervisor.py in the ljr-dev-os repo.

## Data Layer Rules
- ALL Sheets access goes through core/sheets_client.py methods (read_tab, append_row, update_row, find_rows). Never use gspread directly in agent files.
- Sheet headers are exact-match dictionaries. Always print headers before writing if creating a new tab.
- Use shlex.split() for parsing multi-word Telegram arguments, never naive .split(' ').

## AI Calls
- Use core/groq_client.py AIClient.chat() — extend SHARED_SYSTEM_PROMPT, don't replace it.
- Default max_tokens: 250-400 for Telegram responses (4096 char limit, leave room for formatting).
- For structured output, use ai.extract_json() not raw chat() + manual parsing.

## Telegram Formatting
- Use Markdown: *bold*, _italic_, `code`
- Emoji prefixes for sections: 🎯 ✅ 📊 💡 🚨
- Keep responses under 1000 chars when possible — Telegram truncates aggressively on mobile.
- For multi-line content, use the safe_send() pattern (handles Markdown parse errors with plain-text fallback).

## Command Pattern
Every new command in supervisor.py follows:
1. Parse args with shlex
2. Validate / handle missing args with clear error + example
3. Call the relevant agent method
4. Format response with emoji + markdown
5. If it writes data, confirm what was written

## Testing Pattern
After building any command, test with the EXACT command syntax a user would type, show real Telegram-formatted output, not just "function returns correctly."

## Anti-Patterns (DO NOT)
- Don't hardcode Lebron's data — read from master_resume.md or Sheets.
- Don't use `{{ $env.X }}` in n8n workflows (self-hosted blocks this) — bake real values via scripts/build_n8n_workflows.py.
- Don't prefix n8n field values with `=` unless they contain actual `{{ }}` template expressions — a bare ID or URL with `=` prefix gets evaluated as JavaScript and breaks.
- Don't write JSON bodies with raw template strings containing newlines in n8n HTTP nodes — use JSON.stringify({...}) expressions.
- Don't create new Sheets tabs without first checking if an existing tab can be extended.
