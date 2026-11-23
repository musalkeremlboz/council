import json

import pytest
from starlette.testclient import TestClient

from council import cli
from council.oauth import hash_password
from council.panel.app import SECTIONS, build

PAGES = ["/panel/"]
API = [f"/panel/api/{s}" for s in ("schema", "today", "health", "map", "notes", "releases", "settings")]


def test_nothing_is_served_without_a_session(panel):
    for url in PAGES:
        r = panel.get(url)
        assert r.status_code == 303 and r.headers["location"].endswith("/panel/login")
    for url in API:
        r = panel.get(url)
        assert r.status_code == 401 and r.json() == {"error": "signed_out"}


def test_the_right_password_opens_every_page_and_signing_out_closes_them(panel):
    r = panel.post("/panel/login", data={"password": "dogru-sifre-123"})
    assert r.status_code == 303 and "council_panel=" in r.headers["set-cookie"]
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie and "path=/panel" in cookie and "secure" not in cookie
    assert all(panel.get(u).status_code == 200 for u in PAGES + API)
    panel.post("/panel/logout")
    assert panel.get("/panel/api/schema").status_code == 401


def test_five_wrong_passwords_then_the_right_one_is_refused(panel):
    for _ in range(5):
        assert panel.post("/panel/login", data={"password": "yanlis"}).status_code == 401
    assert panel.post("/panel/login", data={"password": "dogru-sifre-123"}).status_code == 429


def test_behind_https_the_cookie_is_secure_and_every_answer_is_closed_to_other_sites(panel):
    r = panel.post("/panel/login", data={"password": "dogru-sifre-123"}, headers={"X-Forwarded-Proto": "https"})
    assert "secure" in r.headers["set-cookie"].lower()
    h = panel.get("/panel/login").headers
    assert "default-src 'self'" in h["content-security-policy"] and "noindex" in h["x-robots-tag"]
    assert panel.post("/panel/login", data={"password": "x"}, headers={"Origin": "https://baska.example"}).status_code == 403


@pytest.mark.parametrize("base,norm", [("/", ""), ("/panel", "/panel"), ("/panel/", "/panel"), ("ic/panel", "/ic/panel")])
def test_the_base_path_can_be_anything(panel_data, base, norm):
    app = build(panel_data, base_path=base, background=False)
    with TestClient(app, base_url="http://127.0.0.1:8766", follow_redirects=False) as c:
        try:
            r = c.get(norm + "/")
            assert r.status_code == 303 and r.headers["location"] == norm + "/login"
            r = c.post(norm + "/login", data={"password": "dogru-sifre-123"})
            assert r.status_code == 303 and r.headers["location"] == norm + "/"
            assert f"path={norm or '/'}" in r.headers["set-cookie"].lower()
            assert c.get(norm + "/").status_code == 200
            assert c.get(norm + "/api/schema").status_code == 200
            out = c.post(norm + "/logout")
            assert out.status_code == 303 and out.headers["location"] == norm + "/login"
            assert c.get(norm + "/api/schema").status_code == 401
        finally:
            app.state.gate.close()


def test_without_an_owner_password_the_command_says_how_to_set_one(tmp_path, capsys):
    from council.store import Store

    data = tmp_path / "data"
    Store(data).index.db.close()
    assert cli.main(["--data", str(data), "panel"]) == 2
    assert "council set-password" in capsys.readouterr().err


def test_a_page_never_shows_the_sign_in_form_to_a_signed_in_visitor_and_bounces_it(panel_signed_in):
    r = panel_signed_in.get("/panel/login")
    assert r.status_code == 303 and r.headers["location"] == "/panel/"
    assert "bolum" in panel_signed_in.get("/panel/").text


def test_a_wrong_password_shows_the_form_again_with_401(panel):
    r = panel.post("/panel/login", data={"password": "yanlis"})
    assert r.status_code == 401 and "<form" in r.text and "{{" not in r.text


def test_the_login_page_has_the_emblem_the_word_and_a_labelled_password_field(panel):
    html = panel.get("/panel/login").text
    assert "<svg" in html and "COUNCIL" in html and 'type="password"' in html and "<label" in html and "{{" not in html


def test_every_answer_carries_the_security_headers_and_html_and_json_are_not_cached(panel_signed_in):
    for url in ("/panel/", "/panel/api/schema", "/panel/static/panel.css"):
        h = panel_signed_in.get(url).headers
        assert h["x-content-type-options"] == "nosniff" and h["referrer-policy"] == "same-origin"
        assert "frame-ancestors 'none'" in h["content-security-policy"] and "form-action 'self'" in h["content-security-policy"]
    assert panel_signed_in.get("/panel/").headers["cache-control"] == "no-store"
    assert panel_signed_in.get("/panel/api/schema").headers["cache-control"] == "no-store"


def test_static_files_are_open_and_the_section_api_names_its_section(panel, panel_signed_in, static_dir):
    css = panel.get("/panel/static/panel.css")
    assert css.status_code == 200 and "#E8421F" in css.text
    assert panel.get("/panel/static/yok.css").status_code == 404
    assert set(panel_signed_in.get("/panel/api/health").json()) == {"summary", "days", "runs", "missing"}
    assert panel_signed_in.get("/panel/api/nope").status_code == 404
    assert SECTIONS == ("schema", "today", "health", "map", "notes", "releases", "settings")


def test_no_owner_password_gives_503_with_the_sentence(tmp_path):
    from council.store import Store

    data = tmp_path / "data"
    Store(data).index.db.close()
    app = build(data, background=False)
    try:
        with TestClient(app, base_url="http://127.0.0.1:8766", follow_redirects=False) as c:
            r = c.post("/panel/login", data={"password": "x"})
            assert r.status_code == 503 and "council set-password" in r.text
    finally:
        app.state.gate.close()


def test_a_busy_database_is_a_plain_503_not_a_traceback(panel, monkeypatch):
    import sqlite3

    def busy(*a, **k):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(panel.app.state.gate, "valid", busy)
    assert panel.get("/panel/").status_code == 503
    assert panel.get("/panel/api/schema").status_code == 503


def test_the_lockout_rule_on_the_page_follows_the_constants(panel, monkeypatch):
    from council import oauth

    monkeypatch.setattr(oauth, "MAX_FAILURES", 7)
    monkeypatch.setattr(oauth, "FAILURE_WINDOW", 1800)
    page = panel.get("/panel/login").text
    assert "7 yanlış denemeden sonra kapı 30 dakika kapanır." in page


def test_the_referrer_policy_is_same_origin_so_a_browser_sends_its_real_origin(panel, panel_signed_in):
    # under no-referrer a browser sends "Origin: null" on its own form post and the guard refuses the sign-in
    for url in ("/panel/login", "/panel/", "/panel/api/schema"):
        assert panel_signed_in.get(url).headers["referrer-policy"] == "same-origin", url


def test_a_sign_in_with_origin_null_is_refused_and_sets_no_cookie(panel):
    r = panel.post("/panel/login", data={"password": "dogru-sifre-123"}, headers={"Origin": "null"})
    assert r.status_code == 403 and "set-cookie" not in r.headers


def test_a_sign_in_from_the_same_host_opens_and_from_another_host_is_refused(panel):
    r = panel.post("/panel/login", data={"password": "dogru-sifre-123"}, headers={"Origin": "http://127.0.0.1:8766"})
    assert r.status_code == 303 and "council_panel=" in r.headers.get("set-cookie", "")
    r = panel.post("/panel/login", data={"password": "dogru-sifre-123"}, headers={"Origin": "http://127.0.0.2:8766"})
    assert r.status_code == 403 and "set-cookie" not in r.headers


def test_the_pulse_address_is_closed_signed_out_and_answers_signed_in(panel, panel_signed_in):
    stranger = TestClient(panel.app, base_url="http://127.0.0.1:8766", follow_redirects=False)
    try:
        r = stranger.get("/panel/api/pulse")
        assert r.status_code == 401 and r.json() == {"error": "signed_out"}
    finally:
        stranger.close()
    r = panel_signed_in.get("/panel/api/pulse")
    assert r.status_code == 200 and set(r.json()) == {"mark", "events"} and r.json()["events"] == []
    for since in ("abc", "", "nan", "-5", "1e999"):
        r = panel_signed_in.get("/panel/api/pulse", params={"since": since})
        assert r.status_code == 200 and r.json()["events"] == [], since
    assert "pulse" not in SECTIONS
    assert panel_signed_in.get("/panel/api/schema").status_code == 200


def test_the_pulse_address_runs_the_view_and_answers_unavailable_when_it_fails(panel_signed_in, monkeypatch):
    from council.panel import views

    def boom(*args):
        raise RuntimeError("boom")

    monkeypatch.setattr(views, "pulse", boom)
    r = panel_signed_in.get("/panel/api/pulse")
    assert r.status_code == 200 and r.json() == {"error": "unavailable"}


# ---------- the two writes: the password and the other sessions ----------

SAME_ORIGIN = {"Origin": "http://127.0.0.1:8766"}
NEW = "yepyeni-sifre-456"


def change(client, body, headers=SAME_ORIGIN):
    return client.post("/panel/api/password", json=body, headers=headers)


def second_session(app):
    other = TestClient(app, base_url="http://127.0.0.1:8766", follow_redirects=False)
    assert other.post("/panel/login", data={"password": "dogru-sifre-123"}).status_code == 303
    return other


def test_the_two_writes_refuse_a_missing_a_foreign_and_a_null_origin(panel_signed_in):
    for headers in ({}, {"Origin": "https://baska.example"}, {"Origin": "null"}, {"Origin": "http://127.0.0.1:9999"}):
        r = change(panel_signed_in, {"current": "dogru-sifre-123", "new": NEW}, headers=headers)
        assert r.status_code == 403 and NEW not in r.text, headers
        r = panel_signed_in.post("/panel/api/sessions/close-others", headers=headers)
        assert r.status_code == 403, headers
    assert panel_signed_in.post("/panel/login", data={"password": "dogru-sifre-123"}).status_code == 303  # unchanged
    assert panel_signed_in.app.state.gate.db.execute("SELECT COUNT(*) FROM failures").fetchone()[0] == 0


def test_signed_out_the_two_writes_and_the_settings_answer_401(panel):
    assert change(panel, {"current": "dogru-sifre-123", "new": NEW}).json() == {"error": "signed_out"}
    assert change(panel, {"current": "dogru-sifre-123", "new": NEW}).status_code == 401
    r = panel.post("/panel/api/sessions/close-others", headers=SAME_ORIGIN)
    assert r.status_code == 401 and r.json() == {"error": "signed_out"}
    r = panel.get("/panel/api/settings")
    assert r.status_code == 401 and r.json() == {"error": "signed_out"}


def test_every_answer_of_a_password_change_and_none_echoes_a_password(panel_signed_in):
    from council.oauth import MIN_PASSWORD

    c = panel_signed_in
    cases = [
        ({"current": "dogru-sifre-123", "new": "kisa"}, 400, {"error": "weak"}),
        ({"current": "dogru-sifre-123", "new": "k" * 201}, 400, {"error": "weak"}),
        ({"current": "dogru-sifre-123", "new": "dogru-sifre-123"}, 400, {"error": "same"}),
        ({"current": "yanlis-sifre-789", "new": NEW}, 403, {"error": "wrong"}),
        ({"current": "dogru-sifre-123"}, 400, {"error": "bad_request"}),
        ({"current": 5, "new": NEW}, 400, {"error": "bad_request"}),
        (["dogru-sifre-123", NEW], 400, {"error": "bad_request"}),
    ]
    for body, status, answer in cases:
        r = change(c, body)
        assert (r.status_code, r.json()) == (status, answer), body
        for word in ("dogru-sifre-123", NEW, "yanlis-sifre-789", "kisa"):
            assert word not in r.text, (body, word)
    r = c.post("/panel/api/password", content=b"{not json", headers={**SAME_ORIGIN, "Content-Type": "application/json"})
    assert (r.status_code, r.json()) == (400, {"error": "bad_request"})
    r = c.post("/panel/api/password", data={"current": "dogru-sifre-123", "new": NEW}, headers=SAME_ORIGIN)
    assert (r.status_code, r.json()) == (400, {"error": "bad_request"})   # a form post is not the page's request
    r = c.post("/panel/api/password", content=b"{" + b" " * 10000 + b"}",
               headers={**SAME_ORIGIN, "Content-Type": "application/json"})
    assert (r.status_code, r.json()) == (400, {"error": "bad_request"})
    assert c.get("/panel/api/settings").json()["min_length"] == MIN_PASSWORD


def test_a_change_closes_the_other_sessions_and_the_new_password_opens_the_door(panel_signed_in):
    c = panel_signed_in
    other = second_session(c.app)
    try:
        assert c.get("/panel/api/settings").json()["sessions"] == 2
        r = change(c, {"current": "dogru-sifre-123", "new": NEW})
        assert (r.status_code, r.json()) == (200, {"ok": True, "closed": 1}) and NEW not in r.text
        assert c.get("/panel/api/schema").status_code == 200       # the caller stays signed in
        assert other.get("/panel/api/schema").status_code == 401   # the other session is closed
        assert other.post("/panel/login", data={"password": "dogru-sifre-123"}).status_code == 401
        assert other.post("/panel/login", data={"password": NEW}).status_code == 303
    finally:
        other.close()


def test_five_wrong_current_passwords_lock_the_door_and_the_change_answers_429(panel_signed_in):
    c = panel_signed_in
    for _ in range(5):
        assert change(c, {"current": "yanlis-sifre-789", "new": NEW}).status_code == 403
    r = change(c, {"current": "dogru-sifre-123", "new": NEW})
    assert (r.status_code, r.json()) == (429, {"error": "locked"})
    stranger = TestClient(c.app, base_url="http://127.0.0.1:8766", follow_redirects=False)
    try:
        assert stranger.post("/panel/login", data={"password": "dogru-sifre-123"}).status_code == 429
    finally:
        stranger.close()


def test_closing_the_other_sessions_answers_how_many_and_keeps_the_callers(panel_signed_in):
    c = panel_signed_in
    others = [second_session(c.app) for _ in range(2)]
    try:
        info = c.get("/panel/api/settings").json()
        assert set(info) == {"sessions", "expires", "min_length"} and info["sessions"] == 3
        r = c.post("/panel/api/sessions/close-others", headers=SAME_ORIGIN)
        assert (r.status_code, r.json()) == (200, {"closed": 2})
        assert all(o.get("/panel/api/schema").status_code == 401 for o in others)
        assert c.get("/panel/api/settings").json()["sessions"] == 1
        assert c.post("/panel/api/sessions/close-others", headers=SAME_ORIGIN).json() == {"closed": 0}
    finally:
        for o in others:
            o.close()


def test_a_change_that_cannot_be_written_answers_unavailable_and_changes_nothing(panel_signed_in, monkeypatch):
    from council import oauth

    def refuse(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(oauth, "write_owner", refuse)
    r = change(panel_signed_in, {"current": "dogru-sifre-123", "new": NEW})
    assert (r.status_code, r.json()) == (500, {"error": "unavailable"})
    monkeypatch.undo()
    assert panel_signed_in.get("/panel/api/schema").status_code == 200


def test_no_log_record_carries_a_password(panel_signed_in, caplog, monkeypatch):
    import logging

    from council import oauth

    caplog.set_level(logging.DEBUG)
    c = panel_signed_in
    change(c, {"current": "yanlis-sifre-789", "new": NEW})
    change(c, {"current": "dogru-sifre-123", "new": "kisa-ama-gizli"[:9]})
    real = oauth.write_owner

    def refuse(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(oauth, "write_owner", refuse)
    change(c, {"current": "dogru-sifre-123", "new": NEW})            # a failure is logged with its traceback
    monkeypatch.setattr(oauth, "write_owner", real)
    assert change(c, {"current": "dogru-sifre-123", "new": NEW}).status_code == 200
    assert caplog.records, "the failure above is logged, so the capture is live"
    for rec in caplog.records:
        text = rec.getMessage() + (logging.Formatter().formatException(rec.exc_info) if rec.exc_info else "")
        for word in ("dogru-sifre-123", NEW, "yanlis-sifre-789", "kisa-ama-"):
            assert word not in text, (rec.name, word)


# ---------- fix round 1 ----------

def test_an_empty_origin_is_refused_like_a_missing_one(panel_signed_in):
    other = second_session(panel_signed_in.app)
    try:
        r = change(panel_signed_in, {"current": "dogru-sifre-123", "new": NEW}, headers={"Origin": ""})
        assert r.status_code == 403
        r = panel_signed_in.post("/panel/api/sessions/close-others", headers={"Origin": ""})
        assert r.status_code == 403
        assert other.get("/panel/api/schema").status_code == 200          # nobody was signed out
        assert other.post("/panel/login", data={"password": "dogru-sifre-123"}).status_code == 303
    finally:
        other.close()


def test_a_password_that_cannot_be_utf8_is_a_bad_request_before_the_gate(panel_signed_in, panel_data, caplog):
    import logging

    caplog.set_level(logging.DEBUG)
    before = (panel_data / "owner.json").read_bytes()
    gate = panel_signed_in.app.state.gate
    for body in ('{"current": "dogru-sifre-123", "new": "abcdefghij\\ud800"}',
                 '{"current": "dogru-sifre-12\\udfff", "new": "yepyeni-sifre-456"}'):
        r = panel_signed_in.post("/panel/api/password", content=body.encode(),
                                 headers={**SAME_ORIGIN, "Content-Type": "application/json"})
        assert (r.status_code, r.json()) == (400, {"error": "bad_request"}), body
    assert gate.db.execute("SELECT COUNT(*) FROM failures").fetchone()[0] == 0
    assert (panel_data / "owner.json").read_bytes() == before
    for rec in caplog.records:
        text = rec.getMessage() + (logging.Formatter().formatException(rec.exc_info) if rec.exc_info else "")
        for word in ("ud800", "udfff", "\ud800", "\udfff", "abcdefghij", "position", "dogru-sifre"):
            assert word not in text, (rec.name, word)


def test_the_gate_itself_refuses_a_password_that_cannot_be_utf8_without_raising(panel_data):
    from council.panel.gate import Gate

    g = Gate(panel_data)
    try:
        mine = g.sign_in("dogru-sifre-123", now=1.0)
        assert g.change_password(mine, "dogru-sifre-123", "abcdefghij\ud800", now=2.0) == "weak"
        assert g.change_password(mine, "dogru\ud800", "yepyeni-sifre-456", now=2.0) == "wrong"
        assert g.sign_in("x\udfff", now=3.0) is None
    finally:
        g.close()


def test_a_failed_change_logs_no_words_of_the_exception(panel_signed_in, caplog, monkeypatch):
    import logging

    from council import oauth

    def refuse(data_dir, password):
        raise ValueError("leaky " + password)

    caplog.set_level(logging.DEBUG)
    monkeypatch.setattr(oauth, "write_owner", refuse)
    r = change(panel_signed_in, {"current": "dogru-sifre-123", "new": NEW})
    assert r.status_code == 500 and caplog.records
    for rec in caplog.records:
        text = rec.getMessage() + (logging.Formatter().formatException(rec.exc_info) if rec.exc_info else "")
        assert NEW not in text and "leaky" not in text


def test_a_body_declared_larger_than_the_limit_is_refused_unread():
    import asyncio

    from council.panel.app import MAX_BODY, read_limited

    class Declared:
        headers = {"content-length": str(50 * 1024 * 1024)}

        async def stream(self):
            raise AssertionError("the body was read")
            yield b""

    assert asyncio.run(read_limited(Declared(), MAX_BODY)) is None


def test_a_body_without_a_length_is_read_only_up_to_the_limit():
    import asyncio

    from council.panel.app import MAX_BODY, read_limited

    pulled = []

    class Chunked:
        def __init__(self, chunks, length=None):
            self.chunks, self.headers = chunks, ({} if length is None else {"content-length": length})

        async def stream(self):
            for c in self.chunks:
                pulled.append(len(c))
                yield c

    big = Chunked([b"x" * 1024] * 50000)
    assert asyncio.run(read_limited(big, MAX_BODY)) is None
    assert sum(pulled) <= MAX_BODY + 1024                        # stopped at the limit, not at 50 MB
    assert asyncio.run(read_limited(Chunked([b'{"a":', b' 1}']), MAX_BODY)) == b'{"a": 1}'
    assert asyncio.run(read_limited(Chunked([b"x" * 10], length="abc"), MAX_BODY)) == b"x" * 10
    assert asyncio.run(read_limited(Chunked([b"x" * (MAX_BODY + 1)], length="5"), MAX_BODY)) is None  # a lie


def test_a_large_chunked_body_through_the_route_is_a_bad_request(panel_signed_in):
    def chunks():
        for _ in range(2000):
            yield b"x" * 1024

    r = panel_signed_in.post("/panel/api/password", content=chunks(),
                             headers={**SAME_ORIGIN, "Content-Type": "application/json"})
    assert (r.status_code, r.json()) == (400, {"error": "bad_request"})
