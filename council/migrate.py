"""Bring the memory a user already has into a COUNCIL vault. Sources are only read, never changed.

Two layers, because no list of memory systems is ever complete:

1. What can be recognised from files is copied right away: the instruction and memory files AI agents
   keep in the home folder, and note vaults found among the folders the user opened in Claude Code.
2. A thread then asks the first agent session to look for any other memory system in use on this
   computer, move it over, and sort everything that was copied.

A vault whose layout COUNCIL knows maps onto COUNCIL's own files. Everything else lands under
``imported/``, where it is searchable but not loaded at session start.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from .importer import Importer, _find
from .store import SEED, Store, StoreError, now_local

MAX_NOTE_BYTES = 200_000
MAX_NOTES = 2000

# Where agents keep what they remember about the user, relative to the home folder: (source name, glob).
AGENT_FILES = [
    ("claude-code", ".claude/CLAUDE.md"),
    ("claude-code", ".claude/projects/*/memory/*.md"),
    ("codex", ".codex/AGENTS.md"),
    ("codex", ".codex/memories/**/*.md"),
    ("gemini", ".gemini/GEMINI.md"),
]
SKIP_NAMES = {"MEMORY.md"}  # an index that only points at the files next to it


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _is_mapped_vault(path: Path) -> bool:
    """A notes vault whose layout the mapping importer understands (companion files, projects, knowledge)."""
    try:
        if not path.is_dir():
            return False
        companion = _find(path, "Companion")
        return bool(companion and (companion / "Core.md").is_file())
    except OSError:
        return False


def _opened_folders(home: Path) -> list[Path]:
    """Folders the user opened in Claude Code, as recorded in ~/.claude.json."""
    try:
        projects = json.loads((home / ".claude.json").read_text(encoding="utf-8")).get("projects", {})
    except (OSError, ValueError):
        return []
    return [Path(p) for p in projects if isinstance(p, str) and Path(p).is_absolute()]


def _agent_files(home: Path) -> list[tuple[str, Path, str]]:
    """(source name, file, target note path) for every agent memory file under the home folder."""
    out, home_prefix = [], re.sub(r"[^A-Za-z0-9]", "-", str(home))
    for name, pattern in AGENT_FILES:
        for f in sorted(home.glob(pattern)):
            if not f.is_file() or f.name in SKIP_NAMES:
                continue
            parts = list(f.relative_to(home).parts[1:-1])  # folders between the agent's folder and the file
            parts = [p[len(home_prefix):] if p.startswith(home_prefix) else p for p in parts if p not in ("projects", "memory", "memories")]
            middle = "/".join(_slug(p) or "home" for p in parts)
            target = "/".join(x for x in ("imported", name, middle, (_slug(f.stem) or "note") + ".md") if x)
            out.append((name, f, target))
    return out


def detect(home: Path) -> list[dict]:
    """Memory already on this computer: [{"kind", "path", "notes"}]."""
    found = []
    for p in _opened_folders(home):
        if _is_mapped_vault(p):
            found.append({"kind": "vault", "path": str(p), "notes": len(Importer(p, None).scan())})
    files = _agent_files(home)
    if files:
        found.append({"kind": "agents", "path": str(home), "notes": len(files)})
    return found


def kind_of(path: Path) -> str:
    return "vault" if _is_mapped_vault(path) else "folder"


def is_fresh(store: Store) -> bool:
    """True while the vault holds nothing but its seed notes."""
    try:
        return set(store.list()) == set(SEED) and all(store.read(p).text == text for p, text in SEED.items())
    except StoreError:
        return False


def _readable(f: Path) -> str | None:
    try:
        return None if f.stat().st_size > MAX_NOTE_BYTES else f.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _write_new(store: Store, target: str, f: Path) -> bool:
    """Copy ``f`` to the note ``target`` unless a note is already there."""
    text = _readable(f)
    try:
        if text is None or not text.strip() or store.exists(target):
            return False
        text = text.rstrip("\n") + f"\n\n> Imported from `{f}` on {now_local():%Y-%m-%d}.\n"
        store.write(target, text, reason=f"import {f.name}")
    except StoreError:
        return False
    return True


def import_agent_files(store: Store, home: Path) -> list[str]:
    return [target for _, f, target in _agent_files(home) if _write_new(store, target, f)]


def import_folder(store: Store, src: Path) -> list[str]:
    """Copy every Markdown note of a folder to ``imported/<folder>/...``, keeping its layout."""
    base, done = f"imported/{_slug(src.name) or 'notes'}", []
    files = sorted(f for f in src.rglob("*.md") if not any(part.startswith(".") for part in f.relative_to(src).parts))
    for f in files[:MAX_NOTES]:
        parts = [re.sub(r"[^\w.-]+", "-", part).strip("-.") or "note" for part in f.relative_to(src).parts]
        parts[-1] = parts[-1] if parts[-1].endswith(".md") else parts[-1] + ".md"
        target = f"{base}/{'/'.join(parts)}"
        if _write_new(store, target, f):
            done.append(target)
    return done


def _state(store: Store) -> dict:
    try:
        return json.loads((store.data / "imports.json").read_text())
    except (OSError, ValueError):
        return {"sources": {}}


def run(store: Store, sources: list[dict], say=print, explicit: bool = False, ask_agent: bool = True) -> int:
    """Import each source once, then leave the agent a thread to finish the move.

    ``explicit`` marks sources the user named: they are imported again on request, and a mapped vault
    may then replace the core notes of a memory that is already in use.
    """
    state, loose, total = _state(store), [], 0
    for src in sources:
        path, kind = Path(src["path"]), src["kind"]
        if not explicit and str(path) in state["sources"]:
            continue
        if kind == "vault":
            if not explicit and not is_fresh(store):
                say(f"    skipped {path}: this memory is already in use. To import it anyway: council import \"{path}\"")
                continue
            count = len(Importer(path, store).run()["notes"])
        else:
            notes = import_agent_files(store, path) if kind == "agents" else import_folder(store, path)
            count = len(notes)
            loose += notes
        state["sources"][str(path)] = {"kind": kind, "at": time.time(), "notes": count}
        total += count
        what = {"vault": "notes vault", "agents": "agent memory files", "folder": "folder"}[kind]
        say(f"    imported {count} notes from {path} ({what})")
    if ask_agent and not state.get("asked"):
        folders = sorted({"/".join(n.split("/")[:2]) for n in loose})
        copied = (f"{len(loose)} notes were copied into {', '.join(f'`{f}/`' for f in folders)}; they can be searched "
                  "but are not loaded at session start." if loose else "No loose notes were copied.")
        store.open_thread(
            "### Bring the user's existing memory over\n"
            f"- **Status:** COUNCIL was set up on {now_local():%Y-%m-%d}. {copied}\n"
            "- **Next:** (1) Check whether the agents on this computer use any other memory system: memory or "
            "notes folders, instruction files, memory MCP servers, hooks that add context. If one exists, read it "
            "and move what is still true into COUNCIL; never change or delete the source. (2) Sort what is under "
            "`imported/`: lasting facts and preferences into core.md, corrections into rules.md, project knowledge "
            "into projects/<name>/. (3) Tell the user what was moved, then close this thread.\n\n",
            "existing memory to bring over",
        )
        state["asked"] = True
    tmp = store.data / ".imports.json.tmp"
    tmp.write_text(json.dumps(state))
    tmp.replace(store.data / "imports.json")
    return total
