# 🧑‍💻 Developer Notes & Architecture Guide

This document acts as the technical "Bible" for Project Synapse. It explains **how it works under the hood** and provides step-by-step recipes for **extending functionality**.

---

## 1. System Architecture

Project Synapse is built on a **Microservice-Lite** pattern using Flask Blueprints.

### **Directory Structure Explained**
*   `app.py`: The application factory. It initializes extensions and registers Blueprints. **Do not add business logic here.**
*   `routes/`: Contains all URL endpoints, grouped by domain.
    *   `notion_routes.py`: Handles CSV upload, database listing, and sync triggers.
    *   `main_routes.py`: Renders the dashboard and handles Google Task API proxies.
*   `intergrations/`: (Typo specific to legacy repo) Logic adapters for external APIs.
    *   `intergrations/notion/processor.py`: **The Core Engine**. Handles all data transformation (CSV -> Notion Payload).
    *   `intergrations/notion/client.py`: Low-level wrapper around `notion-client` library.
*   `utils/`: Stateless helper functions.
    *   `google_calendar_sync.py`: Specialized logic for parsing academic dates from iCal.

---

## 2. Core Logic Pipelines

### **A. CSV Import Pipeline (`processor.py`)**
When a user uploads a CSV to `/api/notion/import_csv`:
1.  **Read & Sanitize**: `import_csv_to_database` reads the file stream.
    *   *Crucial Step*: `csv_content.lstrip('\ufeff')` removes BOM characters common in Excel exports.
    *   *Filter*: Empty rows are discarded immediately.
2.  **Row Parsing**: `_build_properties_from_csv_row` maps CSV headers to Notion Properties.
    *   It checks `notion_schema.json` (deprecated) or internal mapping logic.
    *   **Extension Point**: Modify this method to support new columns (e.g., adding "Instructor Name").
3.  **Session Generation** (For Courses):
    *   If the database type is `courses`, `_generate_course_sessions` is triggered.
    *   It calculates 18 weeks of dates based on the **First Class Date (Week 1)**.
    *   **Timezone**: All dates are converted to `UTC+8` using `TZ_TAIPEI`.

### **B. Google Calendar Sync (`google_calendar_sync.py`)**
Synchronizing semester dates involves complex regex matching to handle human-written event titles.
*   **Priority System**:
    *   **Priority 2 (High)**: Overwrites everything. Matches exact events like `全校開始上課` (Start of all classes) vs generic "Start".
    *   **Priority 1 (Low)**: Generic fallbacks (e.g., `114-1 Start`).
*   **Date Inference**: If an event has no "Year/Semester" in the title (e.g., just "Start"), the system infers it from the month (Feb=Spring, Sept=Fall).

---

## 3. 🛠️ Extension Guide (Cookbook)

### **Scenario A: Adding a New CSV Column**
You want to import a "Credit Hours" column for courses.

1.  **Update Notion**: Add a "Number" property named "Credits" to your Notion Database.
2.  **Update Processor**:
    *   Open `intergrations/notion/processor.py`.
    *   Locate `_build_properties_from_csv_row`.
    *   Add mapping logic:
        ```python
        # Map CSV 'Credit' header to Notion 'Credits' property
        if 'Credit' in row:
            properties['Credits'] = {'number': int(row['Credit'])}
        ```
3.  **Deploy**: Restart the service.

### **Scenario B: Supporting a New Database Type**
You want to manage "Student profiles" in Synapse.

1.  **Config**: Add `STUDENT_DATABASE_ID` to `.env` and `config/config.py`.
2.  **Route**: Update `routes/notion_routes.py` to accept `type="students"` in the upload endpoint.
3.  **Processor**:
    *   Update `import_csv_to_database` to handle `database_type == 'students'`.
    *   Define validation rules (e.g., "Student ID" is required).

### **Scenario C: Creating a New Dashboard Widget**
1.  **Backend**: Create a route in `routes/main_routes.py` that returns the data JSON (e.g., `/api/students/stats`).
2.  **Frontend**:
    *   Edit `templates/index.html` to add a placeholder `<div>`.
    *   Create `static/js/students.js` to fetch from your API and render the UI.
    *   Import your script in `index.html`.

---

## 4. Debugging & Common Issues

### **"Database ID Not Found"**
*   **Cause**: The `.env` file was updated, but the generic config loader didn't pick it up.
*   **Fix**: We force `load_dotenv(override=True)` in specific routes (`notion_routes.py`) to guarantee fresh config is read on each request.

### **"[SSL] Record Layer Failure"**
*   **Cause**: Sharing a single `googleapiclient` service object across threads (Flask requests).
*   **Fix**: Always verify `utils/google_*.py` uses **thread-local storage** or re-instantiates services per request. Never make the service object a global variable.

### **Timezone Offsets**
*   **Standard**: Always use `datetime.replace(tzinfo=timezone(timedelta(hours=8)))`.
*   **Notion API**: Requires ISO 8601 strings *with offsets* (e.g., `2024-01-01T09:00:00+08:00`). Sending naive strings defaults to UTC, causing "8-hour late" times.
