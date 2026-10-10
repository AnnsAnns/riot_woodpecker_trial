#!/usr/bin/env python3
"""
Headless Forgejo OAuth login against a local Woodpecker server.

Drives the full authorization-code flow without a browser and prints the
Woodpecker personal access token on stdout.

Assumes (host-side):
  - Woodpecker at http://localhost:8000
  - Forgejo    at http://localhost:3000
and that Woodpecker is configured with FORGEJO_URL=http://forgejo:3000 and
HOST=http://woodpecker-server:8000 (container names). Those are rewritten to
localhost for the host-side HTTP requests.
"""

import http.cookiejar
import base64
import hashlib
import hmac
import json
import os
import re
import subprocess
import sqlite3
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

WP = os.environ.get("POC_WP_URL", "http://localhost:8000")
FJ = os.environ.get("POC_FJ_URL", "http://localhost:3000")
USER = os.environ.get("POC_FORGEJO_ADMIN", "pocadmin")
PASSWORD = os.environ.get("POC_FORGEJO_ADMIN_PASSWORD", "pocpassword123")

REWRITE = {
    "//forgejo:3000": "//localhost:3000",
    "//woodpecker-server:8000": "//localhost:8000",
}

REDIRECT_CODES = (301, 302, 303, 307, 308)


def rewrite(url: str) -> str:
    for a, b in REWRITE.items():
        url = url.replace(a, b)
    return url


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):  # noqa: D102
        return None


jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(
    urllib.request.HTTPCookieProcessor(jar), NoRedirect()
)


def http(method, url, data=None, cookie=None):
    url = rewrite(url)
    headers = {"User-Agent": "poc-oauth"}
    if cookie:
        headers["Cookie"] = cookie
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = opener.open(request)
        return resp.getcode(), resp.geturl(), resp.read().decode("utf-8", "replace"), resp.headers
    except urllib.error.HTTPError as e:
        return e.code, e.geturl(), e.read().decode("utf-8", "replace"), e.headers


def follow(url, limit=12):
    for _ in range(limit):
        code, cur, body, hdrs = http("GET", url)
        if code in REDIRECT_CODES:
            url = urllib.parse.urljoin(cur, hdrs.get("Location"))
            continue
        return code, cur, body, hdrs
    raise RuntimeError("too many redirects")


def csrf(html: str) -> str:
    m = re.search(r'name="_csrf"\s+value="([^"]+)"', html)
    if not m:
        m = re.search(r'value="([^"]+)"\s+name="_csrf"', html)
    if not m:
        raise RuntimeError("no _csrf token found")
    return m.group(1)


def hidden_inputs(html: str) -> dict:
    out = {}
    for tag in re.findall(r"<input\b[^>]*>", html):
        name = re.search(r'name="([^"]+)"', tag)
        value = re.search(r'value="([^"]*)"', tag)
        if name:
            out[name.group(1)] = value.group(1) if value else ""
    return out


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def mint_user_token(secret: str, user_id: int) -> str:
    """Mint the JWT Woodpecker accepts as a personal access token.

    Mirrors shared/token.Token.Sign: HS256 over {user-id, type=user} with the
    user's hash as the secret.
    """
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"},
                               separators=(",", ":")).encode())
    payload = b64url(json.dumps({"user-id": str(user_id), "type": "user"},
                                separators=(",", ":")).encode())
    signing_input = f"{header}.{payload}"
    sig = hmac.new(secret.encode(), signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{b64url(sig)}"


def read_user_credentials(login: str):
    """Read (id, hash) for `login` from the Woodpecker sqlite DB via docker cp."""
    container = os.environ.get("POC_WP_CONTAINER", "poc-woodpecker-server")
    db_in_container = os.environ.get(
        "POC_WP_DB", "/var/lib/woodpecker/woodpecker.sqlite"
    )
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        subprocess.run(
            ["docker", "cp", f"{container}:{db_in_container}", path],
            check=True, capture_output=True,
        )
        con = sqlite3.connect(path)
        try:
            row = con.execute(
                "SELECT id, hash FROM users WHERE login = ?", (login,)
            ).fetchone()
        finally:
            con.close()
    finally:
        os.unlink(path)
    if not row:
        raise RuntimeError(f"user {login!r} not found in Woodpecker DB")
    return row[0], row[1]


def main():
    # 1. kick off OAuth -> Woodpecker 303 to Forgejo authorize URL
    code, cur, body, hdrs = http("GET", f"{WP}/authorize")
    if code not in REDIRECT_CODES:
        raise RuntimeError(f"expected redirect from {WP}/authorize, got {code}")
    authorize_url = urllib.parse.urljoin(cur, hdrs.get("Location"))
    print(f"[login] authorize -> {authorize_url}", file=sys.stderr)

    # 2. follow to Forgejo login page (we are not logged in yet)
    code, cur, body, hdrs = follow(authorize_url)
    if code != 200:
        raise RuntimeError(f"expected login page, got {code} at {cur}")
    token = csrf(body)

    # where Forgejo should send us back after login
    redirect_to = urllib.parse.parse_qs(urllib.parse.urlparse(cur).query).get(
        "redirect_to", [authorize_url]
    )[0]

    # 3. submit credentials
    code, cur, body, hdrs = http(
        "POST",
        f"{FJ}/user/login",
        {"_csrf": token, "user_name": USER, "password": PASSWORD,
         "redirect_to": redirect_to},
    )
    if code not in REDIRECT_CODES:
        raise RuntimeError(f"login failed (got {code}); check credentials")
    grant_url = urllib.parse.urljoin(cur, hdrs.get("Location"))
    print(f"[login] logged in -> {grant_url}", file=sys.stderr)

    # 4. Forgejo grant page (or straight back to Woodpecker if already granted)
    code, cur, body, hdrs = follow(grant_url)
    if code in REDIRECT_CODES:  # pragma: no cover - defensive
        callback = urllib.parse.urljoin(cur, hdrs.get("Location"))
    elif "login/oauth/grant" in body or "authorize" in body.lower():
        if os.environ.get("POC_LOGIN_DEBUG"):
            with open("/tmp/poc-grant.html", "w") as f:
                f.write(body)
            print("[login] dumped grant page to /tmp/poc-grant.html", file=sys.stderr)
        fields = hidden_inputs(body)
        fields["_csrf"] = csrf(body)
        # Gitea/Forgejo render the approve control as a submit button with
        # name="granted"; include it explicitly.
        if "granted" not in fields:
            fields["granted"] = "true"
        code, cur, body, hdrs = http("POST", f"{FJ}/login/oauth/grant", fields)
        if code not in REDIRECT_CODES:
            raise RuntimeError(f"grant failed (got {code})")
        callback = urllib.parse.urljoin(cur, hdrs.get("Location"))
    else:
        callback = cur
    print(f"[login] callback -> {callback}", file=sys.stderr)

    # 5. hit Woodpecker callback -> sets user_sess cookie
    code, cur, body, hdrs = follow(callback)
    print(f"[login] session established ({code})", file=sys.stderr)
    if os.environ.get("POC_LOGIN_DEBUG"):
        for c in jar:
            print(f"[login] cookie {c.name}={c.value[:10]}... domain={c.domain} path={c.path} secure={c.secure}", file=sys.stderr)

    # 6. mint a personal access token from the user record. We cannot use the
    # browser session for API calls because session tokens additionally require
    # a CSRF header, so instead we reproduce Woodpecker's user-token JWT
    # (HS256, secret = user.hash) using the hash stored in the DB.
    user_id, user_hash = read_user_credentials(USER)
    token = mint_user_token(user_hash, user_id)
    print(f"[login] minted user token for id={user_id}", file=sys.stderr)
    print(token)


if __name__ == "__main__":
    main()
