import base64
import os
import time

import requests
from nacl import public

GITHUB_API = "https://api.github.com"


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

    owner, name = repo.split("/", 1)
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    last_error: str | None = None
    for attempt in range(3):
        try:
            _put_repo_secret(headers, owner, name, "WHOOP_REFRESH_TOKEN", refresh_token)
            return
        except RuntimeError as exc:
            last_error = str(exc)
            if attempt < 2:
                time.sleep(2**attempt)

    raise RuntimeError(
        "Failed to persist WHOOP_REFRESH_TOKEN to GitHub secrets after WHOOP token refresh. "
        "WHOOP has already invalidated the previous refresh token, so you must re-authorize "
        "(python scripts/get_token.py) and update the WHOOP_REFRESH_TOKEN secret. "
        "GH_REPO_PAT may be expired or lack Secrets write permission. "
        f"{last_error or ''}".strip()
    )


def _put_repo_secret(
    headers: dict[str, str],
    owner: str,
    repo: str,
    secret_name: str,
    secret_value: str,
) -> None:
    key_url = f"{GITHUB_API}/repos/{owner}/{repo}/actions/secrets/public-key"
    key_response = requests.get(key_url, headers=headers, timeout=30)
    if key_response.status_code >= 400:
        raise RuntimeError(
            f"Could not fetch GitHub Actions public key ({key_response.status_code}): "
            f"{key_response.text.strip()}"
        )

    key_data = key_response.json()
    key_id = key_data.get("key_id")
    public_key = key_data.get("key")
    if not key_id or not public_key:
        raise RuntimeError("GitHub Actions public key response was missing key_id or key")

    encrypted = _encrypt_secret(public_key, secret_value)
    put_url = f"{GITHUB_API}/repos/{owner}/{repo}/actions/secrets/{secret_name}"
    put_response = requests.put(
        put_url,
        headers=headers,
        json={"encrypted_value": encrypted, "key_id": key_id},
        timeout=30,
    )
    if put_response.status_code >= 400:
        raise RuntimeError(
            f"Could not update {secret_name} ({put_response.status_code}): {put_response.text.strip()}"
        )


def _encrypt_secret(public_key: str, secret_value: str) -> str:
    public_key_bytes = base64.b64decode(public_key)
    sealed_box = public.SealedBox(public.PublicKey(public_key_bytes))
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")
