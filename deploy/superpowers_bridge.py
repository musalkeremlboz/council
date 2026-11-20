#!/usr/bin/env python3
"""SessionStart bridge for the Superpowers plugin on a remote (SSH) Claude Code host.

The Claude desktop app copies synced plugins to the remote host but not their hooks.
This script finds the copy the app shipped (so it always matches the user's synced
version), injects the same `using-superpowers` context the plugin's own hook would,
and adds a note when a newer upstream release exists (see `check` below).

  python3 superpowers_bridge.py          # SessionStart hook
  python3 superpowers_bridge.py check    # daily: record the latest upstream release
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

PLUGINS = Path("/root/.claude/remote/plugins")
STATUS = Path("/var/lib/council/upstream/superpowers.json")
REPO = "obra/superpowers"


def synced_copy() -> tuple[Path, str] | None:
    best = None
    for manifest in PLUGINS.glob("*/*/.claude-plugin/plugin.json"):
        try:
            meta = json.loads(manifest.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if meta.get("name") != "superpowers":
            continue
        root = manifest.parent.parent
        mtime = manifest.stat().st_mtime
        if best is None or mtime > best[0]:
            best = (mtime, root, str(meta.get("version", "")))
    return (best[1], best[2]) if best else None


def vtuple(v: str) -> tuple:
    return tuple(int(x) for x in v.lstrip("v").split(".") if x.isdigit())


def hook() -> None:
    found = synced_copy()
    if not found:
        return
    root, version = found
    try:
        skill = (root / "skills/using-superpowers/SKILL.md").read_text()
    except OSError:
        return
    context = (
        "<EXTREMELY_IMPORTANT>\nYou have superpowers.\n\n**Below is the full content of your "
        "'superpowers:using-superpowers' skill - your introduction to using skills. For all other "
        f"skills, use the 'Skill' tool:**\n\n{skill}\n</EXTREMELY_IMPORTANT>"
    )
    try:
        latest = json.loads(STATUS.read_text()).get("latest", "")
    except (OSError, json.JSONDecodeError):
        latest = ""
    if latest and version and vtuple(latest) > vtuple(version):
        context += (
            f"\n\nNote for the user: Superpowers on this server is {version}; upstream released {latest}. "
            "Tell the user once. It updates when the Claude desktop app syncs the newer version."
        )
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}))


def check() -> None:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "council-superpowers-check"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        latest = json.loads(r.read().decode())["tag_name"]
    found = synced_copy()
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps({"latest": latest.lstrip("v"), "synced": found[1] if found else None}) + "\n")
    print(f"upstream {latest}, synced {found[1] if found else 'none'}")


if __name__ == "__main__":
    check() if sys.argv[1:] == ["check"] else hook()
