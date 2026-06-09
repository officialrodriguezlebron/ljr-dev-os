# LJR.devOS — All Commands

## Career Commands

### /kyn [job post]
**Input:** Full job post text  
**Output:** KYN score (0-100), rate signal, employer signal, skill fit, Pakwan pass/fail, hidden instructions  
**Example:**
```
/kyn We're looking for a Shopify developer to manage our store.
Budget: $8-12/hr. Full-time, long-term position. Must know Liquid and CRO.
Start your application with "SHOPIFY2024" to prove you read this.
```
**Output:** Score: 85/100 ✅ | Rate: $10/hr | Employer: Strong | Fit: High | Hidden: "SHOPIFY2024"

---

### /analyze [job post]
**Input:** Full job post (min 50 chars)  
**Output:** Full KYN analysis + employer research + proof points selected + cover letter + rate anchor  
**Use when:** You're serious about applying. Takes ~10 seconds (Groq call).

---

### /apply [job post]
**Input:** Full job post  
**Output:** Same as /analyze — formatted as ready-to-send application package  
**Use when:** Copy-paste mode. Get the message body and send.

---

### /followup
**Input:** None  
**Output:** List of applications where Follow-up Date <= today and Replied = No  
**Use when:** Morning routine. Check what employers to follow up with.

---

### /track Platform|Employer|Role|KYN|Status
**Input:** Pipe-separated values  
**Output:** Confirmation + row added to APPLICATIONS tab  
**Example:**
```
/track OnlineJobs.ph | TechStore PH | Shopify Dev | 78 | applied
```

---

### /stats
**Input:** None  
**Output:** Total applications, replies, reply rate %, offers  

---

## Profile Commands

### /me
**Input:** None  
**Output:** Full profile — name, school, skills, proof points, income progress, active projects  

---

### /projects
**Input:** None  
**Output:** All projects from PROJECTS tab — status, next task  

---

## Skills Commands

### /skills
**Input:** None  
**Output:** All tracked skills — strong vs learning count  

---

### /gaps
**Input:** None  
**Output:** Top skill gaps ranked by market frequency — with learning resources  

---

## Learning Commands

### /learn [skill]
**Input:** Skill name  
**Output:** 3-week learning path — resources, week milestones, proof project  
**Example:** `/learn Meta Ads`  

---

### /roadmap [weeks]
**Input:** Number of weeks (default: 4)  
**Output:** Multi-week learning roadmap based on top skill gaps  
**Example:** `/roadmap 6`

---

### /log [skill] [notes]
**Input:** Skill name + progress notes  
**Output:** Saved to LEARNING LOG tab  
**Example:** `/log Meta Ads Finished Module 1 — audience targeting basics`

---

### /logshow
**Input:** None  
**Output:** Last 5 learning log entries  

---

## Planning Commands

### /plan [hours]
**Input:** Hours available (default: 2.0)  
**Output:** Prioritized task list for the session — thesis first, then income, then learning  
**Example:** `/plan 3`

---

### /next
**Input:** None  
**Output:** Single most important action right now  
**Use when:** You have 15 minutes and want to do something useful.

---

### /morning
**Input:** None  
**Output:** Morning briefing — situation summary, 3 priorities, motivational line  
**Use when:** Start of day. Also triggered automatically by n8n at 7am PHT.

---

## Passive Features (Auto-triggered)

### Long text without /command
Any message over 100 characters without a slash command → instant /kyn score  
**Use:** Paste a job post directly without typing /kyn

### n8n Morning Brief
Fires at 7:00am PHT via cron. No action needed.

### n8n Follow-up Reminder
Fires at 9:00am PHT. Sends list of due follow-ups.

### n8n Skills Extractor
POST to webhook `/extract-skills` with `{job_post: "..."}` → updates SKILLS tab frequency

### n8n Income Tracker
POST to webhook `/income-paid` with `{client, role, amount_usd}` → logs + sends progress bar

### n8n Interview Calendar
POST to webhook `/interview-booked` with `{employer, role, interview_date, kyn_score}` → creates Calendar event + notifies Telegram
