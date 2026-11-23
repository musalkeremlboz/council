"""The panel's web app: a sign-in door in front of seven sections, each asking the API for its answer. Nothing but
static files is served without a session. Two addresses write: the owner password (owner.json, the one file the
panel writes besides panel.sqlite3) and closing the other sessions; both take a POST from the page itself only."""
from __future__ import annotations

import asyncio
import contextlib
import html
import json
import logging
import re
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse, Response
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from .. import oauth
from . import text_tr, views
from ..store import now_local as store_now
from .gate import SESSION_TTL, Gate
from .sampler import Sampler

SECTIONS = ("schema", "today", "health", "map", "notes", "releases", "settings")
VIEWS = {"map": "memory_map"}  # the one section whose view is not named after it
COOKIE = "council_panel"
STATIC = Path(__file__).parent / "static"
CSP = "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")
MAX_BODY = 4096  # bytes of a password change; two passwords of 200 characters fit many times over


async def read_limited(request, limit: int) -> bytes | None:
    """The body, or None when it is larger than limit: a declared length over the limit is refused unread, and a body
    without a usable length (or one that lies) is read only until it passes the limit."""
    declared = request.headers.get("content-length")
    if declared is not None and declared.strip().isdigit() and int(declared) > limit:
        return None
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > limit:
            return None
    return bytes(body)


def _utf8(text: str) -> bool:
    """False for a string a browser could never have sent, such as one with a lone surrogate."""
    try:
        text.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


def _normalise(base_path: str) -> str:
    """'/panel/', 'panel' and '/panel' are one thing; '/' and '' mean the root (an empty prefix)."""
    return "/" + base_path.strip("/") if base_path.strip("/") else ""


class _Headers(BaseHTTPMiddleware):
    def __init__(self, app, static: str = "/static/", strict: frozenset = frozenset()):
        super().__init__(app)
        self.static = static  # the path prefix of the static files
        self.strict = strict  # POST addresses that need an Origin: the page's own fetch always sends one

    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method == "POST" and not origin and request.url.path in self.strict:  # missing or empty
            response: Response = PlainTextResponse("forbidden", status_code=403)
        elif request.method == "POST" and origin and urlsplit(origin).netloc != request.headers.get("host", ""):
            response = PlainTextResponse("forbidden", status_code=403)
        else:
            response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"  # under no-referrer a browser posts its own form with "Origin: null"
        kind = response.headers.get("content-type", "")
        if kind.startswith(("text/html", "application/json")):
            response.headers["Cache-Control"] = "no-store"
        elif request.url.path.startswith(self.static):
            # scripts, styles and fonts are asked again each time (a 304 when unchanged): a page served no-store
            # must never run with a script kept from before an update
            response.headers["Cache-Control"] = "no-cache"
        return response


def build(data_dir, base_path: str = "/panel", service_url: str = "http://127.0.0.1:8765",
          background: bool = True) -> Starlette:
    base = _normalise(base_path)
    gate = Gate(Path(data_dir))
    sampler = Sampler(Path(data_dir), service_url)  # the service address is configuration, never a request's
    pages = {name: (STATIC / name).read_text(encoding="utf-8") for name in ("login.html", "index.html")}

    def render(name: str, **extra: str) -> HTMLResponse:
        values = {**text_tr.texts(), "base": base, "error": "", **extra}
        return HTMLResponse(PLACEHOLDER.sub(lambda m: html.escape(values.get(m.group(1), "")), pages[name]))

    def signed_in(request: Request) -> bool:
        return gate.valid(request.cookies.get(COOKIE, ""))

    def go(path: str) -> RedirectResponse:
        return RedirectResponse(base + path, status_code=303)

    async def index(request: Request):
        if not signed_in(request):
            return go("/login")
        # the page's copy travels in one attribute, escaped like every other value
        return render("index.html", ui=json.dumps(text_tr.ui(), ensure_ascii=False))

    async def login_page(request: Request):
        return go("/") if signed_in(request) else render("login.html")

    async def login(request: Request):
        if not gate.configured():
            return PlainTextResponse(text_tr.TEXTS["no_owner_password"], status_code=503)
        if gate.locked():
            return PlainTextResponse(text_tr.texts()["locked"], status_code=429)
        form = await request.form()
        password = form.get("password", "")
        token = gate.sign_in(password if isinstance(password, str) else "")
        if token is None:
            page = render("login.html", error=text_tr.TEXTS["wrong_password"])
            page.status_code = 401
            return page
        response = go("/")
        secure = request.url.scheme == "https" or request.headers.get("x-forwarded-proto", "").lower() == "https"
        response.set_cookie(COOKIE, token, max_age=SESSION_TTL, path=base or "/", httponly=True,
                            samesite="strict", secure=secure)
        return response

    async def logout(request: Request):
        token = request.cookies.get(COOKIE, "")
        if token:
            gate.sign_out(token)
        response = go("/login")
        response.delete_cookie(COOKIE, path=base or "/", httponly=True, samesite="strict")
        return response

    def signed_out() -> JSONResponse:
        return JSONResponse({"error": "signed_out"}, status_code=401)

    async def api(request: Request):
        section = request.path_params["section"]
        if section not in SECTIONS:
            return JSONResponse({"error": "not_found"}, status_code=404)
        if section == "settings":  # the door's own answer: the sessions, not the memory
            info = gate.session_info(request.cookies.get(COOKIE, ""))
            if info is None:
                return signed_out()
            return JSONResponse({**info, "min_length": oauth.MIN_PASSWORD})
        if not signed_in(request):
            return signed_out()
        view = getattr(views, VIEWS.get(section, section))
        try:
            if section == "releases":
                data = await run_in_threadpool(view)
            elif section in ("schema", "health"):
                data = await run_in_threadpool(view, data_dir, store_now(), sampler)
            else:
                data = await run_in_threadpool(view, data_dir, store_now())
            return JSONResponse(data)  # written here, so a value JSON cannot hold is a failure like any other
        except Exception:
            logging.getLogger("council").exception("panel section %s failed", section)
            return JSONResponse({"error": "unavailable"})

    async def pulse(request: Request):
        if not signed_in(request):
            return JSONResponse({"error": "signed_out"}, status_code=401)
        try:
            since = float(request.query_params.get("since", ""))
        except ValueError:
            since = None  # absent or not a number: the mark only
        try:
            return JSONResponse(await run_in_threadpool(views.pulse, data_dir, store_now(), since))
        except Exception:
            logging.getLogger("council").exception("panel pulse failed")
            return JSONResponse({"error": "unavailable"})

    async def password(request: Request):
        # the passwords live in this function only: never logged, never in an answer, never in an exception's words
        token = request.cookies.get(COOKIE, "")
        if not signed_in(request):
            return signed_out()
        if request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
            return JSONResponse({"error": "bad_request"}, status_code=400)
        raw = await read_limited(request, MAX_BODY)  # too large: 400 bad_request like any other odd body
        try:
            body = json.loads(raw) if raw is not None else None
        except ValueError:
            body = None
        if not isinstance(body, dict) or not isinstance(body.get("current"), str) or not isinstance(body.get("new"), str):
            return JSONResponse({"error": "bad_request"}, status_code=400)
        if not (_utf8(body["current"]) and _utf8(body["new"])):
            return JSONResponse({"error": "bad_request"}, status_code=400)
        try:
            result = await run_in_threadpool(gate.change_password, token, body["current"], body["new"])
        except Exception as exc:
            # the kind of failure only: an exception's words or traceback could carry a character of a password
            logging.getLogger("council").error("panel password change failed (%s)", type(exc).__name__)
            return JSONResponse({"error": "unavailable"}, status_code=500)
        if result == "ok":
            return JSONResponse({"ok": True, "closed": result.closed})
        status = {"signed_out": 401, "locked": 429, "wrong": 403}.get(result, 400)
        return JSONResponse({"error": str(result)}, status_code=status)

    async def close_others(request: Request):
        if not signed_in(request):
            return signed_out()
        return JSONResponse({"closed": gate.sign_out_others(request.cookies.get(COOKIE, ""))})

    async def busy(request: Request, exc: Exception):
        return PlainTextResponse(text_tr.TEXTS["busy"], status_code=503)

    routes = [
        Route(base + "/", index),
        Route(base + "/login", login_page, methods=["GET"]),
        Route(base + "/login", login, methods=["POST"]),
        Route(base + "/logout", logout, methods=["POST"]),
        Route(base + "/api/pulse", pulse),  # before the section route, which would answer 404 to it
        Route(base + "/api/password", password, methods=["POST"]),
        Route(base + "/api/sessions/close-others", close_others, methods=["POST"]),
        Route(base + "/api/{section}", api),
        Mount(base + "/static", StaticFiles(directory=STATIC), name="static"),
    ]
    if base:
        routes.insert(0, Route(base, index))

    strict = frozenset({base + "/api/password", base + "/api/sessions/close-others"})

    @contextlib.asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(sampler.loop()) if background else None
        try:
            yield
        finally:
            if task is not None:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    app = Starlette(routes=routes, middleware=[Middleware(_Headers, static=base + "/static/", strict=strict)],
                    exception_handlers={sqlite3.OperationalError: busy}, lifespan=lifespan)
    app.state.gate = gate
    app.state.sampler = sampler
    app.state.base = base
    app.state.service_url = service_url
    return app
