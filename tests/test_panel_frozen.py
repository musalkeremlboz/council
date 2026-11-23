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

def test_read_only_index_and_usage_refuse_a_missing_file_and_create_nothing(tmp_path):
    from council.index import Index
    with pytest.raises(FileNotFoundError):
        Index(tmp_path / "a.sqlite3", readonly=True)
    with pytest.raises(FileNotFoundError):
        Usage(tmp_path / "b.sqlite3", readonly=True)
    assert list(tmp_path.iterdir()) == []
