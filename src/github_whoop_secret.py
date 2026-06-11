import os
import subprocess
import tempfile
import time


def _running_in_github_actions() -> bool:
    return os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true"


def update_whoop_refresh_token_secret_if_configured(refresh_token: str) -> None:
    """If GH_REPO_PAT and GITHUB_REPOSITORY are set, persist WHOOP_REFRESH_TOKEN to repo secrets.

    WHOOP rotates refresh tokens on each refresh; without this, scheduled runs fail after the first job.
    """
    pat = os.environ.get("GH_REPO_PAT", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()

    if not pat or not repo:
        if _running_in_github_actions():
            raise RuntimeError(
                "GH_REPO_PAT is not configured. WHOOP rotates refresh tokens on every refresh; "
                "without persisting the new token to repository secrets, the next scheduled run "
                "will fail with invalid_grant. Add a fine-grained PAT with Secrets read/write."
            )
        return

    last_error: subprocess.CalledProcessError | None = None
    for attempt in range(3):
        try:
            _gh_secret_set(repo, pat, refresh_token)
            return
        except subprocess.CalledProcessError as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2**attempt)

    detail = ""
    if last_error and last_error.stderr:
        detail = last_error.stderr.decode("utf-8", errors="replace").strip()
    raise RuntimeError(
        "Failed to persist WHOOP_REFRESH_TOKEN to GitHub secrets after WHOOP token refresh. "
        "WHOOP has already invalidated the previous refresh token, so you must re-authorize "
        "(python scripts/get_token.py) and update the WHOOP_REFRESH_TOKEN secret. "
        f"GH_REPO_PAT may be expired or lack Secrets write permission. {detail}".strip()
    ) from last_error


def _gh_secret_set(repo: str, pat: str, refresh_token: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, suffix=".txt") as f:
        f.write(refresh_token)
        path = f.name

    try:
        subprocess.run(
            [
                "gh",
                "secret",
                "set",
                "WHOOP_REFRESH_TOKEN",
                "--repo",
                repo,
                "--body-file",
                path,
            ],
            env={**os.environ, "GH_TOKEN": pat},
            check=True,
            capture_output=True,
            timeout=120,
        )
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
