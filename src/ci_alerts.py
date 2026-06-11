import os


def running_in_github_actions() -> bool:
    return os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true"


def emit_whoop_auth_alert(error: str) -> None:
    """Surface Whoop auth failures in the GitHub Actions job summary and annotations."""
    if not running_in_github_actions():
        return

    remediation = (
        "1. Run `python scripts/get_token.py` locally\n"
        "2. Update the `WHOOP_REFRESH_TOKEN` repository secret\n"
        "3. Verify `GH_REPO_PAT` is set, not expired, and has **Secrets: Read and write**\n"
        "4. Re-run this workflow manually"
    )
    summary = (
        "## Whoop auth failed\n\n"
        "The scheduled sync could not refresh the Whoop OAuth token. "
        "Until this is fixed, hourly runs will keep failing.\n\n"
        f"**Error:** `{error}`\n\n"
        "### Recovery\n\n"
        f"{remediation}\n"
    )
    _append_step_summary(summary)
    # GitHub Actions workflow command — shows under Annotations on the run page.
    print(f"::error title=Whoop auth failed::{error}")


def emit_whoop_secret_persist_ok() -> None:
    if not running_in_github_actions():
        return
    _append_step_summary("- Whoop refresh token persisted to `WHOOP_REFRESH_TOKEN` secret\n")


def _append_step_summary(markdown: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write(markdown)
