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


def test_the_pulse_and_the_session_fields_give_away_no_text(leaky_panel, leaky):
    import time

    from council.usage import Usage

    usage = Usage(leaky / "usage.sqlite3")
    try:
        usage.record("inject", "sess0002abcdefgh", "MESAJ-SIRRI", 300, None,
                     [{"path": "projects/ev/kaynak.md", "heading": "BASLIK-SIRRI"}], ts=time.time())
    finally:
        usage.db.close()
    # the query text of the event carries a marker; the session id is shown and is not text
    for url in ("/panel/api/pulse", "/panel/api/pulse?since=1", "/panel/api/pulse?since=abc"):
        body = leaky_panel.get(url).text
        assert not leaked(body), url
    assert leaky_panel.get("/panel/api/pulse?since=1").json()["events"], "the leak test proves nothing on no events"
    today = leaky_panel.get("/panel/api/today").json()
    assert today["sessions"] and all(set(s) == {"id", "key", "first_minute", "last_minute", "events", "at_limit", "chars"}
                                     for s in today["sessions"])
    assert not leaked(str(today))


def test_the_settings_and_the_two_writes_give_away_no_text_and_no_password(leaky_panel):
    same = {"Origin": "http://127.0.0.1:8766"}
    settings = leaky_panel.get("/panel/api/settings")
    assert set(settings.json()) == {"sessions", "expires", "min_length"} and not leaked(settings.text)
    answers = [leaky_panel.post("/panel/api/password", json=body, headers=same) for body in (
        {"current": "yanlis-sifre", "new": "yepyeni-sifre-456"},
        {"current": PASSWORD, "new": "kisa"},
        {"current": PASSWORD, "new": PASSWORD},
        {"current": "GOVDE-SIRRI", "new": "GOVDE-SIRRI"},
    )]
    answers.append(leaky_panel.post("/panel/api/sessions/close-others", headers=same))
    answers.append(leaky_panel.post("/panel/api/password", json={"current": PASSWORD, "new": "yepyeni-sifre-456"},
                                    headers=same))
    assert answers[-1].status_code == 200
    for r in answers:
        assert not leaked(r.text) and PASSWORD not in r.text and "yepyeni" not in r.text, r.text
