import unicodedata

from conftest import PASSWORD, SECRETS
from starlette.testclient import TestClient

from council.panel.app import SECTIONS


def _ascii(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text.replace("ı", "i")) if not unicodedata.combining(c))


# every marker as written and with its Turkish letters made plain, each compared without regard to case
FORMS = sorted({form.casefold() for s in SECRETS for form in (s, _ascii(s))})


def leaked(text: str) -> list[str]:
    text = text.casefold()
    return [f for f in FORMS if f in text or f in _ascii(text)]


def test_the_markers_are_folded_both_ways_and_are_in_the_memory(leaky):
    assert "tarif-sirri" in FORMS and "cekirdek-sirri" in FORMS and "ÇEKİRDEK-SIRRI".casefold() in FORMS
    assert leaked("… Cekirdek-Sirri …") and leaked("çekirdek-sırrı") and not leaked("projects/ev/kaynak.md")
    vault = " ".join(p.read_text(encoding="utf-8") for p in (leaky / "vault").rglob("*.md"))
    for marker in ("TARİF-SIRRI", "ZAMAN-SIRRI", "ÇEKİRDEK-SIRRI", "İPLİK-SIRRI", "KART-SIRRI", "OTURUM-SIRRI"):
        assert marker in vault, marker


def test_no_address_of_the_panel_gives_away_text(leaky_panel):
    for section in SECTIONS:
        body = leaky_panel.get(f"/panel/api/{section}").text
        assert not leaked(body), section
    for page in ("/panel/", "/panel/login"):
        assert not leaked(leaky_panel.get(page).text)


def test_no_error_answer_gives_away_text(leaky_panel):
    stranger = TestClient(leaky_panel.app, base_url="http://127.0.0.1:8766", follow_redirects=False)
    try:
        for section in SECTIONS:
            r = stranger.get(f"/panel/api/{section}")
            assert r.status_code == 401 and not leaked(r.text), section
        r = leaky_panel.get("/panel/api/yok-boyle-bir-bolum")
        assert r.status_code == 404 and not leaked(r.text)
        for _ in range(5):
            assert not leaked(stranger.post("/panel/login", data={"password": "yanlis"}).text)
        r = stranger.post("/panel/login", data={"password": PASSWORD})
        assert r.status_code == 429 and not leaked(r.text)
    finally:
        stranger.close()


def test_the_schema_and_today_are_not_empty_in_the_leak_memory(leaky_panel):
    """Guards the leak test above: it proves nothing if the two sections it checks answer empty."""
    schema = leaky_panel.get("/panel/api/schema").json()
    assert schema["events"] and "kaynak.md" in str(schema["events"])
    assert leaky_panel.get("/panel/api/today").json()["events"]


def test_notes_and_map_are_not_empty_in_the_leak_memory(leaky_panel):
    """Guards the leak test the same way for the notes and the map."""
    assert leaky_panel.get("/panel/api/notes").json()["ranking"]
    assert leaky_panel.get("/panel/api/map").json()["notes"]


def test_the_health_address_and_the_panel_file_give_away_no_question(leaky_panel, leaky):
    """The check reads the saved questions; neither its answer nor the panel's own file may carry their text."""
    sampler = leaky_panel.app.state.sampler
    sampler.sample(probe=lambda url: True)
    assert sampler.run_check(force=True)
    for section in ("health", "schema"):
        body = leaky_panel.get(f"/panel/api/{section}").text
        assert not leaked(body), section
    assert leaky_panel.get("/panel/api/health").json()["runs"], "the leak test proves nothing on an empty history"
    raw = b"".join(p.read_bytes() for p in leaky.glob("panel.sqlite3*"))
    assert not leaked(raw.decode("utf-8", errors="replace"))
