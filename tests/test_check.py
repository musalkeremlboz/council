import json

import pytest

from council import check, cli
from council.store import Store


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "data")
    s.write("projects/havuz/kurs.md", "# Kurs açılışı\n\nKurs açarken önce proje, sonra federasyon seçilir.")
    s.write("projects/havuz/turnike.md", "# Turnike\n\nTurnike kartı okumazsa kayıt tarihine bakılır.")
    s.write("projects/ev/kira.md", "# Kira\n\nKira her ayın yirmi beşinde ödenir.")
    return s


def put(store, path, text):
    """Write a note whether or not the store already has one of that name (a new store starts with a few)."""
    store.write(path, text, expected_sha=store.read(path).sha if store.exists(path) else "")


# ---------- questions ----------

def test_a_question_is_saved_with_its_notes_and_a_date_and_can_be_removed(store):
    q = check.add_question(store, "  kurs nasıl açılıyordu  ", ["projects/havuz/kurs.md", "/projects/havuz/kurs.md"])
    assert q["question"] == "kurs nasıl açılıyordu" and q["expect"] == ["projects/havuz/kurs.md"]
    assert len(q["added"]) == 10 and q["added"][4] == "-"
    saved = json.loads((store.data / "questions.json").read_text(encoding="utf-8"))
    assert saved == [q]
    assert check.questions(store) == [q]
    assert check.remove_question(store, "Kurs nasıl açılıyordu ") is True
    assert check.questions(store) == [] and check.remove_question(store, "kurs nasıl açılıyordu") is False


def test_adding_the_same_question_again_replaces_it(store):
    check.add_question(store, "kira ne zaman", ["projects/ev/kira.md"])
    check.add_question(store, "Kira ne zaman", ["projects/ev/kira.md", "projects/havuz/kurs.md"])
    got = check.questions(store)
    assert len(got) == 1 and got[0]["expect"] == ["projects/ev/kira.md", "projects/havuz/kurs.md"]


@pytest.mark.parametrize("question, paths", [
    ("", ["projects/ev/kira.md"]), ("   ", ["projects/ev/kira.md"]),      # nothing to ask
    ("kira ne zaman", []),                                              # nothing expected
    ("kira ne zaman", ["projects/ev/yok.md"]),                          # no such note
    ("kira ne zaman", ["../etc/passwd.md"]),                            # refused by the store
])
def test_a_question_needs_text_and_notes_that_exist(store, question, paths):
    with pytest.raises(check.CheckError):
        check.add_question(store, question, paths)
    assert not (store.data / "questions.json").exists()


def test_an_unreadable_questions_file_is_reported_not_replaced(store):
    (store.data / "questions.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(check.CheckError):
        check.questions(store)
    with pytest.raises(check.CheckError):
        check.add_question(store, "kira ne zaman", ["projects/ev/kira.md"])
    assert (store.data / "questions.json").read_text(encoding="utf-8") == "{not json"


# ---------- search report ----------

def test_search_report_counts_both_ways_and_says_what_came_instead(store):
    check.add_question(store, "kurs açarken ne seçilir", ["projects/havuz/kurs.md"])
    check.add_question(store, "turnike kartı okumuyor", ["projects/ev/kira.md"])          # the wrong note is expected
    r = check.search_report(store)
    assert (r["questions"], r["measured"], r["auto"], r["search"]) == (2, 2, 1, 1)
    assert r["gone"] == []
    [miss] = r["missed"]
    assert miss["question"] == "turnike kartı okumuyor" and miss["expect"] == ["projects/ev/kira.md"]
    assert miss["auto"] is False and miss["search"] is False
    assert miss["got_auto"][0] == "projects/havuz/turnike.md" and miss["got_search"][0] == "projects/havuz/turnike.md"


def test_any_of_the_expected_notes_is_a_hit(store):
    check.add_question(store, "kira ne zaman ödenir", ["projects/havuz/kurs.md", "projects/ev/kira.md"])
    r = check.search_report(store)
    assert (r["auto"], r["search"], r["missed"]) == (1, 1, [])


def test_a_note_always_in_context_counts_as_coming_by_itself(store):
    put(store, "core.md", "# Çekirdek\n\nKısa cevap ver.")
    check.add_question(store, "zzzz qqqq", ["core.md"])                                    # matches nothing
    r = check.search_report(store)
    assert r["auto"] == 1 and r["search"] == 0
    [miss] = r["missed"]
    assert miss["auto"] is True and miss["search"] is False


def test_a_question_whose_note_is_gone_is_listed_apart_not_as_a_miss(store):
    check.add_question(store, "kira ne zaman ödenir", ["projects/ev/kira.md"])
    check.add_question(store, "kurs açarken ne seçilir", ["projects/havuz/kurs.md"])
    store.remove("projects/ev/kira.md")
    r = check.search_report(store)
    assert (r["questions"], r["measured"], r["auto"], r["search"]) == (2, 1, 1, 1)
    assert r["gone"] == [{"question": "kira ne zaman ödenir", "expect": ["projects/ev/kira.md"]}] and r["missed"] == []


def test_search_report_changes_nothing(store):
    check.add_question(store, "kurs açarken ne seçilir", ["projects/havuz/kurs.md"])
    before = store._git("rev-parse", "HEAD").stdout, (store.data / "questions.json").read_bytes()
    check.search_report(store); check.link_report(store)
    assert (store._git("rev-parse", "HEAD").stdout, (store.data / "questions.json").read_bytes()) == before
    assert not (store.data / "usage.sqlite3").exists()


def test_no_questions_is_an_empty_report(store):
    r = check.search_report(store)
    assert (r["questions"], r["measured"], r["auto"], r["search"], r["missed"], r["gone"]) == (0, 0, 0, 0, [], [])


# ---------- links ----------

def broken(store):
    return {(b["note"], b["target"]) for b in check.link_report(store)["broken"]}


def test_wiki_and_markdown_links_resolve_from_the_root_and_from_the_note(store):
    store.write("projects/havuz/project.md", "\n".join([
        "# Havuz",
        "[[projects/havuz/kurs]] [[projects/havuz/kurs.md]] [[kurs]] [[turnike|kart]] [[projects/ev/kira#Ödeme]]",
        "[kurs](kurs.md) [kira](../ev/kira.md) [kira](projects/ev/kira.md) [bölüm](kurs.md#adimlar) [boşluk](../ev/kira.md \"başlık\")",
        "[[projects/havuz/yok]] [[eski-not]] [eski](eski.md) [dış](../../disari.md)",
    ]))
    r = check.link_report(store)
    assert r["checked"] == 14
    assert broken(store) == {("projects/havuz/project.md", t) for t in
                             ("projects/havuz/yok", "eski-not", "eski.md", "../../disari.md")}


def test_what_is_not_a_link_to_a_note_is_not_checked(store):
    store.write("notes/a.md", "\n".join([
        "# A",
        "`[[yok-bir]]` ve ``[x](yok-iki.md)`` satır içi kod",
        "```", "[[yok-uc]]", "[x](yok-dort.md)", "```",
        "~~~text", "[[yok-bes]]", "~~~",
        "[site](https://example.com/a.md) [posta](mailto:a@example.com) [bölüm](#baslik) ![resim](sekil.png) [dosya](rapor.pdf)",
        "[[sekil.png]] `projects/yok/dosya.md`",
    ]))
    r = check.link_report(store)
    assert r["checked"] == 0 and r["broken"] == []


def test_history_notes_are_not_checked(store):
    for path in ("log/2026-11.md", "sessions/2026-11.md", "sessions.md"):
        put(store, path, "# Kayıt\n\n[[projects/havuz/eski-ad]]")
    put(store, "threads.md", "# Threads\n\n[[projects/havuz/eski-ad]]")
    assert broken(store) == {("threads.md", "projects/havuz/eski-ad")}


def test_a_broken_link_names_where_the_note_may_have_gone(store):
    store.write("projects/yeni/Testak.md", "# Testak\n\nkart")
    store.write("arsiv/Testak.md", "# Testak\n\neski")
    store.write("notes/a.md", "# A\n\n[[projects/eski/Testak]] [[projects/eski/Testak]] [x](../eski/Baska.md)")
    r = check.link_report(store)
    assert r["checked"] == 3
    assert r["broken"] == [
        {"note": "notes/a.md", "target": "../eski/Baska.md", "maybe": []},
        {"note": "notes/a.md", "target": "projects/eski/Testak", "maybe": ["arsiv/Testak.md", "projects/yeni/Testak.md"]},
    ]


def test_link_names_are_compared_exactly(store):
    store.write("notes/a.md", "# A\n\n[[projects/havuz/Kurs]] [[KURS]] [x](../projects/havuz/kurs.md)")
    assert broken(store) == {("notes/a.md", "projects/havuz/Kurs"), ("notes/a.md", "KURS")}


# ---------- words no note contains ----------

def test_absent_lists_the_content_words_no_note_contains(store):
    absent = store.index.absent
    assert absent("turnike kartı ve Testak ayarı nasıl") == ["Testak", "ayarı"]
    assert absent("turnikeler kartının") == []                      # other forms of words the notes have
    assert absent("ve ile bir bu") == [] and absent("") == [] and absent("a ! ?") == []
    assert absent("zebra Zebra zebralar testak") == ["zebra", "testak"]         # one per word, as first typed
    assert absent(" ".join(f"yok{i:02d}x" for i in range(30))) == [f"yok{i:02d}x" for i in range(8)]
    assert absent(" ".join(f"yok{i:02d}x" for i in range(30)), limit=2) == ["yok00x", "yok01x"]


@pytest.fixture
def search_tool(tmp_path, monkeypatch):
    """The council_search tool of a built server, called the way a client calls it, and the server's store."""
    import asyncio

    from council import server

    made = []
    real = server.MCPServer
    monkeypatch.setattr(server, "MCPServer", lambda *a, **k: made.append(real(*a, **k)) or made[-1])
    monkeypatch.setenv("COUNCIL_TOKEN", "t0k")
    _, store = server.build(str(tmp_path / "data"))
    store.write("projects/havuz/turnike.md", "# Turnike\n\nTurnike kartı okumazsa kayıt tarihine bakılır.")

    def call(query):
        result = asyncio.run(made[0].call_tool("council_search", {"query": query}))
        return json.loads(result.content[0].text)

    return call, store


def test_the_search_tool_answers_with_hits_and_the_words_not_found(search_tool):
    call, _ = search_tool
    got = call("turnike testak")
    assert [h["path"] for h in got["hits"]] == ["projects/havuz/turnike.md"] and got["not_found"] == ["testak"]
    got = call("turnike kartı")
    assert got["hits"] and got["not_found"] == []
    assert call("zzzz") == {"hits": [], "not_found": ["zzzz"]}


def test_a_failing_absent_check_does_not_fail_the_search(search_tool, monkeypatch, caplog):
    call, store = search_tool
    monkeypatch.setattr(type(store.index), "absent", lambda self, q, limit=8: 1 / 0)
    got = call("turnike testak")
    assert [h["path"] for h in got["hits"]] == ["projects/havuz/turnike.md"] and got["not_found"] == []
    assert "words not in memory left out" in caplog.text


# ---------- command line ----------

def run(store, *args):
    return cli.main(["--data", str(store.data), *args])


def test_check_prints_both_reports_and_fails_when_something_needs_attention(store, capsys):
    assert run(store, "check") == 0
    out = capsys.readouterr().out
    assert "search: no questions yet" in out and 'council check add "question" path/to/note.md' in out
    assert "links: 0 checked, 0 broken" in out

    assert run(store, "check", "add", "kurs açarken ne seçilir", "projects/havuz/kurs.md") == 0
    assert run(store, "check", "add", "turnike kartı okumuyor", "projects/ev/kira.md") == 0
    assert "saved" in capsys.readouterr().out
    store.write("notes/a.md", "# A\n\n[[projects/havuz/kurs]] [[projects/eski/turnike]]")
    assert run(store, "check") == 1
    out = capsys.readouterr().out
    assert "search: 2 questions · comes by itself 1/2 · found by search 1/2" in out
    assert 'missed: "turnike kartı okumuyor"' in out and "expected: projects/ev/kira.md" in out
    assert "by itself came: projects/havuz/turnike.md" in out and "search found: projects/havuz/turnike.md" in out
    assert "links: 2 checked, 1 broken" in out
    assert "notes/a.md → projects/eski/turnike  (maybe: projects/havuz/turnike.md)" in out


def test_check_parts_run_alone_and_gone_notes_are_named(store, capsys):
    run(store, "check", "add", "kira ne zaman ödenir", "projects/ev/kira.md")
    store.remove("projects/ev/kira.md")
    store.write("notes/a.md", "# A\n\n[[projects/yok/x]]")
    capsys.readouterr()
    assert run(store, "check", "search") == 1
    out = capsys.readouterr().out
    assert 'note gone: "kira ne zaman ödenir" (expected projects/ev/kira.md)' in out and "links:" not in out
    assert "search: 1 questions · 1 with no note left" in out
    assert run(store, "check", "links") == 1
    out = capsys.readouterr().out
    assert "links: 1 checked, 1 broken" in out and "search:" not in out
    assert run(store, "check", "remove", "kira ne zaman ödenir") == 0 and run(store, "check", "search") == 0
    assert run(store, "check", "remove", "kira ne zaman ödenir") == 1


def test_check_refuses_what_it_cannot_do(store, capsys):
    assert run(store, "check", "add", "kira ne zaman") == 2                       # no note named
    assert run(store, "check", "add", "kira ne zaman", "projects/ev/yok.md") == 2
    assert run(store, "check", "remove") == 2
    assert run(store, "check", "links", "fazla") == 2
    (store.data / "questions.json").write_text("[", encoding="utf-8")
    assert run(store, "check") == 2
    assert "questions.json" in capsys.readouterr().err


def test_search_command_names_the_words_no_note_contains(store, capsys):
    assert run(store, "search", "turnike testak") == 0
    out = capsys.readouterr().out
    assert "projects/havuz/turnike.md" in out and out.rstrip().endswith("no note contains: testak")
    run(store, "search", "turnike kartı")
    assert "no note contains" not in capsys.readouterr().out


# ---------- found by review ----------

def test_the_command_leaves_hand_edits_and_missing_notes_as_they_are(store, capsys):
    (store.vault / "projects/ev/kira.md").write_text("# Kira\n\nelle değişti [[yok]]", encoding="utf-8")
    (store.vault / "threads.md").unlink()
    commits = store._git("rev-list", "--count", "HEAD").stdout
    status = store._git("status", "--short").stdout
    for args in (("check",), ("check", "links"), ("check", "search"),
                 ("check", "add", "kurs açarken ne seçilir", "projects/havuz/kurs.md"),
                 ("check", "remove", "kurs açarken ne seçilir")):
        run(store, *args)
    assert "projects/ev/kira.md → yok" in capsys.readouterr().out          # the edit on disk is what is checked
    assert store._git("rev-list", "--count", "HEAD").stdout == commits
    assert store._git("status", "--short").stdout == status and not (store.vault / "threads.md").exists()


def test_a_question_is_saved_under_the_name_the_note_has(store):
    with pytest.raises(check.CheckError):
        check.add_question(store, "kurs açarken ne seçilir", ["Projects/Havuz/Kurs.md"])     # no note of that name
    import unicodedata
    nfd = unicodedata.normalize("NFD", "notes/çalışma.md")
    (store.vault / "notes").mkdir()
    (store.vault / nfd).write_text("# Çalışma\n\nÇalışma saatleri dokuzda başlar.", encoding="utf-8")
    store.index.sync(store.vault)
    on_disk = next(p for p in store.list() if p.startswith("notes/"))
    q = check.add_question(store, "çalışma saatleri", [unicodedata.normalize("NFC", "notes/çalışma.md")])
    assert q["expect"] == [on_disk]
    r = check.search_report(store)
    assert (r["auto"], r["search"], r["missed"], r["gone"]) == (1, 1, [], [])
    store.write("notes/b.md", "# B\n\n[[notes/" + unicodedata.normalize("NFC", "çalışma") + "]]")
    assert check.link_report(store)["broken"] == []


def test_a_renamed_note_is_gone_not_missed(store):
    check.add_question(store, "kira ne zaman ödenir", ["projects/ev/kira.md"])
    store.move("projects/ev/kira.md", "projects/ev/Kira-Odeme.md")
    r = check.search_report(store)
    assert r["measured"] == 0 and [g["expect"] for g in r["gone"]] == [["projects/ev/kira.md"]]


@pytest.mark.parametrize("text, expected", [
    ("```code``` satır başında kod\n[[yok-a]]", ["yok-a"]),                          # not a fence: the line goes on
    ("````\n```\n[[icte]]\n```\n````\n[[yok-b]]", ["yok-b"]),                         # a fence inside a longer one
    ("```\n[[icte]]\n````\n[[yok-c]]", ["yok-c"]),                                   # closed by a longer run
    ("~~~\n[[icte]]\n```\n[[icte2]]\n~~~\n[[yok-d]]", ["yok-d"]),                    # the other fence does not close it
    ("```\n[[icte]]\n", []),                                                         # never closed: code to the end
    ("`kod\ndevam [[icte]]` sonra [[yok-e]]", ["yok-e"]),                            # inline code over a line break
    ("bir ` işareti\n\n[[yok-f]] ve ` bir daha", ["yok-f"]),                         # not code: a paragraph apart
    ("\\`[[yok-k]]\\` ve `[[icte]]`", ["yok-k"]),                                    # an escaped backtick is not code
    ("| a | b |\n|---|---|\n| [[projects/havuz/kurs\\|K]] | [[yok-g\\|G]] |", ["yok-g"]),   # escaped pipe in a table
    ("[[Python 3.12]] [[rapor 2026.11]] [[sekil.PNG]] [[veri.csv]]", ["Python 3.12", "rapor 2026.11"]),
    ("[x](<projects/havuz/kurs.md>) [x](<yok h.md>) [x](yok-i.md 'başlık') [x](yok-j.md (başlık))",
     ["yok h.md", "yok-i.md", "yok-j.md"]),
    ("[x](//host/a.md) [x](kurs.md) [x](turnike.md)", ["kurs.md", "turnike.md"]),     # a bare name is for [[...]] only
])
def test_links_in_odd_markdown(store, text, expected):
    store.write("notes/a.md", "# A\n\n" + text)
    assert [b["target"] for b in check.link_report(store)["broken"]] == sorted(expected)


def test_questions_file_with_a_byte_order_mark_is_read_and_an_entry_without_notes_is_refused(store):
    entry = [{"question": "kira ne zaman ödenir", "expect": ["projects/ev/kira.md"], "added": "2026-11-22"}]
    (store.data / "questions.json").write_text(json.dumps(entry), encoding="utf-8-sig")
    assert check.questions(store) == entry
    (store.data / "questions.json").write_text(json.dumps([{"question": "x", "expect": []}]), encoding="utf-8")
    with pytest.raises(check.CheckError):
        check.questions(store)


# ---------- note search: stems and filler words ----------

def test_a_long_word_finds_its_other_long_forms(store):
    from council.index import build_query, note_query
    store.write("projects/x/kurulum.md", "# Kurulum\n\nYardımcının hafıza bağlantısı kuruldu.")
    assert [h["path"] for h in store.index.search("bağlanmasını")] == ["projects/x/kurulum.md"]
    assert store.index.absent("bağlanmasını yapılandırılmamış") == ["yapılandırılmamış"]
    assert note_query("bağlanmasını kartı turnikeler") == '"baglan"* OR "karti"* OR "turnik"*'
    # skills are matched with the older, longer stems: their thresholds were measured with them
    assert build_query("bağlanmasını kartı turnikeler") == '"baglanmas"* OR "karti"* OR "turnike"*'


def test_request_words_do_not_pick_notes(store):
    from council.index import build_query, note_query
    store.write("notes/istek.md", "# İstek\n\nBunu yapabiliriz, istiyorum; lütfen bana söyler misin.")
    said = "Turnike için bunu istiyorum, yapabiliriz, lütfen?"
    for content_only in (True, False):                                               # unasked and asked alike
        assert [h["path"] for h in store.index.search(said, content_only=content_only)] == ["projects/havuz/turnike.md"]
        assert note_query(said, content_only=content_only) == '"turni"*'
    only_such = "bunu istiyorum, lütfen"
    assert store.index.search(only_such, content_only=True) == []                    # nothing to send unasked
    assert [h["path"] for h in store.index.search(only_such)] == ["notes/istek.md"]  # a search uses what it was given
    assert note_query(only_such) == '"bunu"* OR "istiyo"* OR "lutfe"*' and note_query(only_such, content_only=True) == ""
    assert note_query("a ! ?") == "" and store.index.search("a ! ?") == []
    assert "istiyo" in build_query(said, content_only=True)                           # skill matching is untouched
    assert store.index.absent("bunu istiyorum lütfen") == []                          # nothing to report about them


# ---------- commands that only read ----------

def test_a_command_that_only_reads_commits_nothing_and_seeds_nothing(store, capsys):
    (store.vault / "projects/ev/kira.md").write_text("# Kira\n\nelle değişti", encoding="utf-8")
    (store.vault / "threads.md").unlink()
    commits = store._git("rev-list", "--count", "HEAD").stdout
    status = store._git("status", "--short").stdout
    for args in (("context", "kira"), ("search", "kira"), ("usage",), ("reindex",)):
        assert run(store, *args) == 0
    assert "projects/ev/kira.md" in capsys.readouterr().out               # the edit on disk is what is read
    assert store._git("rev-list", "--count", "HEAD").stdout == commits
    assert store._git("status", "--short").stdout == status and not (store.vault / "threads.md").exists()


@pytest.mark.parametrize("args", [("context",), ("search", "kira"), ("check",), ("usage",), ("reindex",),
                                  ("backup",), ("watch-size", "--notes", "1", "--title", "t")])
def test_a_folder_with_no_memory_is_refused_and_left_as_it_is(tmp_path, capsys, args):
    missing, empty = tmp_path / "yok", tmp_path / "bos"
    empty.mkdir()
    for data in (missing, empty):
        assert cli.main(["--data", str(data), *args]) == 2
        assert f"no memory at {data}" in capsys.readouterr().err
    assert not missing.exists() and not list(empty.iterdir())


WRITER = """
import sys
from council import check
from council.store import Store
store = Store(sys.argv[1], readonly=True)
for i in range(int(sys.argv[3])):
    check.add_question(store, f"soru {sys.argv[2]}-{i}", ["projects/ev/kira.md"])
"""


def test_questions_added_by_several_processes_at_once_are_all_kept(store):
    import subprocess
    import sys

    writers, each = 6, 15
    procs = [subprocess.Popen([sys.executable, "-c", WRITER, str(store.data), str(w), str(each)],
                              stderr=subprocess.PIPE, text=True) for w in range(writers)]
    errors = [p.communicate()[1] for p in procs]
    assert [p.returncode for p in procs] == [0] * writers, errors
    saved = {q["question"] for q in check.questions(store)}
    assert saved == {f"soru {w}-{i}" for w in range(writers) for i in range(each)}


# ---------- the questions travel with the backup ----------

def _backed_up(tmp_path, store):
    """Back the store up to a bare remote and return a fresh copy of what the remote holds."""
    import subprocess

    remote, copy = tmp_path / "remote.git", tmp_path / "copy"
    if not remote.exists():
        subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
        store._git("remote", "add", "backup", str(remote))
    assert store.backup()["ok"] is True
    subprocess.run(["git", "clone", "-q", "--branch", "main", str(remote), str(copy)], check=True)
    return copy


def test_the_backup_carries_the_saved_questions(tmp_path, store):
    check.add_question(store, "kira ne zaman ödenir", ["projects/ev/kira.md"])
    copy = _backed_up(tmp_path, store)
    kept = json.loads((copy / ".council/questions.json").read_text(encoding="utf-8"))
    assert [q["question"] for q in kept] == ["kira ne zaman ödenir"]


def test_the_copy_of_the_questions_in_the_vault_is_not_a_note(tmp_path, store):
    check.add_question(store, "kira ne zaman ödenir", ["projects/ev/kira.md"])
    _backed_up(tmp_path, store)
    assert not [p for p in store.list() if "question" in p]
    assert check.search_report(Store(store.data, readonly=True))["search"] == 1  # it does not answer for the note
    assert store._git("status", "--short").stdout == ""


def test_a_memory_restored_from_its_backup_has_its_questions(tmp_path, store):
    check.add_question(store, "kira ne zaman ödenir", ["projects/ev/kira.md"])
    copy = _backed_up(tmp_path, store)
    restored = tmp_path / "restored"
    restored.mkdir()
    copy.rename(restored / "vault")
    again = Store(restored, readonly=True)
    assert [q["question"] for q in check.questions(again)] == ["kira ne zaman ödenir"]
    check.add_question(again, "turnike okumazsa", ["projects/havuz/turnike.md"])   # saved where questions live
    assert len(json.loads((restored / "questions.json").read_text(encoding="utf-8"))) == 2


def test_a_backup_with_no_questions_adds_nothing_to_the_vault(tmp_path, store):
    copy = _backed_up(tmp_path, store)
    assert not (copy / ".council").exists() and not (store.vault / ".council").exists()


def test_a_later_backup_carries_the_questions_as_they_are_then(tmp_path, store):
    check.add_question(store, "kira ne zaman ödenir", ["projects/ev/kira.md"])
    _backed_up(tmp_path, store)
    check.add_question(store, "turnike okumazsa", ["projects/havuz/turnike.md"])
    assert store.backup()["ok"] is True
    kept = store._git("show", "HEAD:.council/questions.json").stdout
    assert "turnike okumazsa" in kept and store._git("status", "--short").stdout == ""
