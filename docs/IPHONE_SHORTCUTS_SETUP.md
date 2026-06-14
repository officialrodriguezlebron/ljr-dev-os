# iPhone Shortcuts Setup — LJR.devOS HTTP API

Run any bot command from iPhone without Telegram open.
Works on the same WiFi. No cloud services required.

---

## 1. Install dependencies

```
pip install -r requirements.txt
```

## 2. Generate an API key

```
python -c "import secrets; print(secrets.token_hex(16))"
```

Copy the output (e.g. `a3f8c2d1e4b5...`). You'll need it in step 3 and in the Shortcut.

## 3. Add to .env

```
LJROS_API_KEY=<paste your key here>
```

## 4. Start both servers

**Option A — one window (recommended):**
```
python core/run_all.py
```

**Option B — two windows:**
```
# Window 1
python -m core.telegram_bot

# Window 2
uvicorn core.api_server:app --host 0.0.0.0 --port 8000
```

Or double-click `start.bat` and choose option 1 or 2.

## 5. Find your PC's local IP

Open Command Prompt:
```
ipconfig
```
Look for **IPv4 Address** under your active adapter (e.g. `192.168.1.105`).
Your iPhone must be on the **same WiFi network**.

## 6. Test from PC first

```
curl -X POST http://localhost:8000/run ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: <your key>" ^
  -d "{\"command\": \"/today\", \"args\": \"\"}"
```

Expected response: `{"output": "...your schedule..."}`

## 7. Test health from iPhone

Open Safari on your iPhone (same WiFi) and visit:
```
http://<PC-IP>:8000/health
```
Should show: `{"status": "ok", "ai": "Groq ✅ | Gemini ..."}`

---

## 8. Build the Shortcuts

### Shortcut 1 — LJR Today
One-tap to see today's schedule.

1. Shortcuts app → **+** → **Add Action**
2. Search: **Get Contents of URL**
3. Set:
   - URL: `http://<PC-IP>:8000/run`
   - Method: **POST**
   - Headers:
     - `Content-Type` → `application/json`
     - `X-API-Key` → `<your key>`
   - Request Body: **JSON**
     - `command` → `/today`
     - `args` → *(leave empty)*
4. Add action: **Get Dictionary Value** → Key: `output`
5. Add action: **Show Notification** (or **Show Result**)
6. Name it: **LJR Today**

---

### Shortcut 2 — LJR PDP
Type a product name, get a full 9-section Shopify PDP.

Same as above, except:
- `command` → `/pdp`
- `args` → **Ask Each Time** (prompt: "Product info")

---

### Shortcut 3 — LJR Reply
Paste a message, get 3 tone variants.

Same as above, except:
- `command` → `/reply`
- `args` → **Ask Each Time** (prompt: "Paste the message")

---

### Shortcut 4 — LJR Quick (universal)
Type any full command. Covers all 41 commands with one shortcut.

1. Same URL/headers as above
2. Request Body JSON:
   - `command` → **Ask Each Time** (prompt: "Command (e.g. /tiktok Sonny Hat)")
   - `args` → *(leave empty)*
3. The API parses the full string automatically — you can type `/pdp Sonny Corduroy Hat` and it works.

This is the most flexible shortcut — use it when you don't want to build per-command shortcuts.

---

## 9. Tip: Show output as text

Some outputs are long (PDPs, content calendars). To read them:
- Use **Show Result** instead of **Show Notification** — it opens a scrollable modal
- Or use **Copy to Clipboard** and paste into Notes

---

## 10. (Optional) Access outside home WiFi

If you need to reach the API from cellular or a different network:

**Tailscale (easiest, free):**
1. Install Tailscale on PC and iPhone
2. Use your Tailscale IP (`100.x.x.x`) instead of the local `192.168.x.x`
3. No port forwarding, no router config

**ngrok (temporary public URL, free tier):**
```
ngrok http 8000
```
Copy the `https://xxxx.ngrok.io` URL and use it in Shortcuts.
Expires when you stop ngrok — not suitable for permanent use.

Neither is required for same-WiFi use.

---

## All Available Commands

| Command | What it does |
|---------|-------------|
| `/today` | Today's schedule |
| `/overview` | Daily dashboard |
| `/plan [hours] [energy]` | Session task list |
| `/next` | Single next action |
| `/morning` | Morning briefing |
| `/weekplan` | Mon-Fri plan |
| `/pdp [product info]` | 9-section Shopify PDP |
| `/tiktok [info]` | TikTok Shop listing |
| `/meta [info]` | Meta ads creative |
| `/contentcal [brief]` | 4-week content calendar |
| `/emailaudit [info]` | Email flow audit |
| `/reel [brief]` | Short-form video script |
| `/reply [message]` | 3 tone variants |
| `/kyn [job post]` | KYN job score |
| `/analyze [url or text]` | Full job analysis |
| `/followup` | Follow-ups due today |
| `/stats` | Application stats |
| `/me` | Profile card |
| `/skills` | Skills list |
| `/gaps` | Skill gaps |
| `/hours` | Toggl hours this week |
| `/toggl [desc] [Xmin]` | Log time entry |
| `/idea [desc]` | Generate Claude Code spec |
| `/free` | Free calendar slots today |
| `/schedule [N]` | Next N days calendar |
