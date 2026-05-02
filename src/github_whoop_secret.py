import os
import subprocess
import tempfile


def update_whoop_refresh_token_secret_if_configured(refresh_token: str) -> None:
    """If GH_REPO_PAT and GITHUB_REPOSITORY are set, persist WHOOP_REFRESH_TOKEN to repo secrets.

    WHOOP rotates refresh tokens on each refresh; without this, scheduled runs fail after the first job.
    """
    pat = os.environ.get("GH_REPO_PAT", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not pat or not repo:
        return

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
            timeout=120,
        )
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
