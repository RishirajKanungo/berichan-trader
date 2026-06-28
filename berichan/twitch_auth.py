"""
Reusable Twitch OAuth (implicit grant) helper.

Opens the Twitch authorization page in the browser and runs a tiny local
HTTP server to capture the access token from the redirect fragment. Used by
the GUI's "Re-authenticate" button and available to scripts.

obtain_token() is blocking; call it from a worker thread / executor so it
doesn't freeze a UI event loop.
"""

from __future__ import annotations

import json
import secrets
import threading
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

REDIRECT_PORT = 3000
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"
SCOPES = "chat:read chat:edit user:manage:whispers"
REQUIRED_SCOPES = SCOPES.split()
_VALIDATE_URL = "https://id.twitch.tv/oauth2/validate"

_CAPTURE_PAGE = """\
<!DOCTYPE html>
<html>
<head><title>Twitch Auth</title></head>
<body>
<p>Capturing token…</p>
<script>
  const params = new URLSearchParams(window.location.hash.slice(1));
  const token = params.get("access_token");
  const state = params.get("state") || "";
  if (token) {
    fetch("/callback?token=" + encodeURIComponent(token)
          + "&state=" + encodeURIComponent(state))
      .then(() => {
        document.body.innerHTML =
          "<h2>&#9989; Token captured!</h2><p>You can close this tab and return to the app.</p>";
      });
  } else {
    document.body.innerHTML = "<h2>&#10060; No token found.</h2>";
  }
</script>
</body>
</html>
"""


def authorize_url(client_id: str, scopes: str = SCOPES, state: str = "") -> str:
    url = (
        "https://id.twitch.tv/oauth2/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri={REDIRECT_URI}"
        "&response_type=token"
        f"&scope={scopes.replace(' ', '+')}"
    )
    if state:
        url += f"&state={state}"
    return url


def obtain_token(
    client_id: str, scopes: str = SCOPES, timeout: float = 180.0
) -> str | None:
    """
    Run the browser OAuth flow and return the raw access token (no 'oauth:'
    prefix), or None on timeout / state mismatch. Blocking.

    A random `state` is sent on the authorize request and verified on the
    redirect to reject tokens that didn't originate from this request.
    """
    captured: dict[str, str] = {}
    done = threading.Event()
    expected_state = secrets.token_urlsafe(24)

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/":
                body = _CAPTURE_PAGE.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif parsed.path == "/callback":
                qs = parse_qs(parsed.query)
                token = qs.get("token", [None])[0]
                state = qs.get("state", [""])[0]
                if token and secrets.compare_digest(state, expected_state):
                    captured["token"] = token
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"OK")
                done.set()

        def log_message(self, *_):
            pass

    server = HTTPServer(("localhost", REDIRECT_PORT), _Handler)
    serve_thread = threading.Thread(target=server.serve_forever, daemon=True)
    serve_thread.start()

    try:
        webbrowser.open(authorize_url(client_id, scopes, expected_state))
        done.wait(timeout=timeout)
    finally:
        server.shutdown()
        server.server_close()

    return captured.get("token")


def validate_token(token: str, timeout: float = 10.0) -> dict | None:
    """
    Validate a Twitch access token via the OAuth /validate endpoint.

    Returns a dict {login, user_id, scopes, expires_in} on success, or None if
    the token is missing, expired, or invalid. Accepts a token with or without
    the 'oauth:' prefix. Blocking — call from a worker thread / executor.
    """
    raw = token[len("oauth:"):] if token.startswith("oauth:") else token
    if not raw:
        return None
    req = urllib.request.Request(
        _VALIDATE_URL, headers={"Authorization": f"OAuth {raw}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return None
    return {
        "login": data.get("login", ""),
        "user_id": data.get("user_id", ""),
        "scopes": data.get("scopes", []),
        "expires_in": data.get("expires_in", 0),
    }


def missing_scopes(scopes: list[str]) -> list[str]:
    """Return the required scopes not present in the given list."""
    return [s for s in REQUIRED_SCOPES if s not in scopes]
