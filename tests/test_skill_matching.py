import json, pathlib
import pytest
from council.index import build_query
from council.learn import Learning
from council.store import Store

DATA = json.loads((pathlib.Path(__file__).parent / "scenarios" / "skills.json").read_text(encoding="utf-8"))
# Long messages (150 to 650 characters), written by an author who saw neither the matching code nor the short set's
# results. off_topic: no skill's subject. off_topic_neighbour: a skill's subject, but not the work it covers.
LONG = json.loads((pathlib.Path(__file__).parent / "scenarios" / "skills_long.json").read_text(encoding="utf-8"))

def load(data_dir):
    """A Learning holding every scenario skill."""
    L = Learning(Store(data_dir))
    for s in DATA["skills"]:
        L.write_skill(**s)
    return L

@pytest.fixture(scope="module")
def learning(tmp_path_factory):
    return load(tmp_path_factory.mktemp("data"))

def test_scenario_set_is_big_enough_and_does_not_copy_the_when_lines():
    assert len(DATA["skills"]) >= 12 and len(DATA["on_topic"]) >= 20 and len(DATA["off_topic"]) >= 10
    when = {s["name"]: set(build_query(s["when"], content_only=True).split(" OR ")) for s in DATA["skills"]}
    for case in DATA["on_topic"]:
        said = set(build_query(case["message"], content_only=True).split(" OR "))
        assert len(said & when[case["expect"]]) < 0.5 * len(when[case["expect"]]), case["message"]

def test_the_right_skill_is_among_the_two_shown_for_80_percent(learning):
    hits = sum(any(m["title"] == c["expect"] for m in learning.match(c["message"])) for c in DATA["on_topic"])
    assert hits / len(DATA["on_topic"]) >= 0.80, f"{hits}/{len(DATA['on_topic'])}"

def test_off_topic_messages_get_a_skill_at_most_20_percent(learning):
    shown = sum(bool(learning.match(m)) for m in DATA["off_topic"])
    assert shown / len(DATA["off_topic"]) <= 0.20, f"{shown}/{len(DATA['off_topic'])}"

def test_retired_skills_never_match(tmp_path):
    L = load(tmp_path / "own")  # its own folder: retiring must not change what the shared fixture measures
    name = DATA["skills"][0]["name"]
    L.feedback(name, "wrong", session="x"); L.feedback(name, "wrong", session="y")
    assert all(m["title"] != name for case in DATA["on_topic"] for m in L.match(case["message"]))

@pytest.mark.parametrize("k", [1, 2, 3, 6, 14])
def test_the_decision_does_not_depend_on_how_many_skills_exist(tmp_path, k):
    """Every user starts with one skill: the bars hold for the first k skills of the set."""
    L = Learning(Store(tmp_path / "data"))
    names = set()
    for s in DATA["skills"][:k]:
        L.write_skill(**s)
        names.add(s["name"])
    cases = [c for c in DATA["on_topic"] if c["expect"] in names]
    hits = sum(any(m["title"] == c["expect"] for m in L.match(c["message"])) for c in cases)
    shown = sum(bool(L.match(m)) for m in DATA["off_topic"])
    assert hits / len(cases) >= 0.80, f"k={k}: on-topic {hits}/{len(cases)}"
    assert shown / len(DATA["off_topic"]) <= 0.20, f"k={k}: off-topic {shown}/{len(DATA['off_topic'])}"

def test_a_skill_still_matches_among_many_ordinary_notes_sharing_its_words(tmp_path):
    """The skill is scored directly, not picked from the top of a vault-wide search."""
    store = Store(tmp_path / "data")
    L = Learning(store)
    L.write_skill("Servisi yeniden kurarken beklet", when="Çalışan bir servisin üstüne yeniden kurulum yapılırken",
                  steps="1. Eski işi durdur\n2. Bittiğini doğrula\n3. Yenisini yükle",
                  learned_from="Yeniden kurulum 'Input/output error' verdi; bekleyince düzeldi.")
    for i in range(300):                                  # written straight to disk: 300 commits would be slow
        f = store.vault / "log" / f"2026-{i:04d}.md"
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(f"# Log {i}\n\nçalışan servisin üstüne yeniden kurulum yapıldı, servis yeniden kuruldu {i}\n",
                     encoding="utf-8")
    store.index.sync(store.vault)
    found = L.match("çalışan servisin üstüne yeniden kurulum yapacağım")
    assert [m["path"] for m in found] == ["skills/servisi-yeniden-kurarken-beklet.md"]


# ---------- long messages ----------

@pytest.fixture(scope="module")
def long_learning(tmp_path_factory):
    L = Learning(Store(tmp_path_factory.mktemp("long")))
    for s in LONG["skills"]:
        L.write_skill(**s)
    return L

def test_long_messages_on_another_subject_get_a_skill_at_most_20_percent(long_learning):
    """Length alone must not bring a skill up: a long message shares some words with every long note."""
    shown = sum(bool(long_learning.match(m)) for m in LONG["off_topic"])
    assert shown / len(LONG["off_topic"]) <= 0.20, f"{shown}/{len(LONG['off_topic'])}"

def test_long_on_topic_messages_keep_their_skill(long_learning):
    """A floor against going backwards, not the goal: the goal is 80%, measured 71% (2026-11-21)."""
    hits = sum(any(m["title"] == c["expect"] for m in long_learning.match(c["message"])) for c in LONG["on_topic"])
    assert hits / len(LONG["on_topic"]) >= 0.65, f"{hits}/{len(LONG['on_topic'])}"

@pytest.mark.xfail(reason="words tell the subject, not what is asked: measured 8/14 (2026-11-21)", strict=False)
def test_long_messages_on_a_skills_subject_but_asking_something_else_get_no_skill(long_learning):
    shown = sum(bool(long_learning.match(m)) for m in LONG["off_topic_neighbour"])
    assert shown / len(LONG["off_topic_neighbour"]) <= 0.20, f"{shown}/{len(LONG['off_topic_neighbour'])}"

def _one_skill(tmp_path, **fields):
    L = Learning(Store(tmp_path / "data"))
    L.write_skill(**fields)
    return L

def test_forms_of_one_word_count_as_one_word(tmp_path):
    """Two different words must be in the title or When line; "sistemi, sistemimiz, sistemlerin" is one."""
    L = _one_skill(tmp_path, name="Sistemi yedekten geri yükleme", when="Sunucu bozulduğunda yedekten dönülürken",
                   steps="1. Yedeği bul\n2. Geri yükle", learned_from="Disk dolunca veritabanı bozuldu.")
    assert L.match("sistemi sistemimiz sistemlerin") == []
    assert [m["title"] for m in L.match("sistemi yedekten nasıl geri alırım")] == ["Sistemi yedekten geri yükleme"]

def test_words_found_only_in_the_body_do_not_bring_a_skill_up(tmp_path):
    L = _one_skill(tmp_path, name="Raporu PDF olarak dışa aktarma", when="Aylık rapor paylaşılmadan önce",
                   steps="1. Yazıcı sürücüsünü seç\n2. Kenar boşluğunu ayarla\n3. Filigranı kaldır",
                   learned_from="Filigran çıktıda kalmıştı.")
    assert L.match("yazıcı sürücüsü filigran kenar boşluğu") == []
    assert len(L.match("aylık raporu pdf olarak dışa aktar")) == 1
