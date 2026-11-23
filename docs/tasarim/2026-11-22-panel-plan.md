# COUNCIL Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A password-protected web panel, served by a separate `council panel` process, that shows how the memory works and what state it is in, using only note paths, counts and times.

**Architecture:** A new subpackage `council/panel/` builds a Starlette app that reads the memory's data folder without writing to it (a "frozen" store, read-only SQLite) and keeps its own `panel.sqlite3` for sessions, failed sign-ins, health samples and check results. The browser side is plain HTML, CSS and JavaScript that polls one JSON address per section. Three small behaviour-neutral changes to existing memory modules come first (named constants, a truly read-only way to open the data, a side-effect-free start-context plan).

**Tech Stack:** Python 3.11+, Starlette and uvicorn (both already installed through the `mcp` and `uvicorn` dependencies), sqlite3, pytest with `starlette.testclient`. No new dependencies, no build step.

**Spec:** `docs/tasarim/2026-11-22-panel.md` (Turkish). Read it first; this plan covers its phases 1–3. Phase 4 (installing on the owner's server) and phase 5 (two new records in the memory service) are separate, approval-gated work and are not in this plan.

## Global Constraints

- The panel never returns or shows: a note's body, a section heading, the text of a user message, the text of a rule, a commit message, or the text of a check question. The only note information it may return is the note's path.
- The panel writes to exactly one file in the data folder: `panel.sqlite3`. Everything else is opened read-only.
- No new dependencies. No build step: static files are served as written.
- All 231 existing tests pass unchanged after every task. `python -m pytest -q` is the project's test command; run it before each commit.
- Tests must pass on Linux, macOS and Windows (CI runs all three): build paths with `pathlib`, never assume `/`, close SQLite connections before deleting files.
- All text a person reads in the panel is Turkish and lives in `council/panel/text_tr.py`. Code, identifiers, comments, commit messages and test names are English.
- Colours, exactly: ground `#F4F5F3`, ink `#111416`, accent ("kor") `#E8421F`, surface `#FFFFFF`, quiet fill `#E9EBE8`, secondary text `#4A5157`, hairline `#D5D8D4`, control border `#848B91`, map stage `#111416` with `#F4F5F3` dots. The accent marks only two things: the memory itself and the selected item.
- Shapes: full circles and flat cuts; card corners 12px; no shadows, no gradients. Progress is drawn with rings, not bars.
- Fonts are bundled in the package; the panel loads nothing from another host.
- The browser code never puts data into the page with `innerHTML`; it uses `textContent` and created elements.
- Numbers shown as rules in the panel come from the named constants of Task 1, never from literals.
- Commit after each task, on the branch `panel`. Do not push, do not merge.

## Review Focus

1. **A data file is missing, empty or busy** (fresh install with no `usage.sqlite3`, no git history, an index the service is writing): every section answers with empty lists and "no record", never with a 500. Tests in Tasks 6, 8, 9, 12.
2. **A note path contains characters that matter to HTML or JSON** (`<`, `&`, quotes, emoji, spaces, non-ASCII): it reaches the page as text, exactly. Tests in Tasks 6 and 10.
3. **The session ends while the page is open:** the JSON address answers 401 and the page goes to the sign-in page instead of showing stale data as live. Tests in Tasks 5 and 10.
4. **Day boundaries and the server's time zone:** "today" and the 30-day strip follow the memory's local time (`store.now_local()`), not UTC. Tests in Tasks 8 and 12.
5. **The panel is served under a path prefix behind a proxy:** redirects, cookie path and static addresses work for `--base-path /panel` and for `--base-path /`, with and without a trailing slash, and the cookie is `Secure` when the request arrived over HTTPS (`X-Forwarded-Proto: https`). Tests in Task 5.

---

## File Structure

| File | Responsibility |
|---|---|
| `council/context.py` (modify) | Named budget constants; `start_plan()` |
| `council/index.py`, `council/store.py`, `council/usage.py` (modify) | Read-only ways to open the index, the store and the usage log |
| `council/check.py` (modify) | `note_links()` |
| `council/panel/__init__.py` | Empty |
| `council/panel/gate.py` | Sign-in, sessions, lockout; owns the `sessions` and `failures` tables |
| `council/panel/reader.py` | Read-only access to the memory's data; returns paths, counts and times only |
| `council/panel/mechanism.py` | The blocks of the schema and their rules, filled from constants |
| `council/panel/text_tr.py` | Every Turkish string |
| `council/panel/views.py` | One function per section that builds its JSON |
| `council/panel/sampler.py` | Health samples and check runs; owns the `samples` and `runs` tables |
| `council/panel/app.py` | The Starlette app: routes, headers, cookie |
| `council/panel/releases.json` | Versions, ring, what is next |
| `council/panel/static/` | `index.html`, `login.html`, `panel.css`, `panel.js`, one `.js` per section, fonts |
| `council/cli.py` (modify) | The `panel` command |
| `deploy/council-panel.service`, `deploy/Caddyfile` (modify), `docs/kurulum.md`, `docs/setup.md` (modify) | Running it on a server |
| `tests/conftest.py`, `tests/test_panel_*.py` | Tests |

---

### Task 1: Named budget constants

**Files:**
- Modify: `council/context.py`, `council/server.py`
- Test: `tests/test_panel_constants.py`

**Interfaces:**
- Produces, in `council/context.py`: `START_BUDGET = 9000`, `START_CARDS = 2`, `START_RELEVANT_LIMIT = 6`, `START_RELEVANT_CLIP = 900`, `MESSAGE_BUDGET = 3500`, `MESSAGE_LIMIT = 5`, `SECTION_CLIP = 800`, `MIN_ROOM = 200`. Already named elsewhere and used as they are: `learn.INDEX_BUDGET`, `learn.SKILL_LIMIT`, `learn.MIN_HEAD_WORDS`, `learn.PROMOTE_AFTER`, `learn.RETIRE_WRONG`, `learn.RETIRE_NOT_HELPED`, `hook.REVIEW_EVERY`, `oauth.MAX_FAILURES`, `oauth.FAILURE_WINDOW`, `store.BACKUP_GRACE`.

- [ ] **Step 1: Write the failing test**

```python
import inspect
from council import context

def test_budgets_are_named_and_are_the_defaults():
    assert (context.START_BUDGET, context.START_CARDS, context.MESSAGE_BUDGET, context.MESSAGE_LIMIT) == (9000, 2, 3500, 5)
    assert (context.SECTION_CLIP, context.MIN_ROOM, context.START_RELEVANT_LIMIT, context.START_RELEVANT_CLIP) == (800, 200, 6, 900)
    rel = inspect.signature(context.relevant).parameters
    assert rel["budget"].default == context.MESSAGE_BUDGET and rel["limit"].default == context.MESSAGE_LIMIT
    boot = inspect.signature(context.bootstrap).parameters
    assert boot["budget"].default == context.START_BUDGET and boot["cards"].default == context.START_CARDS
```

- [ ] **Step 2: Run it:** `python -m pytest tests/test_panel_constants.py -q` — expected FAIL (`AttributeError: START_BUDGET`).
- [ ] **Step 3: Add the constants** at the top of `council/context.py` and replace each literal in `relevant()` and `bootstrap()` with its constant (`3500`, `5`, `800`, `200` in `relevant`; `9000`, `2`, `6`, `900`, `200` in `bootstrap`). In `council/server.py` replace the `9000` default in `api_context` with `START_BUDGET`. Change nothing else.
- [ ] **Step 4: Run** `python -m pytest -q` — expected: 232 passed, 1 xfailed.
- [ ] **Step 5: Commit** `git commit -am "Budgets and limits of the context are named constants"`

### Task 2: Opening the data without writing to it

**Files:**
- Modify: `council/index.py`, `council/store.py`, `council/usage.py`
- Test: `tests/test_panel_frozen.py`

**Interfaces:**
- Produces: `Index(path, readonly: bool = False)`; `Store(data_dir, readonly: bool = False, frozen: bool = False)`; `Usage(path, readonly: bool = False)`.
  - `Index(readonly=True)` opens with `sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True, check_same_thread=False)`, creates nothing, resets nothing. A missing file raises `FileNotFoundError`.
  - `Store(frozen=True)` creates no folder, runs no git command, seeds nothing, opens the index read-only and does not sync it. A data folder with no `vault` folder raises `StoreError("no memory at <path>")`; a missing index raises `StoreError("no search index at <path>")`. Its write methods are not guarded: the panel never calls them.
  - `Usage(readonly=True)` opens the same way, creates no table, deletes no rows; `record()` does nothing. A missing file raises `FileNotFoundError`.

- [ ] **Step 1: Write the failing tests**

```python
import hashlib
import pytest
from council import check
from council.store import Store, StoreError
from council.usage import Usage

def snapshot(data):
    return {p.relative_to(data).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(data.rglob("*")) if p.is_file() and ".git/" not in p.as_posix()}

@pytest.fixture
def memory(tmp_path):
    data = tmp_path / "data"
    s = Store(data)
    s.write("projects/ev/kira.md", "# Kira\n\nKira her ayın yirmi beşinde ödenir.")
    u = Usage(data / "usage.sqlite3"); u.record("inject", "s1", "kira ne zaman", 120, 3.2, [{"path": "projects/ev/kira.md", "heading": "Kira", "score": 3.2}]); u.db.close()
    check.add_question(s, "kira ne zaman ödenir", ["projects/ev/kira.md"])
    s.index.db.close()
    (data / "vault" / "elle.md").write_text("# Elle\n\nelle yazıldı", encoding="utf-8")   # not in the index, not committed
    return data

def test_a_frozen_store_reads_everything_and_changes_no_file(memory):
    before = snapshot(memory)
    s = Store(memory, frozen=True)
    assert "projects/ev/kira.md" in s.list() and s.read("projects/ev/kira.md").text.startswith("# Kira")
    assert s.index.search("kira")[0]["path"] == "projects/ev/kira.md"
    assert check.search_report(s)["questions"] == 1
    u = Usage(memory / "usage.sqlite3", readonly=True)
    assert u.summary()["notes"]["projects/ev/kira.md"]["injected"] == 1
    u.record("inject", "s2", "x", 1)
    s.index.db.close(); u.db.close()
    assert snapshot(memory) == before

def test_a_frozen_store_does_not_start_a_memory(tmp_path):
    with pytest.raises(StoreError, match="no memory at"):
        Store(tmp_path / "yok", frozen=True)
    assert not (tmp_path / "yok").exists()
    (tmp_path / "bos" / "vault").mkdir(parents=True)
    with pytest.raises(StoreError, match="no search index at"):
        Store(tmp_path / "bos", frozen=True)
    assert [p.name for p in (tmp_path / "bos").iterdir()] == ["vault"]
```

- [ ] **Step 2: Run:** `python -m pytest tests/test_panel_frozen.py -q` — expected FAIL (`TypeError: unexpected keyword argument 'frozen'`).
- [ ] **Step 3: Implement** the three `readonly` / `frozen` paths as described under Interfaces. `Store.resolve`, `read`, `list` and `exists` work unchanged on a frozen store.
- [ ] **Step 4: Run** `python -m pytest -q` — expected: 234 passed, 1 xfailed.
- [ ] **Step 5: Commit** `git commit -am "The index, the store and the usage log can be opened without writing to them"`

### Task 3: The start context as a plan, without side effects

**Files:**
- Modify: `council/context.py`
- Test: `tests/test_panel_start_plan.py`

**Interfaces:**
- Produces: `context.start_plan(store, budget: int = START_BUDGET, cards: int = START_CARDS, announce: bool = True) -> dict` returning `{"notices": list[str], "used": int, "sections": [{"title": str, "path": str, "sep": str, "units": list[str], "shown": int}]}`. `sections` holds the four fixed sections in order (Core, Rules, Active threads, Latest sessions), including empty ones (`units == []`). `shown` is how many leading units fit. `used` is the character count after the header and notices, before the first section, exactly as `bootstrap` counts it today. With `announce=False` the update notice is not asked for (`local.update_notice` is not called), so nothing is written.
- `bootstrap()` is rewritten on top of `start_plan(announce=True)` and returns exactly the same text as before.

- [ ] **Step 1: Write the failing tests**

```python
import json
from council import context
from council.store import Store

def filled(tmp_path):
    s = Store(tmp_path / "data")
    s.write("core.md", "# Core\n\n" + "k" * 300, expected_sha=s.read("core.md").sha)
    for i in range(3):
        s.upsert_session(f"sess{i}", f"kart {i}", "x" * 400)
    return s

def test_the_plan_says_what_bootstrap_shows(tmp_path):
    s = filled(tmp_path)
    plan = context.start_plan(s, budget=1100, announce=False)
    assert [x["path"] for x in plan["sections"]] == ["core.md", "rules.md", "threads.md", "sessions.md"]
    cards = plan["sections"][3]
    assert len(cards["units"]) == 2 and cards["shown"] < 2                  # START_CARDS cards, and they do not all fit
    text = context.bootstrap(s, budget=1100)
    for sec in plan["sections"]:
        for unit in sec["units"][: sec["shown"]]:
            assert unit in text
    assert "more cards not shown" in text

def test_a_plan_that_does_not_announce_leaves_the_update_notice_for_the_agent(tmp_path):
    s = filled(tmp_path)
    state = s.data / "update.json"
    state.write_text(json.dumps({"installed": {"from": "0.2.0", "to": "0.2.1"}}))
    before = state.read_text()
    assert not any("updated itself" in n for n in context.start_plan(s, announce=False)["notices"])
    assert state.read_text() == before
    assert "updated itself from 0.2.0 to 0.2.1" in context.bootstrap(s)
```

Before writing the second test, read `council/local.py` (`_update_state`, `_save_update_state`, `update_notice`) and use the file name and shape those functions use; adjust the two literals above if they differ.

- [ ] **Step 2: Run:** `python -m pytest tests/test_panel_start_plan.py -q` — expected FAIL (`AttributeError: start_plan`).
- [ ] **Step 3: Implement `start_plan`** by moving the first half of `bootstrap` into it (reading the four notes, the size notice, the backup notice, the update notice when `announce`, and the `_take` loop that decides `shown`). `bootstrap` calls it and renders the sections, the "not shown" lines and the relevant notes as today.
- [ ] **Step 4: Run** `python -m pytest -q` — expected: 236 passed, 1 xfailed. The existing bootstrap tests are the proof that the text did not change.
- [ ] **Step 5: Commit** `git commit -am "The start context is planned by a function that changes nothing"`

### Task 4: Sign-in, sessions and lockout

**Files:**
- Create: `council/panel/__init__.py`, `council/panel/gate.py`
- Modify: `pyproject.toml` (`packages = ["council", "council.panel"]`; package data `"council.panel" = ["static/*", "releases.json"]`)
- Test: `tests/test_panel_gate.py`

**Interfaces:**
- Produces:

```python
SESSION_TTL = 12 * 3600
class Gate:
    def __init__(self, data_dir: Path): ...            # opens <data>/panel.sqlite3, creates tables sessions(hash TEXT PRIMARY KEY, expires REAL) and failures(ts REAL)
    def configured(self) -> bool: ...                  # <data>/owner.json exists
    def locked(self, now: float | None = None) -> bool: ...
    def sign_in(self, password: str, now: float | None = None) -> str | None: ...   # a new token, or None
    def valid(self, token: str, now: float | None = None) -> bool: ...
    def sign_out(self, token: str) -> None: ...
    def close(self) -> None: ...
```

- Uses `council.oauth.check_password`, `MAX_FAILURES` (5) and `FAILURE_WINDOW` (900). Only the SHA-256 of a token is stored. `sign_in` returns `None` and counts nothing when no owner password is set; returns `None` without checking the password while locked; a wrong password adds a failure. Expired sessions and failures older than the window are deleted on each call.

- [ ] **Step 1: Write the failing tests**

```python
import json
from council.oauth import hash_password
from council.panel.gate import Gate, SESSION_TTL

def gate(tmp_path, password="dogru-sifre-123"):
    data = tmp_path / "data"; data.mkdir(exist_ok=True)
    if password:
        (data / "owner.json").write_text(json.dumps(hash_password(password)))
    return Gate(data)

def test_the_right_password_opens_a_session_that_ends_after_twelve_hours(tmp_path):
    g = gate(tmp_path)
    token = g.sign_in("dogru-sifre-123", now=1000.0)
    assert token and g.valid(token, now=1000.0 + SESSION_TTL - 1) and not g.valid(token, now=1000.0 + SESSION_TTL + 1)
    assert not g.valid("uydurma", now=1000.0) and not g.valid("", now=1000.0)

def test_five_wrong_passwords_lock_the_door_for_fifteen_minutes_even_for_the_right_one(tmp_path):
    g = gate(tmp_path)
    for i in range(5):
        assert g.sign_in("yanlis", now=1000.0 + i) is None
    assert g.locked(now=1010.0) and g.sign_in("dogru-sifre-123", now=1010.0) is None
    g.close()
    again = Gate(tmp_path / "data")                                        # the lock survives a restart
    assert again.locked(now=1010.0) and not again.locked(now=1000.0 + 4 + 901)
    assert again.sign_in("dogru-sifre-123", now=1000.0 + 4 + 901)

def test_signing_out_ends_the_session_and_no_password_set_opens_nothing(tmp_path):
    g = gate(tmp_path)
    token = g.sign_in("dogru-sifre-123", now=5.0); g.sign_out(token)
    assert not g.valid(token, now=6.0)
    bare = gate(tmp_path / "x", password=None)
    assert not bare.configured() and bare.sign_in("herhangi", now=1.0) is None and not bare.locked(now=2.0)
```

- [ ] **Step 2: Run:** `python -m pytest tests/test_panel_gate.py -q` — expected FAIL (`ModuleNotFoundError: council.panel`).
- [ ] **Step 3: Implement `Gate`.** Tokens come from `secrets.token_urlsafe(32)`; compare hashes, never tokens.
- [ ] **Step 4: Run** `python -m pytest -q` — expected: 239 passed, 1 xfailed.
- [ ] **Step 5: Commit** `git add -A && git commit -m "Panel: sign-in with the owner password, sessions, lockout"`

### Task 5: The app, the command and the door test

**Files:**
- Create: `council/panel/app.py`, `council/panel/text_tr.py`, `council/panel/static/login.html`, `council/panel/static/index.html`, `council/panel/static/panel.css`, `tests/conftest.py`
- Modify: `council/cli.py`
- Test: `tests/test_panel_door.py`

**Interfaces:**
- Consumes: `Gate` (Task 4).
- Produces: `council.panel.app.build(data_dir, base_path: str = "/panel", service_url: str = "http://127.0.0.1:8765", background: bool = True) -> Starlette`, and `SECTIONS = ("schema", "today", "health", "map", "notes", "releases")`. `app.state.gate` is the `Gate`. `background=False` starts no background work (tests pass it).
- Produces in `tests/conftest.py` (new file): fixtures `panel_data(tmp_path) -> Path` (a memory made with `Store`, `owner.json` for the password `"dogru-sifre-123"`, the store's index closed), `panel(panel_data)` (`TestClient(build(panel_data, background=False), base_url="http://127.0.0.1:8766", follow_redirects=False)`), `panel_signed_in(panel)` (the same client after a successful sign-in) and `static_dir() -> Path` (the package's `static` folder).
- Addresses, all under `base_path` (normalised: leading slash, no trailing slash; `/` means the root):

| Address | Signed in | Signed out |
|---|---|---|
| `GET /` | `index.html` | 303 to `/login` |
| `GET /login` | 303 to `/` | `login.html` |
| `POST /login` (form field `password`) | — | right: 303 to `/` with the cookie; wrong: `login.html` with 401; locked: 429; no owner password: 503 with the sentence telling how to set one |
| `POST /logout` | clears the session and the cookie, 303 to `/login` | 303 to `/login` |
| `GET /api/<section>` | JSON (until its task lands: `{"section": "<name>"}`) | 401 `{"error": "signed_out"}` |
| `GET /static/<file>` | file | file (static files hold no data) |

- Cookie: name `council_panel`, `HttpOnly`, `SameSite=Strict`, `Path=<base_path or "/">`, `Max-Age=SESSION_TTL`, and `Secure` when the request's scheme is `https` or its `X-Forwarded-Proto` header is `https`.
- Every response carries: `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'`, `X-Robots-Tag: noindex, nofollow`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`; HTML and JSON also `Cache-Control: no-store`.
- `POST` requests with an `Origin` header whose host differs from the request's `Host` are refused with 403.
- The HTML files take their texts and the base path through `{{name}}` placeholders filled from `text_tr.py`; `login.html` shows the emblem, the word COUNCIL, a password field with a label, a sign-in button and the lockout rule. `index.html` is, for now, the header with the six navigation links and an empty `<main id="bolum">`.
- CLI: `council panel [--host 127.0.0.1] [--port 8766] [--base-path /panel] [--service-url http://127.0.0.1:8765]`. Add `"panel"` to `NEEDS_MEMORY`. When no owner password is set it prints `council panel: set the owner password first: council set-password` to stderr and returns 2.

- [ ] **Step 1: Write the fixtures** in `tests/conftest.py` **and the failing tests** in `tests/test_panel_door.py`:

```python
PAGES = ["/panel/"] ; API = [f"/panel/api/{s}" for s in ("schema", "today", "health", "map", "notes", "releases")]

def test_nothing_is_served_without_a_session(panel):
    for url in PAGES:
        r = panel.get(url); assert r.status_code == 303 and r.headers["location"].endswith("/panel/login")
    for url in API:
        r = panel.get(url); assert r.status_code == 401 and r.json() == {"error": "signed_out"}

def test_the_right_password_opens_every_page_and_signing_out_closes_them(panel):
    r = panel.post("/panel/login", data={"password": "dogru-sifre-123"})
    assert r.status_code == 303 and "council_panel=" in r.headers["set-cookie"]
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/panel" in cookie and "secure" not in cookie
    assert all(panel.get(u).status_code == 200 for u in PAGES + API)
    panel.post("/panel/logout")
    assert panel.get("/panel/api/schema").status_code == 401

def test_five_wrong_passwords_then_the_right_one_is_refused(panel):
    for _ in range(5):
        assert panel.post("/panel/login", data={"password": "yanlis"}).status_code == 401
    assert panel.post("/panel/login", data={"password": "dogru-sifre-123"}).status_code == 429

def test_behind_https_the_cookie_is_secure_and_every_answer_is_closed_to_other_sites(panel):
    r = panel.post("/panel/login", data={"password": "dogru-sifre-123"}, headers={"X-Forwarded-Proto": "https"})
    assert "secure" in r.headers["set-cookie"].lower()
    h = panel.get("/panel/login").headers
    assert "default-src 'self'" in h["content-security-policy"] and "noindex" in h["x-robots-tag"]
    assert panel.post("/panel/login", data={"password": "x"}, headers={"Origin": "https://baska.example"}).status_code == 403

@pytest.mark.parametrize("base", ["/", "/panel", "/panel/", "ic/panel"])
def test_the_base_path_can_be_anything(tmp_path, base): ...
    # build(..., base_path=base): sign in at <normalised base>/login, the redirect goes to <normalised base>/, the cookie path matches

def test_without_an_owner_password_the_command_says_how_to_set_one(tmp_path, capsys): ...
    # cli.main(["--data", data, "panel"]) == 2 and "council set-password" in capsys.readouterr().err
```

- [ ] **Step 2: Run:** `python -m pytest tests/test_panel_door.py -q` — expected FAIL (`ModuleNotFoundError: council.panel.app`).
- [ ] **Step 3: Implement `build`, the two HTML files, `panel.css`, `text_tr.py` and the CLI command.** One middleware adds the headers; one helper reads the cookie and asks `Gate.valid`. `panel.css` defines the colours of Global Constraints as custom properties and the three `@font-face` rules (font files arrive in Task 10; until then the stack falls back to `system-ui`).
- [ ] **Step 4: Run** `python -m pytest -q` — all pass.
- [ ] **Step 5: Commit** `git add -A && git commit -m "Panel: the app, the command, and nothing without a session"`

### Task 6: Reading the memory without its text

**Files:**
- Create: `council/panel/reader.py`
- Modify: `council/check.py`, `tests/conftest.py`
- Test: `tests/test_panel_reader.py`

**Interfaces:**
- Produces in `council/check.py`: `note_links(store) -> dict[str, list[str]]`: for every note (history notes included), the paths of the notes its wiki links and Markdown links lead to, each once, itself excluded, unresolved links left out. Build it on the existing private helpers by adding `_resolve(note, target, wiki, notes, by_stem) -> str | None` and letting `_resolves` call it; `link_report` keeps its results.
- Produces in `council/panel/reader.py` (every function returns empty results when its file is missing, unreadable or busy, and never raises to the caller):

```python
def open_memory(data_dir) -> Store                      # Store(data_dir, frozen=True)
def note_list(store) -> list[dict]                      # {"path", "sections": int, "chars": int, "skill": bool}, sorted by path
def note_links(store) -> dict[str, list[str]]           # check.note_links
def events(data_dir, since: float, limit: int = 500) -> list[dict]   # newest first: {"ts": float, "kind": str, "chars": int, "paths": [str]}
def note_usage(data_dir) -> dict[str, dict[str, int]]   # path -> {"injected", "read", "found"}
def usage_since(data_dir) -> float | None               # time of the oldest usage event
def changes(store, since: float) -> list[dict]          # newest first: {"ts": float, "paths": [str], "added": [str]}
def learnings(data_dir, since: float) -> list[dict]     # newest first: {"ts": float, "kind": "rule" | "skill", "path": str, "undone": bool}
def backup_state(data_dir) -> dict | None               # {"last_ok": float | None, "failing": bool}
```

  - `sections` counts lines starting with `#`, `##` or `###`. `skill` is `learn.is_skill(path)`.
  - `events` reads `usage.sqlite3` read-only, takes `path` from each hit and drops `heading`, `query` and `session`; paths appear once per event, in order.
  - `changes` runs `git -C <vault> log --since=<iso> --format=@%at --name-status -- "*.md"` and reads only the time lines and the status and path columns. Commit subjects are never requested. `added` holds the paths with status `A`.
  - `learnings` reads the `ledger` list of `learning.json`: kinds `skill_new` and `skill_edit` become `"skill"`, `rule` stays; `ts` is parsed from the ISO string; `line` and every other field are dropped.
- Produces in `tests/conftest.py`: `SECRETS = ("GOVDE-SIRRI", "BASLIK-SIRRI", "MESAJ-SIRRI", "KURAL-SIRRI", "ACIKLAMA-SIRRI", "SORU-SIRRI")` and the fixture `leaky(tmp_path) -> Path`: a memory whose note bodies carry the first, a section heading the second, a usage event's query the third, a rule saved with `Learning.add_rule` the fourth, a write's `reason` the fifth and a check question the sixth; with at least one inject, one read and one search event, one skill, two linked notes, and one note whose folder name is `not <b>&"adı` (review focus 2). It closes every connection it opened. Also `leaky_panel(leaky)`: a signed-in `TestClient` over `build(leaky, background=False)` (the fixture writes `owner.json` too).

- [ ] **Step 1: Write the failing tests** in `tests/test_panel_reader.py`:

```python
import json
from council.panel import reader
from tests.conftest import SECRETS

def everything(data):
    s = reader.open_memory(data)
    out = {"notes": reader.note_list(s), "links": reader.note_links(s), "events": reader.events(data, 0),
           "usage": reader.note_usage(data), "changes": reader.changes(s, 0), "learn": reader.learnings(data, 0),
           "backup": reader.backup_state(data)}
    s.index.db.close()
    return out

def test_the_reader_gives_paths_and_counts_and_none_of_the_text(leaky):
    out = everything(leaky)
    text = json.dumps(out, ensure_ascii=False)
    assert not [s for s in SECRETS if s in text]
    assert any(n["path"].startswith('projects/not <b>&"adı/') for n in out["notes"])     # an odd name arrives as it is
    assert {e["kind"] for e in out["events"]} >= {"inject", "read", "search"} and all(set(e) == {"ts", "kind", "chars", "paths"} for e in out["events"])
    assert out["links"] and out["changes"] and out["changes"][0]["paths"]
    assert {l["kind"] for l in out["learn"]} == {"rule", "skill"}

def test_a_memory_with_nothing_recorded_yet_reads_as_empty(tmp_path): ...
    # a Store with only its seed notes, no usage.sqlite3, no learning.json, no backup.json, vault/.git removed:
    # events == [], note_usage == {}, usage_since is None, changes == [], learnings == [], backup_state is None

def test_note_links_names_where_each_link_leads_and_link_report_is_unchanged(leaky): ...
    # check.note_links(store)["<linking note>"] == ["<linked note>"]; check.link_report(store) equals its value before this task for the fixture
```

- [ ] **Step 2: Run:** `python -m pytest tests/test_panel_reader.py -q` — expected FAIL (`ModuleNotFoundError: council.panel.reader`).
- [ ] **Step 3: Implement** `check.note_links`, `reader.py` and the fixture.
- [ ] **Step 4: Run** `python -m pytest -q` — all pass.
- [ ] **Step 5: Commit** `git add -A && git commit -m "Panel: reading paths, counts and times from the memory, never its text"`

### Task 7: The blocks of the schema

**Files:**
- Create: `council/panel/mechanism.py`
- Modify: `council/panel/text_tr.py`
- Test: `tests/test_panel_mechanism.py`

**Interfaces:**
- Produces: `mechanism.LANES = ("start", "message", "end", "memory")` and `mechanism.blocks() -> list[dict]`, each `{"id", "lane", "name", "sub", "what", "rules": [str]}`, in this order and with these ids: lane `start`: `h1`, `bas`, `diz`; lane `message`: `h2`, `ara`, `sec`, `isa`; lane `end`: `h3`, `yaz`, `ogr`; lane `memory`: `haf`, `yed`, `den`.
- Texts live in `text_tr.BLOCKS` with `{name}` placeholders; `blocks()` fills them with numbers formatted the Turkish way (thousands separated by a dot: `9.000`). The copy:

| id | name · sub | what | rules (placeholders in braces) |
|---|---|---|---|
| h1 | Hook · oturum açıldı | Yardımcı yeni bir oturum açtığında kendiliğinden çalışan küçük betik. Sunucudan başlangıç bağlamını ister ve oturumun önüne koyar. | Sunucuya 8 saniyede ulaşamazsa oturum hafızasız başlar ve yardımcı bunu sana bir kez söyler. · Oturum sıkıştırıldığında da çalışır. · Hook kullanamayan yardımcılar aynı bağlamı bir araç çağrısıyla alır. |
| bas | Başlangıç bağlamı · en çok {START_BUDGET} karakter | Her oturumun başında yüklenen sabit bilgi: kim olduğun, düzeltmelerin, açık konular ve son {START_CARDS} oturumun kartı. | Toplam bütçe {START_BUDGET} karakter. · Sıra: çekirdek, kurallar, açık konular, oturum kartları. · Sığmayan sessizce atılmaz, adıyla bildirilir. |
| diz | İş tarifi dizini · en çok {INDEX_BUDGET} karakter | Kayıtlı iş tariflerinin listesi: tarif başına bir satır, yalnız notun yolu. İstenen iş bir tarifin işiyse yardımcı o notu açar. | En çok {INDEX_BUDGET} karakter; başlangıç bağlamının bütçesinden ayrıdır. · Önce kalıcı tarifler, sonra adaylar. · Tarifin metni kendiliğinden bağlama girmez. |
| h2 | Hook · mesaj geldi | Her mesajında çalışır. Mesajı sunucuya gönderir, dönen ilgili notları mesajına ekler. | Otomatik sistem bildirimleri için arama yapılmaz. · Her mesaja oturum kimliği ve o anki saat eklenir. |
| ara | Arama · kelime kökleriyle | Mesajın kelimeleri köklerine indirilir ve bütün notların bölümlerinde aranır. | Türkçe harfler sadeleştirilir: "şifre" ile "sifre" aynı sonucu verir. · Dolgu ve istek sözcükleri aramaya girmez. · Kelime tabanlıdır: aynı şeyi başka sözcüklerle sorarsan kaçırabilir. |
| sec | Seçim · en çok {MESSAGE_LIMIT} bölüm | Aramanın bulduğu adaylardan mesaja eklenecek olanlar seçilir. | En çok {MESSAGE_LIMIT} bölüm. · Toplam en çok {MESSAGE_BUDGET} karakter. · Bir bölümden en çok {SECTION_CLIP} karakter alınır. · Kalan yer {MIN_ROOM} karakterin altına inince durur. · Aynı bölüm bir oturumda yalnız bir kez gönderilir. |
| isa | İşaret · en çok {SKILL_LIMIT} tarif | Mesajın bir iş tarifiyle kelime olarak eşleşirse o tarifin yolu tek satırlık bir işaret olarak eklenir. Açıp açmamaya yardımcı karar verir. | Mesaj başına en çok {SKILL_LIMIT} işaret. · Mesajın en az {MIN_HEAD_WORDS} kelimesi tarifin başlığında ya da "ne zaman" satırında geçmelidir. · Aynı tarif bir oturumda bir kez işaret edilir. |
| h3 | Hook · cevap bitti | Yardımcı cevabını bitirirken çalışır. Kaydedilmemiş iş varsa bir kez hatırlatır; uzun bir iş bittiyse öğrenme sorusunu sorar. | Oturum not ya da dosya değiştirdi ama günlüğe işlemediyse hatırlatır. · Aynı iş için ikinci kez hatırlatmaz. · Yalnız oturum olaylarına bağlanabilen yardımcılarda çalışır. |
| yaz | Yazma · kart · konu · günlük | Anlamlı bir iş bitince yardımcı üç şeyi yazar: kendi oturum kartını, ilgili konunun güncel durumunu ve günlük kaydını. | Bir notu değiştirmeden önce okumak zorunludur; not o arada değiştiyse yazma reddedilir. · Her yazma tarihli bir kayıttır; eski hâl geri getirilebilir. · Her oturum yalnız kendi kartını yazar. |
| ogr | Öğrenme · {REVIEW_EVERY} araç çağrısında bir | Uzun bir işin sonunda hafıza yardımcıya sorar: bu işten öğrenilecek bir şey var mı? Düzeltmen kural, işin yolu iş tarifi olur. | Son sorudan beri en az {REVIEW_EVERY} araç çağrısı yapıldıysa sorulur. · Sır gibi görünen şey yazılamaz. · Yeni tarif aday doğar; {PROMOTE_AFTER} ayrı oturumda işe yararsa kalıcı olur. · {RETIRE_NOT_HELPED} oturum "işe yaramadı" deyip hiçbiri "yaradı" demediyse ya da {RETIRE_WRONG} kez "yanlış" dendiyse emekli olur. · Her öğrenme sana tek satırla bildirilir ve geri alınabilir. |
| haf | Hafıza | Notların kendisi: düz metin dosyaları. Tek doğru kaynak budur; öteki bütün bloklar buradan okur ya da buraya yazar. | Her değişiklik tarihli bir kayıttır. · İki yardımcı aynı notu birbirinin üstüne yazamaz. · Arama indeksi silinirse notlardan yeniden kurulur. |
| yed | Yedek | Notlar geçmişiyle birlikte özel bir yedek deposuna gönderilir. | {BACKUP_GRACE_DAYS} gün başarısız kalırsa yardımcı oturum başında seni uyarır. · Denetim soruları da yedeğe girer. |
| den | Denetim | Kayıtlı sorularla hafızanın doğru notu hâlâ bulup bulmadığına bakar. Hiçbir notu değiştirmez. | Her soru iki yoldan ölçülür: not kendiliğinden geliyor mu, aramayla bulunuyor mu. · Notlar arasındaki kırık bağlantıları da listeler. |

- [ ] **Step 1: Write the failing tests**

```python
from council import context, hook, learn
from council.panel import mechanism

def test_the_blocks_are_the_thirteen_of_the_spec_in_their_lanes():
    got = [(b["id"], b["lane"]) for b in mechanism.blocks()]
    assert got == [("h1", "start"), ("bas", "start"), ("diz", "start"), ("h2", "message"), ("ara", "message"), ("sec", "message"),
                   ("isa", "message"), ("h3", "end"), ("yaz", "end"), ("ogr", "end"), ("haf", "memory"), ("yed", "memory"), ("den", "memory")]
    assert all(b["name"] and b["what"] and b["rules"] and "{" not in b["what"] + "".join(b["rules"]) + b["sub"] for b in mechanism.blocks())

def test_every_number_in_a_rule_comes_from_the_code(monkeypatch):
    by = {b["id"]: b for b in mechanism.blocks()}
    assert "9.000" in by["bas"]["sub"] and "3.500" in " ".join(by["sec"]["rules"]) and "3.000" in by["diz"]["sub"]
    monkeypatch.setattr(context, "MESSAGE_BUDGET", 4200); monkeypatch.setattr(context, "MESSAGE_LIMIT", 7)
    monkeypatch.setattr(learn, "INDEX_BUDGET", 5000); monkeypatch.setattr(hook, "REVIEW_EVERY", 20)
    by = {b["id"]: b for b in mechanism.blocks()}
    assert "4.200" in " ".join(by["sec"]["rules"]) and "7 bölüm" in by["sec"]["sub"]
    assert "5.000" in by["diz"]["sub"] and "20 araç" in by["ogr"]["sub"]
```

- [ ] **Step 2: Run** — expected FAIL (`ModuleNotFoundError`).
- [ ] **Step 3: Implement** `blocks()`: it reads the constants at call time (not at import), so a changed constant changes the text.
- [ ] **Step 4: Run** `python -m pytest -q` — all pass.
- [ ] **Step 5: Commit** `git add -A && git commit -m "Panel: the blocks of the schema, their rules read from the code"`

### Task 8: Schema and Today as data; the leak test

**Files:**
- Create: `council/panel/views.py`
- Modify: `council/panel/app.py`, `council/panel/text_tr.py`
- Test: `tests/test_panel_views.py`, `tests/test_panel_leak.py`

**Interfaces:**
- Consumes: `reader` (Task 6), `mechanism.blocks()` (Task 7), `context.start_plan` (Task 3), `learn.Learning(store).index()`.
- Produces: `views.schema(data_dir, now: datetime) -> dict`, `views.today(data_dir, now: datetime) -> dict`, and `views.AT_LIMIT = lambda chars: chars >= context.MESSAGE_BUDGET - context.MIN_ROOM`. `app.py` serves them at `/api/schema` and `/api/today` with `now = store.now_local()`. A section whose function raises answers 200 with `{"error": "unavailable"}` and logs the exception; it never answers 500.
- `schema` returns:

```python
{"status": {"notes": int, "backup_last_ok": float | None, "backup_failing": bool, "skills": int},
 "lanes": [...], "blocks": [...],                                   # mechanism
 "numbers": {"<block id>": [str, ...]},                             # live lines per block, Turkish
 "events": [{"ts": float, "kind": str, "title": str, "path": [block ids], "memory": "read" | "written" | "",
             "steps": [{"block": str, "text": str, "value": str}]}]}   # the 30 newest, newest first
```

  - Events merge three sources: usage events, `changes` (one event per commit time; kind from the changed paths, first match wins: `sessions.md` → `card`, `threads.md` → `thread`, a path under `log/` → `log`, a `rules.md` → `rule`, a skill path → `skill`, else `note`) and `learnings`. Each kind's lit blocks (`path`):

| kind | path | memory |
|---|---|---|
| `start`, `context` | `h1` (not for `context`), `bas`, `diz`, `haf` | read |
| `inject` | `h2`, `ara`, `sec`, `haf` (and `isa` when a `pointer` event shares its second) | read |
| `inject` with 0 chars | `h2`, `ara`, `sec` | — |
| `read`, `open`, `search` | `haf` | read |
| `card`, `thread`, `log`, `note` | `h3`, `yaz`, `haf` | written |
| `rule`, `skill` (from a change or a learning) | `h3`, `ogr`, `haf` | written |

  - Steps are short Turkish sentences from `text_tr` with values that are counts, character totals and note paths only (for `inject`: the number of sections chosen, the character total with "sınıra dayandı" when `AT_LIMIT`, then the note paths one per line). No step shows a heading, a query or stems.
  - `numbers` gives live lines for `bas` (characters shown per fixed section, from `start_plan(announce=False)`), `diz` (skills listed and left out), `h2` and `sec` (last 24 hours: messages, messages given notes, mean characters when given), `isa` (pointers, opened), `haf` (notes, changes in the last 7 days), `yed` (time of the last successful backup or "kayıt yok"), `den` (number of saved questions).
- `today` returns:

```python
{"date": "YYYY-MM-DD", "now_minute": int,
 "lanes": ["start", "inject", "read", "search", "open", "pointer"],
 "events": [{"minute": int, "lane": str, "chars": int, "at_limit": bool}],       # today's usage events, oldest first; kind "context" goes to lane "start"
 "counts": {"start": int, "inject": int, "read": int, "search": int, "open": int, "pointer": int}, "at_limit": int,
 "budgets": {"start": {"budget": int, "parts": [{"name": str, "chars": int}], "left_out": [{"name": str, "chars": int}]},
             "message": {"budget": int, "min_room": int},
             "index": {"budget": int, "chars": int, "listed": int, "left_out": int}}}
```

  - "Today" is the memory's local day containing `now`; `minute` is minutes since local midnight.
  - `budgets.start.parts` has one entry per fixed section with the characters shown; `left_out` names what did not fit (for cards: `"oturum kartı"` with its length).

- [ ] **Step 1: Write the failing tests.** In `tests/test_panel_leak.py`:

```python
from tests.conftest import SECRETS

def test_no_address_of_the_panel_gives_away_text(leaky_panel):
    for section in ("schema", "today", "health", "map", "notes", "releases"):
        body = leaky_panel.get(f"/panel/api/{section}").text
        assert not [s for s in SECRETS if s in body], section
    for page in ("/panel/", "/panel/login"):
        assert not [s for s in SECRETS if s in leaky_panel.get(page).text]
```

  In `tests/test_panel_views.py` (use `leaky` and a small fixture that records usage events at fixed times):
  - `test_an_inject_event_lights_its_blocks_and_lists_paths_only`: the newest inject event has `path == ["h2", "ara", "sec", "haf"]`, `memory == "read"`, and its steps mention the note path and no heading.
  - `test_writes_come_from_the_history_of_the_notes`: after `store.upsert_session(...)` and `store.append_log(...)`, events of kind `card` and `log` exist with `path == ["h3", "yaz", "haf"]`.
  - `test_at_limit_is_the_last_two_hundred_characters`: `AT_LIMIT(3299)` is false, `AT_LIMIT(3300)` and `AT_LIMIT(3527)` are true; `today()["at_limit"]` counts only such inject events.
  - `test_today_is_the_local_day`: with `TZ` set so that local midnight differs from UTC midnight, an event one hour before local midnight is not in `today()["events"]` and one an hour after is, with `minute == 60`.
  - `test_the_start_budget_names_what_did_not_fit`: with a small budget (monkeypatch `context.START_BUDGET`), `budgets["start"]["left_out"]` is not empty and the parts add up to at most the budget.
  - `test_an_empty_memory_gives_empty_sections_not_an_error`: on a memory with nothing recorded, both views return with `events == []` and the address answers 200.
- [ ] **Step 2: Run** — expected FAIL (`ModuleNotFoundError: council.panel.views`).
- [ ] **Step 3: Implement** `views.schema`, `views.today`, their texts, and the two routes.
- [ ] **Step 4: Run** `python -m pytest -q` — all pass.
- [ ] **Step 5: Commit** `git add -A && git commit -m "Panel: the schema and today as data; no address gives away text"`

### Task 9: Notes, Map and Releases as data

**Files:**
- Create: `council/panel/releases.json`
- Modify: `council/panel/views.py`, `council/panel/app.py`
- Test: `tests/test_panel_views.py`

**Interfaces:**
- Produces: `views.notes(data_dir, now) -> dict`, `views.memory_map(data_dir, now) -> dict`, `views.releases() -> dict`, served at `/api/notes`, `/api/map`, `/api/releases`.

```python
notes -> {"since": float | None, "total": int,
          "ranking": [{"path": str, "injected": int, "read": int, "found": int}],     # used notes, most used first (sum of the three), ties by path
          "unused": [str],                                                            # notes with no usage at all, by path
          "always_loaded": ["core.md", "rules.md", "threads.md", "sessions.md"],
          "days": [{"date": "YYYY-MM-DD", "changes": int, "notes": int, "added": int}]}   # the last 35 local days, oldest first; a day with no change has zeros
memory_map -> {"notes": [{"path": str, "sections": int, "chars": int, "skill": bool, "region": str, "changed": float | None}],
          "links": [[int, int]],                                                      # indexes into notes, each pair once, lower index first
          "regions": [{"id": str, "name": str, "count": int}],
          "recent": [str]}                                                            # paths of the newest inject event
```

  - `region`: a note directly in the vault root → `cekirdek`; `projects/<name>/…` → `<name>`; `log/…` and `sessions/…` → `gecmis`; otherwise the first folder. `name` is the Turkish label from `text_tr.REGIONS` when there is one (`cekirdek` → Çekirdek, `gecmis` → Geçmiş, `knowledge` → Bilgi, `skills` → İş tarifleri, `imported` → İçe aktarılan), else the id itself.
  - `changed` is the time of the newest change that touched the note, from `reader.changes`.
- `releases.json` holds `{"ring": [{"n": 1, "name": "Hafıza", "state": "full"}, {"n": 2, "name": "İşlerden öğrenme", "state": "measured"}, {"n": 3, "state": "waiting"}, … 6], "versions": [...], "next": [...]}` with the four versions and the seven "next" items exactly as the spec's "Sürüm dosyası" section lists them; each version `{"version", "state": "pending" | "released" | "first", "date", "summary", "added": [str]}`, each next item `{"title", "text", "waits_for"}`.

- [ ] **Step 1: Write the failing tests:** `test_the_ranking_puts_the_most_used_note_first_and_lists_the_unused`, `test_days_follow_the_history_and_days_without_change_are_zero`, `test_the_map_groups_notes_by_folder_and_links_each_pair_once`, `test_the_recent_notes_are_those_of_the_newest_message`, `test_releases_has_six_ring_parts_four_versions_and_seven_next_items` (also: version numbers are unique and the first ring part is `full`).
- [ ] **Step 2: Run** — expected FAIL.
- [ ] **Step 3: Implement** the three functions, the routes and the data file.
- [ ] **Step 4: Run** `python -m pytest -q` — all pass, including the leak test for the three new addresses.
- [ ] **Step 5: Commit** `git add -A && git commit -m "Panel: notes, map and releases as data"`

### Task 10: The page: shell, Schema and Today

**Files:**
- Create: `council/panel/static/panel.js`, `schema.js`, `today.js`, `fonts/CouncilHalka.woff2`, `fonts/DMSans.ttf`, `fonts/DMMono-Regular.ttf`, `fonts/DMMono-Medium.ttf`, `fonts/OFL-DMSans.txt`, `fonts/OFL-DMMono.txt`
- Modify: `council/panel/static/index.html`, `panel.css`, `pyproject.toml` (package data `static/*`, `static/fonts/*`), `council/panel/app.py` (serve `static/fonts/<file>`)
- Test: `tests/test_panel_static.py`

**Interfaces:**
- Consumes: the JSON of Task 8.
- Produces: `panel.js` exposes `window.Panel = {base, get(section) -> Promise<object>, el(tag, attrs, children), fmt: {number, time, date}, sections: {}}`; each section file registers `Panel.sections.<name> = {render(root, data), update(root, data)}`. `get` goes to `<base>/login` when the answer is 401. The shell shows one section at a time, chosen by the address fragment (`#sema`, `#bugun`, `#saglik`, `#harita`, `#notlar`, `#guncellemeler`; default `#sema`), asks for its data every 5 seconds while the tab is visible, and calls `update`.
- Fonts: copy `brand/font/CouncilHalka.woff2`; take DM Sans (variable) and DM Mono (Regular, Medium) from the `google/fonts` repository on GitHub (`ofl/dmsans`, `ofl/dmmono`) together with their `OFL.txt` files.

**What the two sections show** (the spec's "Ekranların içeriği" is the reference; every panel has a one-sentence line under its title saying what it answers):
- *Şema:* status strip; three lanes of blocks drawn left to right, each block a button with one side round and one side cut flat (`border-radius: 32px 0 0 32px`), joined by 2px lines that end at a vertical line in front of the memory ring (a circle with a 16px accent border); Yedek and Denetim under the ring; the list of events with a "canlı izleme" toggle that steps through the events every 4 seconds until something is clicked; under them either the selected event's steps as numbered cards or the selected block's "ne yapar", rules and live numbers. Blocks on the selected event's path are drawn ink-filled; a small accent dot travels along the lines between them. A block's detail ends with the sentence from `text_tr` telling the owner to say the block's name to change how it works.
- *Bugün:* six counters; six lanes over a 24-hour axis with one mark per event (circle size from characters for the inject lane; ring for start and open; half circles for search and pointer), a vertical line at "now", the "yalnız sınıra dayananlar" toggle with its definition under it; three rings of equal size (start budget in up to five slices separated by flat gaps, with a list of the slices and of what did not fit; the selected event's characters against the message budget, in the accent colour; the skill index).
- Motion: a new event appears with one short transition and then stays still. Only the travelling dot and (later) the map's rotation move continuously; both can be switched off and both start off when `prefers-reduced-motion: reduce` matches.

- [ ] **Step 1: Write the failing tests** in `tests/test_panel_static.py`:

```python
def test_the_page_loads_nothing_from_another_host_and_never_builds_html_from_data(static_dir):
    for f in static_dir.rglob("*"):
        if f.suffix in (".html", ".css", ".js"):
            text = f.read_text(encoding="utf-8")
            assert "http://" not in text and "https://" not in text and "//fonts." not in text, f.name
            if f.suffix == ".js":
                assert "innerHTML" not in text and "outerHTML" not in text and "document.write" not in text, f.name

def test_fonts_and_scripts_are_served_and_the_shell_names_the_six_sections(panel_signed_in):
    for name in ("panel.css", "panel.js", "schema.js", "today.js", "fonts/CouncilHalka.woff2", "fonts/DMSans.ttf"):
        assert panel_signed_in.get(f"/panel/static/{name}").status_code == 200
    page = panel_signed_in.get("/panel/").text
    assert all(w in page for w in ("Şema", "Bugün", "Sağlık", "Harita", "Notlar", "Güncellemeler"))
    assert panel_signed_in.get("/panel/static/../gate.py").status_code in (400, 404)

def test_a_wheel_would_carry_the_static_files(): ...
    # pyproject's package-data for council.panel lists static/*, static/fonts/* and releases.json
```

- [ ] **Step 2: Run** — expected FAIL.
- [ ] **Step 3: Implement** the shell and the two sections.
- [ ] **Step 4: Check it in a browser.** Make a memory to look at: `council --data /tmp/panel-deneme token && council --data /tmp/panel-deneme set-password --generate` (note the printed password), start `council --data /tmp/panel-deneme serve --port 8799` briefly so the notes and index exist, record a few events by calling its `/api/context`, stop it, then run `council --data /tmp/panel-deneme panel --port 8766` and open `http://127.0.0.1:8766/panel/`. Confirm: sign-in works; a wrong password shows the error; Şema shows the thirteen blocks in three lanes and the ring; clicking a block shows its rules with the numbers 9.000, 3.500 and 3.000; clicking an event darkens its path; Bugün shows marks on the right lanes; a note path containing `<b>` shows as text; with the session cookie deleted, the next refresh lands on the sign-in page; at a 390px-wide window nothing overflows sideways except the lanes, which scroll inside their own box. Write what you saw in the commit message body.
- [ ] **Step 5: Run** `python -m pytest -q` — all pass. **Commit** `git add -A && git commit -m "Panel: the page, the schema and today"`

### Task 11: The page: Notes, Map and Releases

**Files:**
- Create: `council/panel/static/notes.js`, `map.js`, `releases.js`
- Modify: `council/panel/static/index.html`, `panel.css`
- Test: `tests/test_panel_static.py` (extend the served-files list)

**Interfaces:**
- Consumes: the JSON of Task 9; `window.Panel` (Task 10).

**What the three sections show:**
- *Notlar:* the ranking as rows (note path in the mono face, a 1px line with a 14px ink circle placed at `total / max`, the three counts) for the 18 most used notes with a "tümünü göster" button; the unused notes as a separate set with their count over the total, and the sentence that an unused note is not a note to delete; the always-loaded notes named as not counted. The calendar: weeks as columns, weekdays as rows, the last 35 days; circle size in four steps by that day's changes (1–20, 21–80, 81–110, 111 and more; a day before the first recorded change is a 4px hairline dot); clicking a day shows its three counts; the selected day is the accent colour.
- *Harita:* one `<canvas>` on a dark stage (`#111416`), 640px tall. Notes are dots sized by characters, placed on small spheres per region around a centre; the root notes sit inside an accent ring at the centre; skills are hollow rings; links are thin lines. Dragging rotates, the wheel and two buttons zoom, a toggle stops the slow rotation, a toggle shows names, region buttons hide and show regions. Positions are computed once from the data with a fixed seed, so the same memory always draws the same map. Clicking a dot selects the note: its neighbours and their lines brighten, the rest dim, and a card under the stage shows its path, region, sections, characters, link counts and its neighbours' paths as buttons. A legend names dot, ring and centre. Notes of the newest message (`recent`) carry a small accent mark. Names switch off by themselves above 60 visible notes unless a note is selected.
- *Güncellemeler:* the six-part ring (first part accent, a `measured` part dashed ink, `waiting` parts hairline) with "N / 6"; version cards newest first (number in the display face, state badge with one side cut flat, date, one-sentence summary, the list of what was added); the numbered "Sıradakiler" list with what each item waits for.

- [ ] **Step 1: Extend the test** `test_fonts_and_scripts_are_served…` with `notes.js`, `map.js`, `releases.js`; run — expected FAIL.
- [ ] **Step 2: Implement** the three sections.
- [ ] **Step 3: Check it in a browser** with the memory of Task 10 after adding a dozen linked notes in three project folders: the ranking order matches `council usage`; the unused set is right; the calendar's selected day shows today's counts; the map draws, rotates smoothly with 200 notes (generate them for this check), keeps the same layout after a reload, and selecting a dot lists its neighbours; the releases page shows four versions and seven items. Write what you saw in the commit message body.
- [ ] **Step 4: Run** `python -m pytest -q` — all pass. **Commit** `git add -A && git commit -m "Panel: notes, the map and releases on the page"`

### Task 12: Health: samples, check runs, the section

**Files:**
- Create: `council/panel/sampler.py`, `council/panel/static/health.js`
- Modify: `council/panel/views.py`, `council/panel/app.py`, `council/panel/static/index.html`, `panel.css`, `council/panel/text_tr.py`
- Test: `tests/test_panel_health.py`

**Interfaces:**
- Consumes: `reader.backup_state`, `check.search_report`, `check.questions`, `Gate`'s database file.
- Produces:

```python
SAMPLE_EVERY = 900          # seconds
CHECK_EVERY = 3600
KEEP_DAYS = 400
class Sampler:
    def __init__(self, data_dir, service_url: str): ...       # tables samples(ts REAL, service INTEGER, backup INTEGER, updates INTEGER) and runs(ts REAL, head TEXT, auto TEXT, search TEXT) in panel.sqlite3
    def sample(self, now: float | None = None, probe=None) -> dict: ...     # one row; probe(url) -> bool defaults to an HTTP GET of <service_url>/health with a 3 second timeout
    def run_check(self, now: float | None = None, force: bool = False) -> bool: ...   # runs when the vault's HEAD changed since the last run or CHECK_EVERY passed, or force
    def days(self, now: datetime, count: int = 30) -> list[dict]: ...       # oldest first: {"date", "service": state, "backup": state, "updates": state}
    def runs(self, limit: int = 12) -> list[dict]: ...                       # oldest first: {"ts", "auto": [bool], "search": [bool]}
    async def loop(self) -> None: ...                                         # sample every SAMPLE_EVERY, then run_check; never raises
```

  - A sample's `backup` is 1 when `backup_state` reports a success within the last `2 * SAMPLE_EVERY` seconds or (no failure and a last success within `BACKUP_GRACE`), 0 when it reports failing or the last success is older, and NULL when no backup is configured (`backup_state` is `None`).
  - A sample's `updates` is NULL when the install has no automatic-update state file (read `council/local.py`, `_update_state`, for its name and shape), 0 when that state holds an `error`, else 1.
  - A day's state per component: `"full"` when every sample of that local day is 1, `"failed"` when every sample is 0, `"partial"` when both occur, `"none"` when there is no sample or every value is NULL.
  - `run_check` stores, per saved question in the order `check.questions` gives them, whether it came by itself and whether search found it; questions whose notes are gone are stored as `null`. The question texts are not stored.
- `views.health(data_dir, now, sampler) -> dict`: `{"summary": {"service": state of the newest sample or "none", "backup": …, "questions": int, "both": int}, "days": [...], "runs": [...], "missing": [int]}` where `missing` holds the 1-based numbers of the questions that the newest run did not find by search or by itself. `build(..., background=True)` starts `Sampler.loop()` as a background task on startup and cancels it on shutdown; `build(..., background=False)` creates the `Sampler` without the loop. `views.schema()["status"]` gains `"service": state of the newest sample or "none"` and `"check": {"questions": int, "auto": int, "search": int} | None` from the newest run, and the status strip shows them.
- *Sağlık on the page:* one sentence of overall state; the 30-day strip with one row per component and one mark per day (filled circle full, half circle partial, a flat bar failed, an empty outline none), the four marks named in a legend, the first day with a sample labelled; the grid of questions (rows numbered, two column groups, filled circle found, outline missed, nothing for `null`), each run's totals above its column, and the list of questions missed today. A component with only `none` days for the whole strip is not drawn.

- [ ] **Step 1: Write the failing tests:**
  - `test_a_day_is_full_partial_failed_or_has_no_record`: insert samples through `sample(now=…, probe=…)` for four local days (all up; up and down; all down; none) and assert the four states.
  - `test_a_day_follows_local_time`: a sample 30 minutes after local midnight belongs to the new day.
  - `test_a_check_runs_when_the_notes_changed_and_stores_no_question_text`: with `leaky`, `run_check(force=True)` stores one run; the database file's bytes contain none of `SECRETS`; a second `run_check()` right after returns False; after a new note is written through a normal `Store` and committed, `run_check()` returns True.
  - `test_health_names_the_questions_missed_by_number`.
  - `test_no_backup_configured_is_no_record_not_a_failure`.
  - `test_the_loop_survives_a_failing_probe`: a probe that raises leaves a sample with `service == 0` and the loop function returns normally when cancelled.
- [ ] **Step 2: Run** — expected FAIL.
- [ ] **Step 3: Implement** the sampler, the view, the route and the section.
- [ ] **Step 4: Check it in a browser:** the strip shows today as full after two samples (call `sample` twice from a Python shell or shorten `SAMPLE_EVERY` through an environment variable you add for this purpose, `COUNCIL_PANEL_SAMPLE_EVERY`); stop the memory service, take a sample: today turns partial; the grid shows the saved questions by number.
- [ ] **Step 5: Run** `python -m pytest -q` — all pass, the leak test included. **Commit** `git add -A && git commit -m "Panel: health samples, check history and the health section"`

### Task 13: Running it on a server; the guides

**Files:**
- Create: `deploy/council-panel.service`
- Modify: `deploy/Caddyfile`, `docs/kurulum.md`, `docs/setup.md`, `council/panel/views.py` (version line)
- Test: `tests/test_panel_views.py`

**Interfaces:**
- `views.schema()["status"]` gains `"panel_version": council.__version__` and `"service_version": str | None` (from the newest sample's `/health` answer, which `Sampler.sample` now also stores in a `version` column); the page shows both and a plain sentence when they differ.
- `deploy/council-panel.service`: modelled on `deploy/council.service` (same user, same `COUNCIL_DATA`, same `TZ`), `ExecStart=/opt/council/.venv/bin/council panel --host 127.0.0.1 --port 8766 --base-path /panel`, `After=council.service`, `Restart=on-failure`.
- `deploy/Caddyfile`: inside the site block, before `reverse_proxy 127.0.0.1:8765`, add `handle /panel* { reverse_proxy 127.0.0.1:8766 }` and wrap the existing proxy in `handle { … }`.
- Guides: a section "Panel" in both languages after the backup section: what it shows, that it needs the owner password (`council set-password`), the command, the service file, the Caddy lines, and that it shows note paths but never note text. Add the `council panel` row to the commands table.

- [ ] **Step 1: Write the failing test** `test_the_status_names_both_versions_and_says_when_they_differ`.
- [ ] **Step 2: Run** — expected FAIL.
- [ ] **Step 3: Implement** the version line, the service file, the Caddy lines and the guide sections.
- [ ] **Step 4: Run** `python -m pytest -q` — all pass.
- [ ] **Step 5: Commit** `git add -A && git commit -m "Panel: service file, proxy lines and the guides"`

---

## After the tasks

These need the owner and are not part of this plan's tasks:

1. A fresh reviewer reads the whole branch against the spec's "Olmaması gerekenler" and the Review Focus above.
2. Merge into `main` and push (the owner's approval).
3. Install on the owner's server (the owner's approval; the spec's phase 4): copy the code with the memory service, add the service file and the Caddy lines, then measure the spec's third criterion (the median time to prepare the context with the panel open against without it; at most 10% more).
4. The owner answers the spec's five questions from the panel (the fourth criterion).
