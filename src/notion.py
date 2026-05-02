import os
from typing import Any, Dict, Optional

import requests

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


class NotionWorkoutSync:
    def __init__(self) -> None:
        self.token = os.environ["NOTION_TOKEN"]
        self.database_id = os.environ["NOTION_DATABASE_ID"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    def upsert_workout(self, workout: Dict[str, Any]) -> str:
        page_id = self._find_existing_workout(workout["date"], workout["start_time"])
        payload = self._build_properties(workout)

        if page_id:
            response = requests.patch(
                f"{NOTION_API_BASE}/pages/{page_id}",
                headers=self.headers,
                json={"properties": payload},
                timeout=30,
            )
            response.raise_for_status()
            return "updated"

        response = requests.post(
            f"{NOTION_API_BASE}/pages",
            headers=self.headers,
            json={
                "parent": {"database_id": self.database_id},
                "properties": payload,
            },
            timeout=30,
        )
        response.raise_for_status()
        return "created"

    def _find_existing_workout(self, day: str, start_time: str) -> Optional[str]:
        response = requests.post(
            f"{NOTION_API_BASE}/databases/{self.database_id}/query",
            headers=self.headers,
            json={
                "filter": {
                    "and": [
                        {"property": "Date", "date": {"equals": day}},
                        {"property": "Start Time", "rich_text": {"equals": start_time}},
                    ]
                }
            },
            timeout=30,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        if not results:
            return None
        return results[0].get("id")

    @staticmethod
    def _build_properties(workout: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "Date": {"date": {"start": workout["date"]}},
            "Sport": {"select": {"name": str(workout["sport"])}},
            "Strain": {"number": _to_float(workout["strain"])},
            "Start Time": {"rich_text": [{"text": {"content": str(workout["start_time"])}}]},
            "End Time": {"rich_text": [{"text": {"content": str(workout["end_time"])}}]},
        }


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
