#!/usr/bin/env python3
"""COUNCIL hook client for Claude Code. Standard library only, so it runs without a venv.

Usage in settings.json: ``python3 ~/.council/hook.py`` for SessionStart, UserPromptSubmit and Stop.
Config: ``~/.config/council/config.json`` -> {"url": "https://host", "token": "..."}.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONFIG = Path(os.environ.get("COUNCIL_CONFIG", "~/.config/council/config.json")).expanduser()
STATE = Path("~/.council/state").expanduser()
MUTATING = ("council_write", "council_edit", "council_session")
FILE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
# Messages the app itself submits (finished background task, CI event): nobody asked anything.
MACHINE_EVENT = re.compile(r"\s*<[a-z][a-z-]*-(?:notification|event)>")


def load_config() -> dict:
    return json.loads(CONFIG.read_text())


def ssl_context() -> ssl.SSLContext:
    """Default trust store; fall back to the OS bundle when Python ships without one (python.org macOS builds)."""
    ctx = ssl.create_default_context()
    paths = ssl.get_default_verify_paths()
    if not (paths.cafile or (paths.openssl_cafile and os.path.exists(paths.openssl_cafile))):
        for bundle in ("/etc/ssl/cert.pem", "/etc/ssl/certs/ca-certificates.crt"):
            if os.path.exists(bundle):
                ctx.load_verify_locations(cafile=bundle)
                break
    return ctx


def fetch(cfg: dict, payload: dict, timeout: float = 8.0) -> str:
    req = urllib.request.Request(
        cfg["url"].rstrip("/") + "/api/context",
        data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {cfg['token']}", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout, context=ssl_context()) as r:
        return json.loads(r.read().decode())["context"]


def emit_context(event: str, text: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}))


def stamp(session_id: str) -> str:
    """Session id and the user's local time (config "timezone" wins over the machine's, e.g. a UTC server)."""
    now = dt.datetime.now().astimezone()
    try:
        tz = load_config().get("timezone")
        if tz:
            from zoneinfo import ZoneInfo

            now = now.astimezone(ZoneInfo(tz))
    except Exception:
        pass
    return f"COUNCIL session={session_id} now={now:%Y-%m-%d %H:%M %z}"


def _epoch(stamp: str | None) -> float | None:
    if not stamp:
        return None
    try:
        return dt.datetime.fromisoformat(stamp.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def tool_uses(transcript: str) -> list[tuple[int, str, float | None]]:
    """(line number, tool name, time) for every tool call in the transcript."""
    out = []
    try:
        with open(transcript, encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if '"tool_use"' not in line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ts = _epoch(entry.get("timestamp"))
                for part in (entry.get("message") or {}).get("content") or []:
                    if isinstance(part, dict) and part.get("type") == "tool_use":
                        out.append((i, str(part.get("name", "")), ts))
    except OSError:
        pass
    return out


def server_last_log(session_id: str) -> float | None:
    """Time of this session's latest council_log as the server saw it (covers logs not made via this transcript)."""
    try:
        cfg = load_config()
        req = urllib.request.Request(
            cfg["url"].rstrip("/") + "/api/session",
            data=json.dumps({"session_id": session_id}).encode(),
            headers={"Authorization": f"Bearer {cfg['token']}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=4, context=ssl_context()) as r:
            value = json.loads(r.read().decode()).get("last_log")
        return float(value) if value else None
    except (OSError, urllib.error.URLError, KeyError, ValueError):
        return None


def stop_check(event: dict, last_logged=server_last_log) -> None:
    """Block once if this session changed memory or files after its last council_log."""
    if event.get("stop_hook_active"):
        return
    sid = str(event.get("session_id", ""))
    uses = tool_uses(str(event.get("transcript_path", "")))
    local_logs = [(i, ts) for i, n, ts in uses if n.endswith("council_log")]
    last_line = max((i for i, _ in local_logs), default=-1)
    last_time = max([ts for _, ts in local_logs if ts] + [last_logged(sid) or 0.0])
    state_file = STATE / f"{sid[:16] or 'unknown'}.json"
    try:
        reminded = json.loads(state_file.read_text()).get("line", -1)
    except (OSError, json.JSONDecodeError):
        reminded = -1

    def pending(i: int, ts: float | None) -> bool:
        if i <= max(last_line, reminded):
            return False
        return ts is None or ts > last_time

    memory = [i for i, n, ts in uses if n.endswith(MUTATING) and pending(i, ts)]
    files = [i for i, n, ts in uses if n in FILE_TOOLS and pending(i, ts)]
    if not memory and not files:
        return
    STATE.mkdir(parents=True, exist_ok=True)
    state_file.write_text(json.dumps({"line": max(i for i, _, _ in uses)}))
    what = "changed COUNCIL notes" if memory else "edited files"
    reason = (
        f"This session {what} after its last council_log. If a meaningful piece of work is finished, "
        f"record it now: council_session (session_id={sid}), update threads.md if a thread moved, then "
        "council_log with the changed notes as refs. If nothing worth remembering happened, just finish."
    )
    print(json.dumps({"decision": "block", "reason": reason}))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    name = event.get("hook_event_name", "")
    sid = str(event.get("session_id", ""))
    if name == "Stop":
        stop_check(event)
        return 0
    if name not in ("SessionStart", "UserPromptSubmit"):
        return 0
    try:
        cfg = load_config()
        if name == "SessionStart":
            text = fetch(cfg, {"mode": "start", "session_id": sid})
        elif MACHINE_EVENT.match(str(event.get("prompt", ""))):
            text = ""
        else:
            text = fetch(cfg, {"mode": "prompt", "query": str(event.get("prompt", "")), "session_id": sid})
        emit_context(name, stamp(sid) + "\n" + text if text else stamp(sid))
    except (OSError, urllib.error.URLError, KeyError, ValueError) as e:
        emit_context(name, f"{stamp(sid)}\nCOUNCIL memory is unreachable ({type(e).__name__}); "
                     "tell the user once and continue without memory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
