"""Full-text index over the vault (SQLite FTS5). Derived data: safe to delete and rebuild."""

from __future__ import annotations

import hashlib
import re
import sqlite3
import threading
from collections.abc import Callable
from pathlib import Path

_WORD = re.compile(r"[\w]+", re.UNICODE)
_FOLD = str.maketrans("ıİçÇğĞöÖşŞüÜâÂîÎûÛ", "iIcCgGoOsSuUaAiIuU")
_ITEM = re.compile(r"^(?:[-*+] |\d+[.)] )")
MAX_CHUNK = 700
ABSENT_WORDS = 40  # different words of one query that absent() looks up
CHUNKER = "2"  # bump when chunks() changes shape; indexes built by another version rebuild themselves

# Filler words (folded) that say nothing about the topic of a message.
STOP = frozenset("""ve veya ile bir bu su o da de mi mu ne nasil neden niye nicin kac hangi hangisi icin gibi ama fakat
cok daha en ben sen biz siz onlar bana beni benim var yok evet hayir tamam olur sonra simdi her hic ki ise
kadar gore neler nerede neydi nedir midir ya the a of to in is""".split())


def fold(text: str) -> str:
    """Lowercase and strip Turkish/Latin diacritics so 'şifresiz' matches 'sifresiz'."""
    return text.translate(_FOLD).lower()


def chunks(text: str) -> list[tuple[str, str]]:
    """Split a note into (heading path, body) sections at Markdown headings."""
    out: list[tuple[str, str]] = []
    stack: list[str] = []
    buf: list[str] = []

    def flush():
        body = "\n".join(buf).strip()
        if body:
            out.extend((" > ".join(stack), piece) for piece in _split(body))
        buf.clear()

    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        m = None if in_fence else re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            flush()
            level = len(m.group(1))
            stack[:] = stack[: level - 1] + [m.group(2).strip()]
            buf.append(line)
        else:
            buf.append(line)
    flush()
    return out or [("", text.strip())]


def _split(body: str, max_len: int = MAX_CHUNK) -> list[str]:
    """Cut an oversized section at its top-level list items; every piece repeats the heading line."""
    if len(body) <= max_len:
        return [body]
    lines = body.splitlines()
    head = lines[:1] if lines[0].startswith("#") else []
    items, cur, in_fence = [], [], False
    for line in lines[len(head):]:
        if not in_fence and _ITEM.match(line) and any(x.strip() for x in cur):
            items.append("\n".join(cur))
            cur = []
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        cur.append(line)
    items.append("\n".join(cur))
    room = max_len - sum(len(x) + 1 for x in head)
    pieces, group, size = [], [], 0
    for item in items:
        if group and size + len(item) + 1 > room:
            pieces.append("\n".join(head + group).strip())
            group, size = [], 0
        group.append(item)
        size += len(item) + 1
    pieces.append("\n".join(head + group).strip())
    return pieces


# What a request is worded with, not what it is about ("bunu yapabilir misin, istiyorum"). Rare in notes, so
# each one that does occur would outweigh the subject. Dropped wherever STOP is.
FILLER = frozenset("""bunu bunun buna bunlar bunlari sunu sunun onu onun ona sey seyi seyler istiyorum istiyoruz istiyor
isterim yapabilir yapabiliriz yapabilirim yapabilirsin edebilir edebiliriz olabilir lazim gerek gerekiyor gerekir misin
misiniz musun musunuz miyim miyiz peki ayrica yani zaten lutfen sana bize size seni bizi diye""".split())
NOTE_STEM = 6  # longest stem a note search matches on: "bağlanmasını" must find "bağlantısı"


def note_query(q: str, content_only: bool = False) -> str:
    """FTS5 query for searching notes: the words of ``q`` that say what it is about.

    Stop words and request words are left out. When nothing else is in ``q``, a search asked for uses
    every word it was given; ``content_only`` (deciding what to send unasked) then searches nothing.

    Long words match on a shorter stem than ``build_query`` uses. Both choices were measured on the owner's
    saved questions and on the older 44-question set. Skills keep ``build_query``.
    """
    words = [w for w in _WORD.findall(fold(q)) if len(w) >= 2]
    about = [w for w in words if w not in STOP and w not in FILLER]
    if not about and not content_only:
        about = words
    return " OR ".join(dict.fromkeys(f'"{_note_stem(w)}"*' for w in about))


def _note_stem(w: str) -> str:
    return _stem(w)[:NOTE_STEM]


def build_query(q: str, content_only: bool = False) -> str:
    """FTS5 query for ``q`` with the stems skill matching was measured with (``council.learn``); notes are
    searched with ``note_query``. ``content_only`` drops filler words."""
    terms = []
    for w in _WORD.findall(fold(q)):
        if len(w) < 2 or (content_only and w in STOP):
            continue
        terms.append(f'"{_stem(w)}"*')
    return " OR ".join(terms)


def _stem(w: str) -> str:
    """Agglutinative languages (Turkish) add suffixes; match on a stem prefix."""
    return w if len(w) < 6 else w[: max(5, len(w) - 3)]


class Index:
    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, sha TEXT NOT NULL);
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
                path UNINDEXED, heading, body, folded, tokenize='unicode61 remove_diacritics 2'
            );
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """
        )
        built = self.db.execute("SELECT value FROM meta WHERE key='chunker'").fetchone()
        if not built or built[0] != CHUNKER:
            with self.db:  # chunk shape changed: forget everything, the next sync() re-reads the notes
                self.db.execute("DELETE FROM files")
                self.db.execute("DELETE FROM chunks")
                self.db.execute("INSERT OR REPLACE INTO meta VALUES('chunker', ?)", (CHUNKER,))

    def update_file(self, rel: str, text: str) -> None:
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        with self._lock, self.db:
            self.db.execute("DELETE FROM chunks WHERE path=?", (rel,))
            for heading, body in chunks(text):
                self.db.execute(
                    "INSERT INTO chunks(path, heading, body, folded) VALUES(?,?,?,?)",
                    (rel, heading, body, fold(heading + "\n" + body)),
                )
            self.db.execute("INSERT OR REPLACE INTO files(path, sha) VALUES(?,?)", (rel, sha))

    def remove_file(self, rel: str) -> None:
        with self._lock, self.db:
            self.db.execute("DELETE FROM chunks WHERE path=?", (rel,))
            self.db.execute("DELETE FROM files WHERE path=?", (rel,))

    def sync(self, vault: Path) -> int:
        """Bring the index in line with the files on disk. Returns the number of changed files."""
        seen, changed = set(), 0
        known = dict(self.db.execute("SELECT path, sha FROM files"))
        for f in vault.rglob("*.md"):
            rel = f.relative_to(vault).as_posix()
            if rel.startswith(".") or "/." in rel:
                continue
            seen.add(rel)
            text = f.read_text(encoding="utf-8", errors="replace")
            if known.get(rel) != hashlib.sha256(text.encode("utf-8")).hexdigest():
                self.update_file(rel, text)
                changed += 1
        for rel in set(known) - seen:
            self.remove_file(rel)
            changed += 1
        return changed

    def search(self, q: str, limit: int = 8, exclude: set[str] | None = None,
               content_only: bool = False, where: Callable[[str], bool] | None = None) -> list[dict]:
        fts = note_query(q, content_only)
        if not fts:
            return []
        exclude = exclude or set()
        with self._lock:
            rows = self.db.execute(
                "SELECT path, heading, body, bm25(chunks, 0.0, 2.0, 0.0, 1.0) AS score "
                "FROM chunks WHERE chunks MATCH ? ORDER BY score LIMIT ?",
                (f"folded : ({fts})", 200 if where else limit * 4),  # a path filter drops rows, so look deeper
            ).fetchall()
        scored = []
        for path, heading, body, score in rows:
            if path in exclude or (where and not where(path)):
                continue
            # Work logs repeat what notes already say; rank curated notes first.
            weight = 0.5 if path.startswith("log/") else 1.0
            scored.append({"path": path, "heading": heading, "text": body, "score": round(-score * weight, 3)})
        scored.sort(key=lambda h: -h["score"])
        return scored[:limit]

    def absent(self, q: str, limit: int = 8) -> list[str]:
        """Content words of ``q`` that no note contains in any form, as first typed, at most ``limit``.

        Forms are matched the way search matches them. Only the first ABSENT_WORDS different words are
        looked up: a pasted page must not turn into hundreds of queries.
        """
        out: list[str] = []
        seen: set[str] = set()
        for word in _WORD.findall(q):
            w = fold(word)
            if len(w) < 2 or w in STOP or w in FILLER or _note_stem(w) in seen:
                continue
            if len(seen) == ABSENT_WORDS or len(out) == limit:
                break
            seen.add(_note_stem(w))
            with self._lock:
                row = self.db.execute("SELECT 1 FROM chunks WHERE chunks MATCH ? LIMIT 1",
                                      (f'folded : ("{_note_stem(w)}"*)',)).fetchone()
            if row is None:
                out.append(word)
        return out
