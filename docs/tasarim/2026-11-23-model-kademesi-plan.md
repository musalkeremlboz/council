# Model Tiers (delegation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A session's sub-agents run one model tier below the session's model, the session is told when to hand work off and how to review it, and a report shows what each model spent.

**Architecture:** Everything lives on the client side. The hook file gains a session-start directive block and a `PreToolUse` handler that rewrites the `model` of a sub-agent call; the installer registers that fourth hook; a new read-only module turns local session records into a report. The memory server is not touched.

**Tech Stack:** Python >= 3.11, standard library only in `council/hook.py` and `council/delegation.py`; pytest.

**Spec:** `docs/tasarim/2026-11-23-model-kademesi.md` (Turkish). Read it first; this plan argues from it.

## Global Constraints

- Branch: `model-kademesi`, cut from `main`. No push, no merge, no release, no change on the owner's Mac settings or on the server without the owner's explicit yes (see Gates).
- `council/hook.py` stays one self-contained, standard-library-only file: it is copied alone to `~/.council/hook.py`. It may not import from the package.
- The hook must never fail, delay or re-permission a tool call: any exception in the `PreToolUse` path ends with exit code 0 and no output; the output never contains `permissionDecision`.
- The `PreToolUse` path makes no network request.
- `council/server.py`, `council/context.py`, `council/learn.py` and everything under `council/panel/` are not modified.
- Tiers come from the family name inside the model id, never from a version number: `fable` or `mythos` = 4, `opus` = 3, `sonnet` = 2, `haiku` = 1, anything else = 0 (unknown).
- Config key `delegation` in `~/.config/council/config.json`: `"enforce"` (default), `"advise"`, `"off"`. Any other value, a missing key or a missing file means `"enforce"`.
- The directive block is at most 1,200 characters.
- Code, comments, test names and commit messages in English, in the repository's style (`Delegation: <sentence>`). End each commit message with the `Co-Authored-By` trailer of the model that wrote it; the session lead supplies the exact line.
- Tests must pass on Linux, macOS and Windows: open files with `encoding="utf-8"`, build paths with `pathlib`, never compare path strings by case.
- User-facing text in README files does not name specific agent products outside the "supported agents" section (project rule). This plan adds no README text; documentation goes to `docs/kurulum.md` and `docs/setup.md` only.

## Review Focus

1. **A record being written while it is read:** the last line of a `.jsonl` file is cut off or is not JSON. Expected: that line is skipped; the hook and the report carry on. (Tests in Tasks 1 and 5.)
2. **A `model` value the hook cannot rank** in the sub-agent call: `null`, an empty string, a full id (`claude-opus-5-5`), or a name with no known family. Expected: a full id is ranked by its family; an unrankable value is left exactly as it is, reason `unknown-model`. (Test in Task 2.)
3. **A very large session record** (hundreds of megabytes). Expected: the main model is found by reading from the end in bounded chunks; the file is never read whole. (Test in Task 1.)
4. **A settings file the installer does not own:** the user's own `PreToolUse` hooks, an entry of ours with an old matcher, invalid JSON. Expected: other entries survive untouched, ours is refreshed in place and never duplicated, invalid JSON is left byte-for-byte. (Tests in Task 4.)
5. **Several sub-agents started in the same turn:** several hook processes append to the decision log at once. Expected: every decision is one whole line; no line is interleaved or lost. (Test in Task 2.)

---

### Task 0: Probe (no product code)

The spec's section "Sonda" lists what is known from documentation only. Nothing in Tasks 2 and 4 may be merged before this task's answers are written down. This task is done by the session lead, not handed to a worker: its answers can change the design.

**Files:**
- Modify: `docs/tasarim/2026-11-23-model-kademesi.md` (append a section `## Sonda sonuçları`)
- Create: `tests/fixtures/pretooluse_agent.json` (one real hook input, with the prompt text, paths and ids replaced by placeholders)

- [ ] **Step 1: Build a throwaway probe hook** outside the repository (scratch directory): a script that appends its stdin to a file and, when `tool_name` is `Agent` or `Task`, prints `{"hookSpecificOutput": {"hookEventName": "PreToolUse", "updatedInput": {**tool_input, "model": "haiku"}}}`.
- [ ] **Step 2: Run one short non-interactive session** with the main model set to Sonnet, in an empty scratch project whose project-level settings register the probe hook for `PreToolUse` with matcher `Agent|Task`. Prompt: ask it to start one general-purpose sub-agent with model `sonnet` that answers with the single word `ok`. The command-line client is not on `PATH` on the owner's Mac; find the one the desktop app ships, or use the server's (`/root/.local/bin/claude`). The owner's user-level memory hooks will also fire: write the probe's session ids into the spec section so they can be subtracted from the running trial's counts.
- [ ] **Step 3: Record the answers** in `## Sonda sonuçları`, each with the evidence (field names seen, file read):
  1. Did the hook fire; which fields does the input carry (`tool_name`, `tool_input` keys, `transcript_path`, `cwd`, and any field that tells a call made inside a sub-agent from one made by the main session)?
  2. Did the sub-agent actually run on Haiku (read `message.model` in its own `agent-*.jsonl`) with no `permissionDecision` in the output? Was a permission question asked that is not asked without the hook?
  3. At the moment the hook ran, did the session record already contain an assistant line with `message.model` for that turn?
  4. Repeat Step 2 three times with no `model` in the request, for agent types `claude`, `Plan` and `Explore` (probe hook switched off): which model did each run on?
- [ ] **Step 4: Decide and write down the consequences.** If 2 fails (the model is not changed, or changing it needs `permissionDecision`): stop, tell the owner; the feature becomes directive-only and Tasks 2 and 4 are dropped. If 3 fails: Task 2 also stores the `model` field of the `SessionStart` input in `~/.council/state/<session>.json` and reads it as a fallback. From 4: every type that ran on the main model joins `INHERITING` in Task 2. From 1: the name of the "inside a sub-agent" field for Task 2 (if there is none, that rule is dropped and the spec says so).
- [ ] **Step 5: Commit** the spec section and the fixture: `Delegation: what the probe showed about the sub-agent hook`.

---

### Task 1: Tiers, the session's model, the mode

**Files:**
- Modify: `council/hook.py`
- Test: `tests/test_delegation_hook.py` (create)

**Interfaces:**
- Produces:
  - `TIERS: dict[str, int] = {"fable": 4, "mythos": 4, "opus": 3, "sonnet": 2, "haiku": 1}`
  - `ALIASES: dict[int, str] = {4: "fable", 3: "opus", 2: "sonnet", 1: "haiku"}`
  - `tier(model: object) -> int` — 0 for anything that is not a string naming a known family (case-insensitive substring match).
  - `main_model(transcript: str) -> str | None` — `message.model` of the last line whose `type` is `assistant`, skipping lines with `isSidechain` true and models that start with `<`.
  - `delegation_mode() -> str` — `"enforce"`, `"advise"` or `"off"`.

- [ ] **Step 1: Write the failing tests**

```python
import json
import pytest
from council import hook

@pytest.fixture(autouse=True)
def no_user_config(tmp_path, monkeypatch):
    monkeypatch.setattr(hook, "CONFIG", tmp_path / "no-config.json")

@pytest.mark.parametrize("model, expected", [
    ("claude-mythos-5-2", 4), ("claude-fable-5-2", 4), ("fable", 4), ("claude-opus-5-5", 3), ("opus", 3),
    ("anthropic.claude-sonnet-5-5", 2), ("Sonnet", 2), ("claude-haiku-5-5", 1),
    ("gpt-9", 0), ("<synthetic>", 0), ("", 0), (None, 0), (7, 0)])
def test_tier_reads_the_family_name(model, expected):
    assert hook.tier(model) == expected

def record(tmp_path, lines):
    f = tmp_path / "t.jsonl"
    f.write_text("\n".join(json.dumps(x) if isinstance(x, dict) else x for x in lines) + "\n", encoding="utf-8")
    return str(f)

def assistant(model, **extra):
    return {"type": "assistant", "message": {"model": model, "content": []}, **extra}

def test_main_model_is_the_last_assistant_model(tmp_path):
    path = record(tmp_path, [assistant("claude-opus-5-5"), {"type": "user"}, assistant("claude-mythos-5-2")])
    assert hook.main_model(path) == "claude-mythos-5-2"

def test_main_model_skips_sidechains_synthetic_and_broken_lines(tmp_path):
    path = record(tmp_path, [assistant("claude-opus-5-5"), assistant("claude-haiku-5-5", isSidechain=True),
                             assistant("<synthetic>"), '{"type": "assistant", "message": {"mod'])
    assert hook.main_model(path) == "claude-opus-5-5"

def test_main_model_is_none_without_a_record_or_an_assistant_line(tmp_path):
    assert hook.main_model(str(tmp_path / "missing.jsonl")) is None
    assert hook.main_model(record(tmp_path, [{"type": "user"}])) is None

def test_main_model_reads_a_large_record_from_the_end(tmp_path, monkeypatch):
    f = tmp_path / "big.jsonl"
    pad = json.dumps({"type": "user", "message": {"content": "x" * 1000}})
    f.write_text("\n".join([json.dumps(assistant("claude-opus-5-5"))] + [pad] * 20000
                           + [json.dumps(assistant("claude-sonnet-5-5"))]) + "\n", encoding="utf-8")
    sizes = []
    class Counting:                                           # a file object that remembers every read size
        def __init__(self, fh): self.fh = fh
        def read(self, n=-1): sizes.append(n); return self.fh.read(n)
        def __getattr__(self, name): return getattr(self.fh, name)
        def __enter__(self): return self
        def __exit__(self, *a): return self.fh.__exit__(*a)
    monkeypatch.setattr(hook, "open", lambda *a, **k: Counting(open(*a, **k)), raising=False)
    assert hook.main_model(str(f)) == "claude-sonnet-5-5"
    assert sizes and all(0 < n <= 1 << 20 for n in sizes)    # bounded chunks, never the whole file

@pytest.mark.parametrize("config, expected", [
    (None, "enforce"), ({}, "enforce"), ({"delegation": "advise"}, "advise"), ({"delegation": "off"}, "off"),
    ({"delegation": "nonsense"}, "enforce"), ({"delegation": False}, "enforce")])
def test_delegation_mode(tmp_path, monkeypatch, config, expected):
    if config is not None:
        (tmp_path / "c.json").write_text(json.dumps(config))
        monkeypatch.setattr(hook, "CONFIG", tmp_path / "c.json")
    assert hook.delegation_mode() == expected
```

- [ ] **Step 2: Run them and see them fail**

Run: `python -m pytest tests/test_delegation_hook.py -q`
Expected: FAIL, `module 'council.hook' has no attribute 'tier'`

- [ ] **Step 3: Implement `tier`, `main_model` and `delegation_mode` in `council/hook.py`.** `main_model` opens the file with the built-in `open` in binary mode (the test watches that name), seeks from the end and reads backwards in chunks of at most 1 MiB until a qualifying line is found or the start is reached; a line split across two chunks must still be parsed whole.

- [ ] **Step 4: Run the tests and see them pass**

Run: `python -m pytest tests/test_delegation_hook.py tests/test_learn_hook.py -q`
Expected: PASS

- [ ] **Step 5: Commit** — `Delegation: the hook can rank a model and read the session's model from its record`

---

### Task 2: The ceiling on a sub-agent call

**Files:**
- Modify: `council/hook.py`
- Test: `tests/test_delegation_hook.py`

**Interfaces:**
- Consumes: `tier`, `ALIASES`, `main_model`, `delegation_mode` (Task 1); Task 0's answers (the sub-agent marker field, the inheriting types, whether the `SessionStart` fallback is needed).
- Produces:
  - `INHERITING: frozenset[str]` — `{"", "general-purpose"}` plus the types Task 0 saw running on the main model.
  - `WORKER_NOTE = "COUNCIL memory is readable with council_search and council_read. Do not write to it; the session that started you records the work."`
  - `DELEGATION_LOG = STATE / "delegation.jsonl"`
  - `agent_inherits(agent_type: str, cwd: str, home: Path | None = None) -> bool`
  - `decide(tool_input: dict, main: str | None, cwd: str = "", home: Path | None = None) -> tuple[dict | None, str]` — the new input (or `None` when nothing changes) and a reason, one of `set`, `lowered`, `kept`, `unknown-main`, `own-model`, `unknown-model`, `fork`. The ceiling is `max(tier(main) - 1, 1)`: a session on the lowest tier keeps its sub-agents on that tier.
  - `log_decision(row: dict) -> None` — appends one line to `DELEGATION_LOG`.
  - `delegation_check(event: dict) -> None` — the `PreToolUse` handler.
  - Decision log line (one JSON object per line): `{"ts": float, "session": str, "type": str, "asked": str | None, "model": str | None, "main": str | None, "reason": str}`; `session` is the first 16 characters of the session id, `model` is what the hook wrote (`None` when it changed nothing). Reasons written by `delegation_check` beyond `decide`'s: `nested`, `off`.

- [ ] **Step 1: Write the failing tests**

```python
CALL = {"description": "d", "prompt": "do it", "subagent_type": "general-purpose"}

@pytest.mark.parametrize("main, extra, model, reason", [
    ("claude-mythos-5-2", {}, "opus", "set"),
    ("claude-fable-5-2", {"model": "fable"}, "opus", "lowered"),
    ("claude-fable-5-2", {"model": "claude-fable-5-2"}, "opus", "lowered"),
    ("claude-fable-5-2", {"model": "opus"}, None, "kept"),
    ("claude-fable-5-2", {"model": "haiku"}, None, "kept"),
    ("claude-opus-5-5", {}, "sonnet", "set"),
    ("claude-opus-5-5", {"model": "opus"}, "sonnet", "lowered"),
    ("claude-sonnet-5-5", {}, "haiku", "set"),
    ("claude-haiku-5-5", {}, "haiku", "set"),
    ("claude-haiku-5-5", {"model": "opus"}, "haiku", "lowered"),
    ("claude-haiku-5-5", {"model": "haiku"}, None, "kept"),
    (None, {}, None, "unknown-main"),
    ("gpt-9", {"model": "opus"}, None, "unknown-main"),
    ("claude-fable-5-2", {"model": "gpt-9"}, None, "unknown-model"),
    ("claude-fable-5-2", {"model": None}, "opus", "set"),
    ("claude-fable-5-2", {"model": ""}, "opus", "set"),
    ("claude-fable-5-2", {"subagent_type": "claude-code-guide"}, None, "own-model"),
    ("claude-fable-5-2", {"subagent_type": "claude-code-guide", "model": "fable"}, "opus", "lowered"),
    ("claude-fable-5-2", {"subagent_type": "fork"}, None, "fork"),
    ("claude-fable-5-2", {"subagent_type": "fork", "model": "fable"}, None, "fork"),
])
def test_decide(tmp_path, main, extra, model, reason):
    new, why = hook.decide({**CALL, **extra}, main, home=tmp_path)
    assert why == reason
    assert (new or {}).get("model") == model

def test_a_changed_call_keeps_every_other_field_and_tells_the_worker_about_memory(tmp_path):
    new, _ = hook.decide({**CALL, "run_in_background": True, "extra": {"a": 1}}, "claude-fable-5-2", home=tmp_path)
    assert new["prompt"] == "do it\n\n" + hook.WORKER_NOTE
    assert {k: new[k] for k in ("description", "subagent_type", "run_in_background", "extra")} == \
           {"description": "d", "subagent_type": "general-purpose", "run_in_background": True, "extra": {"a": 1}}

def test_an_agent_file_decides_whether_a_custom_type_inherits(tmp_path):
    agents = tmp_path / ".claude" / "agents"; agents.mkdir(parents=True)
    (agents / "cheap.md").write_text("---\nname: cheap\nmodel: haiku\n---\nbody\n", encoding="utf-8")
    (agents / "plain.md").write_text("---\nname: plain\n---\nbody\n", encoding="utf-8")
    (agents / "same.md").write_text("---\nname: same\nmodel: inherit\n---\nbody\n", encoding="utf-8")
    project = tmp_path / "proj"; (project / ".claude" / "agents").mkdir(parents=True)
    (project / ".claude" / "agents" / "local.md").write_text("---\nname: local\n---\n", encoding="utf-8")
    assert not hook.agent_inherits("cheap", "", home=tmp_path)
    assert hook.agent_inherits("plain", "", home=tmp_path) and hook.agent_inherits("same", "", home=tmp_path)
    assert hook.agent_inherits("local", str(project), home=tmp_path)
    assert not hook.agent_inherits("someone-elses:agent", "", home=tmp_path)   # unknown type: hands off

def event(tmp_path, main="claude-fable-5-2", **tool_input):
    return {"hook_event_name": "PreToolUse", "tool_name": "Agent", "session_id": "s" * 40, "cwd": str(tmp_path),
            "transcript_path": record(tmp_path, [assistant(main)]), "tool_input": {**CALL, **tool_input}}

def run_check(tmp_path, monkeypatch, capsys, ev):
    monkeypatch.setattr(hook, "STATE", tmp_path / "state")
    monkeypatch.setattr(hook, "DELEGATION_LOG", tmp_path / "state" / "delegation.jsonl")
    hook.delegation_check(ev)
    out = capsys.readouterr().out
    log = tmp_path / "state" / "delegation.jsonl"
    lines = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
    return (json.loads(out) if out else None), lines

def test_the_handler_rewrites_the_model_and_never_decides_permission(tmp_path, monkeypatch, capsys):
    out, lines = run_check(tmp_path, monkeypatch, capsys, event(tmp_path))
    spec = out["hookSpecificOutput"]
    assert spec["hookEventName"] == "PreToolUse" and spec["updatedInput"]["model"] == "opus"
    assert "permissionDecision" not in spec and set(out) == {"hookSpecificOutput"}
    assert lines == [{"ts": lines[0]["ts"], "session": "s" * 16, "type": "general-purpose", "asked": None,
                      "model": "opus", "main": "claude-fable-5-2", "reason": "set"}]

def test_the_handler_is_silent_when_nothing_changes_but_still_logs(tmp_path, monkeypatch, capsys):
    out, lines = run_check(tmp_path, monkeypatch, capsys, event(tmp_path, model="sonnet"))
    assert out is None and lines[0]["reason"] == "kept" and lines[0]["model"] is None and lines[0]["asked"] == "sonnet"

@pytest.mark.parametrize("mode", ["advise", "off"])
def test_the_handler_does_nothing_unless_enforcing(tmp_path, monkeypatch, capsys, mode):
    (tmp_path / "c.json").write_text(json.dumps({"delegation": mode}))
    monkeypatch.setattr(hook, "CONFIG", tmp_path / "c.json")
    out, lines = run_check(tmp_path, monkeypatch, capsys, event(tmp_path))
    assert out is None and lines[0]["reason"] == "off"

def test_other_tools_and_broken_events_pass_untouched(tmp_path, monkeypatch, capsys):
    for ev in ({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}},
               {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": "not a dict"},
               {"hook_event_name": "PreToolUse", "tool_name": "Agent"}):
        out, _ = run_check(tmp_path, monkeypatch, capsys, ev)
        assert out is None

def test_the_old_tool_name_is_handled_too(tmp_path, monkeypatch, capsys):
    out, _ = run_check(tmp_path, monkeypatch, capsys, {**event(tmp_path), "tool_name": "Task"})
    assert out["hookSpecificOutput"]["updatedInput"]["model"] == "opus"

def test_main_never_fails_a_tool_call(tmp_path, monkeypatch, capsys):
    import io
    monkeypatch.setattr(hook, "delegation_check", lambda ev: 1 / 0)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event(tmp_path))))
    assert hook.main() == 0 and capsys.readouterr().out == ""

def test_parallel_decisions_are_whole_lines(tmp_path, monkeypatch):
    import threading
    monkeypatch.setattr(hook, "DELEGATION_LOG", tmp_path / "d.jsonl")
    threads = [threading.Thread(target=hook.log_decision, args=({"n": i, "pad": "x" * 2000},)) for i in range(40)]
    [t.start() for t in threads]; [t.join() for t in threads]
    rows = [json.loads(x) for x in (tmp_path / "d.jsonl").read_text(encoding="utf-8").splitlines()]
    assert sorted(r["n"] for r in rows) == list(range(40))
```

Add one more test from Task 0's fixture: load `tests/fixtures/pretooluse_agent.json`, point its `transcript_path` at a record whose model is Fable, and assert the handler returns `model == "opus"` with every other key of the real input preserved. If Task 0 found the "inside a sub-agent" field, add `test_a_call_from_inside_a_sub_agent_is_left_alone` asserting no output and reason `nested`.

- [ ] **Step 2: Run them and see them fail**

Run: `python -m pytest tests/test_delegation_hook.py -q`
Expected: FAIL, `module 'council.hook' has no attribute 'decide'`

- [ ] **Step 3: Implement** `agent_inherits`, `decide`, `log_decision(row: dict) -> None` and `delegation_check` in `council/hook.py`, and dispatch `PreToolUse` in `main()` before the memory events, inside a `try` that swallows every exception.
  - `decide` order: unknown main; type `fork`; a `model` that is present and non-empty (unrankable → `unknown-model`; above the ceiling → `lowered`; otherwise `kept`); no model and `agent_inherits` → `set`; else `own-model`. The ceiling's alias is `ALIASES[max(tier(main) - 1, 1)]`.
  - `agent_inherits`: true for `INHERITING`; otherwise look for `<home>/.claude/agents/<type>.md` and `<cwd>/.claude/agents/<type>.md` (project first) and read only the front matter between the first two `---` lines: no `model:` line, or `model: inherit`, means true; no file means false.
  - `log_decision` appends one line with a single `write` call on a file opened in append mode; when the file is over 1 MiB it keeps the newer half first. Its failures are swallowed.
  - The handler prints output only when `decide` returned a new input.

- [ ] **Step 4: Run the tests and see them pass**

Run: `python -m pytest tests/test_delegation_hook.py tests/test_learn_hook.py tests/test_council.py -q`
Expected: PASS

- [ ] **Step 5: Commit** — `Delegation: a sub-agent call is held one tier below the session's model`

---

### Task 3: The directive at session start

**Files:**
- Modify: `council/hook.py`, `docs/kurulum.md`, `docs/setup.md`
- Test: `tests/test_delegation_hook.py`

**Interfaces:**
- Consumes: `delegation_mode` (Task 1).
- Produces: `DELEGATION_BLOCK: str` — the text in the spec's section "Yönerge (oturum başı)", verbatim unless a wording fix is needed; the meaning and every bullet stay.

- [ ] **Step 1: Write the failing tests**

```python
def start(monkeypatch, capsys, fetch):
    import io
    monkeypatch.setattr(hook, "fetch", fetch)
    monkeypatch.setattr(hook, "load_config", lambda: {"url": "http://x", "token": "t"})
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"hook_event_name": "SessionStart", "session_id": "s1"})))
    assert hook.main() == 0
    return json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]

def test_the_block_fits_and_says_the_essentials():
    b = hook.DELEGATION_BLOCK
    assert b.startswith("[Delegation]") and len(b) <= 1200
    for phrase in ("fable/mythos -> opus", "opus -> sonnet", "sonnet -> haiku", "Do it yourself", "Hand off",
                   "Never higher", "Brief each worker", "Check a worker's result", "Do not redo",
                   "Tell the user in one line", "fork"):
        assert phrase in b

def test_session_start_ends_with_the_block(monkeypatch, capsys):
    text = start(monkeypatch, capsys, lambda cfg, payload: "MEMORY")
    assert "MEMORY" in text and text.endswith(hook.DELEGATION_BLOCK)

def test_the_block_is_sent_even_when_memory_is_unreachable(monkeypatch, capsys):
    def down(cfg, payload): raise OSError("down")
    text = start(monkeypatch, capsys, down)
    assert "unreachable" in text and text.endswith(hook.DELEGATION_BLOCK)

def test_advise_keeps_the_block_and_off_drops_it(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(hook, "delegation_mode", lambda: "advise")
    assert start(monkeypatch, capsys, lambda c, p: "MEMORY").endswith(hook.DELEGATION_BLOCK)
    monkeypatch.setattr(hook, "delegation_mode", lambda: "off")
    assert "[Delegation]" not in start(monkeypatch, capsys, lambda c, p: "MEMORY")

def test_a_message_does_not_carry_the_block(monkeypatch, capsys):
    import io
    monkeypatch.setattr(hook, "fetch", lambda c, p: "NOTES")
    monkeypatch.setattr(hook, "load_config", lambda: {"url": "http://x", "token": "t"})
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(
        {"hook_event_name": "UserPromptSubmit", "session_id": "s1", "prompt": "hello"})))
    hook.main()
    assert "[Delegation]" not in capsys.readouterr().out
```

- [ ] **Step 2: Run them and see them fail**

Run: `python -m pytest tests/test_delegation_hook.py -q -k "block or session_start or advise or message_does"`
Expected: FAIL, `module 'council.hook' has no attribute 'DELEGATION_BLOCK'`

- [ ] **Step 3: Add `DELEGATION_BLOCK` and append it** (after a blank line) to the `SessionStart` context in `main()`, in both the normal and the memory-unreachable branch, unless the mode is `off`. Update the module docstring's usage line to name the fourth event.

- [ ] **Step 4: Document the config key** in `docs/kurulum.md` (Turkish) and `docs/setup.md` (English), next to `review_every`: the three values, the default, and that `off` also stops the session-start directive. Do not name agent products.

- [ ] **Step 5: Run the tests and see them pass**

Run: `python -m pytest tests/test_delegation_hook.py tests/test_learn_hook.py -q`
Expected: PASS

- [ ] **Step 6: Commit** — `Delegation: the session is told when to hand work off and how to check it`

---

### Task 4: Registering the fourth hook

**Files:**
- Modify: `council/local.py`, `council/cli.py` (the `serve` branch, before `build(...)`)
- Test: `tests/test_local.py`

**Interfaces:**
- Produces:
  - `TOOL_HOOKS: dict[str, tuple[str, int]] = {"PreToolUse": ("Agent|Task", 5)}` (event → matcher, timeout). `HOOKS` keeps its three memory events and its meaning.
  - `Setup.tool_hooks_installed() -> bool`
  - `Setup.ensure_tool_hooks() -> bool` — adds the missing tool-hook entry to an existing installation; returns whether it wrote the settings file.
  - `status()` prints `hooks        installed|not installed` for the memory hooks exactly as today, then one new line: `delegation   enforce|advise|off`, with ` · hook not registered` appended when the mode is `enforce` and `tool_hooks_installed()` is false.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_local.py`; `make`, `home` and `hook_commands` exist there)

```python
def tool_entries(home):
    settings = json.loads((home / ".claude/settings.json").read_text())
    return [e for e in settings["hooks"].get("PreToolUse", []) if any(".council/hook.py" in h["command"] for h in e["hooks"])]

def test_install_registers_the_sub_agent_hook_with_its_matcher(home):
    (home / ".claude/settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "other-tool"}]}]}}))
    s = make(home)
    local.install(s); local.install(s)                                   # twice: no duplicate
    entries = tool_entries(home)
    assert len(entries) == 1 and entries[0]["matcher"] == "Agent|Task" and entries[0]["hooks"][0]["timeout"] == 5
    assert hook_commands(home, "PreToolUse")[0] == "other-tool"          # the user's own entry survives
    assert s.hooks_installed() and s.tool_hooks_installed()

def test_an_old_matcher_of_ours_is_refreshed_in_place(home):
    s = make(home); local.install(s)
    settings = json.loads((home / ".claude/settings.json").read_text())
    settings["hooks"]["PreToolUse"][0]["matcher"] = "Task"
    (home / ".claude/settings.json").write_text(json.dumps(settings))
    local.install(s)
    assert [e["matcher"] for e in tool_entries(home)] == ["Agent|Task"]

def three_hook_install(home):
    """An installation made by a release that knew only the memory hooks."""
    s = make(home); local.install(s)
    settings = json.loads((home / ".claude/settings.json").read_text())
    del settings["hooks"]["PreToolUse"]
    (home / ".claude/settings.json").write_text(json.dumps(settings))
    return s

def test_an_older_installation_still_counts_as_installed_and_gets_the_hook_added(home):
    s = three_hook_install(home)
    assert s.hooks_installed() and not s.tool_hooks_installed()
    assert s.ensure_tool_hooks() is True and s.tool_hooks_installed()
    assert s.ensure_tool_hooks() is False                                 # nothing left to do

def test_ensure_leaves_a_computer_without_our_hooks_alone(home):
    (home / ".claude/settings.json").write_text(json.dumps({"hooks": {"Stop": [
        {"hooks": [{"type": "command", "command": "other-tool"}]}]}}))
    before = (home / ".claude/settings.json").read_text()
    assert make(home).ensure_tool_hooks() is False
    assert (home / ".claude/settings.json").read_text() == before

def test_ensure_leaves_invalid_settings_alone(home):
    s = three_hook_install(home)
    (home / ".claude/settings.json").write_text("{not json")
    assert s.ensure_tool_hooks() is False and (home / ".claude/settings.json").read_text() == "{not json"

def test_uninstall_removes_the_sub_agent_hook_and_keeps_the_users(home):
    (home / ".claude/settings.json").write_text(json.dumps({"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "other-tool"}]}]}}))
    s = make(home); local.install(s); local.uninstall(s)
    assert json.loads((home / ".claude/settings.json").read_text())["hooks"] == {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "other-tool"}]}]}

def test_status_reports_delegation_on_its_own_line(home):
    s = three_hook_install(home)
    said = []; s.say = said.append
    local.status(s)
    text = "\n".join(said)
    assert "hooks        installed" in text and "delegation   enforce · hook not registered" in text
    s.ensure_tool_hooks()
    cfg = json.loads((home / ".config/council/config.json").read_text())
    (home / ".config/council/config.json").write_text(json.dumps({**cfg, "delegation": "off"}))
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
```

- [ ] **Step 2: Run them and see them fail**

Run: `python -m pytest tests/test_local.py -q -k "sub_agent or matcher or older_installation or ensure or delegation or service_adds"`
Expected: FAIL, `'Setup' object has no attribute 'tool_hooks_installed'`

- [ ] **Step 3: Implement.** In `connect()`, register `TOOL_HOOKS` beside `HOOKS`; an entry of ours is found by `HOOK_MARK` in its command, its command and matcher are refreshed in place, a missing one is appended as `{"matcher": ..., "hooks": [{"type": "command", "command": ..., "timeout": ...}]}`. `ensure_tool_hooks()` acts only when the settings file is valid JSON, `hooks_installed()` is true and the tool hook is missing; it backs the file up once (`_backup_once`) before writing. `disconnect()` already removes our commands from every event; change it only if a test fails. In `cli.py`'s `serve` branch call `ensure_tool_hooks()` when `Setup(data, port=a.port).service_installed()` is true, inside `try/except Exception: pass`: a hand-run or system-wide server (the project owner's own server is one) must not edit anybody's settings. The status line reads the mode with the same rule as the hook (`enforce` unless the config says `advise` or `off`).

- [ ] **Step 4: Run the tests and see them pass**

Run: `python -m pytest tests/test_local.py -q`
Expected: PASS

- [ ] **Step 5: Commit** — `Delegation: the installer registers the sub-agent hook, and an older installation gets it at the next start`

---

### Task 5: The report

**Files:**
- Create: `council/delegation.py`
- Modify: `council/cli.py` (new sub-command, handled before the memory is opened, next to the `install`/`status` branch; it needs no vault)
- Test: `tests/test_delegation_report.py` (create)

**Interfaces:**
- Consumes: nothing from the hook at run time except its tier rule; `council/delegation.py` may `from .hook import tier`.
- Produces:
  - `PRICES: dict[int, dict[str, float]]` keyed by tier, USD per million tokens, keys `input`, `output`, `cache_read`, `cache_write`; and `PRICES_AS_OF: str`. Known list prices (2026-11-03): tier 4 input 8.00, output 40.00, cache read 0.20; tier 3 input 4.00, output 20.00, cache read 0.20; tier 2 input 2.00, output 10.00, cache read 0.10; tier 1 input 0.10, output 0.50, cache read 0.01. Take `cache_write` for each tier from Anthropic's pricing page at build time and set `PRICES_AS_OF` to that day; if the page cannot be read, use 1.25 × input and say so in a comment.
  - `summarise(projects: Path, log: Path, days: float, now: float | None = None) -> dict`
  - `render(summary: dict) -> str`
  - CLI: `council delegation report [--days 14] [--json] [--projects DIR] [--log FILE]`; defaults `~/.claude/projects` and `~/.council/state/delegation.jsonl`; exit code 0.
- Record layout (verified on the owner's Mac): a session is `<projects>/<project>/<session>.jsonl`; its sub-agents are `<projects>/<project>/<session>/subagents/agent-<id>.jsonl` with `agent-<id>.meta.json` beside each. Lines with `type == "assistant"` carry `message.id`, `message.model`, `message.usage` (`input_tokens`, `output_tokens`, `cache_read_input_tokens`, `cache_creation_input_tokens`), `message.content` (tool calls are parts with `type == "tool_use"`) and a top-level ISO `timestamp`. The same `message.id` repeats on several lines: count its usage once. `meta.json` gives `agentType` and the *requested* model only; the model a sub-agent really ran on is the `message.model` of its own lines.
- `summarise` returns `{"days": float, "prices_as_of": str, "tiers": {<main tier as str>: T}}` where `T` is:
  `{"sessions": int, "agents": int, "hook": {<reason>: int}, "models": {<model id>: {"input": int, "output": int, "cache_read": int, "cache_write": int, "cost": float}}, "cost": float, "below_share": float, "violations": int, "forks": int, "small": int, "small_share": float, "estimated_saving": float}`.
  - A session counts when its record was modified within `days`. Its main tier is the tier of its last assistant model; a session whose tier is 0 is skipped.
  - `models` holds the main session and its sub-agents together; `cost` is priced by each model's own tier.
  - `below_share` = cost spent on tiers below the main tier ÷ `cost` (0.0 when `cost` is 0).
  - A sub-agent's comparison point is the main record's last assistant model before the sub-agent's first timestamp (the session's first model when none is earlier). `violations` counts sub-agents whose own tier is above the ceiling `max(that tier - 1, 1)` (the hook's rule), except those whose `agentType` is `fork`, which go to `forks`. A sub-agent whose own tier is 0 is counted in `agents` and `models` (priced at 0) but is never a violation.
  - `small` counts sub-agents that made fewer than 5 tool calls; `small_share` = `small` ÷ `agents`.
  - `estimated_saving` = what the sub-agents' tokens would cost at the main tier's prices minus what they cost at their own. It is an upper-bound estimate and `render` must label it so.
  - `hook` counts decision-log rows whose `session` matches the first 16 characters of a counted session id.

- [ ] **Step 1: Write the failing tests**

```python
import datetime as dt
import json
import os
import pytest
from council import cli, delegation
from council.delegation import PRICES, summarise

M = 1_000_000
FABLE, OPUS, SONNET = "claude-fable-5-2", "claude-opus-5-5", "claude-sonnet-5-5"
SID = "a" * 36

def iso(t): return dt.datetime.fromtimestamp(t, dt.timezone.utc).isoformat().replace("+00:00", "Z")

def line(model, mid, t, tools=0, **usage):
    return {"type": "assistant", "timestamp": iso(t),
            "message": {"id": mid, "model": model, "usage": usage, "content": [{"type": "tool_use", "name": "Read"}] * tools}}

def session(tree, lines, sid=SID):
    f = tree / "proj" / f"{sid}.jsonl"; f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("\n".join(x if isinstance(x, str) else json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    return f

def worker(tree, name, lines, meta={"agentType": "general-purpose"}, sid=SID):
    d = tree / "proj" / sid / "subagents"; d.mkdir(parents=True, exist_ok=True)
    (d / f"agent-{name}.jsonl").write_text("\n".join(x if isinstance(x, str) else json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    if meta is not None:
        (d / f"agent-{name}.meta.json").write_text(json.dumps(meta), encoding="utf-8")

def tier4(tree, log=None):
    return summarise(tree, log or tree / "none.jsonl", days=14)["tiers"]["4"]

def test_tokens_are_counted_once_per_message_and_priced_by_tier(tmp_path):
    session(tmp_path, [line(FABLE, "m1", 10, output_tokens=1000), line(FABLE, "m1", 11, output_tokens=1000)])
    worker(tmp_path, "w", [line(OPUS, "w1", 20, input_tokens=M, cache_read_input_tokens=M, cache_creation_input_tokens=M)])
    t = tier4(tmp_path)
    assert t["sessions"] == 1 and t["agents"] == 1 and t["models"][FABLE]["output"] == 1000
    opus = PRICES[3]["input"] + PRICES[3]["cache_read"] + PRICES[3]["cache_write"]
    assert t["models"][OPUS]["cost"] == pytest.approx(opus)
    assert t["cost"] == pytest.approx(opus + 1000 / M * PRICES[4]["output"])
    assert t["below_share"] == pytest.approx(opus / t["cost"])

def test_a_worker_above_the_ceiling_is_a_violation_and_a_fork_is_counted_apart(tmp_path):
    session(tmp_path, [line(FABLE, "m1", 10, output_tokens=1)])
    worker(tmp_path, "ok", [line(OPUS, "a", 20, output_tokens=1)])
    worker(tmp_path, "bad", [line(FABLE, "b", 20, output_tokens=1)])
    worker(tmp_path, "fork", [line(FABLE, "c", 20, output_tokens=1)], meta={"agentType": "fork"})
    worker(tmp_path, "odd", [line("gpt-9", "d", 20, output_tokens=1)], meta=None)       # unknown model, no meta file
    t = tier4(tmp_path)
    assert (t["agents"], t["violations"], t["forks"]) == (4, 1, 1)

def test_the_comparison_point_follows_a_model_switch(tmp_path):
    session(tmp_path, [line(OPUS, "m1", 0, output_tokens=1), line(FABLE, "m2", 100, output_tokens=1)])
    worker(tmp_path, "early", [line(OPUS, "a", 50, output_tokens=1)])      # main was Opus then: Opus is above the ceiling
    worker(tmp_path, "late", [line(OPUS, "b", 150, output_tokens=1)])      # main is Fable now: Opus is the ceiling
    assert tier4(tmp_path)["violations"] == 1                                # the session is filed under its last model

def test_small_runs_and_the_estimate(tmp_path):
    session(tmp_path, [line(FABLE, "m1", 10, output_tokens=1)])
    worker(tmp_path, "small", [line(SONNET, "a", 20, tools=2, output_tokens=M)])
    worker(tmp_path, "big", [line(SONNET, "b", 20, tools=5), line(SONNET, "c", 21, tools=4)])
    t = tier4(tmp_path)
    assert t["small"] == 1 and t["small_share"] == 0.5
    assert t["estimated_saving"] == pytest.approx(PRICES[4]["output"] - PRICES[2]["output"])

def test_hook_decisions_are_joined_by_session_and_old_sessions_are_left_out(tmp_path):
    session(tmp_path, [line(FABLE, "m1", 10, output_tokens=1)])
    old = session(tmp_path, [line(FABLE, "m9", 10, output_tokens=1)], sid="b" * 36)
    os.utime(old, (1, 1))
    log = tmp_path / "d.jsonl"
    log.write_text("\n".join([json.dumps({"session": SID[:16], "reason": r}) for r in ("set", "set", "kept")]
                             + [json.dumps({"session": "zzz", "reason": "set"}), "{cut"]) + "\n", encoding="utf-8")
    t = tier4(tmp_path, log)
    assert t["sessions"] == 1 and t["hook"] == {"set": 2, "kept": 1}

def test_broken_lines_and_unrankable_sessions_do_not_stop_the_report(tmp_path):
    session(tmp_path, [line(FABLE, "m1", 10, output_tokens=5), '{"type": "assistant", "message": {"id": "m2", "mo'])
    session(tmp_path, [line("gpt-9", "x", 10, output_tokens=5)], sid="c" * 36)
    tiers = summarise(tmp_path, tmp_path / "none.jsonl", days=14)["tiers"]
    assert list(tiers) == ["4"] and tiers["4"]["models"][FABLE]["output"] == 5

def test_the_command_prints_a_report_and_json(tmp_path, capsys):
    args = ["delegation", "report", "--projects", str(tmp_path), "--log", str(tmp_path / "none.jsonl")]
    assert cli.main(args) == 0 and "no sessions in the last 14 days" in capsys.readouterr().out
    session(tmp_path, [line(FABLE, "m1", 10, output_tokens=1)])
    worker(tmp_path, "w", [line(OPUS, "a", 20, output_tokens=1)])
    assert cli.main(args) == 0
    text = capsys.readouterr().out
    assert "upper-bound estimate" in text and delegation.PRICES_AS_OF in text and OPUS in text
    assert cli.main(args + ["--json"]) == 0
    assert json.loads(capsys.readouterr().out)["tiers"]["4"]["agents"] == 1
```

- [ ] **Step 2: Run them and see them fail**

Run: `python -m pytest tests/test_delegation_report.py -q`
Expected: FAIL, `No module named 'council.delegation'`

- [ ] **Step 3: Implement `council/delegation.py` and the sub-command.** Read records line by line (they can be hundreds of megabytes); never print record contents. `render` shows, per main tier: sessions and sub-agent calls; the hook's reasons; a row per model with tokens and list-price cost; the share spent below the main tier; violations and forks; the small-run share; the estimate with the words "upper-bound estimate"; and the date of the prices with a note that these are list prices used as weights, not a bill.

- [ ] **Step 4: Run the tests and see them pass**

Run: `python -m pytest tests/test_delegation_report.py -q`
Expected: PASS

- [ ] **Step 5: Run the report once on this computer's real records** (read-only) and paste its output into the task report: `python -m council.cli delegation report --days 30`. Expected: main tier 4 present, a non-zero violations count (the baseline before the feature is switched on).

- [ ] **Step 6: Commit** — `Delegation: a report of what each model spent and whether the ceiling held`

---

### Task 6: The whole branch

- [ ] **Step 1: Run every test:** `python -m pytest -q` — expected: all pass, none skipped that passed on `main`.
- [ ] **Step 2: Check the copied hook stands alone:** `python -I -c "import runpy, sys; sys.argv=['hook.py']; runpy.run_path('council/hook.py')"  < /dev/null` exits 0 and prints nothing; `grep -n "^from \.\|^import council\|from council" council/hook.py` prints nothing.
- [ ] **Step 3: Check the untouched files:** `git diff --stat main -- council/server.py council/context.py council/learn.py council/panel` prints nothing.
- [ ] **Step 4: Update the spec's status line** to say what was built, the branch head and the test count, and commit.

## Gates (the owner decides each one; none is part of a task)

1. Pushing the branch so the tests run on Linux, macOS and Windows.
2. Switching it on on the owner's Mac: copy `council/hook.py` to `~/.council/hook.py` and add the `PreToolUse` entry to `~/.claude/settings.json` (backup first). The first real handed-off call in the desktop app is then checked against the decision log and the sub-agent's record (spec, Sonda item 5), and the date is noted for the 05.12 trial evaluation.
3. Switching it on for the assistant on the server (same two files under `/root`).
4. Two weeks of use, then the side-by-side trial on three real tasks (spec, "Ölçüm"): its cost is quoted before it starts.
5. Merging to `main` and releasing.
