import json

import pytest
from starlette.testclient import TestClient

from council import cli
from council.oauth import hash_password
from council.panel.app import SECTIONS, build

PAGES = ["/panel/"]
API = [f"/panel/api/{s}" for s in ("schema", "today", "health", "map", "notes", "releases")]


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
    assert SECTIONS == ("schema", "today", "health", "map", "notes", "releases")


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
