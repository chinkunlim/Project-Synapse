# Google Keep Limitations and Alternatives

## What’s the issue?
- Google Keep’s OAuth scopes for reading notes are not publicly supported for third‑party web apps.
- Attempting to request `keep.readonly` or similar results in `invalid_scope` authorization errors.
- There is no official Google Keep REST API for general use comparable to Tasks/Drive/Classroom.

## What we did
- Removed Keep integration from the NDHU dashboard to prevent broken auth and errors.
- Focused on Google Tasks, which has a stable API for listing, creating, completing, and deleting tasks.

## Alternatives
- Use Google Tasks for actionable items and deadlines.
- Export Keep content manually when needed:
  - Google Takeout: export Keep notes in HTML/JSON.
  - Copy/paste important notes into Tasks or Notion.
- If Keep is essential, consider a personal script using unofficial methods at your own risk (not recommended for production).

## Enabling Steps (Tasks)
- NDHU OAuth now requests `https://www.googleapis.com/auth/tasks` (read/write).
- Dashboard supports:
  - List tasklists
  - Create tasks (title, notes, due)
  - Complete tasks
  - Delete tasks

## Future Direction
- If Google publishes official Keep APIs/scopes, we can add a read-only viewer and editor with proper consent.
- Until then, Tasks + Notion remains the recommended workflow for dashboard-managed items.
