from health_json import upsert_daily_health
from notion import NotionWorkoutSync
from whoop import WhoopClient


def main() -> None:
    whoop = WhoopClient()
    notion = NotionWorkoutSync()
    day = whoop.yesterday_iso()

    health_entry = whoop.fetch_health_metrics(day)
    upsert_daily_health(health_entry)

    workouts = whoop.fetch_workouts(day)
    for workout in workouts:
        notion.upsert_workout(workout)

    print(f"Synced {day}: health metrics and {len(workouts)} workouts")


if __name__ == "__main__":
    main()
