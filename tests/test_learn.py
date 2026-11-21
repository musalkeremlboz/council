import json, time
import pytest
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

from council import learn
from council.learn import Learning

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
