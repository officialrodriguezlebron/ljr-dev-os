# n8n Setup Guide — LJR.devOS

## 1. Install n8n on Windows

```bash
# Install globally via npm
npm install -g n8n

# Start n8n
n8n start

# n8n opens at: http://localhost:5678
```

Or use Docker (recommended for always-on):
```bash
docker run -d --name n8n -p 5678:5678 -v ~/.n8n:/home/node/.n8n n8nio/n8n
```

## 2. Set Environment Variables in n8n

In n8n → Settings → Environment Variables, add:
```
GROQ_API_KEY=your_groq_key
TELEGRAM_TOKEN=your_bot_token
LJROS_SHEETS_ID=your_google_sheets_id
OWNER_TELEGRAM_ID=your_telegram_user_id
```

To get your Telegram user ID: message @userinfobot on Telegram.

## 3. Set Up Google Sheets Credential

1. Go to Google Cloud Console → Create Project
2. Enable: Google Sheets API, Google Calendar API, Google Drive API
3. Create Service Account → Download JSON key → save as `google-credentials.json`
4. In n8n → Credentials → New → Google Sheets OAuth2 → paste credentials
5. Share your LJR.devOS Master Sheets workbook with the service account email

## 4. Create the Google Sheet

Create a new Google Sheet named **LJR.devOS Master** with these tabs:

### Tab: PROFILE
| Field | Value | Last Updated |

### Tab: SKILLS
| Skill | Level | Gap | Frequency | Priority | Resource | Completed |

### Tab: PROJECTS
| Project | Status | Next Task | Deadline | Priority | GitHub | Blocked By |

Seed Projects tab:
- RutaSmart | Compliance Mode | Documentation | TBD | 1 | github.com/officialrodriguezlebron/rutasmart-data-collector |
- CareerOS | Complete | Maintenance | — | 2 | github.com/officialrodriguezlebron/tempo |
- LuxeWear | Complete | — | — | 3 | — |
- LJR.devOS | In Progress | Bot testing | — | 4 | github.com/officialrodriguezlebron/ljr-dev-os |

### Tab: APPLICATIONS
| Date | Platform | Employer | Role | KYN | Status | Notes | Follow-up Date | Replied | Offer |

### Tab: LEARNING LOG
| Date | Skill | Resource | Time (min) | Notes | Completed |

### Tab: INCOME
| Month | Client | Role | Amount USD | Status | Notes |

### Tab: DAILY LOG
| Date | Tasks Planned | Done | Hours | Wins | Blockers |

## 5. Import Workflows

For each JSON file in the `n8n/` folder:

1. Open n8n → Workflows → New
2. Click menu (⋮) → Import from file
3. Select the JSON file
4. Click Save
5. Configure credentials when prompted

**Import order:**
1. `morning_briefing.json`
2. `followup_reminder.json`
3. `skills_extractor.json`
4. `interview_calendar.json`
5. `income_tracker.json`

## 6. Activate Workflows

After importing and configuring credentials:
- Toggle each workflow to **Active**
- Morning briefing fires at 7am PHT (23:00 UTC)
- Follow-up reminder fires at 9am PHT (01:00 UTC)

## 7. Set Webhook URLs

For webhook-triggered workflows (skills_extractor, interview_calendar, income_tracker):

1. Open the workflow in n8n
2. Click the Webhook node
3. Copy the **Production URL**
4. Add to your `.env` as `N8N_WEBHOOK_URL=http://your-n8n-host:5678`

## 8. Test Each Workflow

### Test Morning Briefing
Click Execute in n8n. Should send a message to your Telegram.

### Test Follow-up Reminder
Add a test row to Applications tab with Follow-up Date = today, Replied = No.
Execute workflow. Should send reminder.

### Test Skills Extractor
```bash
curl -X POST http://localhost:5678/webhook/extract-skills \
  -H "Content-Type: application/json" \
  -d '{"job_post": "We need a Shopify developer with Liquid, React, and n8n experience."}'
```

### Test Income Tracker
```bash
curl -X POST http://localhost:5678/webhook/income-paid \
  -H "Content-Type: application/json" \
  -d '{"client": "Test Client", "role": "Shopify Dev", "amount_usd": 100}'
```
Should post to Telegram with income progress bar.

## 9. Always-On Setup (Windows)

To run n8n on startup:
1. Install PM2: `npm install -g pm2`
2. Start n8n via PM2: `pm2 start n8n --name ljros-n8n`
3. Save: `pm2 save`
4. Set startup: `pm2 startup`
