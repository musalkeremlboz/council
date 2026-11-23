"""Single-owner OAuth 2.1 authorization server for COUNCIL.

Lets hosted Claude apps (claude.ai web, desktop, mobile) connect as a custom
connector: Claude registers itself (DCR), the owner approves on a login page with
the owner password, and Claude gets short-lived access tokens plus rotating
refresh tokens. The static token from ``<data>/token`` stays valid for hooks and
local Claude Code clients.
"""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import hmac
import html
import json
import os
import secrets
import sqlite3
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    RefreshToken,
    RegistrationError,
    TokenError,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

ACCESS_TTL = 3600
REFRESH_TTL = 60 * 60 * 24 * 60
CODE_TTL = 300
PENDING_TTL = 600
HOSTED_CALLBACKS = {"https://claude.ai/api/mcp/auth_callback", "https://claude.com/api/mcp/auth_callback"}
MAX_FAILURES = 5
FAILURE_WINDOW = 900
MIN_PASSWORD = 10   # characters, not bytes; the command line and the panel ask the same
MAX_PASSWORD = 200


def _h(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def allowed_redirect(uri: str) -> bool:
    if uri in HOSTED_CALLBACKS:
        return True
    p = urlparse(uri)
    return p.scheme == "http" and p.hostname in ("localhost", "127.0.0.1") and p.path == "/callback"


def _encode(password: str) -> bytes:
    """UTF-8 bytes of a password; a string that has none (a lone surrogate) raises a ValueError whose words carry
    no character of it, so no log or traceback can."""
    try:
        return password.encode("utf-8")
    except UnicodeEncodeError:
        pass
    raise ValueError("the password is not valid UTF-8")


def hash_password(password: str) -> dict:
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(_encode(password), salt=salt, n=2**14, r=8, p=1)
    return {"salt": salt.hex(), "hash": dk.hex(), "n": 2**14}


def check_password(password: str, record: dict) -> bool:
    try:
        raw = _encode(password)
    except ValueError:
        return False
    dk = hashlib.scrypt(raw, salt=bytes.fromhex(record["salt"]), n=record["n"], r=8, p=1)
    return hmac.compare_digest(dk.hex(), record["hash"])


def _keep_owner(old: Path, tmp: str) -> None:
    """Give the new file the old one's owner and group, so a service running as its own user can still read a file
    the owner replaced with sudo. Where that is not allowed or not possible (Windows), the file stays as it is."""
    chown = getattr(os, "chown", None)
    if chown is None:
        return
    try:
        st = os.stat(old)
        chown(tmp, st.st_uid, st.st_gid)
    except OSError:  # PermissionError included; no old file
        pass


def write_owner(data_dir: Path, password: str) -> None:
    """Replace owner.json with the record of a new password, whole or not at all: the record goes to a temporary
    file in the same folder (so the rename is atomic), readable by the owner alone, then takes the old one's place.
    The memory service reads the file on every check, so the new password holds there at once."""
    data = Path(data_dir)
    body = json.dumps(hash_password(password))
    fd, tmp = tempfile.mkstemp(prefix=".owner-", suffix=".tmp", dir=data)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o600)
        _keep_owner(data / "owner.json", tmp)
        os.replace(tmp, data / "owner.json")
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


class OwnerOAuthProvider:
    def __init__(self, data_dir: Path, base_url: str, static_token: str):
        self.data = Path(data_dir)
        self.base = base_url.rstrip("/")
        self.static_token = static_token
        self._lock = threading.Lock()
        self._failures: list[float] = []
        self.db = sqlite3.connect(self.data / "oauth.sqlite3", check_same_thread=False)
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS clients(id TEXT PRIMARY KEY, info TEXT NOT NULL, created REAL);
            CREATE TABLE IF NOT EXISTS pending(id TEXT PRIMARY KEY, client_id TEXT, params TEXT, expires REAL);
            CREATE TABLE IF NOT EXISTS codes(hash TEXT PRIMARY KEY, data TEXT, expires REAL);
            CREATE TABLE IF NOT EXISTS tokens(hash TEXT PRIMARY KEY, kind TEXT, data TEXT, expires REAL);
            """
        )

    # ---------- helpers ----------
    def _q(self, sql: str, args: tuple = ()):
        with self._lock, self.db:
            return self.db.execute(sql, args).fetchall()

    def owner_record(self) -> dict | None:
        f = self.data / "owner.json"
        return json.loads(f.read_text()) if f.exists() else None

    # ---------- clients ----------
    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        rows = self._q("SELECT info FROM clients WHERE id=?", (client_id,))
        return OAuthClientInformationFull.model_validate_json(rows[0][0]) if rows else None

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        uris = [str(u) for u in (client_info.redirect_uris or [])]
        if not uris or not all(allowed_redirect(u) for u in uris):
            raise RegistrationError("invalid_redirect_uri", "only Claude callback URLs are accepted")
        self._q("INSERT OR REPLACE INTO clients VALUES(?,?,?)", (client_info.client_id, client_info.model_dump_json(), time.time()))

    # ---------- authorization ----------
    async def authorize(self, client: OAuthClientInformationFull, params: AuthorizationParams) -> str:
        rid = secrets.token_urlsafe(24)
        self._q("DELETE FROM pending WHERE expires < ?", (time.time(),))
        self._q("INSERT INTO pending VALUES(?,?,?,?)", (rid, client.client_id, params.model_dump_json(), time.time() + PENDING_TTL))
        return f"{self.base}/login?req={rid}"

    def _pending(self, rid: str):
        rows = self._q("SELECT client_id, params FROM pending WHERE id=? AND expires > ?", (rid, time.time()))
        return (rows[0][0], AuthorizationParams.model_validate_json(rows[0][1])) if rows else None

    async def login_page(self, request: Request):
        rid = request.query_params.get("req", "") if request.method == "GET" else (await request.form()).get("req", "")
        pending = self._pending(str(rid))
        if not pending:
            return HTMLResponse(_page("This sign-in link expired. Start the connection again from Claude."), 400)
        client_id, params = pending
        client = await self.get_client(client_id)
        host = urlparse(str(params.redirect_uri)).hostname or "?"
        name = html.escape((client.client_name if client else None) or "Claude")
        if request.method == "GET":
            return HTMLResponse(_page(_form(rid, name, host)))

        form = await request.form()
        now = time.time()
        self._failures = [t for t in self._failures if now - t < FAILURE_WINDOW]
        if len(self._failures) >= MAX_FAILURES:
            return HTMLResponse(_page("Too many wrong attempts. Wait 15 minutes and try again."), 429)
        record = self.owner_record()
        if form.get("action") != "approve":
            self._q("DELETE FROM pending WHERE id=?", (rid,))
            return RedirectResponse(construct_redirect_uri(str(params.redirect_uri), error="access_denied", state=params.state), 302)
        if not record or not check_password(str(form.get("password", "")), record):
            self._failures.append(now)
            await asyncio.sleep(1)
            return HTMLResponse(_page(_form(rid, name, host, error="Wrong password.")), 401)

        self._q("DELETE FROM pending WHERE id=?", (rid,))
        code = secrets.token_urlsafe(32)
        ac = AuthorizationCode(
            code=code, scopes=params.scopes or [], expires_at=now + CODE_TTL, client_id=client_id,
            code_challenge=params.code_challenge, redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource, subject="owner",
        )
        self._q("INSERT INTO codes VALUES(?,?,?)", (_h(code), ac.model_copy(update={"code": ""}).model_dump_json(), ac.expires_at))
        return RedirectResponse(construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state), 302)

    async def load_authorization_code(self, client: OAuthClientInformationFull, authorization_code: str):
        rows = self._q("SELECT data FROM codes WHERE hash=? AND expires > ?", (_h(authorization_code), time.time()))
        if not rows:
            return None
        ac = AuthorizationCode.model_validate_json(rows[0][0]).model_copy(update={"code": authorization_code})
        return ac if ac.client_id == client.client_id else None

    def _issue(self, client_id: str, scopes: list[str], resource: str | None) -> OAuthToken:
        now = int(time.time())
        access, refresh = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        at = AccessToken(token="", client_id=client_id, scopes=scopes, expires_at=now + ACCESS_TTL, resource=resource, subject="owner")
        rt = RefreshToken(token="", client_id=client_id, scopes=scopes, expires_at=now + REFRESH_TTL, resource=resource, subject="owner")
        self._q("INSERT INTO tokens VALUES(?,?,?,?)", (_h(access), "access", at.model_dump_json(), at.expires_at))
        self._q("INSERT INTO tokens VALUES(?,?,?,?)", (_h(refresh), "refresh", rt.model_dump_json(), rt.expires_at))
        self._q("DELETE FROM tokens WHERE expires < ?", (now,))
        return OAuthToken(access_token=access, token_type="Bearer", expires_in=ACCESS_TTL,
                          refresh_token=refresh, scope=" ".join(scopes) or None)

    async def exchange_authorization_code(self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode) -> OAuthToken:
        deleted = self._q("DELETE FROM codes WHERE hash=? RETURNING hash", (_h(authorization_code.code),))
        if not deleted:
            raise TokenError("invalid_grant", "authorization code already used")
        return self._issue(client.client_id, authorization_code.scopes, authorization_code.resource)

    async def load_refresh_token(self, client: OAuthClientInformationFull, refresh_token: str):
        rows = self._q("SELECT data FROM tokens WHERE hash=? AND kind='refresh' AND expires > ?", (_h(refresh_token), time.time()))
        if not rows:
            return None
        rt = RefreshToken.model_validate_json(rows[0][0]).model_copy(update={"token": refresh_token})
        return rt if rt.client_id == client.client_id else None

    async def exchange_refresh_token(self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]) -> OAuthToken:
        deleted = self._q("DELETE FROM tokens WHERE hash=? AND kind='refresh' RETURNING hash", (_h(refresh_token.token),))
        if not deleted:  # rotation: a refresh token works exactly once
            raise TokenError("invalid_grant", "refresh token already used")
        return self._issue(client.client_id, scopes or refresh_token.scopes, refresh_token.resource)

    # ---------- resource server ----------
    async def load_access_token(self, token: str) -> AccessToken | None:
        if self.static_token and hmac.compare_digest(token.encode(), self.static_token.encode()):
            return AccessToken(token=token, client_id="council-static", scopes=[], subject="owner")
        rows = self._q("SELECT data FROM tokens WHERE hash=? AND kind='access' AND expires > ?", (_h(token), time.time()))
        if not rows:
            return None
        return AccessToken.model_validate_json(rows[0][0]).model_copy(update={"token": token})

    async def revoke_token(self, token) -> None:
        self._q("DELETE FROM tokens WHERE hash=?", (_h(token.token),))


def _page(body: str) -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>COUNCIL</title>
<style>
:root{{color-scheme:light dark;--bg:#f6f5f2;--fg:#1d1d1b;--mut:#6b6a66;--card:#fff;--line:#e2e0da;--acc:#1f4fd1}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--fg:#eceae4;--mut:#9b9992;--card:#1f1f1d;--line:#33322f;--acc:#7da2ff}}}}
body{{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}}
main{{width:min(380px,calc(100% - 32px));background:var(--card);border:1px solid var(--line);border-radius:14px;padding:28px}}
h1{{font-size:20px;margin:0 0 6px;letter-spacing:.04em}} p{{color:var(--mut);margin:0 0 18px}}
input{{width:100%;box-sizing:border-box;padding:12px;border:1px solid var(--line);border-radius:10px;background:transparent;color:var(--fg);font-size:16px}}
.row{{display:flex;gap:10px;margin-top:14px}} button{{flex:1;padding:12px;border-radius:10px;border:1px solid var(--line);font-size:16px;background:transparent;color:var(--fg)}}
button.go{{background:var(--acc);border-color:var(--acc);color:#fff}} .err{{color:#d33;margin:0 0 12px}}
</style></head><body><main>{body}</main></body></html>"""


def _form(rid: str, name: str, host: str, error: str = "") -> str:
    err = f'<p class="err">{html.escape(error)}</p>' if error else ""
    return f"""<h1>COUNCIL</h1><p><b>{name}</b> wants access to your memory. After approval you return to <b>{html.escape(host)}</b>.</p>
{err}<form method="post" action="/login"><input type="hidden" name="req" value="{html.escape(rid)}">
<input type="password" name="password" placeholder="Owner password" autocomplete="current-password" autofocus>
<div class="row"><button name="action" value="deny">Deny</button><button class="go" name="action" value="approve">Approve</button></div></form>"""
