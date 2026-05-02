import os
import secrets
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import requests

AUTH_URL = "https://api.prod.whoop.com/oauth/oauth2/auth"
TOKEN_URL = "https://api.prod.whoop.com/oauth/oauth2/token"
REDIRECT_URI = "http://localhost:8000/callback"


class CallbackHandler(BaseHTTPRequestHandler):
    server_version = "WhoopOAuth/1.0"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        params = parse_qs(parsed.query)
        self.server.auth_code = params.get("code", [None])[0]  # type: ignore[attr-defined]
        self.server.auth_state = params.get("state", [None])[0]  # type: ignore[attr-defined]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<h1>Whoop authorization received. You can close this tab.</h1>")

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def main() -> None:
    client_id = os.environ.get("WHOOP_CLIENT_ID")
    client_secret = os.environ.get("WHOOP_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Set WHOOP_CLIENT_ID and WHOOP_CLIENT_SECRET first")

    state = secrets.token_urlsafe(16)
    auth_params = urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "scope": "offline read:recovery read:sleep read:cycles read:workout",
            "state": state,
        }
    )
    url = f"{AUTH_URL}?{auth_params}"

    server = HTTPServer(("localhost", 8000), CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    print("Opening browser for Whoop OAuth...")
    print(url)
    webbrowser.open(url)

    try:
        while getattr(server, "auth_code", None) is None:
            time.sleep(0.2)
    finally:
        server.shutdown()
        thread.join(timeout=2)

    code = getattr(server, "auth_code", None)
    returned_state = getattr(server, "auth_state", None)
    if not code:
        raise RuntimeError("No authorization code received")
    if returned_state != state:
        raise RuntimeError("OAuth state mismatch")

    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        raise RuntimeError("No refresh token returned")

    print("\nInitial Whoop refresh token:\n")
    print(refresh_token)
    print("\nStore this in GitHub Actions secret WHOOP_REFRESH_TOKEN")


if __name__ == "__main__":
    main()
