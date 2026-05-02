import json
from pathlib import Path
from typing import Any, Dict, List

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "data.json"


def upsert_daily_health(entry: Dict[str, Any]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    records = _read_records()

    updated = False
    for idx, row in enumerate(records):
        if row.get("date") == entry.get("date"):
            records[idx] = entry
            updated = True
            break

    if not updated:
        records.append(entry)

    records.sort(key=lambda item: item.get("date", ""))
    DATA_FILE.write_text(json.dumps(records, indent=2), encoding="utf-8")


def _read_records() -> List[Dict[str, Any]]:
    if not DATA_FILE.exists():
        return []
    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []
