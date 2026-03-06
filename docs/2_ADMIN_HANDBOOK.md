# 🛡️ Administrator Handbook — Project Synapse

This document is for administrators responsible for configuring, securing, and maintaining **Project Synapse**.

---

## 1. System Architecture

Project Synapse uses a **microservice-lite** architecture:

```
[Browser]
    ↕ HTTP
[Flask Dashboard] ←→ [Notion API]
    ↕                ↕
[N8N Container]  [Google APIs]
    ↕
[PDF Worker Container]
```

### Containers

| Container | External Port | Internal Port | Purpose |
|---|---|---|---|
| `dashboard` | 5003 | 5001 | Main Flask web application |
| `n8n` | 5678 | 5678 | Automation workflows |
| `pdf-worker` | 5002 | 5001 | LaTeX → PDF compilation |

> The Flask app runs on internal port **5001** inside Docker and is exposed as **5003** externally. Some OAuth callback URLs hardcoded in `ndhu_routes.py` reference port `5001` — update these if port mapping changes.

### Key Directories

```
project/
├── app.py                  # Flask factory
├── extensions.py           # Global Singleton initialization
├── routes/                 # API Blueprint handlers (by domain)
├── integrations/           # All external API adapters
│   ├── notion/             # Notion client, processor, config
│   ├── google_classroom_integration.py
│   ├── google_calendar_sync.py
│   └── google_ndhu_integration.py
├── utils/                  # Internal helpers (no external API deps)
│   ├── task_queue.py       # Background ThreadPoolExecutor
│   ├── validators.py       # @validate_json_params decorator
│   ├── errors.py           # Global error handler with Trace IDs
│   ├── env_manager.py      # .env read/write helpers
│   └── logger.py           # Centralized logging
├── config/                 # Static configuration
│   ├── config.py           # Flask Config class
│   ├── course_schedule_config.py
│   └── notion_schema.json  # Database schema definition
├── templates/              # Jinja2 HTML templates
├── static/                 # CSS / JS / images
├── docs/                   # Documentation (this folder)
├── scripts/                # One-off maintenance scripts
└── tests/                  # Integration test scripts
```

---

## 2. Environment Variables Reference

Managed via `.env` file and the **System Admin → System Settings** UI.

### Notion Configuration

| Variable | Description |
|---|---|
| `NOTION_API_KEY` | Internal Integration token from notion.so/my-integrations |
| `PARENT_PAGE_ID` | ID of the top-level Dashboard page in Notion |

### Active Database IDs
Auto-populated by the Sync Status feature:

| Variable | Database |
|---|---|
| `COURSE_HUB_ID` | Course Hub |
| `CLASS_SESSION_ID` | Class Sessions |
| `TASK_DATABASE_ID` | Tasks |
| `NOTE_DATABASE_ID` | Lecture Notes |
| `RESOURCE_DATABASE_ID` | Resources |
| `THEORY_HUB_ID` | Theory Hub |

### Google Credential Files

| File | Service | Notes |
|---|---|---|
| `config/google_credentials.json` | Google Classroom + Drive | OAuth 2.0 client (Web Application type) |
| `config/google_credential_ndhu.json` | NDHU Google Tasks | Separate OAuth 2.0 client (Web Application type) |
| `config/google_token.pickle` | Classroom | Auto-saved OAuth token |
| `config/token.json` | NDHU Tasks | Auto-saved OAuth token |

> **Security**: All 4 files above are in `.gitignore`. Never commit them. Set `chmod 600` on each file.

---

## 3. Security Best Practices

1. **Secrets in `.env`**: Never commit `.env` to version control. It is in `.gitignore`.
2. **Credential files**: `config/google_*.json` and `config/google_token*.pickle` are also gitignored. Set `chmod 600` permissions.
3. **Masked UI**: The System Settings UI masks all `*_ID` and `*_KEY` fields by default.
4. **N8N Cookies**: `N8N_SECURE_COOKIE=false` is set for local-only access. Change this if exposing N8N publicly via HTTPS.
5. **Notion Integration**: Only grant access to pages/databases the integration needs. Use the "Apply to sub-pages" option carefully.

---

## 4. Data Flow — Course CSV Import

```
CSV File (user upload)
    ↓
course_import_processor.py
    ├─ Parse rows (中/英文 field names auto-detected)
    ├─ Strip BOM characters (Excel compatibility)
    ├─ Filter empty rows
    └─ Call course_schedule_parser
         └─ Convert "三9/三10/三11" → 14:10–17:10 Wed
    ↓
integrations/notion/processor.py
    ├─ Write to Course Hub database
    └─ _generate_course_sessions()
         ├─ Calculate 18 weekly session dates from semester start
         ├─ All times in UTC+8 (Taipei)
         └─ Create 18 Class Session records + Lecture Note pages
```

### CSV Specifications

- **Encoding**: UTF-8 preferred; BOM is auto-stripped
- **Empty rows**: Filtered automatically
- **Merged periods**: Consecutive periods on same day (e.g., 9, 10, 11) are merged into one session
- **18-week limit**: Strictly limits auto-generated sessions to 18 from the first class date

---

## 5. Google Calendar Semester Sync

The system reads semester dates from a Google Calendar using keyword matching:

| Event Priority | Event Title Pattern | Purpose |
|---|---|---|
| High (2) | `全校開始上課` | Exact semester start date |
| Low (1) | `114-1 Start` | Generic start fallback |
| Auto-detect | `寒假開始` / `暑假開始` | Semester end (1 day before break) |

**Date Inference**: If event title has no year/semester, the system infers from the month (Feb → Spring, Sept → Fall).

**Enrollment Year Filter**: Set `ENROLLMENT_YEAR` in `.env` to prune semesters before that year from sync results.

---

## 6. Notion Database Auto-Recovery

If database IDs are missing from `.env`, the system uses a **recursive page traversal** algorithm:

1. Start from `PARENT_PAGE_ID`
2. Fetch all child blocks (up to 2 levels deep)
3. Match `child_database` blocks by title
4. Fall back to Notion search API if not found in traversal

> **Why traversal instead of search?** Notion's search API only indexes objects directly shared with the integration at the top level. Nested databases inside sub-pages aren't returned by search — traversal bypasses this limitation.

---

## 7. Maintenance Operations

### Update Application
```bash
git pull origin main
docker-compose up -d --build
```

### View Logs
```bash
# All containers
docker-compose logs -f

# Dashboard only
docker logs dashboard -f

# N8N only
docker logs n8n -f
```

### Reset Google Token
```bash
rm config/google_token.pickle
# Then re-authenticate from the Classroom page
```

### Rebuild from Scratch
```bash
docker-compose down
docker-compose up -d --build
```

---

## 8. Disaster Recovery

### Lost Database IDs
1. Go to **Notion Admin → Database Status**
2. Click **🔄 Sync Status** — the system will scan Notion and recover IDs automatically
3. Restart Docker to apply

### Accidentally Deleted Notion Database
1. Go to Notion Admin → **Danger Zone** → **Re-initialize**
2. This creates new empty databases (archived/deleted data is not restored — check Notion Trash)

### Environment Variables Corrupted
1. Open **System Admin → System Settings**
2. Manually re-enter the affected values
3. Restart Docker
