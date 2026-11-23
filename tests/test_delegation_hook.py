import io
import json
import os
import subprocess
import sys
from pathlib import Path
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

def test_main_model_reads_the_request_line_before_any_reply_and_after_a_switch(tmp_path):
    request = lambda model: {"type": "api-request", "querySource": "sdk", "params": {"model": model}}
    assert hook.main_model(record(tmp_path, [{"type": "user"}, request("claude-haiku-5-5")])) == "claude-haiku-5-5"
    path = record(tmp_path, [request("claude-opus-5-5"), assistant("claude-opus-5-5"), request("claude-mythos-5-2")])
    assert hook.main_model(path) == "claude-mythos-5-2"
    assert hook.main_model(record(tmp_path, [assistant("claude-opus-5-5"), {"type": "api-request", "params": "x"}])) == "claude-opus-5-5"

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
        (tmp_path / "c.json").write_text(json.dumps(config), encoding="utf-8")
        monkeypatch.setattr(hook, "CONFIG", tmp_path / "c.json")
    assert hook.delegation_mode() == expected

@pytest.mark.parametrize("config, expected", [
    (None, "enforce"), ([], "enforce"), ("off", "enforce"), ({}, "enforce"), ({"delegation": "advise"}, "advise"),
    ({"delegation": "off"}, "off"), ({"delegation": "OFF"}, "enforce"), ({"delegation": ["off"]}, "enforce")])
def test_mode_of_is_one_pure_rule(config, expected):
    assert hook.mode_of(config) == expected

def test_main_model_gives_up_after_the_scan_limit(tmp_path, monkeypatch):
    pad = json.dumps({"type": "user", "message": {"content": "x" * 100}})
    path = record(tmp_path, [assistant("claude-opus-5-5")] + [pad] * 100)    # about 12 kB without a model line
    monkeypatch.setattr(hook, "CHUNK", 1000)
    monkeypatch.setattr(hook, "SCAN_LIMIT", 5000)
    assert hook.main_model(path) is None
    monkeypatch.setattr(hook, "SCAN_LIMIT", 1 << 20)
    assert hook.main_model(path) == "claude-opus-5-5"

@pytest.mark.parametrize("chunk", [7, 64, 100, 1000])
def test_main_model_parses_a_line_that_straddles_chunks_or_is_longer_than_one(tmp_path, monkeypatch, chunk):
    monkeypatch.setattr(hook, "CHUNK", chunk)
    long_reply = assistant("claude-opus-5-5", note="y" * 300)
    path = record(tmp_path, [assistant("claude-haiku-5-5"), {"type": "user"}, long_reply, {"type": "user"}])
    assert hook.main_model(path) == "claude-opus-5-5"

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
    ("claude-fable-5-2", {"subagent_type": "big"}, "opus", "lowered"),
    ("claude-opus-5-5", {"subagent_type": "mid"}, "sonnet", "lowered"),
    ("claude-fable-5-2", {"subagent_type": "cheap"}, None, "own-model"),
    ("claude-fable-5-2", {"subagent_type": "odd"}, None, "own-model"),
    ("claude-fable-5-2", {"subagent_type": "big", "model": "haiku"}, None, "kept"),
])
def test_decide(tmp_path, main, extra, model, reason):
    agents = tmp_path / ".claude" / "agents"; agents.mkdir(parents=True)
    for name, declared in (("big", "fable"), ("mid", "opus"), ("cheap", "haiku"), ("odd", "weird")):
        (agents / f"{name}.md").write_text(f"---\nname: {name}\nmodel: {declared}\n---\nbody\n", encoding="utf-8")
    new, why = hook.decide({**CALL, **extra}, main, home=tmp_path)
    assert why == reason
    assert (new or {}).get("model") == model

def test_a_changed_call_keeps_every_other_field_and_tells_the_worker_about_memory(tmp_path):
    new, _ = hook.decide({**CALL, "run_in_background": True, "extra": {"a": 1}}, "claude-fable-5-2", home=tmp_path)
    assert new["prompt"] == "do it\n\n" + hook.WORKER_NOTE
    assert {k: new[k] for k in ("description", "subagent_type", "run_in_background", "extra")} == \
           {"description": "d", "subagent_type": "general-purpose", "run_in_background": True, "extra": {"a": 1}}

def test_an_agent_file_says_which_model_a_custom_type_runs_on(tmp_path):
    agents = tmp_path / ".claude" / "agents"; agents.mkdir(parents=True)
    (agents / "cheap.md").write_text("---\nname: cheap\nmodel: haiku\n---\nbody\n", encoding="utf-8")
    (agents / "quoted.md").write_text("\n---\nname: quoted\nmodel: \"opus\"\n---\n", encoding="utf-8")
    (agents / "plain.md").write_text("---\nname: plain\n---\nbody\n", encoding="utf-8")
    (agents / "same.md").write_text("---\nname: same\nmodel: inherit\n---\nbody\n", encoding="utf-8")
    project = tmp_path / "proj"; (project / ".claude" / "agents").mkdir(parents=True)
    (project / ".claude" / "agents" / "local.md").write_text("---\nname: local\n---\n", encoding="utf-8")
    (project / ".claude" / "agents" / "cheap.md").write_text("---\nmodel: sonnet\n---\n", encoding="utf-8")
    assert hook.declared_model("cheap", "", home=tmp_path) == (True, "haiku")
    assert hook.declared_model("cheap", str(project), home=tmp_path) == (True, "sonnet")   # the project's file first
    assert hook.declared_model("quoted", "", home=tmp_path) == (True, "opus")
    assert hook.declared_model("plain", "", home=tmp_path) == (True, None)
    assert hook.declared_model("same", "", home=tmp_path) == (True, None)
    assert hook.declared_model("local", str(project), home=tmp_path) == (True, None)
    assert hook.declared_model("general-purpose", "", home=tmp_path) == (True, None)        # built-in, inherits
    assert hook.declared_model("missing", "", home=tmp_path) == (False, None)
    assert hook.declared_model("someone-elses:agent", "", home=tmp_path) == (False, None)   # unknown type: hands off

def test_front_matter_is_only_at_the_top_of_the_file(tmp_path):
    agents = tmp_path / ".claude" / "agents"; agents.mkdir(parents=True)
    (agents / "ruled.md").write_text("# Ruled\n\nSome text.\n\n---\nmodel: haiku\n---\n\nMore.\n", encoding="utf-8")
    assert hook.declared_model("ruled", "", home=tmp_path) == (True, None)
    new, why = hook.decide({**CALL, "subagent_type": "ruled"}, "claude-fable-5-2", home=tmp_path)
    assert (new["model"], why) == ("opus", "set")

def event(tmp_path, main="claude-fable-5-2", **tool_input):
    return {"hook_event_name": "PreToolUse", "tool_name": "Agent", "session_id": "s" * 40, "cwd": str(tmp_path),
            "tool_use_id": "toolu_1", "transcript_path": record(tmp_path, [assistant(main)]),
            "tool_input": {**CALL, **tool_input}}

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
    assert lines == [{"ts": lines[0]["ts"], "session": "s" * 16, "tool_use_id": "toolu_1", "type": "general-purpose",
                      "asked": None, "model": "opus", "main": "claude-fable-5-2", "reason": "set"}]
    assert isinstance(lines[0]["ts"], float)

def test_the_handler_is_silent_when_nothing_changes_but_still_logs(tmp_path, monkeypatch, capsys):
    out, lines = run_check(tmp_path, monkeypatch, capsys, event(tmp_path, model="sonnet"))
    assert out is None and lines[0]["reason"] == "kept" and lines[0]["model"] is None and lines[0]["asked"] == "sonnet"

@pytest.mark.parametrize("mode", ["advise", "off"])
def test_the_handler_does_nothing_unless_enforcing(tmp_path, monkeypatch, capsys, mode):
    (tmp_path / "c.json").write_text(json.dumps({"delegation": mode}), encoding="utf-8")
    monkeypatch.setattr(hook, "CONFIG", tmp_path / "c.json")
    out, lines = run_check(tmp_path, monkeypatch, capsys, event(tmp_path))
    assert out is None and lines[0]["reason"] == mode and lines[0]["tool_use_id"] == "toolu_1"

def test_other_tools_and_broken_events_pass_untouched(tmp_path, monkeypatch, capsys):
    for ev in ({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}},
               {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": "not a dict"},
               {"hook_event_name": "PreToolUse", "tool_name": "Agent"}):
        out, lines = run_check(tmp_path, monkeypatch, capsys, ev)
        assert out is None
        assert lines == []

def test_the_old_tool_name_is_handled_too(tmp_path, monkeypatch, capsys):
    out, _ = run_check(tmp_path, monkeypatch, capsys, {**event(tmp_path), "tool_name": "Task"})
    assert out["hookSpecificOutput"]["updatedInput"]["model"] == "opus"

def stdin(text):
    """A stand-in for piped stdin: the hook reads its bytes."""
    return io.TextIOWrapper(io.BytesIO(text.encode("utf-8")), encoding="utf-8")

def test_main_never_fails_a_tool_call(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(hook, "delegation_check", lambda ev: 1 / 0)
    monkeypatch.setattr("sys.stdin", stdin(json.dumps(event(tmp_path))))
    assert hook.main() == 0 and capsys.readouterr().out == ""

HOOK_FILE = Path(hook.__file__)

def run_hook_file(tmp_path, data: bytes):
    """The hook file run on its own, as the assistant runs it, with nothing real in reach. Its text streams get
    a Windows code page, as on a Turkish Windows machine, so reading stdin as text would garble or fail."""
    env = {**os.environ, "HOME": str(tmp_path), "USERPROFILE": str(tmp_path),
           "COUNCIL_CONFIG": str(tmp_path / "no-config.json"), "PYTHONIOENCODING": "cp1254:strict"}
    return subprocess.run([sys.executable, str(HOOK_FILE)], input=data, capture_output=True, env=env, timeout=60)

def test_the_hook_file_reads_its_input_as_utf8_bytes(tmp_path):
    text = "Şu dosyayı özetle: çığ, öğüt, İstanbul 🙂"
    data = json.dumps(event(tmp_path, prompt=text), ensure_ascii=False).encode("utf-8")
    done = run_hook_file(tmp_path, data)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["hookSpecificOutput"]["updatedInput"]["prompt"].startswith(text)

def test_the_hook_file_ignores_input_that_is_not_utf8(tmp_path):
    done = run_hook_file(tmp_path, b"\x81\x8d{")
    assert done.returncode == 0 and done.stdout == b"", done.stderr

def test_parallel_decisions_are_whole_lines(tmp_path, monkeypatch):
    import threading
    monkeypatch.setattr(hook, "DELEGATION_LOG", tmp_path / "d.jsonl")
    threads = [threading.Thread(target=hook.log_decision, args=({"n": i, "pad": "x" * 2000},)) for i in range(40)]
    [t.start() for t in threads]; [t.join() for t in threads]
    rows = [json.loads(x) for x in (tmp_path / "d.jsonl").read_text(encoding="utf-8").splitlines()]
    assert sorted(r["n"] for r in rows) == list(range(40))

def test_the_log_is_trimmed_to_its_newer_half_and_stays_whole(tmp_path, monkeypatch):
    log = tmp_path / "d.jsonl"
    monkeypatch.setattr(hook, "DELEGATION_LOG", log)
    monkeypatch.setattr(hook, "LOG_LIMIT", 10_000)
    for i in range(200):                                          # about 60 bytes a row: several trims
        hook.log_decision({"n": i, "pad": "x" * 40})
        assert log.stat().st_size <= hook.LOG_LIMIT
    rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    assert rows[-1]["n"] == 199 and [r["n"] for r in rows] == list(range(rows[0]["n"], 200))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["d.jsonl"]            # no temp file left behind

# Appends are not atomic across processes on Windows; a lost log row there is accepted.
@pytest.mark.skipif(os.name == "nt", reason="appends are not atomic across processes on Windows")
def test_processes_appending_at_once_leave_whole_lines(tmp_path):
    data = json.dumps(event(tmp_path)).encode("utf-8")
    env = {**os.environ, "HOME": str(tmp_path), "USERPROFILE": str(tmp_path),
           "COUNCIL_CONFIG": str(tmp_path / "no-config.json")}
    procs = [subprocess.Popen([sys.executable, str(HOOK_FILE)], stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, env=env) for _ in range(12)]
    for p in procs:
        p.stdin.write(data); p.stdin.close()
    assert all(p.wait(timeout=60) == 0 for p in procs)
    lines = (tmp_path / ".council" / "state" / "delegation.jsonl").read_text(encoding="utf-8").splitlines()
    rows = [json.loads(x) for x in lines]
    assert len(rows) == 12 and all(r["reason"] == "set" for r in rows)

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "pretooluse_agent.json").read_text(encoding="utf-8"))

def real(tmp_path, key):
    return {**FIXTURE[key], "cwd": str(tmp_path), "transcript_path": record(tmp_path, [assistant("claude-fable-5-2")])}

def test_a_real_input_is_rewritten_and_keeps_its_other_fields(tmp_path, monkeypatch, capsys):
    out, _ = run_check(tmp_path, monkeypatch, capsys, real(tmp_path, "main"))
    new, old = out["hookSpecificOutput"]["updatedInput"], FIXTURE["main"]["tool_input"]
    assert new["model"] == "opus" and new["prompt"].startswith(old["prompt"])
    assert {k: new[k] for k in old if k != "prompt"} == {k: v for k, v in old.items() if k != "prompt"}

def test_a_call_from_inside_a_sub_agent_is_left_alone(tmp_path, monkeypatch, capsys):
    out, lines = run_check(tmp_path, monkeypatch, capsys, real(tmp_path, "nested"))   # the input carries agent_id
    assert out is None and lines[0]["reason"] == "nested"


def start(monkeypatch, capsys, fetch):
    monkeypatch.setattr(hook, "fetch", fetch)
    monkeypatch.setattr(hook, "load_config", lambda: {"url": "http://x", "token": "t"})
    monkeypatch.setattr("sys.stdin", stdin(json.dumps({"hook_event_name": "SessionStart", "session_id": "s1"})))
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
    assert "MEMORY" in text and text.endswith("\n\n" + hook.DELEGATION_BLOCK)

def test_the_block_is_sent_even_when_memory_is_unreachable(monkeypatch, capsys):
    def down(cfg, payload): raise OSError("down")
    text = start(monkeypatch, capsys, down)
    assert "unreachable" in text and text.endswith("\n\n" + hook.DELEGATION_BLOCK)

def test_advise_keeps_the_block_and_off_drops_it(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(hook, "delegation_mode", lambda: "advise")
    assert start(monkeypatch, capsys, lambda c, p: "MEMORY").endswith(hook.DELEGATION_BLOCK)
    monkeypatch.setattr(hook, "delegation_mode", lambda: "off")
    assert "[Delegation]" not in start(monkeypatch, capsys, lambda c, p: "MEMORY")

def test_a_message_does_not_carry_the_block(monkeypatch, capsys):
    monkeypatch.setattr(hook, "fetch", lambda c, p: "NOTES")
    monkeypatch.setattr(hook, "load_config", lambda: {"url": "http://x", "token": "t"})
    monkeypatch.setattr("sys.stdin", stdin(json.dumps(
        {"hook_event_name": "UserPromptSubmit", "session_id": "s1", "prompt": "hello"})))
    hook.main()
    assert "[Delegation]" not in capsys.readouterr().out
