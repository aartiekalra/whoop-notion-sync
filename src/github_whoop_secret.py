import os
import subprocess


def update_whoop_refresh_token_secret_if_configured(refresh_token: str) -> None:
    """If GH_REPO_PAT and GITHUB_REPOSITORY are set, persist WHOOP_REFRESH_TOKEN to repo secrets.

    WHOOP rotates refresh tokens on each refresh; without this, scheduled runs fail after the first job.
    """
    pat = os.environ.get("GH_REPO_PAT", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not pat or not repo:
        return

    subprocess.run(
        [
            "gh",
            "secret",
            "set",
            "WHOOP_REFRESH_TOKEN",
            "--repo",
            repo,
            "--body",
            refresh_token,
        ],
        env={**os.environ, "GH_TOKEN": pat},
        check=True,
        timeout=120,
    )
