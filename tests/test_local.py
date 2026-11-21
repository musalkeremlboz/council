import json
import re
import subprocess
import sys
import time

import pytest

from council import __version__, local, migrate
from council.context import bootstrap
from council.store import Store


class Recorder:
    """Stands in for subprocess: remembers every command and answers with a chosen exit code."""

    def __init__(self, fail=()):
        self.calls, self.fail = [], fail

    def __call__(self, cmd):
        self.calls.append(cmd)
        bad = any(word in cmd for word in self.fail)
        return subprocess.CompletedProcess(cmd, 1 if bad else 0, "", "boom" if bad else "")

    def ran(self, *words):
        return [c for c in self.calls if all(w in c for w in words)]


@pytest.fixture
def home(tmp_path):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    return h


def make(home, system="Darwin", **kw):
    run = kw.pop("run", Recorder())
    s = local.Setup(home / ".council", port=8799, home=home, system=system, run=run, say=lambda *_: None, **kw)
    s.healthy = lambda wait=0: __version__
    return s


def hook_commands(home, event):
    settings = json.loads((home / ".claude" / "settings.json").read_text())
    return [h["command"] for e in settings["hooks"][event] for h in e["hooks"]]


def test_install_sets_everything_up_and_keeps_other_settings(home):
    (home / ".claude" / "settings.json").write_text(json.dumps({
        "model": "x", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "other-tool"}]}]}}))
    (home / ".claude.json").write_text(json.dumps({"mcpServers": {"other": {"url": "http://x"}}, "projects": {}}))
    s = make(home)
    assert local.install(s) == 0

    assert (home / "Library/LaunchAgents/ai.council.memory.plist").exists()
    assert (home / "Library/LaunchAgents/ai.council.update.plist").exists()
    assert s.run.ran("launchctl", "bootstrap")
    cfg = json.loads((home / ".config/council/config.json").read_text())
    assert cfg["url"] == "http://127.0.0.1:8799" and cfg["token"] == (home / ".council/token").read_text().strip()
    assert (home / ".council/hook.py").exists()

    settings = json.loads((home / ".claude/settings.json").read_text())
    assert settings["model"] == "x"
    assert hook_commands(home, "Stop")[0] == "other-tool" and ".council/hook.py" in hook_commands(home, "Stop")[1]
    assert all(".council/hook.py" in hook_commands(home, e)[-1] for e in ("SessionStart", "UserPromptSubmit"))
    assert (home / ".claude/settings.json.before-council").exists()
    cj = json.loads((home / ".claude.json").read_text())
    assert cj["mcpServers"]["other"] and cj["mcpServers"]["council"]["url"] == "http://127.0.0.1:8799/mcp"
    assert s.hooks_installed()


def test_install_twice_does_not_duplicate(home):
    s = make(home)
    local.install(s)
    local.install(make(home))
    assert len(hook_commands(home, "SessionStart")) == 1
    threads = Store(home / ".council").read("threads.md").text
    assert threads.count("Bring the user's existing memory over") == 1


def test_install_refuses_to_replace_another_memory(home):
    cfg = home / ".config/council/config.json"
    cfg.parent.mkdir(parents=True)
    cfg.write_text(json.dumps({"url": "https://memory.example.com", "token": "t"}))
    s = make(home)
    assert local.install(s) == 1
    assert json.loads(cfg.read_text())["url"] == "https://memory.example.com"
    assert not s.run.calls and not (home / ".claude/settings.json").exists()
    assert local.install(make(home), force=True) == 0
    assert json.loads(cfg.read_text())["url"] == "http://127.0.0.1:8799"


def test_install_without_auto_update(home):
    s = make(home)
    local.install(s, auto_update=False)
    assert not (home / "Library/LaunchAgents/ai.council.update.plist").exists()
    assert not s.updater_installed()


def test_uninstall_removes_only_ours_and_keeps_notes(home):
    (home / ".claude/settings.json").write_text(json.dumps(
        {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "other-tool"}]}]}}))
    s = make(home)
    local.install(s)
    local.uninstall(s)
    settings = json.loads((home / ".claude/settings.json").read_text())
    assert settings["hooks"] == {"Stop": [{"hooks": [{"type": "command", "command": "other-tool"}]}]}
    assert "council" not in json.loads((home / ".claude.json").read_text())["mcpServers"]
    assert not (home / "Library/LaunchAgents/ai.council.memory.plist").exists()
    assert not (home / ".config/council/config.json").exists()
    assert (home / ".council/vault/core.md").exists()


def test_invalid_settings_file_is_left_alone(home):
    (home / ".claude/settings.json").write_text("{not json")
    assert local.install(make(home)) == 0
    assert (home / ".claude/settings.json").read_text() == "{not json"


def test_linux_uses_systemd_user_units(home):
    s = make(home, system="Linux")
    assert local.install(s) == 0
    unit = (home / ".config/systemd/user/council.service").read_text()
    assert "council.cli" in unit and "serve --port 8799" in unit
    assert s.run.ran("systemctl", "--user", "enable", "council-update.timer")
    local.uninstall(s)
    assert not (home / ".config/systemd/user/council.service").exists()


def test_linux_without_user_systemd_reports_it(home):
    s = make(home, system="Linux", run=Recorder(fail=("daemon-reload",)))
    assert local.install(s) == 1


def test_windows_uses_login_entry_and_scheduled_task(home, monkeypatch):
    registry, spawned = {}, []

    def run_value(self, command):
        if command is None:
            registry.clear()
        elif command:
            registry["cmd"] = command
        return bool(registry)

    monkeypatch.setattr(local.Setup, "_win_run_value", run_value)
    s = make(home, system="Windows", spawn=spawned.append)
    assert local.install(s) == 0
    assert "council.cli" in registry["cmd"] and "serve" in registry["cmd"]
    assert spawned and spawned[0][-3:] == ["serve", "--port", "8799"]
    assert s.run.ran("schtasks", "/Create", "COUNCIL Update")
    assert "\\" not in hook_commands(home, "SessionStart")[0] or sys.platform != "win32"
    (home / ".council/service.pid").write_text("4242")
    s.healthy = lambda wait=0: None
    local.uninstall(s)
    assert not registry and s.run.ran("taskkill", "4242") and s.run.ran("schtasks", "/Delete")


def test_port_is_remembered(home):
    local.install(make(home))
    assert local.Setup(home / ".council", home=home).port == 8799


# ---------------------------------------------------------------- updates

def test_version_order():
    assert local.version_tuple("v0.10.0") > local.version_tuple("0.9.3")
    assert local.version_tuple("v0.2.0") == local.version_tuple("0.2.0")


def test_update_installs_newer_release_and_tells_the_agent_once(home):
    s = make(home)
    local.install(s)
    s.run.calls.clear()
    assert local.update(s, latest=lambda: "v9.0.0") == 0
    pip = s.run.ran("pip", "install")
    assert pip and pip[0][-1].endswith("@v9.0.0") and pip[0][0] == sys.executable
    assert s.run.ran("launchctl", "kickstart")
    store = Store(home / ".council")
    first = bootstrap(store)
    assert f"updated itself from {__version__} to 9.0.0" in first
    assert "updated itself" not in bootstrap(store)


def test_update_does_nothing_when_current(home):
    s = make(home)
    assert local.update(s, latest=lambda: "v" + __version__) == 0
    assert not s.run.ran("pip")
    assert local.update(s, latest=lambda: "v0.0.1") == 0
    assert not s.run.ran("pip")


def test_update_failures_are_recorded(home):
    s = make(home, run=Recorder(fail=("pip",)))
    s.data.mkdir(parents=True, exist_ok=True)
    assert local.update(s, latest=lambda: None) == 1
    assert local.update(s, latest=lambda: "v9.0.0") == 1
    state = json.loads((s.data / "update.json").read_text())
    assert "v9.0.0" in state["error"] and "installed" not in state
    store = Store(s.data)
    assert "automatic update" not in bootstrap(store)  # one failed check (a laptop offline) is not news
    state["error_since"] = time.time() - 4 * 86400
    (s.data / "update.json").write_text(json.dumps(state))
    assert "automatic update is failing" in bootstrap(store)
    assert "automatic update" not in bootstrap(store)  # told once, then again only after a week


# ---------------------------------------------------------------- existing memory

def agent_home(home):
    (home / ".claude/CLAUDE.md").write_text("# About me\n\nShort answers, please.")
    # Claude Code names a project's folder after its path, every other character turned into a dash
    mem = home / ".claude/projects" / (re.sub(r"[^A-Za-z0-9]", "-", str(home)) + "-blog") / "memory"
    mem.mkdir(parents=True)
    (mem / "MEMORY.md").write_text("- [Db](db-choice.md)")
    (mem / "db-choice.md").write_text("---\nname: db-choice\n---\n\nThe blog uses SQLite.")
    (home / ".codex").mkdir()
    (home / ".codex/AGENTS.md").write_text("Always run the tests.")
    return home


def test_agent_memory_files_are_found_and_copied_once(home):
    store = Store(home / ".council")
    found = migrate.detect(agent_home(home))
    assert found == [{"kind": "agents", "path": str(home), "notes": 3}]
    assert migrate.run(store, found, say=lambda *_: None) == 3
    notes = sorted(n for n in store.list() if n.startswith("imported/"))
    assert notes == ["imported/claude-code/blog/db-choice.md", "imported/claude-code/claude.md", "imported/codex/agents.md"]
    assert "The blog uses SQLite." in store.read(notes[0]).text and "Imported from" in store.read(notes[0]).text
    thread = store.read("threads.md").text
    assert "Bring the user's existing memory over" in thread and "`imported/claude-code/`" in thread
    assert store.index.search("SQLite")[0]["path"] == "imported/claude-code/blog/db-choice.md"
    assert migrate.run(store, migrate.detect(home), say=lambda *_: None) == 0
    assert (home / ".claude/CLAUDE.md").read_text() == "# About me\n\nShort answers, please."


def test_agent_is_asked_even_when_nothing_was_found(home):
    store = Store(home / ".council")
    assert migrate.detect(home) == []
    migrate.run(store, [], say=lambda *_: None)
    assert "any other memory system" in store.read("threads.md").text


def vault_folder(tmp_path):
    v = tmp_path / "Brain"
    (v / "01-Companion").mkdir(parents=True)
    (v / "01-Companion/Core.md").write_text("# Core\n\nLikes tea.")
    return v


def test_known_vault_maps_onto_core_only_while_memory_is_fresh(home, tmp_path):
    v = vault_folder(tmp_path)
    (home / ".claude.json").write_text(json.dumps({"projects": {str(v): {}, str(tmp_path / "gone"): {}}}))
    found = migrate.detect(home)
    assert found == [{"kind": "vault", "path": str(v), "notes": 1}]

    used = Store(home / "used")
    used.write("projects/a/project.md", "# A")
    said = []
    assert migrate.run(used, found, say=said.append) == 0 and "already in use" in said[0]
    assert "Likes tea" not in used.read("core.md").text

    fresh = Store(home / "fresh")
    assert migrate.run(fresh, found, say=lambda *_: None) == 1
    assert "Likes tea." in fresh.read("core.md").text


def test_named_folder_is_copied_with_its_layout(home, tmp_path):
    src = tmp_path / "My Notes"
    (src / "work" / ".hidden").mkdir(parents=True)
    (src / "work/plan one.md").write_text("Ship it.")
    (src / "work/.hidden/x.md").write_text("no")
    (src / "readme.txt").write_text("no")
    store = Store(home / ".council")
    assert migrate.kind_of(src) == "folder"
    migrate.run(store, [{"kind": "folder", "path": str(src)}], say=lambda *_: None, explicit=True)
    assert [n for n in store.list() if n.startswith("imported/")] == ["imported/my-notes/work/plan-one.md"]
