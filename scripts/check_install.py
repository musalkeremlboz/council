"""Checks a real `council install` from the outside. CI runs it on Linux, macOS and Windows.

  python scripts/check_install.py seed     # before installing: give the home folder an agent memory
  python scripts/check_install.py verify   # after installing: service, hook, import, update, uninstall
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HOME = Path.home()
PORT = 8799
PYTHON = HOME / ".council" / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def council(*args):
    r = subprocess.run([str(PYTHON), "-m", "council.cli", *args], capture_output=True, text=True)
    print(f"$ council {' '.join(args)}  -> {r.returncode}\n{r.stdout}{r.stderr}")
    return r


def healthy():
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2) as r:
            return json.loads(r.read().decode())["ok"]
    except OSError:
        return False


def shell():
    """The shell Claude Code runs hooks with: sh, or Git Bash on Windows."""
    git_bash = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git" / "bin" / "bash.exe"
    return [str(git_bash), "-c"] if os.name == "nt" else ["sh", "-c"]


def seed():
    (HOME / ".claude").mkdir(exist_ok=True)
    (HOME / ".claude" / "CLAUDE.md").write_text("# About me\n\nThe blog project uses SQLite.\n", encoding="utf-8")
    (HOME / ".claude" / "settings.json").write_text(json.dumps(
        {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "echo other"}]}]}}), encoding="utf-8")


def verify():
    assert council("status").returncode == 0 and healthy()

    settings = json.loads((HOME / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert settings["hooks"]["Stop"][0]["hooks"][0]["command"] == "echo other", "another tool's hook was lost"
    command = settings["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    event = json.dumps({"hook_event_name": "SessionStart", "session_id": "ci"})
    r = subprocess.run([*shell(), command], input=event, capture_output=True, text=True, encoding="utf-8")
    print(f"$ {command}  -> {r.returncode}\n{r.stdout[:300]}{r.stderr}")
    context = json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
    assert "COUNCIL session=ci" in context and "unreachable" not in context
    assert "Bring the user's existing memory over" in context

    assert "imported/claude-code/claude.md" in council("search", "SQLite").stdout, "agent memory was not imported"
    assert "council" in json.loads((HOME / ".claude.json").read_text(encoding="utf-8"))["mcpServers"]

    assert council("update").returncode in (0, 1)  # 1 only when GitHub cannot be reached from here
    assert healthy()

    assert council("uninstall").returncode == 0
    for _ in range(20):
        if not healthy():
            break
        time.sleep(0.5)
    assert not healthy(), "the service is still running after uninstall"
    assert (HOME / ".council" / "vault" / "core.md").exists(), "uninstall must keep the notes"
    assert "hooks" not in json.loads((HOME / ".claude" / "settings.json").read_text(encoding="utf-8")) or \
        "SessionStart" not in json.loads((HOME / ".claude" / "settings.json").read_text(encoding="utf-8"))["hooks"]
    print("install check passed")


if __name__ == "__main__":
    {"seed": seed, "verify": verify}[sys.argv[1]]()
