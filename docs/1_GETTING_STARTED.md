# 🚀 Getting Started — Project Synapse

Welcome to **Project Synapse**, an AI-powered academic management dashboard for university instructors. It integrates **Notion**, **Google Classroom**, **Google Calendar**, **N8N Automation**, and **PDF Processing** into a single, unified interface.

> **Access**: `http://localhost:5003` | N8N: `http://localhost:5678` | Notion Admin: `http://localhost:5003/notion`

---

## 1. System Requirements

| Requirement | Details |
|---|---|
| OS | macOS, Linux, or Windows (WSL2 recommended) |
| Python | 3.10 or higher |
| Docker Desktop | Required (runs N8N + PDF service) |
| Git | For code management |

---

## 2. Installation & Setup

### Step 1: Clone the Repository
```bash
git clone https://github.com/chinkunlim/Project-Synapse.git
cd Project-Synapse
```

### Step 2: Configure Environment Variables
Create a `.env` file at the project root:
```env
# ── Notion ──────────────────────────────────
NOTION_API_KEY=your_integration_token
PARENT_PAGE_ID=your_parent_page_id

# ── Databases (auto-filled after first Sync Status) ─
COURSE_HUB_ID=
CLASS_SESSION_ID=
TASK_DATABASE_ID=
NOTE_DATABASE_ID=
RESOURCE_DATABASE_ID=
THEORY_HUB_ID=

# ── Academic Settings ───────────────────────
ENROLLMENT_YEAR=114

# ── N8N Automation ──────────────────────────
N8N_BASE_URL=http://n8n:5678
N8N_API_KEY=

# ── Google OAuth (optional, local dev only) ─
OAUTHLIB_INSECURE_TRANSPORT=1
```

> **How to get `PARENT_PAGE_ID`**: Open your Notion page in the browser. The last 32-character segment of the URL is the page ID.

### Step 3: Start the Application
```bash
docker-compose up -d --build
```

The dashboard will be available at **http://localhost:5003**.

> **First launch** may take 1–2 minutes while N8N initializes.

---

## 3. Notion Integration Setup

### Step 1: Create a Notion Integration
1. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Click **New Integration** → Name it "Project Synapse"
3. Copy the **Internal Integration Token** → paste as `NOTION_API_KEY`

### Step 2: Share Your Dashboard Page
1. Open your Notion Dashboard page
2. Click **`...`** (top right) → **Connections** → find your integration
3. Select **"Apply to all sub-pages"** ✅

> This is **critical** — without this step, databases inside sub-pages won't be accessible via the API.

### Step 3: Sync Database IDs
1. Go to `http://localhost:5003/notion`
2. Under **Database Status**, click **🔄 Sync Status**
3. The system will automatically find and save all database IDs into `.env`
4. **Restart Docker** to apply the saved IDs:
   ```bash
   docker-compose down && docker-compose up -d
   ```

---

## 4. N8N Automation Setup

1. Open [http://localhost:5678](http://localhost:5678) and log in
2. Go to **Settings → API** → Create an API Key
3. Enter the key in **System Admin → System Settings → `N8N_API_KEY`**
4. Restart Docker

> **Safari users**: n8n requires HTTPS cookies. The docker-compose already sets `N8N_SECURE_COOKIE=false` for local access.

---

## 5. Google Classroom Setup

### Step 1: Google Cloud Console
1. Visit [console.cloud.google.com](https://console.cloud.google.com)
2. Enable: **Google Classroom API** and **Google Drive API**

### Step 2: OAuth Consent Screen
1. Go to **APIs & Services → OAuth consent screen**
2. Select **External** user type
3. Add the following scopes:
```
https://www.googleapis.com/auth/classroom.courses.readonly
https://www.googleapis.com/auth/classroom.rosters.readonly
https://www.googleapis.com/auth/classroom.topics
https://www.googleapis.com/auth/classroom.courseworkmaterials
https://www.googleapis.com/auth/classroom.coursework.me
https://www.googleapis.com/auth/drive.file
```
4. Under **Test users**, add your Google account email address

### Step 3: Create OAuth 2.0 Client
1. Go to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
2. Application type: **Web Application**
3. Authorized redirect URI: `http://localhost:5003/api/classroom/auth/callback`
4. Download the JSON → rename to `google_credentials.json` → place in `config/`

### Step 4: First-Time Authentication
1. Go to `http://localhost:5003/classroom`
2. Click **Connect Google Classroom**
3. Complete the Google authorization flow
4. Credentials save automatically to `config/google_token.pickle`

---

## 6. NDHU Tasks (Google Tasks) Setup

The NDHU Tasks integration uses a **separate** OAuth client from Classroom.

1. In Google Cloud Console, create a **second** OAuth 2.0 Client ID (Web Application type)
2. Authorized redirect URI: `http://localhost:5001/api/ndhu/auth/callback`
   > Note: The NDHU callback uses port `5001` (internal Flask port). If running outside Docker, use `5003`.
3. Download the JSON → rename to `google_credential_ndhu.json` → place in `config/`
4. Required scopes:
   ```
   https://www.googleapis.com/auth/tasks
   ```
5. Authenticate from the **Dashboard** page via the NDHU Tasks connect button

---

## 7. Troubleshooting

| Problem | Solution |
|---|---|
| Dashboard not loading | Check `docker ps` — ensure all 3 containers are running |
| Notion databases not found | Re-share the parent page with your integration (include sub-pages) |
| Database IDs lost after rebuild | Go to Notion Admin → Sync Status, then restart Docker |
| Google Classroom auth fails | Delete `config/google_token.pickle` and re-authenticate |
| NDHU Tasks auth fails | Delete `config/token.json` and re-authenticate from Dashboard |
| N8N not accessible in Safari | Ensure `N8N_SECURE_COOKIE=false` is in `docker-compose.yml` |
| Port 5678 access denied in browser | Visit `http://localhost:5678` not `5003/n8n` for N8N admin UI |

---

> **Next steps**: See [User Manual](3_USER_MANUAL.md) for feature walkthroughs, or [Admin Handbook](2_ADMIN_HANDBOOK.md) for system management.
