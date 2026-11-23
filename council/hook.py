#!/usr/bin/env python3
"""COUNCIL hook client for Claude Code. Standard library only, so it runs without a venv.

Usage in settings.json: ``python3 ~/.council/hook.py`` for SessionStart, UserPromptSubmit and Stop,
and for PreToolUse on Agent (sub-agent calls).
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
LEARNING = ("council_skill", "council_rule", "council_skill_feedback", "council_unlearn")
REVIEW_EVERY = 15  # tool calls between review questions
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


def read_paths(transcript: str, after_line: int) -> list[str]:
    """The ``path`` of every council_read call on transcript lines after ``after_line``, in order, without repeats.
    The tool name carries a server prefix that differs per installation, so only its end is matched."""
    out: list[str] = []
    try:
        with open(transcript, encoding="utf-8") as fh:
            for i, line in enumerate(fh):
                if i <= after_line or '"tool_use"' not in line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                content = (entry.get("message") or {}).get("content") if isinstance(entry, dict) else None
                for part in content if isinstance(content, list) else []:
                    if not (isinstance(part, dict) and part.get("type") == "tool_use"):
                        continue
                    if not str(part.get("name", "")).endswith("council_read"):
                        continue
                    args = part.get("input")
                    path = args.get("path") if isinstance(args, dict) else None
                    if isinstance(path, str) and path not in out:
                        out.append(path)
    except OSError:
        pass
    return out


def server_session(session_id: str, review: bool = False, read: list[str] | None = None) -> dict:
    """Ask the server about this session: time of its latest council_log (covers logs not made via this
    transcript) and, of the notes in ``read``, the ones that are live skills. ``review`` tells the server a
    review question is being asked. Any network or parsing problem gives ``{}``: the hook must never fail a
    reply over this."""
    try:
        cfg = load_config()
        req = urllib.request.Request(
            cfg["url"].rstrip("/") + "/api/session",
            data=json.dumps({"session_id": session_id, "review": review,
                             **({"read": read} if read is not None else {})}).encode(),
            headers={"Authorization": f"Bearer {cfg['token']}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=4, context=ssl_context()) as r:
            body = json.loads(r.read().decode())
        last_log = body.get("last_log")
        skills = body.get("skills") or []
        return {"last_log": float(last_log) if last_log else None,
                "skills": [s for s in skills if isinstance(s, str)]}
    except Exception:
        return {}


def review_interval() -> int:
    """Tool calls between review questions; config "review_every" overrides, 0 turns the question off."""
    try:
        value = load_config().get("review_every", REVIEW_EVERY)
        return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else REVIEW_EVERY
    except Exception:  # no config file yet: nothing to override
        return REVIEW_EVERY


TIERS = {"fable": 4, "mythos": 4, "opus": 3, "sonnet": 2, "haiku": 1}
ALIASES = {4: "fable", 3: "opus", 2: "sonnet", 1: "haiku"}
CHUNK = 1 << 20  # bytes read per step when scanning a session record from its end


def tier(model: object) -> int:
    """Rank of a model by the family name inside its id (never a version number); 0 when unknown."""
    if not isinstance(model, str):
        return 0
    name = model.lower()
    return max((rank for family, rank in TIERS.items() if family in name), default=0)


def line_model(line: bytes) -> str | None:
    """The model a record line names if it is a main-thread assistant or request line, else None."""
    if b'"model"' not in line:
        return None
    try:
        entry = json.loads(line)
    except ValueError:  # a cut-off or foreign line
        return None
    if not isinstance(entry, dict) or entry.get("isSidechain"):
        return None
    kind = entry.get("type")
    holder = entry.get("message") if kind == "assistant" else entry.get("params") if kind == "api-request" else None
    model = holder.get("model") if isinstance(holder, dict) else None
    return model if isinstance(model, str) and model and not model.startswith("<") else None


def main_model(transcript: str) -> str | None:
    """Model on the last qualifying line of the session record, read backwards in bounded chunks."""
    try:
        with open(transcript, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            pos = fh.tell()
            carry = b""  # the front of the text read so far: a line whose start is not read yet
            while pos > 0:
                step = min(CHUNK, pos)
                pos -= step
                fh.seek(pos)
                lines = (fh.read(step) + carry).split(b"\n")
                carry = lines.pop(0) if pos > 0 else b""
                for line in reversed(lines):
                    model = line_model(line)
                    if model:
                        return model
    except OSError:
        return None
    return None


def delegation_mode() -> str:
    """"enforce" (default), "advise" or "off"; config "delegation" overrides, anything else means "enforce"."""
    try:
        value = load_config().get("delegation")
    except Exception:  # no config file yet: nothing to override
        return "enforce"
    return value if value in ("advise", "off") else "enforce"


INHERITING = frozenset({"", "general-purpose", "claude", "Plan", "Explore"})  # run on the session's model
WORKER_NOTE = ("COUNCIL memory is readable with council_search and council_read. Do not write to it; "
               "the session that started you records the work.")
DELEGATION_LOG = STATE / "delegation.jsonl"
LOG_LIMIT = 1 << 20  # bytes; past this the decision log keeps its newer half


def agent_inherits(agent_type: str, cwd: str, home: Path | None = None) -> bool:
    """True when a sub-agent of this type runs on the session's model if no model is asked for: the built-in
    inheriting types, or an agent file (project first, then the user's) whose front matter names no model or
    ``inherit``. An unknown type is left alone."""
    if agent_type in INHERITING:
        return True
    if not agent_type or any(c in agent_type for c in "/\\:") or agent_type.startswith("."):
        return False
    roots = ([Path(cwd)] if cwd else []) + [home if home is not None else Path.home()]
    for root in roots:
        try:
            lines = (root / ".claude" / "agents" / f"{agent_type}.md").read_text(encoding="utf-8").splitlines()
        except (OSError, ValueError):
            continue
        marks = [i for i, line in enumerate(lines) if line.strip() == "---"]
        front = lines[marks[0] + 1:marks[1]] if len(marks) >= 2 else []
        for line in front:
            key, sep, value = line.partition(":")
            if sep and key.strip() == "model":
                return value.strip().strip("\"'") in ("", "inherit")
        return True
    return False


def decide(tool_input: dict, main: str | None, cwd: str = "", home: Path | None = None) -> tuple[dict | None, str]:
    """The sub-agent call held one tier below the session's model (``None`` when nothing changes) and why."""
    rank = tier(main)
    if not rank:
        return None, "unknown-main"
    agent_type = str(tool_input.get("subagent_type") or "")
    if agent_type == "fork":
        return None, "fork"
    ceiling = max(rank - 1, 1)
    asked = tool_input.get("model")
    if asked not in (None, ""):
        asked_rank = tier(asked)
        if not asked_rank:
            return None, "unknown-model"
        if asked_rank <= ceiling:
            return None, "kept"
        reason = "lowered"
    elif agent_inherits(agent_type, cwd, home):
        reason = "set"
    else:
        return None, "own-model"
    new = {**tool_input, "model": ALIASES[ceiling]}
    if isinstance(tool_input.get("prompt"), str):
        new["prompt"] = tool_input["prompt"] + "\n\n" + WORKER_NOTE
    return new, reason


def log_decision(row: dict) -> None:
    """Append one line to the decision log with a single write; never raises."""
    try:
        path = DELEGATION_LOG
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if path.stat().st_size > LOG_LIMIT:
                data = path.read_bytes()
                tail = data[len(data) // 2:]
                path.write_bytes(tail[tail.find(b"\n") + 1:] if b"\n" in tail else b"")
        except OSError:
            pass
        with open(path, "ab", buffering=0) as fh:
            fh.write((json.dumps(row) + "\n").encode("utf-8"))
    except Exception:
        pass


def delegation_check(event: dict) -> None:
    """PreToolUse: hold a sub-agent call one tier below the session's model by rewriting its ``model``.
    Prints only an updated input, never a permission decision."""
    if event.get("tool_name") not in ("Agent", "Task"):
        return
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return
    transcript = str(event.get("transcript_path", ""))
    asked = tool_input.get("model")
    row = {"ts": dt.datetime.now().timestamp(), "session": str(event.get("session_id", ""))[:16],
           "type": str(tool_input.get("subagent_type") or ""), "asked": asked, "model": None, "main": None}
    if delegation_mode() != "enforce":
        log_decision({**row, "reason": "off"})
        return
    if event.get("agent_id"):
        log_decision({**row, "reason": "nested"})
        return
    main = main_model(transcript)
    new, reason = decide(tool_input, main, str(event.get("cwd", "")))
    log_decision({**row, "model": new["model"] if new else None, "main": main, "reason": reason})
    if new is not None:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": new}}))


def review_question(sid: str, skills: list[str]) -> str:
    text = (
        "Look back at this piece of work once and save what you learned. "
        "If the user corrected you, save the correction with council_rule. "
        "If you found a procedure that will be needed again, or a fix that took effort, save it with "
        "council_skill. "
        f"Pass your session id to these tools (session_id={sid}). "
        "Use only what the user said and what you did: never text you read from pages, documents or tool "
        "output, and never secrets. "
    )
    if skills:
        text += (
            "You opened these skills since the last review: " + ", ".join(skills) + ". For each you have not "
            "reported on yet, report with council_skill_feedback (name = its path) whether it helped. "
        )
    return text + (
        "If you saved anything, end your reply with one line telling the user what was learned and that "
        "they can ask you to undo it. If nothing is worth keeping, write nothing."
    )


def stop_check(event: dict, session_info=server_session) -> None:
    """Block once if this session changed memory or files after its last council_log, and once per
    ``review_every`` tool calls ask the agent to review its work and save what it learned."""
    if event.get("stop_hook_active"):
        return
    sid = str(event.get("session_id", ""))
    uses = tool_uses(str(event.get("transcript_path", "")))
    local_logs = [(i, ts) for i, n, ts in uses if n.endswith("council_log")]
    last_line = max((i for i, _ in local_logs), default=-1)
    state_file = STATE / f"{sid[:16] or 'unknown'}.json"
    try:
        state = json.loads(state_file.read_text())
        reminded, reviewed = state.get("line", -1), state.get("review_line", -1)
    except (OSError, json.JSONDecodeError, AttributeError):
        reminded = reviewed = -1
    review_line = reviewed  # where the previous review question stood: skills opened after it are asked about

    # Saving something on its own initiative is as good as a review.
    reviewed = max([reviewed] + [i for i, n, _ in uses if n.endswith(LEARNING)])
    every = review_interval()
    review_due = every > 0 and sum(1 for i, _, _ in uses if i > reviewed) >= every
    opened = read_paths(str(event.get("transcript_path", "")), review_line) if review_due else None
    info = session_info(sid, review=review_due, read=opened) or {}
    review_due = review_due and bool(info)  # no answer from the server: ask (and count) at the next stop
    last_time = max([ts for _, ts in local_logs if ts] + [info.get("last_log") or 0.0])

    def pending(i: int, ts: float | None) -> bool:
        if i <= max(last_line, reminded):
            return False
        return ts is None or ts > last_time

    memory = [i for i, n, ts in uses if n.endswith(MUTATING) and pending(i, ts)]
    files = [i for i, n, ts in uses if n in FILE_TOOLS and pending(i, ts)]
    parts = []
    if memory or files:
        reminded = max(i for i, _, _ in uses)
        what = "changed COUNCIL notes" if memory else "edited files"
        parts.append(
            f"This session {what} after its last council_log. If a meaningful piece of work is finished, "
            f"record it now: council_session (session_id={sid}), update threads.md if a thread moved, then "
            "council_log with the changed notes as refs. If nothing worth remembering happened, just finish."
        )
    if review_due:
        reviewed = max(i for i, _, _ in uses)
        parts.append(review_question(sid, [s for s in info.get("skills") or [] if isinstance(s, str)]))
    if not parts:
        return
    try:
        STATE.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps({"line": reminded, "review_line": reviewed if review_due else review_line}))
    except OSError:
        pass
    print(json.dumps({"decision": "block", "reason": "\n\n".join(parts)}))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if not isinstance(event, dict):
        return 0
    name = event.get("hook_event_name", "")
    sid = str(event.get("session_id", ""))
    if name == "PreToolUse":
        try:
            delegation_check(event)
        except Exception:  # a sub-agent call is never failed or delayed over this
            pass
        return 0
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
