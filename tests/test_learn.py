import datetime as dt, json, time
import pytest
from council import learn
from council.learn import Learning
from council.store import Conflict, Store, StoreError

@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "data")

def test_remove_and_move_keep_history_and_index(store):
    store.write("skills/a.md", "# A\n\nelma")
    store.move("skills/a.md", "skills/retired/a.md", "retire")
    assert "skills/retired/a.md" in store.list() and "skills/a.md" not in store.list()
    assert store.index.search("elma")[0]["path"] == "skills/retired/a.md"
    store.write("skills/b.md", "# B\n\nmuz")
    assert store.index.search("muz")[0]["path"] == "skills/b.md"
    with pytest.raises(Conflict):
        store.move("skills/retired/a.md", "skills/b.md")
    store.remove("skills/b.md", "undo")
    assert "skills/b.md" not in store.list() and store.index.search("muz") == []
    with pytest.raises(StoreError):
        store.remove("skills/b.md")
    log = store._git("log", "--format=%s").stdout
    assert "retire" in log and "undo" in log

def test_search_can_filter_paths(store):
    for i in range(12):
        store.write(f"notes/n{i}.md", "# N\n\nkiraz bahçesi")
    store.write("skills/k.md", "# K\n\nkiraz toplama")
    hits = store.index.search("kiraz", limit=2, where=lambda p: p.startswith("skills/"))
    assert [h["path"] for h in hits] == ["skills/k.md"]

SK = dict(when="Çalışan bir servisin üstüne yeniden kurulum yapılırken",
          steps="1. Eski işi durdur\n2. Bittiğini doğrula\n3. Yenisini yükle",
          learned_from="Yeniden kurulum 'Input/output error' verdi; bekleyince düzeldi.")

def test_new_skill_is_a_candidate_note_with_fixed_labels(store):
    out = Learning(store).write_skill("Servisi yeniden kurarken beklet", session="4cc0f9b3-a8bb", **SK)
    assert out["path"] == "skills/servisi-yeniden-kurarken-beklet.md" and out["status"] == "candidate"
    text = store.read(out["path"]).text
    assert text.startswith("# Servisi yeniden kurarken beklet\n")
    for label in ("- **When:** Çalışan bir servisin", "- **Status:** candidate", "- **Source:** ", "session 4cc0f9b3",
                  "## Steps\n", "## Learned from\n"):
        assert label in text
    assert "## Pitfalls" not in text                      # optional section, left out when empty
    assert learn.parse_skill(text)["when"] == SK["when"]
    assert "undo" in out["notice"]
    assert learn.is_skill(out["path"]) and not learn.is_retired(out["path"])

def test_project_skill_and_path_safety(store):
    L = Learning(store)
    assert L.write_skill("Kurs açma", project="Havuz İşi", **SK)["path"] == "projects/havuz-isi/skills/kurs-acma.md"
    assert learn.slug("../../etc/Şifre?") == "etc-sifre"
    for bad in ("", "///", "retired"):
        with pytest.raises(StoreError):
            L.write_skill(bad, **SK)
    assert not learn.is_skill("skills/retired/x.md") and learn.is_retired("projects/p/skills/retired/x.md")
    assert not learn.is_skill("notes/skills.md")

def test_validation_refuses_incomplete_oversized_and_secret(store):
    L = Learning(store)
    with pytest.raises(StoreError, match="learned_from"):
        L.write_skill("x", when="w", steps="s", learned_from="  ")
    with pytest.raises(StoreError, match="When"):
        L.write_skill("x", **{**SK, "when": "w" * 201})
    with pytest.raises(StoreError, match="4000"):
        L.write_skill("x", **{**SK, "steps": "s" * 4001})
    for secret in ("token = ghp_" + "a" * 36, "-----BEGIN OPENSSH PRIVATE KEY-----", "şifre: Hunter2hunter2",
                   "Authorization: Bearer " + "x" * 30):
        with pytest.raises(StoreError, match="secret"):
            L.write_skill("x", **{**SK, "steps": secret})
    assert store.list("skills/") == []
    assert learn.find_secret("Parolayı ortam değişkeninden oku") is None

def test_revising_needs_the_sha_and_keeps_status_and_source(store):
    L = Learning(store)
    first = L.write_skill("beklet", session="s-one", **SK)
    with pytest.raises(Conflict):                         # two writers: the second cannot overwrite
        L.write_skill("beklet", **SK)
    out = L.write_skill("beklet", expected_sha=first["sha"], session="s-two", **{**SK, "pitfalls": "- Yarış durumu"})
    text = store.read(out["path"]).text
    assert "session s-one" in text and "- **Revised:** " in text and "session s-two" in text and "## Pitfalls\n- Yarış" in text
    ledger = json.loads((store.data / "learning.json").read_text())["ledger"]
    assert [e["kind"] for e in ledger] == ["skill_new", "skill_edit"] and "Yarış" not in ledger[1]["before"]

def test_rewriting_a_retired_skill_brings_it_back(store):
    L = Learning(store)
    L.write_skill("beklet", **SK)
    store.move("skills/beklet.md", "skills/retired/beklet.md")
    out = L.write_skill("beklet", **SK)
    assert out["status"] == "candidate" and store.list("skills/") == ["skills/beklet.md"]

def test_state_file_is_read_fresh_and_a_broken_one_counts_as_empty(store):
    (store.data / "learning.json").write_text("{not json")
    a, b = Learning(store), Learning(store)               # two instances share one folder
    a.write_skill("bir", **SK)
    b.write_skill("iki", **SK)
    ledger = json.loads((store.data / "learning.json").read_text())["ledger"]
    assert [e["path"] for e in ledger] == ["skills/bir.md", "skills/iki.md"]

def test_comeback_ledger_keeps_the_retired_note_for_undo(store):
    L = Learning(store)
    L.write_skill("beklet", **SK)
    retired = store.move("skills/beklet.md", "skills/retired/beklet.md").text
    L.write_skill("beklet", **SK)
    ledger = json.loads((store.data / "learning.json").read_text())["ledger"]
    assert ledger[0]["before"] is None and ledger[0]["retired_path"] is None
    assert ledger[1]["kind"] == "skill_new"
    assert ledger[1]["before"] == retired and ledger[1]["retired_path"] == "skills/retired/beklet.md"

def test_comeback_never_leaves_the_skill_without_a_note(store, monkeypatch):
    L = Learning(store)
    L.write_skill("beklet", **SK)
    store.move("skills/beklet.md", "skills/retired/beklet.md")
    real_write = store.write
    seen = []
    def spy(path, *a, **k):
        seen.append(store.list("skills/"))                # state right before the new content lands
        return real_write(path, *a, **k)
    monkeypatch.setattr(store, "write", spy)
    L.write_skill("beklet", **SK)
    assert seen == [["skills/beklet.md"]]

def test_headings_and_multiline_when_are_refused(store):
    L = Learning(store)
    for field in ("steps", "pitfalls", "learned_from"):
        for line in ("# Başlık", "## Steps"):
            with pytest.raises(StoreError, match="heading"):
                L.write_skill("x", **{**SK, field: f"1. adım\n{line}\nson"})
    L.write_skill("x", **{**SK, "pitfalls": "### alt başlık serbest\n#etiket"})
    with pytest.raises(StoreError, match="When"):
        L.write_skill("y", **{**SK, "when": "bir\niki"})
    assert store.list("skills/") == ["skills/x.md"]

def test_render_and_parse_round_trip(store):
    text = learn.render_skill("Başlık", "Ne zaman", "1. a\n2. b", "Şundan öğrendim", "- tuzak",
                              "candidate", "2026-11-21, session abcd1234", "2026-11-22, session efgh5678")
    assert learn.parse_skill(text) == dict(
        title="Başlık", when="Ne zaman", status="candidate", source="2026-11-21, session abcd1234",
        revised="2026-11-22, session efgh5678", steps="1. a\n2. b", pitfalls="- tuzak", learned_from="Şundan öğrendim")

def test_rule_is_added_as_a_dated_line_after_the_other_rules(store):
    store.edit("rules.md", [{"old": "Project-specific rules", "new": "- 2026-01-02: Kısa yaz.\n\nProject-specific rules"}])
    out = Learning(store).add_rule("Teknik terimleri ilk geçtiği yerde açıkla.", session="s1")
    lines = store.read("rules.md").text.splitlines()
    i = lines.index("- 2026-01-02: Kısa yaz.")
    assert lines[i + 1].startswith("- 20") and lines[i + 1].endswith(": Teknik terimleri ilk geçtiği yerde açıkla.")
    assert out["path"] == "rules.md" and out["possible_repeat"] is None

def test_project_rule_creates_the_project_rules_note(store):
    out = Learning(store).add_rule("Önce önizleme göster.", project="Havuz İşi")
    assert out["path"] == "projects/havuz-isi/rules.md" and "Önce önizleme göster." in store.read(out["path"]).text
    assert store.read(out["path"]).text.startswith("# Rules: Havuz İşi\n\n- 20")

def test_a_rule_on_the_same_subject_is_flagged_not_refused(store):
    L = Learning(store)
    L.add_rule("Teknik terimleri ilk geçtiği yerde bir iki cümleyle açıkla.")
    out = L.add_rule("Teknik terimleri açıklamadan kullanma, ilk geçtiği yerde açıkla.")
    assert "Teknik terimleri ilk geçtiği yerde" in out["possible_repeat"]
    assert L.add_rule("Cevapları tablo yerine düz yazıyla ver.")["possible_repeat"] is None
    assert store.read("rules.md").text.count("Teknik terimleri") == 2

def test_rule_with_a_secret_is_refused(store):
    with pytest.raises(StoreError, match="secret"):
        Learning(store).add_rule("Sunucuya parola: Hunter2hunter2 ile gir.")

def test_rule_is_recorded_in_the_ledger_with_its_line_and_match(store):
    L = Learning(store)
    first = L.add_rule("Kısa yaz, gereksiz giriş yapma.", session="abcdefghijklmnopqrstuv")
    L.add_rule("Gereksiz giriş yapma, kısa yaz.")
    ledger = json.loads(L.state_path.read_text(encoding="utf-8"))["ledger"]
    assert [e["kind"] for e in ledger] == ["rule", "rule"]
    assert ledger[0]["session"] == "abcdefghijklmnop" and ledger[0]["repeat_of"] is None
    assert ledger[0]["line"].endswith(": Kısa yaz, gereksiz giriş yapma.") and ledger[0]["path"] == first["path"]
    assert ledger[1]["repeat_of"] == ledger[0]["line"]

def test_rule_needs_text_on_one_line(store):
    for bad in ("", "  ", "iki\nsatır"):
        with pytest.raises(StoreError):
            Learning(store).add_rule(bad)

def test_assignment_whitespace_does_not_span_lines():
    assert learn.find_secret("token:\nRefreshing the page") is None
    assert learn.find_secret("token: abcdef123") == "password or key assignment"

def test_three_sessions_of_help_make_a_candidate_established(store):
    L = Learning(store); p = L.write_skill("beklet", **SK)["path"]
    assert L.feedback("beklet", "helped", session="a")["status"] == "candidate"
    assert L.feedback("beklet", "helped", session="a")["status"] == "candidate"      # same session counts once
    L.feedback("beklet", "helped", session="b")
    assert L.feedback("beklet", "helped", session="c")["status"] == "established"
    assert "- **Status:** established" in store.read(p).text

def test_two_wrongs_or_five_unhelpful_sessions_retire(store):
    L = Learning(store)
    L.write_skill("yanlis", **SK); L.feedback("yanlis", "wrong", session="a")
    assert L.feedback("yanlis", "wrong", session="b") == {"path": "skills/retired/yanlis.md", "status": "retired"}
    assert "- **Status:** retired" in store.read("skills/retired/yanlis.md").text
    p = L.write_skill("yaramaz", **SK)["path"]
    for s in "abcd":
        L.record_shown(p, s)
    assert store.exists(p)
    L.record_shown(p, "e")
    assert not store.exists(p) and store.exists("skills/retired/yaramaz.md")
    q = L.write_skill("yarar", **SK)["path"]; L.feedback("yarar", "helped", session="a")
    for s in "bcdefg":
        L.record_shown(q, s)
    assert store.exists(q)                                 # it helped once: showing it more does not retire it

def test_shown_in_lists_this_sessions_skills_and_unknown_feedback_is_refused(store):
    L = Learning(store); p = L.write_skill("beklet", **SK)["path"]
    L.record_shown(p, "sess-1"); L.record_shown(p, "sess-1")
    assert L.shown_in("sess-1") == [p] and L.shown_in("other") == []
    with pytest.raises(StoreError):
        L.feedback("yok-boyle-skill", "helped")
    with pytest.raises(StoreError):
        L.feedback("beklet", "great")

def test_broken_state_file_does_not_break_learning(store):
    (store.data / "learning.json").write_text("{not json")
    L = Learning(store)
    assert L.shown_in("s") == [] and L.write_skill("beklet", **SK)["status"] == "candidate"
    (store.data / "learning.json").unlink()
    assert Learning(store).summary()["skills_new"] == 0

def test_a_broken_state_file_is_kept_as_bad_copy_before_it_is_replaced(store):
    state = store.data / "learning.json"
    state.write_text("{not json")
    Learning(store).write_skill("beklet", **SK)
    assert (store.data / "learning.json.bad").read_text() == "{not json"
    json.loads(state.read_text())                          # the live file is valid again
    state.write_text("[1, 2")
    Learning(store).write_skill("ikinci", **SK)
    assert (store.data / "learning.json.bad").read_text() == "[1, 2"      # overwritten each time

def test_established_skill_can_retire_and_feedback_is_logged(store):
    L = Learning(store); L.write_skill("beklet", **SK)
    for s in "abc":
        L.feedback("beklet", "helped", session=s)
    L.feedback("beklet", "wrong", session="x"); L.feedback("beklet", "not_helped", session="y")
    assert L.feedback("beklet", "wrong", session="z")["status"] == "retired"
    events = json.loads((store.data / "learning.json").read_text())["feedback"]
    assert [e["outcome"] for e in events][-3:] == ["wrong", "not_helped", "wrong"]
    assert set(events[0]) == {"ts", "path", "outcome", "session"}

def test_project_skill_feedback_and_summary_counts(store):
    L = Learning(store); L.write_skill("proje", project="Ev", **SK)
    out = L.feedback("proje", "wrong", project="Ev", session="a")
    assert out["path"] == "projects/ev/skills/proje.md"
    L.note_review_asked(); L.note_review_asked()
    s = L.summary()
    assert s["skills_new"] == 1 and s["reviews_asked"] == 2
    assert s["skills_revised"] == s["rules"] == s["undone"] == s["established"] == s["retired"] == 0
    assert s["helped_rate"] == 0.0 and s["possible_repeats"] == []  # one feedback, a wrong one
    assert Learning(store).summary(days=0)["skills_new"] == 0

def _on(monkeypatch, day):
    monkeypatch.setattr(learn, "now_local", lambda: dt.datetime(2026, 11, day, 12).astimezone())

def test_feedback_and_shown_without_a_session_count_once_per_day(store, monkeypatch):
    L = Learning(store); p = L.write_skill("beklet", **SK)["path"]
    _on(monkeypatch, 1)
    assert L.feedback("beklet", "helped")["status"] == "candidate"
    assert L.feedback("beklet", "helped")["status"] == "candidate"        # same day counts once
    _on(monkeypatch, 2)
    assert L.feedback("beklet", "helped")["status"] == "candidate"
    _on(monkeypatch, 3)
    assert L.feedback("beklet", "helped")["status"] == "established"
    assert L.shown_in("") == []
    q = L.write_skill("yaramaz", **SK)["path"]
    for day in range(10, 14):
        _on(monkeypatch, day); L.record_shown(q, "")
    assert store.exists(q)
    _on(monkeypatch, 14); L.record_shown(q, "")
    assert not store.exists(q) and store.exists("skills/retired/yaramaz.md")

def test_undo_removes_a_new_skill_restores_a_revised_one_and_drops_a_rule(store):
    L = Learning(store)
    first = L.write_skill("beklet", session="s1", **SK)
    L.write_skill("beklet", expected_sha=first["sha"], session="s1", **{**SK, "steps": "1. Yeni adım"})
    L.add_rule("Önce önizleme göster.", session="s1")
    assert L.unlearn("s1")["undone"] == "rule" and "önizleme" not in store.read("rules.md").text
    assert L.unlearn("s1")["undone"] == "skill_edit" and "1. Eski işi durdur" in store.read("skills/beklet.md").text
    assert L.unlearn("s1")["undone"] == "skill_new" and not store.exists("skills/beklet.md")
    with pytest.raises(StoreError, match="nothing"):
        L.unlearn("s1")
    assert "Yeni adım" in store._git("log", "-p", "--all").stdout       # history keeps everything

def test_undo_refuses_when_the_target_changed_since(store):
    L = Learning(store)
    L.add_rule("Önce önizleme göster.", session="s1")
    text = store.read("rules.md").text
    store.write("rules.md", text.replace("Önce önizleme göster.", "Önce önizleme göster, sonra sor."),
                expected_sha=store.read("rules.md").sha)
    with pytest.raises(StoreError, match="changed"):
        L.unlearn("s1")
    assert "sonra sor" in store.read("rules.md").text
    out = L.write_skill("beklet", session="s2", **SK)
    store.edit(out["path"], [{"old": "1. Eski işi durdur", "new": "1. Elle değişti"}])
    with pytest.raises(StoreError, match="changed"):
        L.unlearn("s2")
    assert store.exists(out["path"])

def test_undoing_a_comeback_puts_the_retired_note_back_as_it_was(store):
    L = Learning(store)
    L.write_skill("beklet", **SK)
    retired = store.move("skills/beklet.md", "skills/retired/beklet.md").text
    L.write_skill("beklet", **{**SK, "steps": "1. Başka"})
    out = L.unlearn()
    assert out["undone"] == "skill_new" and out["path"] == "skills/beklet.md"
    assert not store.exists("skills/beklet.md") and store.read("skills/retired/beklet.md").text == retired

def test_undo_picks_the_latest_of_the_session_or_overall_and_skips_undone(store):
    L = Learning(store)
    L.add_rule("Birinci kural burada.", session="a" * 20)
    L.add_rule("İkinci kural şurada.", session="b")
    assert L.unlearn("a" * 16 + "zzz")["undone"] == "rule"             # sessions match on their first 16 characters
    assert "Birinci" not in store.read("rules.md").text and "İkinci" in store.read("rules.md").text
    assert L.unlearn()["undone"] == "rule" and "İkinci" not in store.read("rules.md").text
    with pytest.raises(StoreError, match="nothing"):
        L.unlearn()

def test_undo_refuses_when_a_learned_skill_was_retired_since(store):
    L = Learning(store)
    out = L.write_skill("beklet", session="s1", **SK)
    store.move(out["path"], "skills/retired/beklet.md")
    with pytest.raises(StoreError, match="changed"):
        L.unlearn("s1")

def test_summary_counts_learning(store):
    L = Learning(store)
    first = L.write_skill("beklet", session="a", **SK)
    L.write_skill("beklet", expected_sha=first["sha"], session="a", **SK)
    L.add_rule("Teknik terimleri ilk geçtiği yerde bir iki cümleyle açıkla.", session="a")
    L.add_rule("Teknik terimleri açıklamadan kullanma, ilk geçtiği yerde açıkla.", session="b")
    L.feedback("beklet", "helped", session="a"); L.feedback("beklet", "not_helped", session="b")
    L.note_review_asked(); L.unlearn("b")
    s = L.summary()
    assert (s["skills_new"], s["skills_revised"], s["rules"], s["undone"], s["reviews_asked"]) == (1, 1, 2, 1, 1)
    assert s["helped_rate"] == 0.5 and len(s["possible_repeats"]) == 1 and s["established"] == s["retired"] == 0
    assert Learning(store).summary(days=0)["rules"] == 0

def test_summary_counts_skills_by_their_status_in_the_vault(store):
    L = Learning(store)
    L.write_skill("kalici", **SK); L.write_skill("eski", **SK)
    for n in range(3):
        L.feedback("kalici", "helped", session=f"s{n}")
    L.feedback("eski", "wrong"); L.feedback("eski", "wrong")
    s = L.summary(days=0)
    assert s["established"] == 1 and s["retired"] == 1

def _tamper_ledger(store, **changes):
    path = store.data / "learning.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["ledger"][-1].update(changes)
    path.write_text(json.dumps(state), encoding="utf-8")

def test_undo_refuses_an_unknown_kind_or_a_damaged_entry_and_changes_nothing(store):
    L = Learning(store)
    L.write_skill("beklet", session="s1", **SK)
    for change in ({"kind": "mystery"}, {"kind": None}, {"path": None}):
        _tamper_ledger(store, **change)
        with pytest.raises(StoreError):
            L.unlearn("s1")
        assert store.exists("skills/beklet.md")
        _tamper_ledger(store, kind="skill_new", path="skills/beklet.md")
    state = json.loads((store.data / "learning.json").read_text(encoding="utf-8"))
    del state["ledger"][-1]["kind"]
    (store.data / "learning.json").write_text(json.dumps(state), encoding="utf-8")
    with pytest.raises(StoreError):
        L.unlearn("s1")
    assert store.exists("skills/beklet.md")

def test_undoing_a_new_skill_drops_its_counters(store):
    L = Learning(store)
    L.write_skill("beklet", session="s1", **SK)
    L.feedback("beklet", "helped", session="s1"); L.feedback("beklet", "wrong", session="s1")
    L.record_shown("skills/beklet.md", "s1")
    L.unlearn("s1")
    assert "skills/beklet.md" not in json.loads((store.data / "learning.json").read_text(encoding="utf-8")).get("skills", {})
    L.write_skill("beklet", session="s2", **SK)
    L.feedback("beklet", "wrong", session="s2")                      # inherited counters would make this the second: retired
    assert store.exists("skills/beklet.md") and not store.exists("skills/retired/beklet.md")

def test_a_status_looking_line_in_the_steps_does_not_stop_promotion_or_retirement(store):
    L = Learning(store)
    steps = "1. Başlığın altına şunu yaz:\n- **Status:** candidate\n2. Kaydet"
    p = L.write_skill("meta", **{**SK, "steps": steps})["path"]
    for s in "abc":
        L.feedback("meta", "helped", session=s)
    fields = learn.parse_skill(store.read(p).text)
    assert fields["status"] == "established" and fields["steps"] == steps   # only the header line changed
    L.write_skill("meta iki", **{**SK, "steps": steps})
    L.feedback("meta iki", "wrong", session="a")
    assert L.feedback("meta iki", "wrong", session="b")["status"] == "retired"
    fields = learn.parse_skill(store.read("skills/retired/meta-iki.md").text)
    assert fields["status"] == "retired" and fields["steps"] == steps

def _damaged(store):
    """A skill note whose header carries two Status lines: no verdict can be carried out on it."""
    text = learn.render_skill("Servis kurulumu bozuk not", SK["when"], SK["steps"], SK["learned_from"])
    store.write("skills/bozuk.md", text.replace("- **Status:** candidate", "- **Status:** candidate\n- **Status:** candidate"))

def test_a_damaged_skill_beside_a_good_one_does_not_stop_the_good_one(store):
    from council.context import skills_block
    L = Learning(store)
    good = L.write_skill("Servisi yeniden kurarken beklet", **SK)["path"]
    L.feedback("Servisi yeniden kurarken beklet", "helped", session="h")   # it has helped: it must stay
    _damaged(store)
    q = "çalışan servisin üstüne yeniden kurulum yapacağım"
    for i in range(6):                                     # once retirement by showing would have been tried
        block, _ = skills_block(L, q, None, f"s{i}")
        assert good in block, i
    L.feedback("bozuk", "wrong", session="a")
    assert L.feedback("bozuk", "wrong", session="b") == {"path": "skills/bozuk.md", "status": "candidate"}
    assert store.exists("skills/bozuk.md") and good in skills_block(L, q, None, "s9")[0]

def test_feedback_takes_the_skill_path_the_review_question_names(store):
    L = Learning(store)
    p = L.write_skill("Servisi yeniden kurarken beklet", **SK)["path"]
    q = L.write_skill("Kurs açma", project="Havuz İşi", **SK)["path"]
    for s in "abc":
        L.feedback(p, "helped", session=s)
    assert learn.parse_skill(store.read(p).text)["status"] == "established"
    L.feedback(q, "wrong", session="a")
    assert L.feedback(q, "wrong", session="b") == {"path": "projects/havuz-isi/skills/retired/kurs-acma.md",
                                                   "status": "retired"}
    with pytest.raises(StoreError, match="no live skill"):
        L.feedback("skills/yok.md", "helped")
