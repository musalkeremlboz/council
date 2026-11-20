"""One-way import from an Avenox Beyin V3 vault into a COUNCIL vault.

Only human/agent-written content is imported (companion files, project notes and
rules, knowledge notes, receipts). Generated indexes, templates and engine files
are skipped. The source vault is never modified.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path

from .store import CORE, RULES, SESSIONS, THREADS, Store

COMPANION = {
    "Core.md": CORE,
    "Soul.md": "soul.md",
    "Kurallar.md": RULES,
    "Threads.md": THREADS,
    "Last-Session.md": SESSIONS,
    "Journal.md": "journal.md",
}
SKIP_KNOWLEDGE = {"index.md"}


def _find(root: Path, suffix: str) -> Path | None:
    for d in sorted(root.iterdir()):
        if d.is_dir() and d.name.endswith(suffix):
            return d
    return None


class Importer:
    def __init__(self, src: str | Path, store: Store):
        self.src = Path(src).expanduser().resolve()
        self.store = store
        self.companion = _find(self.src, "Companion")
        self.projects = _find(self.src, "Projects") or (self.src / "projects")
        self.paths: dict[str, str] = {}  # old relative path -> new path
        self.plan: list[tuple[str, str]] = []  # (old rel, new rel)

    def _add(self, old: Path, new: str) -> None:
        rel = old.relative_to(self.src).as_posix()
        self.paths[rel] = new
        self.plan.append((rel, new))

    def scan(self) -> list[tuple[str, str]]:
        if self.companion:
            for name, target in COMPANION.items():
                f = self.companion / name
                if f.is_file():
                    self._add(f, target)
        if self.projects.is_dir():
            for pdir in sorted(p for p in self.projects.iterdir() if p.is_dir()):
                slug = re.sub(r"[^a-z0-9-]+", "-", pdir.name.lower()).strip("-") or "project"
                for f in sorted(pdir.rglob("*.md")):
                    sub = f.relative_to(pdir).as_posix()
                    if f.name == "Kurallar.md" and f.parent == pdir:
                        new = f"projects/{slug}/rules.md"
                    elif f.stem == pdir.name and f.parent == pdir:
                        new = f"projects/{slug}/project.md"
                    else:
                        new = f"projects/{slug}/{sub}"
                    self._add(f, new)
        kdir = self.src / "knowledge"
        if kdir.is_dir():
            for f in sorted(kdir.rglob("*.md")):
                rel = f.relative_to(kdir).as_posix()
                if rel.split("/")[0] in ("v3", "v2") or f.name in SKIP_KNOWLEDGE:
                    continue  # generated receipt indexes
                self._add(f, f"knowledge/{rel}")
        return self.plan

    def rewrite(self, text: str) -> str:
        for old, new in sorted(self.paths.items(), key=lambda kv: -len(kv[0])):
            text = text.replace(old, new)
        for old, new in self.paths.items():  # [[wikilink]] by file stem
            stem = Path(old).stem
            text = re.sub(rf"\[\[{re.escape(stem)}(\|[^\]]*)?\]\]", lambda m: f"[[{new}{m.group(1) or ''}]]", text)
        return text

    def _convert(self, new: str, text: str) -> str:
        text = self.rewrite(text)
        if new == THREADS:
            text = re.sub(r"^## Active Threads\s*$", "## Active", text, flags=re.M)
            text = re.sub(r"^## Closed Threads\s*$", "## Closed", text, flags=re.M)
        if new == SESSIONS:
            text = re.sub(r"^# Son oturum\s*$", "# Sessions", text, count=1, flags=re.M)
            # drop the engine's instruction paragraph; COUNCIL carries its own protocol
            text = re.sub(r"\n+Henüz bir çalışma sonucu kaydedilmedi\..*\Z", "\n", text, flags=re.S)
        return text

    def receipts(self) -> list[dict]:
        out = []
        rdir = self.src / "receipts"
        if not rdir.is_dir():
            return out
        for f in rdir.glob("*.md"):
            raw = f.read_text(encoding="utf-8")
            m = re.match(r"^---\n(.*?)\n---\n(.*)\Z", raw, re.S)
            if not m:
                continue
            try:
                meta = json.loads(m.group(1))
            except json.JSONDecodeError:
                continue
            out.append({
                "at": dt.datetime.fromisoformat(meta["created_at"]).astimezone(),
                "session": meta.get("session", ""),
                "agent": meta.get("harness", ""),
                "event": meta.get("event_id", ""),
                "refs": [self.paths.get(r, r) for r in meta.get("refs", [])],
                "summary": m.group(2).strip(),
            })
        return sorted(out, key=lambda r: r["at"])

    def run(self, dry_run: bool = False) -> dict:
        plan = self.scan()
        receipts = self.receipts()
        if dry_run:
            return {"notes": plan, "log_entries": len(receipts)}
        for old, new in plan:
            text = self._convert(new, (self.src / old).read_text(encoding="utf-8"))
            _, full = self.store.resolve(new)
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(text, encoding="utf-8")
        months: dict[str, list[str]] = {}
        for r in receipts:
            refs = [x for x in r["refs"] if (self.store.vault / x).is_file()]
            who = " · ".join(x for x in (r["agent"], r["session"][:8]) if x)
            entry = f"## {r['at']:%Y-%m-%d %H:%M} · {who}\n\n{self.rewrite(r['summary'])}\n"
            if refs:
                entry += "\nRefs: " + ", ".join(f"[[{x}]]" for x in refs) + "\n"
            months.setdefault(f"{r['at']:%Y-%m}", []).append(entry)
        for month, entries in months.items():
            _, full = self.store.resolve(f"log/{month}.md")
            full.parent.mkdir(parents=True, exist_ok=True)
            head = full.read_text(encoding="utf-8").rstrip("\n") if full.exists() else f"# Log {month}"
            new = [e for e in entries if e.splitlines()[0] + "\n\n" + e.splitlines()[2] not in head]  # idempotent re-import
            if new:
                full.write_text(head + "\n\n" + "\n".join(new), encoding="utf-8")
        self.store.index.sync(self.store.vault)
        self.store._commit(f"import from {self.src.name}")
        return {"notes": plan, "log_entries": len(receipts)}
