"""Checks a real `council install` from the outside. CI runs it on Linux, macOS and Windows.

  python scripts/check_install.py seed     # before installing: give the home folder an agent memory
  python scripts/check_install.py verify   # after installing: service, hooks, import, sub-agent tiers,
                                           # learning, check, update, uninstall
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


def hook(command, event):
    """Run the installed hook the way Claude Code does: through the shell, the event on stdin."""
    r = subprocess.run([*shell(), command], input=json.dumps(event), capture_output=True, text=True, encoding="utf-8")
    print(f"$ hook {event['hook_event_name']} {event.get('tool_name', '')}  -> {r.returncode}\n{r.stdout[:300]}{r.stderr}")
    assert r.returncode == 0, f"the {event['hook_event_name']} hook failed"
    return json.loads(r.stdout) if r.stdout.strip() else {}


def transcript(name, tool_calls=0):
    """A session record whose main model is Opus, with this many tool calls in it."""
    path = HOME / ".claude" / "projects" / "install-check" / f"{name}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [{"type": "assistant", "timestamp": "2026-01-01T00:00:00Z",
              "message": {"id": "m0", "model": "claude-opus-5-5", "role": "assistant", "content": []}}]
    lines += [{"type": "assistant", "timestamp": f"2026-01-01T00:{i // 60:02d}:{i % 60:02d}Z",
               "message": {"id": f"m{i}", "model": "claude-opus-5-5", "role": "assistant",
                           "content": [{"type": "tool_use", "id": f"t{i}", "name": "Bash", "input": {"command": "ls"}}]}}
              for i in range(1, tool_calls + 1)]
    path.write_text("".join(json.dumps(x) + "\n" for x in lines), encoding="utf-8")
    return str(path)


def check_delegation(settings, command):
    """The installer registers the sub-agent hook, and it sends sub-agents one tier below the session's model."""
    entry = settings["hooks"]["PreToolUse"][0]
    assert entry["matcher"] == "Agent|Task" and entry["hooks"][0]["command"] == command, "the sub-agent hook is missing"
    base = {"hook_event_name": "PreToolUse", "session_id": "ci", "transcript_path": transcript("delegation")}
    agent = {"description": "x", "prompt": "x", "subagent_type": "general-purpose"}
    out = hook(command, {**base, "tool_name": "Agent", "tool_input": agent})
    assert out["hookSpecificOutput"]["updatedInput"]["model"] == "sonnet", "a sub-agent of Opus did not get Sonnet"
    assert hook(command, {**base, "tool_name": "Agent", "tool_input": {**agent, "model": "haiku"}}) == {}, \
        "a sub-agent already below the ceiling was changed"
    assert hook(command, {**base, "tool_name": "Bash", "tool_input": {"command": "ls"}}) == {}, "another tool was changed"


class Mcp:
    """Just enough of an MCP client over plain HTTP: the check runs on a Python without COUNCIL's packages."""

    def __init__(self):
        self.url = f"http://127.0.0.1:{PORT}/mcp"
        self.token = (HOME / ".council" / "token").read_text(encoding="utf-8").strip()
        self.session, self.next_id = None, 0
        self.send("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                 "clientInfo": {"name": "install-check", "version": "1"}})
        self.send("notifications/initialized", None, notify=True)

    def send(self, method, params, notify=False):
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        if not notify:
            self.next_id += 1
            message["id"] = self.next_id
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json",
                   "Accept": "application/json, text/event-stream"}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        request = urllib.request.Request(self.url, json.dumps(message).encode(), headers, method="POST")
        with urllib.request.urlopen(request, timeout=30) as r:
            self.session = r.headers.get("Mcp-Session-Id") or self.session
            body = r.read().decode("utf-8")
        if notify:
            return None
        if body.lstrip().startswith("{"):
            reply = json.loads(body)
        else:  # a server-sent event stream: the reply is the event carrying our id
            events = [json.loads(line[5:]) for line in body.splitlines() if line.startswith("data:")]
            reply = next(e for e in events if e.get("id") == message["id"])
        assert "error" not in reply, f"{method}: {reply.get('error')}"
        return reply["result"]

    def tool(self, tool_name, /, **arguments):
        result = self.send("tools/call", {"name": tool_name, "arguments": arguments})
        text = result["content"][0]["text"] if result.get("content") else ""
        print(f"$ mcp {tool_name}  -> {'error' if result.get('isError') else 'ok'}\n{text[:300]}")
        assert not result.get("isError"), f"{tool_name} failed: {text}"
        return json.loads(text) if text.lstrip().startswith("{") else text


def check_learning(command):
    """Learning works end to end: a saved skill is offered at session start and on a matching message, a long
    piece of work ends with the review question, and what was learned can be undone."""
    mcp = Mcp()
    tools = {t["name"] for t in mcp.send("tools/list", {})["tools"]}
    missing = {"council_skill", "council_rule", "council_skill_feedback", "council_unlearn"} - tools
    assert not missing, f"learning tools missing: {missing}"

    skill = mcp.tool("council_skill", session_id="ci", name="Blog backup", learned_from="install check",
                     when="The user asks for a backup of the blog database",
                     steps="1. Dump the database to a dated file.\n2. Keep the last seven dumps.")
    path = skill["path"]
    assert (HOME / ".council" / "vault" / path).exists(), "the skill was not written"
    mcp.tool("council_skill_feedback", name=path, outcome="helped", session_id="ci")

    start = hook(command, {"hook_event_name": "SessionStart", "session_id": "ci-learn"})
    assert path in start["hookSpecificOutput"]["additionalContext"], "the saved skill is not listed at session start"
    prompt = hook(command, {"hook_event_name": "UserPromptSubmit", "session_id": "ci-learn",
                            "transcript_path": transcript("learn"), "prompt": "please back up the blog database"})
    assert path in prompt["hookSpecificOutput"]["additionalContext"], "the matching skill was not offered"
    stop = hook(command, {"hook_event_name": "Stop", "session_id": "ci-review", "stop_hook_active": False,
                          "transcript_path": transcript("review", tool_calls=16)})
    assert stop.get("decision") == "block" and "council_skill" in stop.get("reason", ""), \
        "a long piece of work did not end with the review question"

    mcp.tool("council_rule", text="Answers stay short.", session_id="ci")
    assert mcp.tool("council_unlearn", session_id="ci")["undone"] == "rule"
    assert mcp.tool("council_unlearn", session_id="ci")["undone"].startswith("skill")
    assert not (HOME / ".council" / "vault" / path).exists(), "undoing did not remove the skill"
    assert "Answers stay short." not in (HOME / ".council" / "vault" / "rules.md").read_text(encoding="utf-8")


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

    check_delegation(settings, command)
    check_learning(command)
    assert council("check").returncode == 0, "council check failed"
    assert council("delegation", "report", "--days", "1").returncode == 0, "the delegation report failed"

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
