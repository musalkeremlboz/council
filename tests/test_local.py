import contextlib
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
    """Stands in for subprocess: remembers every command and answers with a chosen exit code.

    It keeps just enough launchd state for `launchctl print` to tell a loaded job from an unloaded one.
    """

    def __init__(self, fail=()):
        self.calls, self.fail, self.loaded = [], fail, set()

    def __call__(self, cmd):
        self.calls.append(cmd)
        bad = any(word in cmd for word in self.fail)
        if cmd[:2] == ["launchctl", "bootstrap"]:
            self.loaded.add(cmd[-1].rsplit("/", 1)[-1].removesuffix(".plist"))
        elif cmd[:2] == ["launchctl", "bootout"]:
            self.loaded.discard(cmd[-1].rsplit("/", 1)[-1])
        elif cmd[:2] == ["launchctl", "print"] and cmd[-1].count("/") == 2:
            bad = cmd[-1].rsplit("/", 1)[-1] not in self.loaded
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
    settings = json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))
    return [h["command"] for e in settings["hooks"][event] for h in e["hooks"]]


def test_install_sets_everything_up_and_keeps_other_settings(home):
    (home / ".claude" / "settings.json").write_text(json.dumps({
        "model": "x", "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "other-tool"}]}]}}), encoding="utf-8")
    (home / ".claude.json").write_text(json.dumps({"mcpServers": {"other": {"url": "http://x"}}, "projects": {}}), encoding="utf-8")
    s = make(home)
    assert local.install(s) == 0

    assert (home / "Library/LaunchAgents/ai.council.memory.plist").exists()
    assert (home / "Library/LaunchAgents/ai.council.update.plist").exists()
    assert s.run.ran("launchctl", "bootstrap")
    cfg = json.loads((home / ".config/council/config.json").read_text(encoding="utf-8"))
    assert cfg["url"] == "http://127.0.0.1:8799" and cfg["token"] == (home / ".council/token").read_text(encoding="utf-8").strip()
    assert (home / ".council/hook.py").exists()

    settings = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))
    assert settings["model"] == "x"
    assert hook_commands(home, "Stop")[0] == "other-tool" and ".council/hook.py" in hook_commands(home, "Stop")[1]
    assert all(".council/hook.py" in hook_commands(home, e)[-1] for e in ("SessionStart", "UserPromptSubmit"))
    assert (home / ".claude/settings.json.before-council").exists()
    cj = json.loads((home / ".claude.json").read_text(encoding="utf-8"))
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
    cfg.write_text(json.dumps({"url": "https://memory.example.com", "token": "t"}), encoding="utf-8")
    s = make(home)
    assert local.install(s) == 1
    assert json.loads(cfg.read_text(encoding="utf-8"))["url"] == "https://memory.example.com"
    assert not s.run.calls and not (home / ".claude/settings.json").exists()
    assert local.install(make(home), force=True) == 0
    assert json.loads(cfg.read_text(encoding="utf-8"))["url"] == "http://127.0.0.1:8799"


def test_install_without_auto_update(home):
    s = make(home)
    local.install(s, auto_update=False)
    assert not (home / "Library/LaunchAgents/ai.council.update.plist").exists()
    assert not s.updater_installed()


def test_uninstall_removes_only_ours_and_keeps_notes(home):
    (home / ".claude/settings.json").write_text(json.dumps(
        {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "other-tool"}]}]}}), encoding="utf-8")
    s = make(home)
    local.install(s)
    local.uninstall(s)
    settings = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))
    assert settings["hooks"] == {"Stop": [{"hooks": [{"type": "command", "command": "other-tool"}]}]}
    assert "council" not in json.loads((home / ".claude.json").read_text(encoding="utf-8"))["mcpServers"]
    assert not (home / "Library/LaunchAgents/ai.council.memory.plist").exists()
    assert not (home / ".config/council/config.json").exists()
    assert (home / ".council/vault/core.md").exists()


def test_invalid_settings_file_is_left_alone(home):
    (home / ".claude/settings.json").write_text("{not json", encoding="utf-8")
    assert local.install(make(home)) == 0
    assert (home / ".claude/settings.json").read_text(encoding="utf-8") == "{not json"


def test_linux_uses_systemd_user_units(home):
    s = make(home, system="Linux")
    assert local.install(s) == 0
    unit = (home / ".config/systemd/user/council.service").read_text(encoding="utf-8")
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
    (home / ".council/service.pid").write_text("4242", encoding="utf-8")
    s.healthy = lambda wait=0: None
    local.uninstall(s)
    assert not registry and s.run.ran("taskkill", "4242") and s.run.ran("schtasks", "/Delete")


class FakeWinreg:
    """A Run key that allows reading only, as in a sandbox that refuses registry writes (Codex on Windows)."""

    HKEY_CURRENT_USER, KEY_QUERY_VALUE, KEY_SET_VALUE, REG_SZ = object(), 1, 2, 1

    def __init__(self, values=None, readable=True):
        self.values, self.readable = dict(values or {}), readable

    def _key(self, access):
        if access & self.KEY_SET_VALUE or not self.readable:
            raise PermissionError(5, "Access is denied")
        return contextlib.nullcontext(self)

    def OpenKey(self, root, path, reserved=0, access=1):
        return self._key(access)

    def CreateKeyEx(self, root, path, reserved=0, access=2):
        return self._key(access)

    def QueryValueEx(self, key, name):
        if name not in self.values:
            raise FileNotFoundError(2, "not found")
        return self.values[name], self.REG_SZ


@pytest.mark.parametrize("values, expected", [({local.WIN_RUN_NAME: "pythonw serve"}, True), ({}, False)])
def test_windows_status_reads_the_login_entry_without_write_access(home, monkeypatch, values, expected):
    monkeypatch.setitem(sys.modules, "winreg", FakeWinreg(values))
    s = make(home, system="Windows")
    assert s.service_installed() is expected
    assert local.status(s) == 0


def test_windows_status_survives_an_unreadable_registry(home, monkeypatch):
    monkeypatch.setitem(sys.modules, "winreg", FakeWinreg(readable=False))
    said = []
    s = make(home, system="Windows")
    s.say = said.append
    assert s.service_installed() is None
    assert local.status(s) == 0
    assert any("could not be read" in line for line in said)


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
    state = json.loads((s.data / "update.json").read_text(encoding="utf-8"))
    assert "v9.0.0" in state["error"] and "installed" not in state
    store = Store(s.data)
    assert "automatic update" not in bootstrap(store)  # one failed check (a laptop offline) is not news
    state["error_since"] = time.time() - 4 * 86400
    (s.data / "update.json").write_text(json.dumps(state), encoding="utf-8")
    assert "automatic update is failing" in bootstrap(store)
    assert "automatic update" not in bootstrap(store)  # told once, then again only after a week


# ---------------------------------------------------------------- existing memory

def agent_home(home):
    (home / ".claude/CLAUDE.md").write_text("# About me\n\nShort answers, please.", encoding="utf-8")
    # Claude Code names a project's folder after its path, every other character turned into a dash
    mem = home / ".claude/projects" / (re.sub(r"[^A-Za-z0-9]", "-", str(home)) + "-blog") / "memory"
    mem.mkdir(parents=True)
    (mem / "MEMORY.md").write_text("- [Db](db-choice.md)", encoding="utf-8")
    (mem / "db-choice.md").write_text("---\nname: db-choice\n---\n\nThe blog uses SQLite.", encoding="utf-8")
    (home / ".codex").mkdir()
    (home / ".codex/AGENTS.md").write_text("Always run the tests.", encoding="utf-8")
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
    assert "Bring the user's existing memory over" in thread and "offer to retire them" in thread
    assert migrate.summary(store) == (3, [str(home)])
    assert store.index.search("SQLite")[0]["path"] == "imported/claude-code/blog/db-choice.md"
    assert migrate.run(store, migrate.detect(home), say=lambda *_: None) == 0
    assert (home / ".claude/CLAUDE.md").read_text(encoding="utf-8") == "# About me\n\nShort answers, please."


def test_agent_is_asked_even_when_nothing_was_found(home):
    store = Store(home / ".council")
    assert migrate.detect(home) == []
    migrate.run(store, [], say=lambda *_: None)
    assert "not under `imported/` yet" in store.read("threads.md").text


def vault_folder(tmp_path):
    v = tmp_path / "Brain"
    (v / "01-Companion").mkdir(parents=True)
    (v / "01-Companion/Core.md").write_text("# Core\n\nLikes tea.", encoding="utf-8")
    return v


def test_known_vault_maps_onto_core_only_while_memory_is_fresh(home, tmp_path):
    v = vault_folder(tmp_path)
    (home / ".claude.json").write_text(json.dumps({"projects": {str(v): {}, str(tmp_path / "gone"): {}}}), encoding="utf-8")
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
    (src / "work/plan one.md").write_text("Ship it.", encoding="utf-8")
    (src / "work/.hidden/x.md").write_text("no", encoding="utf-8")
    (src / "readme.txt").write_text("no", encoding="utf-8")
    store = Store(home / ".council")
    assert migrate.kind_of(src) == "folder"
    migrate.run(store, [{"kind": "folder", "path": str(src)}], say=lambda *_: None, explicit=True)
    assert [n for n in store.list() if n.startswith("imported/")] == ["imported/my-notes/work/plan-one.md"]


def test_single_file_can_be_imported_and_repeating_adds_nothing(home, tmp_path):
    f = tmp_path / "Facts About Me.md"
    f.write_text("Lives in Izmir.", encoding="utf-8")
    store = Store(home / ".council")
    assert migrate.kind_of(f) == "file"
    said = []
    assert migrate.run(store, [{"kind": "file", "path": str(f)}], say=said.append, explicit=True) == 1
    assert "imported 1 note from" in said[0]
    assert "imported/files/facts-about-me.md" in store.list()
    assert migrate.run(store, [{"kind": "file", "path": str(f)}], say=said.append, explicit=True) == 0


def test_install_stops_when_the_port_belongs_to_another_program(home, monkeypatch):
    s = make(home)
    s.healthy = lambda wait=0: None
    monkeypatch.setattr(local, "_port_taken", lambda port: True)
    said = []
    s.say = said.append
    assert local.install(s) == 1
    assert any("--port 8800" in line for line in said) and not s.run.ran("launchctl", "bootstrap")


def test_status_reports_connections_and_imports(home):
    agent_home(home)
    s = make(home)
    local.install(s)
    said = []
    s.say = said.append
    assert local.status(s) == 0
    text = "\n".join(said)
    assert "mcp tools    connected to Claude Code" in text and "imported     3 notes, from:" in text


def tool_entries(home):
    settings = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))
    return [e for e in settings["hooks"].get("PreToolUse", []) if any(".council/hook.py" in h["command"] for h in e["hooks"])]

def test_install_registers_the_sub_agent_hook_with_its_matcher(home):
    (home / ".claude/settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "other-tool"}]}]}}), encoding="utf-8")
    s = make(home)
    local.install(s); local.install(s)                                   # twice: no duplicate
    entries = tool_entries(home)
    assert len(entries) == 1 and entries[0]["matcher"] == "Agent|Task" and entries[0]["hooks"][0]["timeout"] == 5
    assert hook_commands(home, "PreToolUse")[0] == "other-tool"          # the user's own entry survives
    assert s.hooks_installed() and s.tool_hooks_installed()

def test_an_old_matcher_of_ours_is_refreshed_in_place(home):
    s = make(home); local.install(s)
    settings = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))
    settings["hooks"]["PreToolUse"][0]["matcher"] = "Task"
    (home / ".claude/settings.json").write_text(json.dumps(settings), encoding="utf-8")
    local.install(s)
    assert [e["matcher"] for e in tool_entries(home)] == ["Agent|Task"]

def three_hook_install(home):
    """An installation made by a release that knew only the memory hooks."""
    s = make(home); local.install(s)
    settings = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))
    del settings["hooks"]["PreToolUse"]
    (home / ".claude/settings.json").write_text(json.dumps(settings), encoding="utf-8")
    return s

def test_an_older_installation_still_counts_as_installed_and_gets_the_hook_added(home):
    s = three_hook_install(home)
    assert s.hooks_installed() and not s.tool_hooks_installed()
    assert s.ensure_tool_hooks() is True and s.tool_hooks_installed()
    assert s.ensure_tool_hooks() is False                                 # nothing left to do

def test_ensure_leaves_a_computer_without_our_hooks_alone(home):
    (home / ".claude/settings.json").write_text(json.dumps({"hooks": {"Stop": [
        {"hooks": [{"type": "command", "command": "other-tool"}]}]}}), encoding="utf-8")
    before = (home / ".claude/settings.json").read_text(encoding="utf-8")
    assert make(home).ensure_tool_hooks() is False
    assert (home / ".claude/settings.json").read_text(encoding="utf-8") == before

def test_ensure_leaves_invalid_settings_alone(home):
    s = three_hook_install(home)
    (home / ".claude/settings.json").write_text("{not json", encoding="utf-8")
    assert s.ensure_tool_hooks() is False and (home / ".claude/settings.json").read_text(encoding="utf-8") == "{not json"

def test_uninstall_removes_the_sub_agent_hook_and_keeps_the_users(home):
    (home / ".claude/settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "other-tool"}]}]}}), encoding="utf-8")
    s = make(home); local.install(s); local.uninstall(s)
    assert json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))["hooks"] == {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "other-tool"}]}]}

def test_status_reports_delegation_on_its_own_line(home):
    s = three_hook_install(home)
    said = []; s.say = said.append
    local.status(s)
    text = "\n".join(said)
    assert "hooks        installed" in text and "delegation   enforce · hook not registered" in text
    s.ensure_tool_hooks()
    cfg = json.loads((home / ".config/council/config.json").read_text(encoding="utf-8"))
    (home / ".config/council/config.json").write_text(json.dumps({**cfg, "delegation": "off"}), encoding="utf-8")
    said.clear(); local.status(s)
    assert "delegation   off" in "\n".join(said) and "not registered" not in "\n".join(said)

def test_the_service_adds_the_hook_only_on_an_installer_made_setup(home, monkeypatch):
    from council import cli
    s = three_hook_install(home)
    seen = []
    monkeypatch.setattr(local, "Setup", lambda *a, **k: s)
    monkeypatch.setattr(s, "ensure_tool_hooks", lambda: seen.append("ensured") or True)
    monkeypatch.setattr("uvicorn.run", lambda *a, **k: None)
    monkeypatch.setattr(s, "service_installed", lambda: True)
    cli.main(["--data", str(home / ".council"), "serve", "--port", "8799"])
    monkeypatch.setattr(s, "service_installed", lambda: False)             # e.g. a server run by hand or by systemd
    cli.main(["--data", str(home / ".council"), "serve", "--port", "8799"])
    assert seen == ["ensured"]

def test_our_hook_hand_merged_into_a_users_entry_is_moved_to_its_own(home):
    s = make(home); local.install(s)
    ours = tool_entries(home)[0]["hooks"][0]
    settings = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))
    settings["hooks"]["PreToolUse"] = [{"matcher": "Bash", "hooks": [{"type": "command", "command": "other-tool"}, ours]}]
    (home / ".claude/settings.json").write_text(json.dumps(settings), encoding="utf-8")
    local.install(s)
    entries = json.loads((home / ".claude/settings.json").read_text(encoding="utf-8"))["hooks"]["PreToolUse"]
    assert entries[0] == {"matcher": "Bash", "hooks": [{"type": "command", "command": "other-tool"}]}
    assert [e["matcher"] for e in tool_entries(home)] == ["Agent|Task"] and len(entries) == 2

def test_status_survives_a_config_that_is_not_an_object(home):
    s = three_hook_install(home)
    (home / ".config/council/config.json").write_text("[]", encoding="utf-8")
    said = []; s.say = said.append
    local.status(s)
    assert "delegation   enforce · hook not registered" in "\n".join(said)

def test_the_services_own_edit_keeps_a_copy_of_the_settings_it_changed(home):
    s = three_hook_install(home)
    settings = home / ".claude/settings.json"
    before = settings.read_text(encoding="utf-8")
    backup = home / ".claude/settings.json.before-council-delegation"
    assert s.ensure_tool_hooks() is True
    assert backup.read_text(encoding="utf-8") == before and "PreToolUse" not in before
    three_hook_install(home)                                             # a second edit keeps the first copy
    assert s.ensure_tool_hooks() is True and backup.read_text(encoding="utf-8") == before

def test_the_service_starts_even_when_adding_the_hook_fails(home, monkeypatch):
    from council import cli
    s = three_hook_install(home)
    started = []
    monkeypatch.setattr(local, "Setup", lambda *a, **k: s)
    monkeypatch.setattr(s, "service_installed", lambda: True)
    def broken(): raise RuntimeError("boom")
    monkeypatch.setattr(s, "ensure_tool_hooks", broken)
    monkeypatch.setattr("uvicorn.run", lambda *a, **k: started.append(True))
    assert cli.main(["--data", str(home / ".council"), "serve", "--port", "8799"]) == 0
    assert started == [True]
