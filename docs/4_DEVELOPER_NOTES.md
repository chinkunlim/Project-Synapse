# 🧑‍💻 Developer Notes — Project Synapse

Technical reference for developers extending or maintaining **Project Synapse**.

---

## 1. Architecture Overview

Project Synapse follows a **Flask Blueprint** pattern with clear separation of concerns:

```
app.py                   ← Application factory (no business logic here)
extensions.py            ← Global singleton instances (Notion, Google clients)
routes/                  ← URL handlers, grouped by domain (Blueprint per file)
integrations/            ← All external API adapters
utils/                   ← Internal stateless helpers (no external API deps)
config/                  ← Static configuration classes and files
```

### Design Principles
- `integrations/` depends on external APIs (Notion, Google, N8N)
- `utils/` contains only pure internal logic
- Routes call `integrations/` and `utils/` — never the other way around
- `load_dotenv(override=True)` is called inside routes that need fresh env values

---

## 2. Core Pipelines

### A. Course CSV Import Pipeline

```
User uploads CSV
    ↓
routes/notion_routes.py  ← validates file, reads multipart form
    ↓
utils/course_import_processor.py
    ├─ lstrip('\ufeff')            ← BOM removal (Excel compatibility)
    ├─ filter empty rows
    └─ parse_course_row()          ← field name auto-detection (中/EN)
         └─ utils/course_schedule_parser.py
              └─ parse_schedule("三9/三10/三11")
                   → [(Wed, period9, 14:10, 15:00), ...]
                   → merged into (Wed, 14:10, 17:10)
    ↓
integrations/notion/processor.py
    ├─ create_page() in Course Hub
    └─ _generate_course_sessions()
         ├─ compute 18 weekly dates from semester start
         ├─ all datetimes as "2025-09-03T14:10:00+08:00"
         └─ create_page() × 18 in Class Sessions
```

**Key extension point**: `utils/course_import_processor.py → parse_course_row()` — add new column mappings here.

### B. Google Calendar Semester Sync

```
google_calendar_sync.py
    ├─ fetch iCal from GOOGLE_CALENDAR_URL
    ├─ parse events with icalendar
    ├─ match titles by regex patterns (priority 2 > priority 1)
    │   ├─ Priority 2: "全校開始上課" → exact semester start
    │   └─ Priority 1: "114-1 Start" → generic fallback
    ├─ infer semester from month (Feb→Spring, Sept→Fall)
    └─ filter by ENROLLMENT_YEAR to skip past semesters
```

### C. Notion Database Auto-Recovery

```
processor.find_database_by_title(title)
    ├─ Step 1: _find_db_in_children(PARENT_PAGE_ID, title, depth=2)
    │   ├─ get_block_children(page_id) → blocks
    │   ├─ match child_database by title → return ID
    │   └─ recurse into child_page blocks (depth-limited)
    └─ Step 2 (fallback): client.search(query=title, filter_type="database")
```

> **Why traversal?** Notion's search API only sees objects directly shared with the integration. Nested databases inside sub-pages are invisible to search; traversal bypasses this.

---

## 3. Key Files Reference

| File | Purpose |
|---|---|
| `integrations/notion/client.py` | Low-level HTTP wrapper for Notion REST API |
| `integrations/notion/processor.py` | Business logic: CSV → Notion payload transformation |
| `integrations/google_calendar_sync.py` | iCal parsing + semester date extraction |
| `integrations/google_classroom_integration.py` | Classroom, Drive, and OAuth flows |
| `integrations/google_ndhu_integration.py` | NDHU Google Tasks integration |
| `utils/course_schedule_parser.py` | Taiwan course schedule notation parser |
| `utils/course_import_processor.py` | CSV reading and course row transformation |
| `utils/task_queue.py` | `ThreadPoolExecutor` background task queue |
| `utils/validators.py` | `@validate_json_params` decorator |
| `utils/errors.py` | Global error handler with Trace IDs |
| `config/course_schedule_config.py` | 14 class periods + semester database |

---

## 4. Extension Cookbook

### Adding a New CSV Column

Example: Adding a "Room Number" column to courses.

1. **Update Notion**: Add a `Text` property named `Room` to Course Hub database.
2. **Update processor**:
   ```python
   # in utils/course_import_processor.py → parse_course_row()
   if '教室' in row or 'Room' in row:
       result['room'] = row.get('教室') or row.get('Room', '')
   ```
3. **Map to Notion payload**:
   ```python
   # in integrations/notion/processor.py → _build_course_properties()
   if course_data.get('room'):
       properties['Room'] = {'rich_text': [{'text': {'content': course_data['room']}}]}
   ```

### Adding a New Database Type for CSV Import

1. Add `NEW_DB_ID` to `.env`
2. Update `routes/notion_routes.py` to accept `type="new_type"` in the upload endpoint
3. Add handling in `processor.import_csv_to_database()` for the new type

### Adding a New Dashboard Widget

1. **Backend**: Create route in `routes/main_routes.py` returning JSON:
   ```python
   @main_bp.route('/api/my-widget')
   def my_widget():
       return jsonify({"data": ...})
   ```
2. **Frontend**: Add `<div id="my-widget">` in `templates/index.html`
3. Create `static/js/my_widget.js` to fetch and render

### Modifying Class Period Times

Edit `config/course_schedule_config.py`:
```python
from datetime import time

CLASS_PERIODS = {
    9: (time(14, 10), time(15, 0)),   # Period 9: 14:10–15:00
    # ... modify as needed
}
```

### Adding a New Semester

```python
# config/course_schedule_config.py
SEMESTER_DATABASE[(115, 1)] = Semester(
    year=115,
    semester=1,
    start_date=datetime(2026, 9, 1),
    end_date=datetime(2026, 12, 31)
)
```

---

## 5. Known Issues & Common Pitfalls

### "Database ID Not Found"
- **Cause**: `.env` was updated, but `load_dotenv` wasn't re-called
- **Fix**: Routes that read DB IDs use `load_dotenv(override=True)` on each request

### "[SSL] Record Layer Failure" (Google APIs)
- **Cause**: Shared `googleapiclient` service across threads
- **Fix**: Always re-instantiate Google service objects per request, never as globals

### Timezone Offsets ("8-Hour Late" Events)
- **Standard**: Use `datetime.replace(tzinfo=timezone(timedelta(hours=8)))`
- **Notion API**: Requires ISO 8601 with TZ offset: `"2025-09-01T09:00:00+08:00"` — naive strings default to UTC

### Notion Search API Limitations
- Notion search only returns objects **directly shared** with the integration
- Databases nested inside sub-pages require the **recursive block traversal** approach in `find_database_by_title()`

### N8N "Force Execute" Not Working
- `POST /api/v1/workflows/{id}/run` requires n8n v1.x
- Older versions don't support remote execution for non-webhook workflows
- Solution: Add a Webhook trigger node alongside the Schedule trigger

---

## 6. Testing

Run the course system integration test (no network required):
```bash
docker exec dashboard python /app/scripts/init_taiwan_course_system.py
```

Expected output:
```
✅ 5/5 tests passed
✅ Period configuration: 14 periods
✅ Schedule parsing: 三9/三10/三11 → Wed 14:10–17:10
✅ CSV import: 9 sample courses parsed
```

Manual Notion API test:
```bash
docker exec dashboard python -c "
from integrations.notion.processor import NotionProcessor
import os
p = NotionProcessor(os.getenv('NOTION_API_KEY'))
print(p.find_database_by_title('Tasks'))
"
```
