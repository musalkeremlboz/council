"""The page itself: what the browser is given, and what it may never do with the data."""
import html
import json
import re
import tomllib
from pathlib import Path

SCRIPTS = ("panel.js", "schema.js", "today.js", "health.js", "notes.js", "map.js", "releases.js")
NEVER_IN_JS = ("innerHTML", "outerHTML", "document.write", "insertAdjacentHTML", "eval(", "new Function")


def test_the_page_loads_nothing_from_another_host_and_never_builds_html_from_data(static_dir):
    for f in static_dir.rglob("*"):
        if f.suffix in (".html", ".css", ".js"):
            text = f.read_text(encoding="utf-8")
            assert "http://" not in text and "https://" not in text and "//fonts." not in text, f.name
            if f.suffix == ".js":
                for word in NEVER_IN_JS:
                    assert word not in text, (f.name, word)


def test_fonts_and_scripts_are_served_and_the_shell_names_the_six_sections(panel_signed_in):
    for name in ("panel.css", *SCRIPTS, "fonts/CouncilHalka.woff2"):
        assert panel_signed_in.get(f"/panel/static/{name}").status_code == 200, name
    assert panel_signed_in.get("/panel/static/fonts/yok-boyle-bir-dosya.woff2").status_code == 404
    page = panel_signed_in.get("/panel/").text
    assert all(w in page for w in ("Şema", "Bugün", "Sağlık", "Harita", "Notlar", "Güncellemeler"))
    for fragment in ("#sema", "#bugun", "#saglik", "#harita", "#notlar", "#guncellemeler"):
        assert f'href="{fragment}"' in page
    for name in SCRIPTS:
        assert f'src="/panel/static/{name}"' in page
    for url in ("/panel/static/../gate.py", "/panel/static/%2e%2e/gate.py", "/panel/static/fonts/%2e%2e/%2e%2e/gate.py"):
        assert panel_signed_in.get(url).status_code in (400, 404), url


def _page_data(page: str) -> tuple[str, dict]:
    base = re.search(r'data-base="([^"]*)"', page).group(1)
    texts = json.loads(html.unescape(re.search(r'data-texts="([^"]*)"', page).group(1)))
    return html.unescape(base), texts


def test_the_page_is_told_its_base_and_its_texts(panel_signed_in):
    from council import context
    from council.panel.mechanism import _number

    base, texts = _page_data(panel_signed_in.get("/panel/").text)
    assert base == "/panel"
    for key in ("placeholder", "offline", "live_on", "live_off", "dot_on", "dot_off", "change_block",
                "at_limit_toggle", "at_limit_definition", "lane_start", "lane_pointer"):
        assert texts[key], key
    # a sentence that carries a rule is built from the code's own numbers
    rule = texts["at_limit_definition"]
    assert _number(context.MESSAGE_BUDGET) in rule and _number(context.MIN_ROOM) in rule


def test_every_text_a_script_names_is_given_to_the_page(static_dir):
    from council.panel import text_tr

    texts = text_tr.ui()
    for name in SCRIPTS:
        for key in set(re.findall(r"\bt\.([a-z_0-9]+)", (static_dir / name).read_text(encoding="utf-8"))):
            assert key in texts, (name, key)


def test_a_panel_at_the_root_tells_the_page_an_empty_base(panel_data):
    from starlette.testclient import TestClient

    from conftest import PASSWORD
    from council.panel.app import build

    app = build(panel_data, base_path="/", background=False)
    client = TestClient(app, base_url="http://127.0.0.1:8766", follow_redirects=False)
    try:
        assert client.post("/login", data={"password": PASSWORD}).status_code == 303
        base, _ = _page_data(client.get("/").text)
        assert base == ""
        assert client.get("/static/fonts/CouncilHalka.woff2").status_code == 200
    finally:
        client.close()
        app.state.gate.close()


def test_the_scripts_carry_no_turkish_copy_of_their_own(static_dir):
    # every word the owner reads comes from text_tr.py; the scripts only place it
    for name in SCRIPTS:
        text = (static_dir / name).read_text(encoding="utf-8")
        assert not re.search("[çğıöşüÇĞİÖŞÜ]", text), name


def test_a_wheel_would_carry_the_static_files():
    pyproject = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text(encoding="utf-8"))
    data = pyproject["tool"]["setuptools"]["package-data"]["council.panel"]
    assert {"static/*", "static/fonts/*", "releases.json"} <= set(data)


def test_every_file_the_stylesheet_names_is_shipped(static_dir):
    css = (static_dir / "panel.css").read_text(encoding="utf-8")
    named = re.findall(r"""url\(\s*["']?([^"')]+)["']?\s*\)""", css)
    assert named, "the stylesheet names its display face"
    for name in named:
        assert (static_dir / name).is_file(), name
