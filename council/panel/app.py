"""The panel's web app: a sign-in door in front of six sections. Nothing but static files is served without a session."""
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

from . import text_tr, views
from ..store import now_local as store_now
from .gate import SESSION_TTL, Gate
from .sampler import Sampler

SECTIONS = ("schema", "today", "health", "map", "notes", "releases")
VIEWS = {"map": "memory_map"}  # the one section whose view is not named after it
COOKIE = "council_panel"
STATIC = Path(__file__).parent / "static"
CSP = "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


def _normalise(base_path: str) -> str:
    """'/panel/', 'panel' and '/panel' are one thing; '/' and '' mean the root (an empty prefix)."""
    return "/" + base_path.strip("/") if base_path.strip("/") else ""


class _Headers(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        origin = request.headers.get("origin")
        if request.method == "POST" and origin and urlsplit(origin).netloc != request.headers.get("host", ""):
            response: Response = PlainTextResponse("forbidden", status_code=403)
        else:
            response = await call_next(request)
        response.headers["Content-Security-Policy"] = CSP
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"  # under no-referrer a browser posts its own form with "Origin: null"
        kind = response.headers.get("content-type", "")
        if kind.startswith(("text/html", "application/json")):
            response.headers["Cache-Control"] = "no-store"
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

    async def api(request: Request):
        section = request.path_params["section"]
        if section not in SECTIONS:
            return JSONResponse({"error": "not_found"}, status_code=404)
        if not signed_in(request):
            return JSONResponse({"error": "signed_out"}, status_code=401)
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

    async def busy(request: Request, exc: Exception):
        return PlainTextResponse(text_tr.TEXTS["busy"], status_code=503)

    routes = [
        Route(base + "/", index),
        Route(base + "/login", login_page, methods=["GET"]),
        Route(base + "/login", login, methods=["POST"]),
        Route(base + "/logout", logout, methods=["POST"]),
        Route(base + "/api/{section}", api),
        Mount(base + "/static", StaticFiles(directory=STATIC), name="static"),
    ]
    if base:
        routes.insert(0, Route(base, index))

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

    app = Starlette(routes=routes, middleware=[Middleware(_Headers)],
                    exception_handlers={sqlite3.OperationalError: busy}, lifespan=lifespan)
    app.state.gate = gate
    app.state.sampler = sampler
    app.state.base = base
    app.state.service_url = service_url
    return app
