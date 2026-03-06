# 📘 User Manual — Project Synapse

This manual covers all daily-use features of **Project Synapse**. The system is accessible at **http://localhost:5003**.

---

## 1. Interface Overview

### The Global Console
A real-time feedback log appears at the bottom of every page:
- **Activity Feed**: Shows syncing progress, success messages, and errors
- **Minimize/Maximize**: Double-click the header to toggle
- **Resize**: Drag the top border to adjust height
- **View**: All operation history is logged here

### Navigation
The top navbar links to all modules:
- **🏠 Dashboard** — Overview and task list
- **🏫 Classroom** — Google Classroom management
- **🗺️ Notion Admin** — Database sync and import
- **⚡ Automation** — N8N workflow management
- **📄 Thesis** — PDF compilation
- **⚙️ System Admin** — Settings and environment variables

---

## 2. 🏠 Dashboard

Your real-time status overview:
- **To-Do List**: Tasks from your Notion `Tasks` database — check boxes to mark done instantly
- **NDHU Tasks**: From Google Tasks (NDHU administrative tasks)
- **Connection Status**: N8N, Google Classroom, and Notion connectivity indicators
- **Quick Links**: Frequently-used resources

---

## 3. 🗺️ Notion Admin

Central hub for all Notion-related operations.

### Database Status Panel
Shows the connection status of all 6 databases:
| Database | Purpose |
|---|---|
| Course Hub | Course records |
| Class Sessions | Auto-generated weekly sessions |
| Theory Hub | Research and theory notes |
| Lecture Notes | Per-session notes and materials |
| Tasks | Action items and to-do tracking |
| Resources | Reference materials |

Click **🔄 Sync Status** to auto-detect and save database IDs.

### CSV Import — Course Hub
Import your semester course schedule from a CSV file.

#### Supported CSV Format
```csv
學年,學期,課程代碼,課程名稱,教師,上課時間,上課時數/學分
114,1,CP__20500,諮商理論與技術,/余振民,三9/三10/三11,3/3
114,1,CS101,資料結構,/王教授,一2/一3,3/3
```

| Field | Example | Notes |
|---|---|---|
| 學年 (Year) | `114` | Academic year in ROC calendar (114 = 2025) |
| 學期 (Semester) | `1` | 1 = Fall, 2 = Spring |
| 課程代碼 (Code) | `CP__20500` | Course code |
| 課程名稱 (Name) | `諮商理論與技術` | Course name |
| 教師 (Instructor) | `/余振民` | Leading `/` is auto-stripped |
| 上課時間 (Schedule) | `三9/三10/三11` | Taiwan format (see below) |
| 上課時數/學分 | `3/3` | Hours/credits |

> Download a sample from the Notion Admin page → **「下載範例 CSV」**.

#### Taiwan Class Schedule Format

| Notation | Meaning |
|---|---|
| `三9` | Wednesday, Period 9 (14:10–15:00) |
| `三9/三10/三11` | Wednesday, Periods 9–11 (14:10–17:10) |
| `一2,五4` | Monday Period 2 + Friday Period 4 |

**Class Period Times (NDHU)**:
| Period | Time | Period | Time |
|---|---|---|---|
| 1 | 06:10–07:00 | 8 | 12:10–13:00 |
| 2 | 07:10–08:00 | 9 | 14:10–15:00 |
| 3 | 08:10–09:00 | 10 | 15:10–16:00 |
| 4 | 09:10–10:00 | 11 | 16:10–17:00 |
| 5 | 10:10–11:00 | 12 | 17:10–18:00 |
| 6 | 11:10–12:00 | 13 | 18:10–19:00 |
| 7 | 12:00–12:50 | 14 | 19:30–20:20 |

Weekday mapping: `一=Mon 二=Tue 三=Wed 四=Thu 五=Fri 六=Sat 日=Sun`

#### What Happens After Import
For each course imported:
- ✅ A record is created in **Course Hub** with all metadata
- ✅ **18 Class Sessions** are automatically generated (18-week semester)
- ✅ A **Lecture Note** Notion page is created per session
- ✅ All dates are calculated in **Taipei Time (UTC+8)**
- ✅ Consecutive periods (e.g., 9, 10, 11) are merged into a single session block

### Other CSV Imports
You can also import into: **Tasks**, **Notes**, **Resources**, **Theory Hub**, **Class Sessions** via the CSV import section.

---

## 4. 🏫 Google Classroom Manager

### Connecting
1. Click **Connect Google Classroom**
2. Authorize with your university Google Account
3. Select your role and click **Load Courses**

### Course Management Features
Click any course card to access:
- **Student List**: View roster; export to Excel (Name, Email, User ID)
- **Topic Creator**: Batch-create weekly topics (Week 1–18) with a custom prefix
- **Materials Publisher**: Upload files to Google Drive linked to the course module
- **Assignment Tracker**: View all assignments with submission rate statistics
- **Assignment Creator**: Create assignments with due dates for specific students

### Token Refresh
If Classroom sync fails after a prolonged period:
1. Delete `config/google_token.pickle`
2. Go to the Classroom page and click **Connect** again

---

## 5. ⚡ N8N Automation Hub

Monitor and control your N8N workflows from the dashboard.

### Workflow Cards
Each workflow displays:
- **Status badge**: Active / Inactive
- **Trigger type badge**: ⚡ Webhook / 🕐 Schedule / 👆 Manual
- **Execute button** (when applicable):
  - **Execute Now** (red): Webhook or Manual trigger workflows
  - **Force Execute** (yellow): Schedule trigger workflows

### Execution Behavior
| Trigger Type | Button Label | How It Works |
|---|---|---|
| Webhook | Execute Now | Calls the webhook URL directly |
| Manual | Execute Now | Calls `POST /api/v1/workflows/{id}/run` |
| Schedule | Force Execute | Calls `POST /api/v1/workflows/{id}/run` |

### Opening the N8N Editor
Click **Open in n8n** on any workflow card to open the full N8N visual editor in a new tab.

---

## 6. 📄 Thesis Compilation

Convert Markdown + bibliography into professionally formatted PDFs.

### Workflow
1. **Format Selection**: Choose `APA 7th` or `CJP` (Chinese Journal of Psychology)
2. **Metadata**: Fill in Title, Author, and Abstract (Chinese & English)
3. **Upload Files**:
   - `.md` — Main content
   - `.bib` — Bibliography (ensure citation keys match in the text)
   - Images — Referenced figures
4. Click **Start Compilation** → PDF downloads automatically

---

## 7. ⚙️ System Admin

### System Settings
All environment variables are managed here, organized in two sections:
- **NOTION CONFIGURATION**: `NOTION_API_KEY`, `PARENT_PAGE_ID`
- **OTHER SETTINGS**: Active database IDs (`COURSE_HUB_ID`, etc.), `ENROLLMENT_YEAR`, `N8N_API_KEY`

Sensitive values (keys and IDs) are masked with `*` by default. Click the eye icon 👁 to reveal.

### Enrollment Year
Set `ENROLLMENT_YEAR` (ROC calendar, e.g., `113`) to filter out past semesters from the Google Calendar sync, preventing irrelevant historical data from being imported.

---

## 8. Personalization (Themes)

Click the **Theme Icon** in the navbar:
- 🍱 **Bento** (default) — Clean, card-based modern UI
- 🌙 **Zen Mode** — Deep dark theme for low-light environments
- 📜 **Academic** — Paper texture with serif fonts
- 💻 **Terminal** — Retro monochrome hacker aesthetic

---

## 9. Common Issues

| Issue | Solution |
|---|---|
| CSV import shows 0 results | Check that your CSV uses the correct field names and UTF-8 encoding |
| Class sessions show wrong times | Verify the semester start date is correct and matches the weekday |
| Notion databases show "未設置" | Click Sync Status, then restart Docker |
| N8N workflows not loading | Verify `N8N_API_KEY` is set in System Settings |
| Force Execute fails | Upgrade to n8n v1.x or use a Webhook trigger node |
