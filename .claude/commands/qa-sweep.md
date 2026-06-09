Read CLAUDE.md. Run these checks and report pass/fail for each:
1. npx tsc --noEmit
2. npm run build
3. Test suite
4. CareerOS bot startup: cd careeros && python -c "from lib.profile_reader import parse_proof_points; print('OK')"
5. Secret scan: grep -r "TELEGRAM_TOKEN\|GROQ_API_KEY\|ANTHROPIC_API_KEY" --include="*.ts" --include="*.tsx" --include="*.py" --exclude-dir=node_modules --exclude="*.env*"
6. TODO/console.log scan: grep -rn "console.log\|TODO\|FIXME\|HACK" --include="*.ts" --include="*.tsx" app/ components/ lib/
Fix anything broken. Update CLAUDE.md status.
