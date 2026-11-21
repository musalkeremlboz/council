"""`council install`, `uninstall`, `status` and `update`: COUNCIL on the user's own computer.

Install does everything a new user needs in one go: an access token, a background service that starts
at login, Claude Code hooks and MCP tools, the import of any memory the user already has, and a daily
job that keeps COUNCIL on the latest published release. Nothing here needs administrator rights.

Supported: macOS (launchd), Linux (systemd user services) and Windows (a login entry in the registry
plus a scheduled task for updates).
"""

from __future__ import annotations

import json
import os
import platform
import plistlib
import re
import secrets
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import REPO, __version__

SERVICE = "ai.council.memory"
UPDATER = "ai.council.update"
WIN_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
WIN_RUN_NAME = "COUNCIL Memory"
WIN_TASK = "COUNCIL Update"
HOOKS = {"SessionStart": 10, "UserPromptSubmit": 8, "Stop": 5}
HOOK_MARK = ".council/hook.py"


class Setup:
    """Where things live for one user, and how to reach the operating system. Tests replace ``run``."""

    def __init__(self, data: Path, port: int | None = None, home: Path | None = None, system: str | None = None,
                 run=None, say=print, spawn=None):
        self.home = home or Path.home()
        self.data = Path(data).expanduser().resolve()
        self.config = self.home / ".config" / "council" / "config.json"
        if port is None:  # the port chosen at install time, remembered in the client config
            m = re.fullmatch(r"http://127\.0\.0\.1:(\d+)", str((self._read_json(self.config) or {}).get("url", "")))
            port = int(m.group(1)) if m else 8765
        self.port = port
        self.system = system or platform.system()
        self.say = say
        self.run = run or (lambda cmd: subprocess.run(cmd, capture_output=True, text=True))
        self.url = f"http://127.0.0.1:{port}"
        self.hook = self.home / ".council" / "hook.py"
        self.settings = self.home / ".claude" / "settings.json"
        self.claude_json = self.home / ".claude.json"
        self.python = [sys.executable, "-m", "council.cli", "--data", str(self.data)]
        self.spawn = spawn or _spawn_detached

    # ---------- small helpers ----------
    def _write_json(self, path: Path, value, mode: int | None = None) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".council-tmp")
        tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if mode is not None:
            os.chmod(tmp, mode)
        os.replace(tmp, path)

    def _read_json(self, path: Path):
        """The file's JSON, {} when it does not exist, None when it exists but cannot be parsed."""
        if not path.exists():
            return {}
        try:
            value = json.loads(path.read_text(encoding="utf-8") or "{}")
        except (OSError, ValueError):
            return None
        return value if isinstance(value, dict) else None

    def _backup_once(self, path: Path) -> None:
        backup = path.with_name(path.name + ".before-council")
        if path.exists() and not backup.exists():
            shutil.copy2(path, backup)

    def token(self) -> str:
        f = self.data / "token"
        if not f.exists():
            self.data.mkdir(parents=True, exist_ok=True)
            f.write_text(secrets.token_urlsafe(32) + "\n")
            os.chmod(f, 0o600)
        return f.read_text().strip()

    def healthy(self, wait: float = 0) -> str | None:
        """The running service's version, or None."""
        deadline = time.time() + wait
        while True:
            try:
                with urllib.request.urlopen(self.url + "/health", timeout=2) as r:
                    return json.loads(r.read().decode()).get("version")
            except (OSError, ValueError, urllib.error.URLError):
                if time.time() >= deadline:
                    return None
                time.sleep(0.4)

    # ---------- background service ----------
    def _agents(self) -> Path:
        return self.home / "Library" / "LaunchAgents"

    def _units(self) -> Path:
        return self.home / ".config" / "systemd" / "user"

    def _domain(self) -> str:
        """The user's launchd domain: the desktop session, or the plain user domain over SSH."""
        if not hasattr(self, "_launchd_domain"):
            uid = getattr(os, "getuid", lambda: 0)()
            gui = f"gui/{uid}"
            self._launchd_domain = gui if self.run(["launchctl", "print", gui]).returncode == 0 else f"user/{uid}"
        return self._launchd_domain

    def install_service(self, auto_update: bool) -> None:
        log = str(self.data / "service.log")
        if self.system == "Darwin":
            self._agents().mkdir(parents=True, exist_ok=True)
            jobs = {SERVICE: {
                "Label": SERVICE, "ProgramArguments": self.python + ["serve", "--port", str(self.port)],
                "RunAtLoad": True, "KeepAlive": True, "StandardOutPath": log, "StandardErrorPath": log,
                "ProcessType": "Background",
            }}
            if auto_update:
                jobs[UPDATER] = {
                    "Label": UPDATER, "ProgramArguments": self.python + ["update"],
                    "StartCalendarInterval": {"Hour": 4, "Minute": secrets.randbelow(60)},
                    "StandardOutPath": str(self.data / "update.log"), "StandardErrorPath": str(self.data / "update.log"),
                    "ProcessType": "Background",
                }
            else:
                self._remove_job(UPDATER)
            for label, job in jobs.items():
                plist = self._agents() / f"{label}.plist"
                self.run(["launchctl", "bootout", f"{self._domain()}/{label}"])
                plist.write_bytes(plistlib.dumps(job))
                r = self.run(["launchctl", "bootstrap", self._domain(), str(plist)])
                if r.returncode != 0:
                    raise SetupError(f"launchd refused {label}: {(r.stderr or r.stdout).strip()}")
        elif self.system == "Linux":
            self._units().mkdir(parents=True, exist_ok=True)
            cmd = " ".join(_quote(a) for a in self.python)
            (self._units() / "council.service").write_text(
                "[Unit]\nDescription=COUNCIL memory\n\n[Service]\n"
                f"ExecStart={cmd} serve --port {self.port}\nRestart=on-failure\nRestartSec=3\n\n"
                "[Install]\nWantedBy=default.target\n")
            (self._units() / "council-update.service").write_text(
                f"[Unit]\nDescription=COUNCIL update check\n\n[Service]\nType=oneshot\nExecStart={cmd} update\n")
            (self._units() / "council-update.timer").write_text(
                "[Unit]\nDescription=Daily COUNCIL update check\n\n[Timer]\nOnCalendar=daily\n"
                "RandomizedDelaySec=1h\nPersistent=true\n\n[Install]\nWantedBy=timers.target\n")
            r = self.run(["systemctl", "--user", "daemon-reload"])
            if r.returncode != 0:
                raise SetupError("systemd user services are not available here: " + (r.stderr or "").strip())
            self.run(["systemctl", "--user", "enable", "--now", "council.service"])
            self.run(["systemctl", "--user", "restart", "council.service"])
            verb = ["enable", "--now"] if auto_update else ["disable", "--now"]
            self.run(["systemctl", "--user", *verb, "council-update.timer"])
        elif self.system == "Windows":
            self._win_run_value(self._win_command("serve", "--port", str(self.port)))
            self._win_stop()
            self.spawn(self._win_argv("serve", "--port", str(self.port)))
            if auto_update:
                r = self.run(["schtasks", "/Create", "/TN", WIN_TASK, "/SC", "DAILY", "/ST", f"12:{secrets.randbelow(60):02d}",
                              "/TR", self._win_command("update"), "/F"])
                if r.returncode != 0:
                    self.say("    the daily update check could not be scheduled: " + (r.stderr or r.stdout or "").strip()[:200])
            else:
                self.run(["schtasks", "/Delete", "/TN", WIN_TASK, "/F"])
        else:
            raise SetupError(f"{self.system} is not supported yet (macOS, Linux and Windows are).")

    # Windows: no service manager without administrator rights, so the service is a hidden process
    # started at login from the user's Run key and found again through its pid file.
    def _win_argv(self, *args: str) -> list[str]:
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        return [str(pythonw if pythonw.exists() else sys.executable), *self.python[1:], *args]

    def _win_command(self, *args: str) -> str:
        return subprocess.list2cmdline(self._win_argv(*args))

    def _win_run_value(self, command: str | None) -> bool:
        """Set (or with None, delete) the login entry. Returns whether an entry exists afterwards."""
        import winreg

        access = winreg.KEY_SET_VALUE | winreg.KEY_QUERY_VALUE
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, WIN_RUN_KEY, 0, access) as key:  # a new account may lack the key
            if command is None:
                try:
                    winreg.DeleteValue(key, WIN_RUN_NAME)
                except OSError:
                    pass
                return False
            if command:
                winreg.SetValueEx(key, WIN_RUN_NAME, 0, winreg.REG_SZ, command)
            try:
                winreg.QueryValueEx(key, WIN_RUN_NAME)
                return True
            except OSError:
                return False

    def _win_stop(self) -> None:
        try:
            pid = int((self.data / "service.pid").read_text().strip())
        except (OSError, ValueError):
            return
        self.run(["taskkill", "/PID", str(pid), "/F"])
        for _ in range(20):  # the port is free once the old process is gone
            if not self.healthy():
                break
            time.sleep(0.3)

    def _remove_job(self, label: str) -> None:
        self.run(["launchctl", "bootout", f"{self._domain()}/{label}"])
        (self._agents() / f"{label}.plist").unlink(missing_ok=True)

    def remove_service(self) -> None:
        if self.system == "Darwin":
            self._remove_job(SERVICE)
            self._remove_job(UPDATER)
        elif self.system == "Linux":
            self.run(["systemctl", "--user", "disable", "--now", "council.service", "council-update.timer"])
            for name in ("council.service", "council-update.service", "council-update.timer"):
                (self._units() / name).unlink(missing_ok=True)
            self.run(["systemctl", "--user", "daemon-reload"])
        elif self.system == "Windows":
            self._win_run_value(None)
            self._win_stop()
            self.run(["schtasks", "/Delete", "/TN", WIN_TASK, "/F"])

    def restart_service(self) -> bool:
        if self.system == "Darwin":
            return self.run(["launchctl", "kickstart", "-k", f"{self._domain()}/{SERVICE}"]).returncode == 0
        if self.system == "Windows":
            self._win_stop()
            self.spawn(self._win_argv("serve", "--port", str(self.port)))
            return True
        return self.run(["systemctl", "--user", "restart", "council.service"]).returncode == 0

    def service_installed(self) -> bool:
        if self.system == "Darwin":
            return (self._agents() / f"{SERVICE}.plist").exists()
        if self.system == "Windows":
            return self._win_run_value("")
        return (self._units() / "council.service").exists()

    def updater_installed(self) -> bool:
        if self.system == "Darwin":
            return (self._agents() / f"{UPDATER}.plist").exists()
        if self.system == "Windows":
            return self.run(["schtasks", "/Query", "/TN", WIN_TASK]).returncode == 0
        return self.run(["systemctl", "--user", "is-enabled", "council-update.timer"]).returncode == 0

    # ---------- Claude Code ----------
    def other_connection(self) -> str | None:
        """The address of a different COUNCIL memory this computer is already connected to."""
        cfg = self._read_json(self.config) or {}
        url = str(cfg.get("url", "")).rstrip("/")
        return url if url and url != self.url else None

    def has_claude_code(self) -> bool:
        return (self.home / ".claude").is_dir() or self.claude_json.exists()

    def copy_hook(self) -> None:
        self.hook.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(__file__).with_name("hook.py"), self.hook)

    def connect(self) -> list[str]:
        """Point this computer's Claude Code at the local memory. Returns what could not be done."""
        problems = []
        self._write_json(self.config, {**(self._read_json(self.config) or {}), "url": self.url, "token": self.token()},
                         mode=0o600)
        self.copy_hook()
        if not self.has_claude_code():
            return ["Claude Code was not found on this computer. Run `council install` again after installing it."]

        settings = self._read_json(self.settings)
        if settings is None:
            problems.append(f"{self.settings} is not valid JSON, so the hooks were not added.")
        else:
            # forward slashes work in every shell Claude Code may use, on Windows too
            command = f"{_quote(Path(sys.executable).as_posix())} {_quote(self.hook.as_posix())}"
            hooks = settings.setdefault("hooks", {})
            for event, timeout in HOOKS.items():
                entries = hooks.setdefault(event, [])
                ours = [h for e in entries for h in e.get("hooks", []) if HOOK_MARK in str(h.get("command", ""))]
                if ours:
                    for h in ours:
                        h["command"] = command
                else:
                    entries.append({"hooks": [{"type": "command", "command": command, "timeout": timeout}]})
            self._backup_once(self.settings)
            self._write_json(self.settings, settings)

        cj = self._read_json(self.claude_json)
        if cj is None:
            problems.append(f"{self.claude_json} is not valid JSON, so the MCP tools were not added.")
        else:
            cj.setdefault("mcpServers", {})["council"] = {
                "type": "http", "url": self.url + "/mcp", "headers": {"Authorization": f"Bearer {self.token()}"},
            }
            self._backup_once(self.claude_json)
            self._write_json(self.claude_json, cj, mode=0o600)
        return problems

    def disconnect(self) -> None:
        settings = self._read_json(self.settings)
        if settings and isinstance(settings.get("hooks"), dict):
            for event in list(settings["hooks"]):
                kept = []
                for entry in settings["hooks"][event]:
                    entry["hooks"] = [h for h in entry.get("hooks", []) if HOOK_MARK not in str(h.get("command", ""))]
                    if entry["hooks"]:
                        kept.append(entry)
                if kept:
                    settings["hooks"][event] = kept
                else:
                    del settings["hooks"][event]
            self._write_json(self.settings, settings)
        cj = self._read_json(self.claude_json)
        if cj and cj.get("mcpServers", {}).get("council", {}).get("url", "").startswith(self.url):
            del cj["mcpServers"]["council"]
            self._write_json(self.claude_json, cj, mode=0o600)
        if not self.other_connection():
            self.config.unlink(missing_ok=True)
            self.hook.unlink(missing_ok=True)

    def hooks_installed(self) -> bool:
        settings = self._read_json(self.settings) or {}
        return all(any(HOOK_MARK in str(h.get("command", "")) for e in settings.get("hooks", {}).get(event, [])
                       for h in e.get("hooks", [])) for event in HOOKS)


class SetupError(Exception):
    """Something the user has to know about; the message is shown as is."""


def _spawn_detached(argv: list[str]) -> None:
    """Start a process that outlives this one and shows no window (Windows)."""
    flags = 0x00000008 | 0x00000200 | 0x08000000  # DETACHED_PROCESS, CREATE_NEW_PROCESS_GROUP, CREATE_NO_WINDOW
    subprocess.Popen(argv, creationflags=flags, close_fds=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _quote(arg: str) -> str:
    return arg if re.fullmatch(r"[\w./:@+-]+", arg) else '"' + arg.replace('"', '\\"') + '"'


# ---------------------------------------------------------------- commands

def install(s: Setup, auto_update: bool = True, do_import: bool = True, sources: list[str] | None = None,
            force: bool = False) -> int:
    say = s.say
    other = s.other_connection()
    if other and not force:
        say(f"This computer is already connected to a COUNCIL memory at {other}.")
        say("Nothing was changed. To switch it to a memory on this computer, run: council install --force")
        return 1
    say(f"COUNCIL {__version__}")
    s.token()
    from .store import Store

    store = Store(s.data)  # creates the vault with its first notes
    say(f"1/4 memory        {store.vault}")
    if do_import:
        from . import migrate

        found = [{"kind": migrate.kind_of(Path(p).expanduser()), "path": str(Path(p).expanduser().resolve())}
                 for p in sources] if sources else migrate.detect(s.home)
        if not found:
            say("    no existing memory found on this computer")
        migrate.run(store, found, say=say, explicit=bool(sources))
    try:
        s.install_service(auto_update)
    except SetupError as e:
        say(f"2/4 service       FAILED: {e}")
        say(f"    You can still run it by hand: {' '.join(s.python)} serve")
        return 1
    version = s.healthy(wait=20)
    if not version:
        say(f"2/4 service       did not answer on {s.url}. See {s.data / 'service.log'}")
        return 1
    say(f"2/4 service       running on {s.url}, starts by itself at login")
    problems = s.connect()
    say("3/4 Claude Code   " + ("hooks and MCP tools connected" if not problems else "not fully connected"))
    for p in problems:
        say(f"    {p}")
    say("4/4 updates       " + ("checked every day, installed automatically" if auto_update else "off (run `council update` yourself)"))
    say("")
    say("Done. Open a new Claude Code session and say hello: it already knows what is in the memory.")
    say(f"Your notes are plain files in {store.vault}")
    say(f"The command, for later: {Path(sys.executable).with_name('council')}")
    return 0


def uninstall(s: Setup) -> int:
    s.remove_service()
    s.disconnect()
    s.say("COUNCIL was removed from this computer: service, update check, hooks and MCP tools.")
    s.say(f"Your notes were not touched: {s.data / 'vault'}")
    return 0


def status(s: Setup) -> int:
    version = s.healthy()
    info = _update_state(s.data)
    s.say(f"version      {__version__}")
    s.say(f"service      {'running on ' + s.url + (' (' + version + ')' if version else '') if version else 'not running'}"
          + ("" if s.service_installed() else " · not installed as a background service"))
    s.say(f"hooks        {'installed' if s.hooks_installed() else 'not installed'}")
    s.say(f"auto-update  {'on' if s.updater_installed() else 'off'}"
          + (f" · last check {time.strftime('%Y-%m-%d %H:%M', time.localtime(info['checked']))}" if info.get("checked") else "")
          + (f" · problem: {info['error']}" if info.get("error") else ""))
    s.say(f"notes        {s.data / 'vault'}")
    return 0 if version else 1


# ---------------------------------------------------------------- updates

def version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", v)[:3])


def latest_release(repo: str = REPO) -> str | None:
    """Tag of the latest published release, or None when it cannot be read."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "council-update"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/releases/latest", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read().decode()).get("tag_name") or None
    except (OSError, ValueError, urllib.error.URLError):
        return None


def _update_state(data: Path) -> dict:
    try:
        return json.loads((Path(data) / "update.json").read_text())
    except (OSError, ValueError):
        return {}


def _save_update_state(data: Path, state: dict) -> None:
    Path(data).mkdir(parents=True, exist_ok=True)
    tmp = Path(data) / ".update.json.tmp"
    tmp.write_text(json.dumps(state))
    os.replace(tmp, Path(data) / "update.json")


def update(s: Setup, force: bool = False, latest=latest_release) -> int:
    """Install the latest published release if it is newer than this one, then restart the service."""
    state = _update_state(s.data)
    state["checked"] = time.time()
    tag = latest()
    if not tag:
        state["error"] = "could not read the latest release"
        _save_update_state(s.data, state)
        s.say("could not read the latest release from GitHub")
        return 1
    if version_tuple(tag) <= version_tuple(__version__) and not force:
        state.pop("error", None)
        _save_update_state(s.data, state)
        s.say(f"up to date ({__version__})")
        return 0
    source = os.environ.get("COUNCIL_UPDATE_SOURCE", f"git+https://github.com/{REPO}@{{tag}}").format(tag=tag)
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", source]
    if force:
        cmd[5:5] = ["--force-reinstall", "--no-deps"]
    r = s.run(cmd)
    if r.returncode != 0:
        state["error"] = f"installing {tag} failed: " + ((r.stderr or r.stdout or "").strip().splitlines() or ["pip failed"])[-1][:200]
        _save_update_state(s.data, state)
        s.say(state["error"])
        return 1
    if s.hook.exists():
        s.copy_hook()  # the file on disk is the new release's by now
    state.pop("error", None)
    state["installed"] = {"from": __version__, "to": tag.lstrip("v"), "at": time.time(), "announced": False}
    _save_update_state(s.data, state)
    restarted = s.service_installed() and s.restart_service()
    s.say(f"updated {__version__} -> {tag.lstrip('v')}" + ("" if restarted else " (restart the service to use it)"))
    return 0


def update_notice(data: Path) -> str | None:
    """One sentence for the agent after an automatic update or while updates keep failing; told once."""
    state = _update_state(data)
    done = state.get("installed")
    if done and not done.get("announced"):
        done["announced"] = True
        _save_update_state(data, state)
        return f"COUNCIL updated itself from {done['from']} to {done['to']}. Tell the user once."
    if state.get("error") and time.time() - state.get("error_told", 0) > 7 * 86400:
        state["error_told"] = time.time()
        _save_update_state(data, state)
        return f"COUNCIL's automatic update is failing ({state['error']}). Tell the user once."
    return None
