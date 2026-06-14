# iPhone Shortcuts Setup — LJR.devOS HTTP API

Run any bot command from iPhone without Telegram open.

**Home WiFi:** works immediately with local IP.
**Anywhere (cellular):** install Tailscale (free, 5-min setup) — then use Tailscale IP.
Recommendation: use Tailscale IP from the start so one config works everywhere.

---

## 1. Install dependencies

```
pip install -r requirements.txt
```

## 2. Generate an API key

```
python -c "import secrets; print(secrets.token_hex(16))"
```

Copy the output. You'll need it in step 3 and in every Shortcut.

## 3. Add to .env

```
LJROS_API_KEY=<paste your key here>
```

(Already done if you used `start.bat` — key is in `.env` as `LJROS_API_KEY`.)

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

---

## 5. Set up Tailscale (recommended — works anywhere)

Tailscale creates a private encrypted network between your PC and iPhone.
No public ports, no router config. Free.

**On PC:**
1. Go to tailscale.com/download → download Windows client
2. Install and sign in (Google account is easiest)
3. After install, Tailscale appears in the system tray
4. Get your PC's Tailscale IP:
   ```
   tailscale ip -4
   ```
   It looks like `100.x.x.x` — note this IP for step 7.

**On iPhone:**
1. App Store → search "Tailscale" → Install
2. Sign in with the **same account** used on PC
3. Toggle Tailscale ON (it creates a VPN connection)

Both devices now share a private network. The PC's Tailscale IP
(`100.x.x.x`) is reachable from iPhone on any network including cellular.

---

## 6. Find your local IP (home WiFi only)

Only needed if you're skipping Tailscale:
```
ipconfig
```
Look for **IPv4 Address** under your active adapter (e.g. `192.168.1.105`).
Works only when iPhone and PC are on the same WiFi.

---

## 7. Test the API

**From PC (confirm server is running):**
```
curl -X POST http://localhost:8000/run ^
  -H "Content-Type: application/json" ^
  -H "X-API-Key: <your key>" ^
  -d "{\"command\": \"/today\", \"args\": \"\"}"
```
Expected: `{"output": "...your schedule..."}`

**From iPhone Safari (same WiFi):**
```
http://192.168.x.x:8000/health
```

**From iPhone Safari (Tailscale, any network):**
```
http://100.x.x.x:8000/health
```
Both should show: `{"status": "ok", "ai": "Groq ✅ | ..."}`

**See all commands:**
```
http://100.x.x.x:8000/commands
```

---

## 8. Build the Shortcuts

Use your **Tailscale IP** (`100.x.x.x`) in the URL — works at home and away.

### Shortcut 1 — LJR Today
One-tap to see today's schedule.

1. Shortcuts app → **+** → **Add Action**
2. Search: **Get Contents of URL**
3. Set:
   - URL: `http://100.x.x.x:8000/run`
   - Method: **POST**
   - Headers:
     - `Content-Type` → `application/json`
     - `X-API-Key` → `<your key>`
   - Request Body: **JSON**
     - `command` → `/today`
     - `args` → *(leave empty)*
4. Add action: **Get Dictionary Value** → Key: `output`
5. Add action: **Show Result** (scrollable) or **Show Notification**
6. Name it: **LJR Today**

---

### Shortcut 2 — LJR PDP
Type a product name, get a full 9-section Shopify PDP.

Same as Shortcut 1, except:
- `command` → `/pdp`
- `args` → **Ask Each Time** (prompt: "Product info")

---

### Shortcut 3 — LJR Reply
Paste a message, get 3 tone variants.

Same as Shortcut 1, except:
- `command` → `/reply`
- `args` → **Ask Each Time** (prompt: "Paste the message")

---

### Shortcut 4 — LJR Quick (universal)
Type any full command. One shortcut covers all 41 commands.

Same as Shortcut 1, except:
- `command` → **Ask Each Time** (prompt: "Command (e.g. /tiktok Sonny Hat)")
- `args` → *(leave empty)*

The API parses the full string automatically — type `/pdp Sonny Corduroy Hat`
and it works exactly like sending `/pdp Sonny Corduroy Hat` on Telegram.

---

## 9. Keep the PC running

Remote access works **only while `python core/run_all.py` is running**.

**Minimum setup:**
- Leave the terminal window open when using Shortcuts
- Disable sleep/hibernate on your PC while plugged in:
  Settings → System → Power → Screen and sleep → set all to "Never" (when plugged in)

**[TBD — future option] Auto-start on boot:**
Run as a Windows Scheduled Task or NSSM service so the server starts automatically
when the PC boots, without opening a terminal. Not needed for the LazySun trial.

---

## 10. Timeout note

Long commands (PDPs, content calendars) call Gemini and may take 20-40s.
The API times out at **60 seconds** by default. If a command keeps timing out,
add `LJROS_API_TIMEOUT=90` to `.env`.

---

## 11. Output display tip

Some outputs are long (PDPs, content calendars). To read them:
- Use **Show Result** instead of **Show Notification** — it opens a scrollable modal
- Or use **Copy to Clipboard** and paste into Notes

---

## All Available Commands

| Category | Commands |
|----------|----------|
| Daily | `/today`, `/overview`, `/adjust [text]`, `/reply [msg]`, `/applications`, `/free`, `/schedule [N]` |
| Career | `/analyze [url or text]`, `/kyn [post]`, `/followup`, `/stats`, `/track` |
| Profile | `/me`, `/projects`, `/update`, `/done`, `/sprint` |
| Skills | `/skills`, `/gaps` |
| Learning | `/learn [skill]`, `/roadmap [weeks]`, `/log`, `/logshow` |
| Planning | `/plan [hours] [energy]`, `/next`, `/morning`, `/weekplan` |
| Build | `/idea [desc]`, `/ideas` |
| Ecommerce | `/pdp`, `/tiktok`, `/meta`, `/contentcal`, `/emailaudit`, `/reel`, `/photoreview`, `/feedback` |
| Time | `/toggl [desc] [Xmin]`, `/hours`, `/togglreport` |
| Telegram-only | `/apply` (confirm gate), photo upload QA (send photo in chat) |

Or call `GET /commands` for the live list.
