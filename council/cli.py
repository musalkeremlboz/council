"""Command line: `council install | status | update | uninstall | import | serve | token | context | search | ...`."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
from pathlib import Path

DEFAULT_DATA = os.environ.get("COUNCIL_DATA", "~/.council")
# Commands that work on a memory that is already there: run against a folder without one (a mistyped --data),
# they say so instead of starting an empty memory in it.
NEEDS_MEMORY = {"context", "search", "check", "reindex", "usage", "backup", "watch-release", "watch-size", "panel"}
# Commands that only read the notes: they seed nothing and commit nothing, so an edit made by hand stays
# an uncommitted edit.
READS_ONLY = {"context", "search", "check", "reindex", "usage"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="council", description="COUNCIL memory system")
    ap.add_argument("--data", default=DEFAULT_DATA, help="data directory (default: $COUNCIL_DATA or ~/.council)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    ins = sub.add_parser("install", aliases=["kur"], help="set COUNCIL up on this computer: service, Claude Code, import, updates")
    ins.add_argument("--port", type=int, default=None, help="port of the local service (default 8765)")
    ins.add_argument("--no-auto-update", action="store_true", help="do not install new releases automatically")
    ins.add_argument("--no-import", action="store_true", help="do not look for an existing memory to import")
    ins.add_argument("--from", dest="sources", action="append", default=[], metavar="FOLDER",
                     help="import this folder instead of what is found automatically (repeatable)")
    ins.add_argument("--force", action="store_true", help="replace a connection to another COUNCIL memory")

    for name, alias, text in (("uninstall", "kaldir", "remove the service, hooks and MCP tools; notes are kept"),
                              ("status", "durum", "is the service running, are hooks and updates on"),
                              ("update", "guncelle", "install the latest published release if it is newer")):
        x = sub.add_parser(name, aliases=[alias], help=text)
        x.add_argument("--port", type=int, default=None)
        if name == "update":
            x.add_argument("--force", action="store_true", help="reinstall the latest release even if it is not newer")

    im = sub.add_parser("import", help="import an existing memory: a folder of notes, one file, or everything found on this computer")
    im.add_argument("source", nargs="?", help="folder or Markdown file to import; without it, whatever is found automatically")

    s = sub.add_parser("serve", help="run the MCP + API server")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--public-host", action="append", default=[], help="extra allowed Host header, e.g. memory.example.com")

    pn = sub.add_parser("panel", help="run the password-protected web panel")
    pn.add_argument("--host", default="127.0.0.1")
    pn.add_argument("--port", type=int, default=8766)
    pn.add_argument("--base-path", default="/panel")
    pn.add_argument("--service-url", default="http://127.0.0.1:8765")

    t = sub.add_parser("token", help="create (or show) the access token")
    t.add_argument("--rotate", action="store_true")

    c = sub.add_parser("context", help="print the memory context")
    c.add_argument("query", nargs="?", default="")

    q = sub.add_parser("search", help="full-text search")
    q.add_argument("query")
    q.add_argument("--limit", type=int, default=8)

    k = sub.add_parser("check", help="do saved questions still find their notes, do links still lead to a note (changes no note)")
    k.add_argument("what", nargs="?", choices=["search", "links", "add", "remove"],
                   help='one report alone, or: add "question" NOTE [NOTE ...] / remove "question"')
    k.add_argument("args", nargs="*")

    sub.add_parser("reindex", help="rebuild the search index from the notes")

    i = sub.add_parser("import-avenox", help="import an Avenox Beyin V3 vault (source is not modified)")
    i.add_argument("source")
    i.add_argument("--dry-run", action="store_true")

    w = sub.add_parser("watch-release", help="note a new GitHub release of a repo in threads.md (run daily)")
    w.add_argument("repo", help="owner/name")

    z = sub.add_parser("watch-size", help="open a thread in threads.md once the vault has grown past a size (run daily)")
    z.add_argument("--notes", type=int, default=0, help="fire at this many notes")
    z.add_argument("--chunks", type=int, default=0, help="fire at this many indexed sections")
    z.add_argument("--title", required=True, help="title of the thread to open")
    z.add_argument("--body", default="", help="what to do, written into the thread")

    sub.add_parser("backup", help="push the vault history to its `backup` git remote (run on a timer)")

    u = sub.add_parser("usage", help="what the memory handed out lately")
    u.add_argument("--days", type=float, default=7)

    pw = sub.add_parser("set-password", help="set the owner password used to approve Claude app connections")
    pw.add_argument("--generate", action="store_true", help="generate a random password and print it once")

    dl = sub.add_parser("delegation", help="what each model spent on sub-agents and whether the ceiling held (read-only)")
    dl.add_argument("action", choices=["report"])
    dl.add_argument("--days", type=float, default=14, help="sessions whose record changed in this many days")
    dl.add_argument("--json", action="store_true", help="print the numbers as JSON")
    dl.add_argument("--projects", default=None, help="folder of session records (default ~/.claude/projects)")
    dl.add_argument("--log", default=None, help="hook decision log (default ~/.council/state/delegation.jsonl)")

    a = ap.parse_args(argv)
    data = Path(a.data).expanduser()
    if a.cmd in NEEDS_MEMORY and not (data / "vault").is_dir():
        print(f"council: no memory at {data} (no vault folder there); check --data or COUNCIL_DATA", file=sys.stderr)
        return 2
    data.mkdir(parents=True, exist_ok=True)

    if a.cmd == "token":
        f = data / "token"
        if a.rotate or not f.exists():
            f.write_text(secrets.token_urlsafe(32) + "\n")
            os.chmod(f, 0o600)
        print(f.read_text().strip())
        return 0

    if a.cmd == "set-password":
        import getpass

        from . import oauth

        if a.generate:
            words = secrets.token_urlsafe(18)
            password = "-".join(words[i:i + 6] for i in range(0, 18, 6))
        else:
            password = getpass.getpass("New owner password: ")
            if len(password) < oauth.MIN_PASSWORD or password != getpass.getpass("Repeat: "):
                print(f"passwords differ or shorter than {oauth.MIN_PASSWORD} characters", file=sys.stderr)
                return 1
        try:
            oauth.write_owner(data, password)
        except ValueError as e:
            print(f"council: {e}", file=sys.stderr)  # the words carry no character of the password
            return 1
        print(password if a.generate else "owner password set")
        return 0

    if a.cmd in ("install", "kur", "uninstall", "kaldir", "status", "durum", "update", "guncelle"):
        from . import local

        setup = local.Setup(data, port=a.port)
        if a.cmd in ("install", "kur"):
            return local.install(setup, auto_update=not a.no_auto_update, do_import=not a.no_import,
                                 sources=a.sources, force=a.force)
        if a.cmd in ("uninstall", "kaldir"):
            return local.uninstall(setup)
        if a.cmd in ("status", "durum"):
            return local.status(setup)
        return local.update(setup, force=a.force)

    if a.cmd == "delegation":
        from . import delegation

        projects = Path(a.projects).expanduser() if a.projects else delegation.DEFAULT_PROJECTS
        log = Path(a.log).expanduser() if a.log else delegation.DEFAULT_LOG
        summary = delegation.summarise(projects, log, a.days)
        print(json.dumps(summary, indent=2) if a.json else delegation.render(summary), end="\n" if a.json else "")
        return 0

    if a.cmd == "serve":
        import uvicorn

        from .server import build

        if sys.stderr is None:  # started without a console (Windows, at login): keep a log instead
            sys.stdout = sys.stderr = open(data / "service.log", "a", buffering=1, encoding="utf-8")
        (data / "service.pid").write_text(str(os.getpid()))
        try:  # an installation older than the sub-agent hook gets it; a hand-run or system-wide server edits nothing
            from . import local

            setup = local.Setup(data, port=a.port)
            if setup.service_installed():
                setup.ensure_tool_hooks()
        except Exception:
            pass

        app, _ = build(str(data), public_hosts=a.public_host)
        uvicorn.run(app, host=a.host, port=a.port, log_level="warning", proxy_headers=True, timeout_graceful_shutdown=3)
        return 0

    if a.cmd == "panel":
        import uvicorn

        from .panel.app import build as build_panel

        if not (data / "owner.json").exists():
            print("council panel: set the owner password first: council set-password", file=sys.stderr)
            return 2
        app = build_panel(data, base_path=a.base_path, service_url=a.service_url)
        try:
            uvicorn.run(app, host=a.host, port=a.port, log_level="warning", proxy_headers=True,
                        timeout_graceful_shutdown=3)
        finally:
            app.state.gate.close()
        return 0

    from .store import Store

    store = Store(data, readonly=a.cmd in READS_ONLY)
    if a.cmd == "context":
        from .context import bootstrap

        sys.stdout.write(bootstrap(store, a.query))
    elif a.cmd == "search":
        for h in store.index.search(a.query, limit=a.limit):
            print(f"{h['path']} › {h['heading']}  ({h['score']})")
        if absent := store.index.absent(a.query):
            print(f"no note contains: {', '.join(absent)}")
    elif a.cmd == "check":
        return run_check(store, a.what, a.args)
    elif a.cmd == "reindex":
        store.index.db.execute("DELETE FROM files")
        store.index.db.commit()
        print(f"indexed {store.index.sync(store.vault)} notes")
    elif a.cmd == "watch-release":
        return watch_release(store, a.repo)
    elif a.cmd == "watch-size":
        return watch_size(store, a.notes, a.chunks, a.title, a.body)
    elif a.cmd == "backup":
        res = store.backup()
        print("backup ok" if res["ok"] else f"backup failed: {res['error']}")
        return 0 if res["ok"] else 1
    elif a.cmd == "usage":
        from .usage import Usage

        s = Usage(store.data / "usage.sqlite3").summary(a.days)
        inj = s["inject"]
        print(f"last {a.days:g} days: " + (", ".join(f"{k} {v}" for k, v in sorted(s["events"].items())) or "no events"))
        print(f"messages {inj['messages']}, given notes {inj['with_notes']}, mean {inj['chars_mean']} chars when given")
        for path, n in sorted(s["notes"].items(), key=lambda kv: -sum(kv[1].values())):
            print(f"  {n['injected']:4d} injected {n['read']:4d} read {n['found']:4d} found  {path}")
        unused = [p for p in store.list() if p not in s["notes"]]
        print(f"never injected, read or found: {len(unused)} of {len(store.list())} notes" + "".join(f"\n  {p}" for p in unused))
        from .learn import Learning

        ls = Learning(store).summary(a.days)
        print(f"learning: {ls['reviews_asked']} reviews asked, {ls['skills_new']} skills learned, "
              f"{ls['skills_revised']} revised, {ls['rules']} rules, {ls['undone']} undone")
        rate = "no feedback yet" if ls["helped_rate"] is None else f"helped {ls['helped_rate']:.0%}"
        print(f"skills now: {ls['established']} established, {ls['retired']} retired, {rate}")
        print(f"skills: {s['skills']['pointers']} pointers sent, {s['skills']['opened']} opened")
        for r in ls["possible_repeats"]:
            print(f"possible repeat: {r['line']}  ~  {r['repeat_of']}")
    elif a.cmd == "import":
        from . import migrate

        if a.source:
            src = Path(a.source).expanduser().resolve()
            if not src.exists():
                print(f"not found: {src}", file=sys.stderr)
                return 1
            found, explicit = [{"kind": migrate.kind_of(src), "path": str(src)}], True
        else:
            found, explicit = migrate.detect(Path.home()), False
        total = migrate.run(store, found, explicit=explicit)
        print(f"{total} notes imported" if total else "nothing new to import")
    elif a.cmd == "import-avenox":
        from .importer import Importer

        res = Importer(a.source, store).run(dry_run=a.dry_run)
        for old, new in res["notes"]:
            print(f"{old}  ->  {new}")
        print(f"log entries: {res['log_entries']}{' (dry run)' if a.dry_run else ''}")
    return 0


def run_check(store, what: str | None, args: list[str]) -> int:
    """`council check`: 0 when nothing needs attention, 1 when a question missed its note, a note is gone,
    a link is broken or the question to remove was not there, 2 when the command cannot be carried out."""
    from . import check

    try:
        if what == "add":
            if len(args) < 2:
                raise check.CheckError('usage: council check add "question" NOTE [NOTE ...]')
            q = check.add_question(store, args[0], args[1:])
            print(f'saved: "{q["question"]}" should find {", ".join(q["expect"])}')
            return 0
        if what == "remove":
            if len(args) != 1:
                raise check.CheckError('usage: council check remove "question"')
            removed = check.remove_question(store, args[0])
            print("removed" if removed else "no such question")
            return 0 if removed else 1
        if args:
            raise check.CheckError(f"unexpected: {' '.join(args)}")
        attention = False
        if what in (None, "search"):
            r = check.search_report(store)
            sys.stdout.write(check.render_search(r))
            attention |= bool(r["missed"] or r["gone"])
        if what in (None, "links"):
            r = check.link_report(store)
            sys.stdout.write(check.render_links(r))
            attention |= bool(r["broken"])
        return 1 if attention else 0
    except check.CheckError as e:
        print(f"council check: {e}", file=sys.stderr)
        return 2


def watch_release(store, repo: str) -> int:
    """Record the first seen release as baseline; afterwards add a thread for each newer release."""
    import urllib.request

    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/releases/latest",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "council-watch"},
    )
    with urllib.request.urlopen(req, timeout=20) as r:
        rel = json.loads(r.read().decode())
    tag, url, published = rel["tag_name"], rel["html_url"], rel.get("published_at", "")[:10]
    state = store.data / "watch" / (repo.replace("/", "__") + ".json")
    state.parent.mkdir(exist_ok=True)
    seen = json.loads(state.read_text()).get("tag") if state.exists() else None
    if seen is None:
        state.write_text(json.dumps({"tag": tag}))
        print(f"baseline {repo} {tag}")
        return 0
    if seen == tag:
        print(f"no change ({tag})")
        return 0
    store.open_thread((
        f"### New release: {repo} {tag}\n"
        f"- **Status:** published {published}, not reviewed. Do not install it; review what it brings and "
        f"summarize it for the user. Installing is the user's decision.\n"
        f"- **Source:** {url} (previous seen: {seen})\n\n"
    ), f"new release {repo} {tag}")
    state.write_text(json.dumps({"tag": tag}))
    print(f"new release {repo} {tag}")
    return 0


def watch_size(store, notes: int, chunks: int, title: str, body: str) -> int:
    """Open a thread, once, when the vault holds at least ``notes`` notes or ``chunks`` indexed sections."""
    import hashlib

    from .store import now_local

    state = store.data / "watch" / f"size-{hashlib.sha1(title.encode()).hexdigest()[:12]}.json"
    if state.exists():
        print("already fired")
        return 0
    have_notes = len(store.list())
    have_chunks = store.index.db.execute("SELECT count(*) FROM chunks").fetchone()[0]
    if not ((notes and have_notes >= notes) or (chunks and have_chunks >= chunks)):
        print(f"not yet: {have_notes} notes, {have_chunks} sections")
        return 0
    limit = " or ".join(x for x in (f"{notes} notes" if notes else "", f"{chunks} sections" if chunks else "") if x)
    store.open_thread((
        f"### {title}\n"
        f"- **Status:** on {now_local():%Y-%m-%d} the vault reached {have_notes} notes / {have_chunks} sections "
        f"(threshold: {limit}). {body}\n\n"
    ), f"size threshold reached: {title}")
    state.parent.mkdir(exist_ok=True)
    state.write_text(json.dumps({"fired": now_local().isoformat(), "notes": have_notes, "sections": have_chunks}))
    print(f"threshold reached: {have_notes} notes, {have_chunks} sections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
