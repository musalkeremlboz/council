import json
import os
import shutil
import stat
from pathlib import Path

import pytest

PASSWORD = "dogru-sifre-123"


def remove_history(vault: Path) -> None:
    """Delete a vault's .git folder. Git marks its object files read-only, and Windows refuses to delete those."""

    def unlock(func, path, _exc):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    shutil.rmtree(vault / ".git", onerror=unlock)


@pytest.fixture
def panel_data(tmp_path) -> Path:
    from council.oauth import hash_password
    from council.store import Store

    data = tmp_path / "data"
    store = Store(data)
    store.index.db.close()
    (data / "owner.json").write_text(json.dumps(hash_password(PASSWORD)))
    return data


@pytest.fixture
def panel(panel_data):
    from starlette.testclient import TestClient

    from council.panel.app import build

    app = build(panel_data, background=False)
    client = TestClient(app, base_url="http://127.0.0.1:8766", follow_redirects=False)
    try:
        yield client
    finally:
        client.close()
        app.state.gate.close()


@pytest.fixture
def panel_signed_in(panel):
    r = panel.post("/panel/login", data={"password": PASSWORD})
    assert r.status_code == 303
    return panel


@pytest.fixture
def static_dir() -> Path:
    import council.panel

    return Path(council.panel.__file__).parent / "static"


SECRETS = ("GOVDE-SIRRI", "BASLIK-SIRRI", "MESAJ-SIRRI", "KURAL-SIRRI", "ACIKLAMA-SIRRI", "SORU-SIRRI",
           # the skill's text, the notes every session starts with and a session card, with Turkish letters
           "TARİF-SIRRI", "ZAMAN-SIRRI", "ÇEKİRDEK-SIRRI", "İPLİK-SIRRI", "KART-SIRRI", "OTURUM-SIRRI")
ODD_FOLDER = "not & 'adı' 🗂"  # a space, an ampersand, an apostrophe, a non-ASCII letter and an emoji; legal on every system


@pytest.fixture
def leaky(tmp_path) -> Path:
    """A memory whose every kind of text (body, heading, message, rule, commit reason, question, skill, the notes
    loaded at every start, a session card) carries a marker from SECRETS, so a test can prove an address gives
    none of them away."""
    import time

    from council.check import add_question
    from council.learn import Learning
    from council.oauth import hash_password
    from council.store import Store
    from council.usage import Usage

    data = tmp_path / "data"
    store = Store(data)
    try:
        store.write(f"projects/{ODD_FOLDER}/plan.md", "# Plan\n\nGOVDE-SIRRI is in the body.\n\n## BASLIK-SIRRI\n\nmore\n",
                    reason="ACIKLAMA-SIRRI")
        store.write("projects/ev/kaynak.md", "# Kaynak\n\nGOVDE-SIRRI again.\n\n### BASLIK-SIRRI\n")
        store.write("projects/ev/baglanti.md",
                    "# Bağlantı\n\nSee [[kaynak]] and [again](kaynak.md) and [[yok-boyle-bir-not]].\n")
        Learning(store).write_skill("kira odeme", "when the rent is due ZAMAN-SIRRI", "1. open the bank app TARİF-SIRRI",
                                    "the user said so")
        for path, marker in (("core.md", "ÇEKİRDEK-SIRRI"), ("threads.md", "İPLİK-SIRRI")):
            note = store.read(path)
            store.write(path, note.text + f"\n## {marker}\n\n{marker} is in the body.\n", expected_sha=note.sha)
        store.upsert_session("sess0001", "KART-SIRRI", "OTURUM-SIRRI is on the card.")
        Learning(store).add_rule("KURAL-SIRRI always answer short")
        add_question(store, "SORU-SIRRI where is the rent", ["projects/ev/kaynak.md"])
    finally:
        store.index.db.close()
    now = time.time()
    usage = Usage(data / "usage.sqlite3")
    try:
        hit = [{"path": "projects/ev/kaynak.md", "heading": "BASLIK-SIRRI", "score": 2.5},
               {"path": f"projects/{ODD_FOLDER}/plan.md", "heading": "BASLIK-SIRRI", "score": 1.0}]
        usage.record("start", "s1", "MESAJ-SIRRI", 10, None, [], ts=now - 50)
        usage.record("inject", "s1", "MESAJ-SIRRI", 300, 2.5, hit, ts=now - 40)
        usage.record("read", "s1", "MESAJ-SIRRI", 80, None, hit[:1], ts=now - 30)
        usage.record("search", "s1", "MESAJ-SIRRI", 120, 2.5, hit, ts=now - 20)
    finally:
        usage.db.close()
    (data / "backup.json").write_text(json.dumps({"first_run": now - 100, "last_ok": now - 10, "error": ""}))
    (data / "owner.json").write_text(json.dumps(hash_password(PASSWORD)))
    return data


@pytest.fixture
def leaky_panel(leaky):
    from starlette.testclient import TestClient

    from council.panel.app import build

    app = build(leaky, background=False)
    client = TestClient(app, base_url="http://127.0.0.1:8766", follow_redirects=False)
    try:
        assert client.post("/panel/login", data={"password": PASSWORD}).status_code == 303
        yield client
    finally:
        client.close()
        app.state.gate.close()
