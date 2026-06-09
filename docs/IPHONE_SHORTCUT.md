# iPhone Shortcuts — LJR.devOS

Three shortcuts to control the system from your phone.

---

## Shortcut 1: CareerOS Analyze

**Trigger:** Share Sheet from any app (LinkedIn, OnlineJobs.ph, Kalibrr)  
**Action:** Send selected job post to /analyze  

### Steps:
1. Open **Shortcuts** app → New Shortcut
2. Add action: **Receive** input from Share Sheet (Text)
3. Add action: **Get Contents of URL**
   - URL: `https://api.telegram.org/bot[YOUR_TOKEN]/sendMessage`
   - Method: POST
   - Request body: JSON
   - Body:
     ```json
     {
       "chat_id": "[YOUR_CHAT_ID]",
       "text": "/analyze [Shortcut Input]"
     }
     ```
4. Add action: **Show Notification** — "Sent to CareerOS ✓"
5. Name it: **CareerOS Analyze**
6. Add to Share Sheet

**Usage:** On LinkedIn/OnlineJobs.ph → select job text → Share → CareerOS Analyze

---

## Shortcut 2: Quick KYN

**Trigger:** Tap from Home Screen  
**Action:** Paste clipboard → instant /kyn score  

### Steps:
1. Open **Shortcuts** app → New Shortcut
2. Add action: **Get Clipboard**
3. Add action: **Get Contents of URL**
   - URL: `https://api.telegram.org/bot[YOUR_TOKEN]/sendMessage`
   - Method: POST
   - Request body: JSON
   - Body:
     ```json
     {
       "chat_id": "[YOUR_CHAT_ID]",
       "text": "/kyn [Clipboard]"
     }
     ```
4. Add action: **Show Notification** — "KYN sent ✓"
5. Name it: **Quick KYN**
6. Add to Home Screen

**Usage:** Copy any job post text → tap Quick KYN on home screen → get score in Telegram

---

## Shortcut 3: Morning Check

**Trigger:** Tap from Home Screen or Lock Screen Widget  
**Action:** Trigger /morning briefing  

### Steps:
1. Open **Shortcuts** app → New Shortcut
2. Add action: **Get Contents of URL**
   - URL: `https://api.telegram.org/bot[YOUR_TOKEN]/sendMessage`
   - Method: POST
   - Request body: JSON
   - Body:
     ```json
     {
       "chat_id": "[YOUR_CHAT_ID]",
       "text": "/morning"
     }
     ```
3. Add action: **Open App** → Telegram
4. Name it: **Morning Brief**
5. Add to Home Screen + Lock Screen Widget

**Usage:** Wake up → tap widget → Telegram opens with full morning briefing

---

## Getting Your Credentials

### Telegram Token
1. Message @BotFather on Telegram
2. Send `/newbot`
3. Name it: LJR.devOS
4. Username: `ljrdevos_bot` (or any available)
5. Copy the token

### Your Telegram Chat ID
1. Message @userinfobot on Telegram
2. It replies with your user ID
3. Use that as `[YOUR_CHAT_ID]`

### Filling in Shortcuts
Replace `[YOUR_TOKEN]` and `[YOUR_CHAT_ID]` in each shortcut with your actual values.

---

## Optional: Automation (No-tap Morning Brief)

Instead of tapping the shortcut:
1. Open **Shortcuts** → Automation → New Automation
2. Trigger: **Time of Day** → 7:30am → Every Day
3. Action: Run the Morning Brief shortcut
4. Turn off "Ask Before Running"

Now you get the morning brief automatically (in addition to n8n's Groq-generated one).
