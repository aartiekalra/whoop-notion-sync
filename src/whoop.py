import os
from datetime import date, timedelta
from typing import Any, Dict, List, Tuple

import requests

WHOOP_API_BASE = "https://api.prod.whoop.com/developer/v2"
WHOOP_TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"


class WhoopClient:
    def __init__(self) -> None:
        self.client_id = os.environ["WHOOP_CLIENT_ID"].strip()
        self.client_secret = os.environ["WHOOP_CLIENT_SECRET"].strip()
        self.refresh_token = os.environ["WHOOP_REFRESH_TOKEN"].strip()
        self.access_token = self._refresh_access_token()

    def _refresh_access_token(self) -> str:
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "offline",
        }
        response = requests.post(WHOOP_TOKEN_URL, data=payload, timeout=30)

        # Some WHOOP app configs reject scope on refresh; retry once without it.
        if response.status_code >= 400:
            retry_payload = {k: v for k, v in payload.items() if k != "scope"}
            retry = requests.post(WHOOP_TOKEN_URL, data=retry_payload, timeout=30)
            if retry.ok:
                response = retry

        if response.status_code >= 400:
            detail = response.text.strip()
            raise RuntimeError(f"Whoop token refresh failed ({response.status_code}): {detail}")

        payload = response.json()
        token = payload.get("access_token")
        if not token:
            raise RuntimeError("Whoop OAuth response did not include access_token")
        new_refresh = payload.get("refresh_token")
        if new_refresh:
            self.refresh_token = str(new_refresh).strip()
        return token

    def _get(self, endpoint: str, day: str) -> Any:
        response = requests.get(
            f"{WHOOP_API_BASE}{endpoint}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            params={"start": day, "end": day},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def yesterday_iso() -> str:
        return (date.today() - timedelta(days=1)).isoformat()

    def fetch_health_metrics(self, day: str) -> Dict[str, Any]:
        recovery = self._get("/recovery", day)
        sleep = self._get("/activity/sleep", day)
        cycle = self._get("/cycle", day)

        recovery_item = self._first_item(recovery)
        sleep_item = self._first_item(sleep)
        cycle_item = self._first_item(cycle)

        sleep_ms = self._pick(sleep_item, ["total_in_bed_time_milli", "sleep_duration_ms", "duration_milli"], 0)
        sleep_hrs = round((sleep_ms or 0) / 3_600_000, 2)

        return {
            "date": day,
            "recovery_score": self._pick(recovery_item, ["recovery_score"], 0),
            "hrv": self._pick(recovery_item, ["hrv_rmssd_milli", "hrv"], 0.0),
            "resting_hr": self._pick(recovery_item, ["resting_heart_rate", "resting_hr"], 0),
            "sleep_duration_hrs": sleep_hrs,
            "sleep_performance": self._pick(sleep_item, ["sleep_performance_percentage", "sleep_performance"], 0),
            "daily_strain": self._pick(cycle_item, ["strain", "strain_score", "day_strain"], 0.0),
        }

    def fetch_workouts(self, day: str) -> List[Dict[str, Any]]:
        payload = self._get("/activity/workout", day)
        records = self._extract_records(payload)
        workouts: List[Dict[str, Any]] = []
        for row in records:
            workouts.append(
                {
                    "date": day,
                    "sport": self._pick(row, ["sport_name", "sport", "sport_id"], "Unknown"),
                    "strain": self._pick(row, ["score", "strain", "strain_score"], 0.0),
                    "start_time": self._pick(row, ["start", "start_time", "start_datetime"], ""),
                    "end_time": self._pick(row, ["end", "end_time", "end_datetime"], ""),
                }
            )
        return workouts

    @staticmethod
    def _extract_records(payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            return [row for row in payload if isinstance(row, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ("records", "data", "items", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
        return [payload]

    @staticmethod
    def _first_item(payload: Any) -> Dict[str, Any]:
        records = WhoopClient._extract_records(payload)
        return records[0] if records else {}

    @staticmethod
    def _pick(data: Dict[str, Any], keys: Tuple[str, ...] | List[str], default: Any) -> Any:
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]
        return default
