import json
import zipfile
from datetime import datetime
from typing import List, Dict, Any


def _safe_get(d: Dict[str, Any], key: str, default=None):
    v = d.get(key, default)
    return v if v is not None else default


def _parse_single_json(raw: Dict[str, Any]) -> Dict[str, Any]:
    title = _safe_get(raw, 'title', '')
    text = _safe_get(raw, 'textContent', '')
    labels = [l.get('name') for l in _safe_get(raw, 'labels', []) if isinstance(l, dict)]
    color = _safe_get(raw, 'color', None)
    is_pinned = bool(_safe_get(raw, 'isPinned', False))
    is_archived = bool(_safe_get(raw, 'isArchived', False))
    created_us = _safe_get(raw, 'createdTimestampUsec', None)
    updated_us = _safe_get(raw, 'userEditedTimestampUsec', None)

    def _fmt_ts(us):
        try:
            if us:
                return datetime.utcfromtimestamp(int(us) / 1_000_000).isoformat() + 'Z'
        except Exception:
            return None
        return None

    items = []
    for li in _safe_get(raw, 'listContent', []) or []:
        if isinstance(li, dict):
            items.append({
                'text': _safe_get(li, 'text', ''),
                'isChecked': bool(_safe_get(li, 'isChecked', False))
            })

    attachments = []
    for att in _safe_get(raw, 'attachments', []) or []:
        if isinstance(att, dict):
            attachments.append({
                'filePath': _safe_get(att, 'filePath', ''),
                'mimeType': _safe_get(att, 'mimeType', None)
            })

    return {
        'type': 'list' if items else 'note',
        'title': title,
        'text': text,
        'items': items,
        'labels': labels,
        'color': color,
        'isPinned': is_pinned,
        'isArchived': is_archived,
        'createdAt': _fmt_ts(created_us),
        'updatedAt': _fmt_ts(updated_us),
        'attachments': attachments,
    }


def parse_keep_takeout_zip(zip_path: str) -> List[Dict[str, Any]]:
    """Parse a Google Takeout Keep ZIP and return simplified items.
    Accepts standard Takeout structure where Keep JSON files are in the root or Keep/ folder.
    """
    items: List[Dict[str, Any]] = []
    with zipfile.ZipFile(zip_path, 'r') as z:
        for info in z.infolist():
            name = info.filename
            if not name.lower().endswith('.json'):
                continue
            # Skip manifest or non-note json
            base = name.rsplit('/', 1)[-1].lower()
            if base.startswith('index') or base.startswith('manifest'):
                continue
            try:
                with z.open(info) as fp:
                    data = json.loads(fp.read().decode('utf-8'))
                # Some Takeout exports wrap note data under 'notes'
                if isinstance(data, dict) and 'title' in data:
                    parsed = _parse_single_json(data)
                    items.append(parsed)
                elif isinstance(data, list):
                    for raw in data:
                        if isinstance(raw, dict):
                            items.append(_parse_single_json(raw))
            except Exception:
                # Ignore errors on malformed files to keep import robust
                continue
    return items
