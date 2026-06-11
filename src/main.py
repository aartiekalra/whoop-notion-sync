from ci_alerts import emit_whoop_auth_alert, emit_whoop_secret_persist_ok
from github_whoop_secret import update_whoop_refresh_token_secret_if_configured
from health_json import upsert_daily_health
from notion import NotionWorkoutSync
from whoop import WhoopClient


def _is_whoop_auth_error(message: str) -> bool:
    markers = (
        "Whoop token refresh failed",
        "WHOOP_REFRESH_TOKEN",
        "GH_REPO_PAT",
        "invalid_grant",
    )
    lowered = message.lower()
    return any(marker.lower() in lowered for marker in markers)


def main() -> None:
    try:
        whoop = WhoopClient()
        update_whoop_refresh_token_secret_if_configured(whoop.refresh_token)
        emit_whoop_secret_persist_ok()
        notion = NotionWorkoutSync()
        day = whoop.yesterday_iso()

        health_entry = whoop.fetch_health_metrics(day)
        upsert_daily_health(health_entry)

        workouts = whoop.fetch_workouts(day)
        for workout in workouts:
            notion.upsert_workout(workout)

        print(f"Synced {day}: health metrics and {len(workouts)} workouts")
    except RuntimeError as exc:
        if _is_whoop_auth_error(str(exc)):
            emit_whoop_auth_alert(str(exc))
        raise


if __name__ == "__main__":
    main()
