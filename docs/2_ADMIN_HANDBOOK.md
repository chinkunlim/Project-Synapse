# 🛡️ Administrator Handbook

This document is intended for system administrators responsible for maintaining, securing, and configuring **Project Synapse**.

---

## 1. System Architecture Overview

Project Synapse operates as a microservice-lite architecture:

### **Core Components**
1.  **Web Server (Flask)**:
    *   Handles all HTTP requests, routing, and UI rendering.
    *   Manages sessions and authentication logic.
    *   Located in `app.py` and `routes/`.

2.  **Database & Storage**:
    *   **Notion**: Acts as the primary CMS/Database for tasks, courses, and schedules.
    *   **Local Filesystem**: Stores uploaded PDFs temporarily and configuration files.

3.  **Background Engines (Docker)**:
    *   **N8N (Automation)**: Runs localized automation workflows. Exposed on port `5678`.
    *   **PDF Service**: A specialized container for compiling LaTeX documents into PDFs.

---

## 2. Configuration & Security

### 🔐 Managing Secrets
All sensitive configuration is managed via the **Settings Page** (`/admin`) or directly in the `.env` file.

*   **NOTION_API_KEY**: Grants full access to the workspace. **Rotate this key immediately if compromised.**
*   **FLASK_SECRET_KEY**: Encrypts user sessions. Change this whenever you deploy to a new environment.
*   **GOOGLE_CREDENTIALS**: OAuth tokens are stored in `google_credentials.json`. Ensure this file has strict file permissions (`chmod 600`).

### 🛡️ Security Best Practices
1.  **Access Control**: Ensure the `/admin` route is protected (if deployed publicly). Currently, it relies on local access or basic auth (if configured).
2.  **Firewall**: If hosting on a server, only expose ports `5000` (Web) and optionally `5678` (N8N) if needed.
3.  **Updates**: regular `docker-compose pull` to keep N8N and PDF services patched.

---

## 3. Database Schema & Synchronization

Project Synapse enforces a strict schema on Notion databases to ensure the UI works correctly.

### **Database Structure**
*   **Overview (Parent Page)**: The root of the system.
*   **Tasks DB** (Master Tag Database): Stores all action items.
*   **Course Schedule DB**: Stores academic calendar items.
*   **Thesis DB**: Tracks PDF generation history.

### **Disaster Recovery**
If a user accidentally deletes a database or property in Notion:
1.  Go to **Notion Admin** page.
2.  Use the **"Database Health Check"** tool to identify missing connections.
3.  Click **"Re-initialize"** to recreate the missing structures.
    *   *Note: This will create NEW databases; it cannot restore deleted data from Notion's trash.*

---

---

## 4. Data Import & Sync

### **Google Calendar Synchronization**
The system syncs semester start/end dates from the "Project Synapse" Google Calendar using smart keyword matching:
*   **Semester Start**: Prioritizes events exactly named **"全校開始上課"** (Start of all classes). If not found, falls back to generic "Start" events.
*   **Semester End**: Identified by **"寒假開始"** (Winter Break) or **"暑假開始"** (Summer Break). The semester end date is automatically set to **one day before** the break starts.
*   **18-Week Rule**: The system strictly limits auto-generated sessions to 18 weeks from the first class date.

### **CSV Import Specification**
When uploading `Courses` via CSV, the following logic applies:
*   **Format**: Standard CSV with headers `Name`, `Year`, `Semester`, `Schedule`.
*   **BOM Handling**: The system automatically strips Byte Order Marks (BOM) from Excel-exported files.
*   **Empty Rows**: Completely empty rows are automatically filtered out to prevent duplicate phantom courses.
*   **Session Merging**: Consecutive class periods on the same day (e.g., periods 2, 3, 4) are merged into a single session entry.

---

## 5. Maintenance Operations

### **Log Management**
The system logs events to the browser console and server stdout.
*   **Server Logs**: Check your terminal or Docker logs for backend traceback errors.
*   **Browser Console**: Use the in-app "Global Console" for operation history.

### **Updating the Application**
To update Project Synapse code:
```bash
git pull origin main
pip install -r requirements.txt  # If dependencies changed
docker-compose up -d --build     # If docker services changed
python app.py                    # Restart server
```

### **Google Token Refresh**
If Google integration stops working (e.g., Classroom sync fails):
1.  Delete the `tokens/` directory or `token.json`.
2.  Go to the **Classroom** page and click "Connect".
3.  Re-authenticate to generate a fresh token.
