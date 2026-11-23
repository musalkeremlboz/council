"""The page itself: what the browser is given, and what it may never do with the data."""
import html
import json
import re
import tomllib
from pathlib import Path

SCRIPTS = ("theme.js", "panel.js", "schema.js", "today.js", "health.js", "notes.js", "map.js", "releases.js",
           "settings.js")
NEVER_IN_JS = ("innerHTML", "outerHTML", "document.write", "insertAdjacentHTML", "eval(", "new Function")


def test_the_page_loads_nothing_from_another_host_and_never_builds_html_from_data(static_dir):
    for f in static_dir.rglob("*"):
        if f.suffix in (".html", ".css", ".js"):
            text = f.read_text(encoding="utf-8")
            assert "http://" not in text and "https://" not in text and "//fonts." not in text, f.name
            if f.suffix == ".js":
                for word in NEVER_IN_JS:
                    assert word not in text, (f.name, word)


def test_fonts_and_scripts_are_served_and_the_shell_names_the_seven_sections(panel_signed_in):
    for name in ("panel.css", *SCRIPTS, "fonts/CouncilHalka.woff2"):
        assert panel_signed_in.get(f"/panel/static/{name}").status_code == 200, name
    assert panel_signed_in.get("/panel/static/fonts/yok-boyle-bir-dosya.woff2").status_code == 404
    page = panel_signed_in.get("/panel/").text
    assert all(w in page for w in ("Şema", "Bugün", "Sağlık", "Harita", "Notlar", "Güncellemeler", "Ayarlar"))
    for fragment in ("#sema", "#bugun", "#saglik", "#harita", "#notlar", "#guncellemeler", "#ayarlar"):
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


TEXT_FACES = {"DM Sans": ("fonts/DMSans.ttf",), "DM Mono": ("fonts/DMMono-Regular.ttf", "fonts/DMMono-Medium.ttf")}


def test_the_text_faces_are_shipped_with_their_licences_and_served(static_dir, panel_signed_in):
    css = (static_dir / "panel.css").read_text(encoding="utf-8")
    rules = re.findall(r"@font-face\s*{[^}]*}", css)
    for family, files in TEXT_FACES.items():
        for name in files:
            assert any(f'font-family: "{family}"' in rule and f'url("{name}")' in rule for rule in rules), name
            data = (static_dir / name).read_bytes()
            assert data[:4] == b"\x00\x01\x00\x00", name  # a TrueType file, not an error page saved under its name
            served = panel_signed_in.get(f"/panel/static/{name}")
            assert served.status_code == 200 and served.content == data, name
    for licence in ("fonts/OFL-DMSans.txt", "fonts/OFL-DMMono.txt"):
        assert "SIL Open Font License" in (static_dir / licence).read_text(encoding="utf-8"), licence


def test_the_schema_no_longer_steps_nor_loops_its_dot(static_dir):
    js = (static_dir / "schema.js").read_text(encoding="utf-8")
    css = (static_dir / "panel.css").read_text(encoding="utf-8")
    assert "STEP_EVERY" not in js and "function step(" not in js
    assert "@keyframes akis" not in css and ".nokta.akar" not in css
    dot_rules = [r for r in re.findall(r"[^{}]*\{[^}]*\}", css) if ".nokta" in r.split("{")[0]]
    assert dot_rules, "the travelling dot has its rule"
    assert not any("infinite" in r for r in dot_rules)
    # the dot is moved by the Web Animations API on transform, not by a CSS animation
    assert ".animate(" in js and "transform" in js


def test_today_marks_are_no_longer_buttons_and_the_session_rows_are(static_dir):
    js = (static_dir / "today.js").read_text(encoding="utf-8")
    css = (static_dir / "panel.css").read_text(encoding="utf-8")
    mark = re.search(r'el\("(\w+)", \{[^{]*?class: "isaret.*?\}\)\);', js, re.S)
    assert mark, "the strip draws its marks"
    assert mark.group(1) == "span"
    assert '"aria-hidden": "true"' in mark.group(0) and "onclick" not in mark.group(0)
    # the session rows open their events in place and say so to a screen reader
    assert "aria-expanded" in js and "aria-controls" in js
    # opening is measured and animated, never a jump to height: auto; with reduced motion it opens at once
    assert ".animate(" in js and "P.reducedMotion" in js
    row = re.search(r"\.oturum-satir\s*\{[^}]*\}", css)
    assert row and "min-height: 44px" in row.group(0)


def test_static_files_are_revalidated_and_pages_and_answers_are_never_stored(panel_signed_in):
    # a page served no-store must never run with an old script kept from before an update
    for name in ("today.js", "schema.js", "panel.css", "fonts/CouncilHalka.woff2"):
        first = panel_signed_in.get(f"/panel/static/{name}")
        assert first.status_code == 200 and first.headers["cache-control"] == "no-cache", name
        again = panel_signed_in.get(f"/panel/static/{name}", headers={"If-None-Match": first.headers["etag"]})
        assert again.status_code == 304, name
    assert panel_signed_in.get("/panel/").headers["cache-control"] == "no-store"
    assert panel_signed_in.get("/panel/api/today").headers["cache-control"] == "no-store"


# ---------- the theme ----------

def _blocks(css: str, selector: str) -> list[str]:
    """The bodies of every rule whose selector is exactly `selector` (nested in an at-rule or not)."""
    return [m.group(1) for m in re.finditer(r"(?:^|[{};])\s*" + re.escape(selector) + r"\s*\{([^{}]*)\}", css)]


def _tokens(body: str) -> dict:
    return dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", body))


def test_the_dark_theme_defines_every_token_twice_once_by_choice_and_once_by_the_system(static_dir):
    css = re.sub(r"/\*.*?\*/", "", (static_dir / "panel.css").read_text(encoding="utf-8"), flags=re.S)
    light = _tokens(_blocks(css, ":root")[0])
    chosen = _blocks(css, ':root[data-theme="dark"]')
    system = re.search(r"@media\s*\(prefers-color-scheme:\s*dark\)\s*\{\s*:root:not\(\[data-theme=\"light\"\]\)\s*\{([^{}]*)\}", css)
    assert len(chosen) == 1 and system, "a dark block for a choice and one for the system"
    colours = {k for k, v in light.items() if v.strip().startswith("#")}
    for body in (chosen[0], system.group(1)):
        dark = _tokens(body)
        assert set(dark) == colours, set(dark) ^ colours
        assert dark["--zemin"].upper() == "#111416" and dark["--murekkep"].upper() == "#F4F5F3"
        assert dark["--vurgu"].upper() == "#E8421F"
    assert _tokens(chosen[0]) == _tokens(system.group(1))


# every CSS named colour (CSS Color 4), so a script cannot slip one in under a name
NAMED_COLOURS = set("""aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet brown
burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan darkgoldenrod
darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen
darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue
firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew
hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan
lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue lightslategray
lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine mediumblue mediumorchid
mediumpurple mediumseagreen mediumslateblue mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream
mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen
paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red rosybrown royalblue
saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey snow springgreen
steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow yellowgreen""".split())


def test_no_script_names_a_colour_of_its_own(static_dir):
    # every colour a script uses is a token read from the stylesheet when it draws, so both themes are right
    for name in SCRIPTS:
        text = (static_dir / name).read_text(encoding="utf-8")
        if name == "map.js":
            # the one exception: the stand-ins after each stage token, used only when no stylesheet answers
            fallback = re.search(r"var TONES = \{.*?\};", text, re.S)
            assert fallback, "map.js keeps its stage tokens in TONES"
            text = text.replace(fallback.group(0), "")
        assert not re.search(r"#[0-9A-Fa-f]{6}\b|#[0-9A-Fa-f]{3}\b|rgba?\(|hsla?\(|hwb\(|lab\(|lch\(", text), name
        quoted = set(re.findall(r"""["']([a-z]+)["']""", text))
        assert not quoted & NAMED_COLOURS, (name, quoted & NAMED_COLOURS)


def test_nothing_is_picked_from_a_native_dropdown(static_dir):
    # the owner's rule: whatever opens on a click is drawn with the panel's own elements
    for f in static_dir.glob("*"):
        if f.suffix in (".html", ".js"):
            text = f.read_text(encoding="utf-8")
            assert "<select" not in text and 'createElement("select")' not in text and 'el("select"' not in text, f.name
    js = (static_dir / "map.js").read_text(encoding="utf-8")
    for word in ('role: "combobox"', '"aria-expanded"', '"aria-controls"', 'role: "listbox"', 'role: "option"',
                 '"aria-activedescendant"', "ArrowDown", "ArrowUp", "Escape", "Enter"):
        assert word in js, word


def test_both_pages_choose_their_theme_before_the_stylesheet(panel):
    from conftest import PASSWORD

    login = panel.get("/panel/login").text
    assert panel.post("/panel/login", data={"password": PASSWORD}).status_code == 303
    for page in (login, panel.get("/panel/").text):
        head = page.split("</head>")[0]
        assert '<meta name="color-scheme" content="light dark">' in head
        theme = head.find('<script src="/panel/static/theme.js"></script>')  # not deferred: it runs before paint
        assert 0 < theme < head.find("panel.css"), "theme.js comes first"
        # the mark's ink follows the theme: no fixed ink or ground colour in the drawing
        assert "#111416" not in page and "#F4F5F3" not in page.upper()


def test_the_settings_section_is_drawn_with_the_panels_own_buttons(static_dir):
    js = (static_dir / "settings.js").read_text(encoding="utf-8")
    assert "P.sections.settings" in js and "aria-pressed" in js
    assert '"select"' not in js and "<select" not in js
    for key in ("theme_system", "theme_light", "theme_dark", "theme_title"):
        assert "t." + key in js, key
    panel = (static_dir / "panel.js").read_text(encoding="utf-8")
    assert 'ayarlar: "settings"' in panel


def test_the_password_form_is_a_real_form_that_password_managers_know(static_dir):
    js = (static_dir / "settings.js").read_text(encoding="utf-8")
    assert 'el("form"' in js and "preventDefault" in js
    assert js.count('type: "password"') == 3
    assert 'autocomplete: "current-password"' in js and js.count('autocomplete: "new-password"') == 2
    assert "P.post(" in js and "P.get(" not in js  # the shell asks for the settings; the page only posts
    for key in ("password_title", "password_claude", "password_rule", "open_sessions_title",
                "open_sessions_close", "open_sessions_confirm", "open_sessions_cancel", "password_remind"):
        assert "t." + key in js, key
    for word in ("confirm(", "alert(", "prompt(", "localStorage", "sessionStorage"):
        assert word not in js, word


def test_the_page_posts_with_its_own_origin_and_cookie_and_a_401_signs_out(static_dir):
    panel = (static_dir / "panel.js").read_text(encoding="utf-8")
    post = panel[panel.index("function post("):]
    post = post[:post.index("\n  }\n")]
    assert 'method: "POST"' in post and 'credentials: "same-origin"' in post and '"Content-Type": "application/json"' in post
    assert "401" in post and "/login" in post
    assert "post: post" in panel


def test_the_settings_section_asks_the_server_and_draws_without_its_answer(static_dir):
    js = (static_dir / "settings.js").read_text(encoding="utf-8")
    assert "local: true" not in js and "drawsWithout: true" in js
    panel = (static_dir / "panel.js").read_text(encoding="utf-8")
    assert "drawsWithout" in panel


def test_the_settings_copy_names_the_minimum_from_the_constant(monkeypatch):
    from council import oauth
    from council.panel import text_tr

    monkeypatch.setattr(oauth, "MIN_PASSWORD", 14)
    ui = text_tr.ui()
    assert ui["password_min"] == 14 and "14 karakter" in ui["password_rule"] and "Claude" in ui["password_claude"]


def test_the_panels_turkish_copy_says_sifre_never_parola(panel):
    from council.panel import text_tr

    words = " ".join(str(v) for v in {**text_tr.texts(), **text_tr.ui()}.values())
    assert "arola" not in words
    page = panel.get("/panel/login").text
    assert "Sahip şifresi" in page and "arola" not in page
    assert "arola" not in panel.post("/panel/login", data={"password": "yanlis"}).text


def _dict_literals(tree):
    import ast
    return [node for node in ast.walk(tree) if isinstance(node, ast.Dict)]


def test_no_text_key_is_defined_twice_nor_given_a_second_meaning_by_an_override():
    import ast
    from council.panel import text_tr

    tree = ast.parse(Path(text_tr.__file__).read_text(encoding="utf-8"))
    for node in _dict_literals(tree):
        keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
        assert len(keys) == len(set(keys)), sorted({k for k in keys if keys.count(k) > 1})
    # texts() and ui() spread a base table and add sentences built from constants; none may replace a base key
    for base, built in ((text_tr.TEXTS, text_tr.texts), (text_tr.PAGE, text_tr.ui)):
        func = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == built.__name__)
        literal = next(n for n in ast.walk(func) if isinstance(n, ast.Dict) and None in n.keys)
        added = {k.value for k in literal.keys if isinstance(k, ast.Constant)}
        assert not added & set(base), sorted(added & set(base))


def test_today_and_settings_each_say_their_own_sentence_above_their_sessions(static_dir):
    from council.panel import text_tr

    ui = text_tr.ui()
    assert ui["sessions_lede"].startswith("En yeni oturum üstte")
    assert "şifre" in ui["open_sessions_lede"] and ui["open_sessions_lede"] != ui["sessions_lede"]
    settings = (static_dir / "settings.js").read_text(encoding="utf-8")
    assert "t.sessions_" not in settings and "t.open_sessions_lede" in settings
    today = (static_dir / "today.js").read_text(encoding="utf-8")
    assert "t.sessions_lede" in today and "t.open_sessions_" not in today


def _top_level_rules(css: str) -> list[str]:
    """The selectors of every rule outside an @-block (media queries legitimately restate a rule)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, depth, start, at = [], 0, 0, []
    for i, ch in enumerate(css):
        if ch == "{":
            selector = css[start:i].strip()
            if depth == 0 and not selector.startswith("@"):
                out.append(selector)
            at.append(selector.startswith("@"))
            depth += 1
            start = i + 1
        elif ch == "}":
            depth -= 1
            at.pop()
            start = i + 1
        elif ch == ";" and (depth == 0 or (at and at[-1])):
            start = i + 1
    return out


def test_no_class_is_declared_as_a_standalone_rule_twice(static_dir):
    selectors = _top_level_rules((static_dir / "panel.css").read_text(encoding="utf-8"))
    standalone = [s for s in selectors if re.fullmatch(r"\.[\w-]+", s)]
    twice = sorted({s for s in standalone if standalone.count(s) > 1})
    assert twice == [], twice


def test_todays_open_session_has_no_scroll_box_of_its_own(static_dir):
    css = (static_dir / "panel.css").read_text(encoding="utf-8")
    today = (static_dir / "today.js").read_text(encoding="utf-8")
    settings = (static_dir / "settings.js").read_text(encoding="utf-8")
    assert "olay-listesi" not in today and '"oturum-olaylari"' in today
    assert '"oturum-sayi"' not in settings and '"acik-oturum-sayi"' in settings
    selectors = _top_level_rules(css)
    for name in ("oturum-olaylari", "olay-listesi", "oturum-sayi", "acik-oturum-sayi"):
        assert sum(1 for s in selectors if re.search(r"\." + name + r"(?![\w-])", s)) >= 1, name
    # the schema's list keeps its own scroll; Today's list shares no rule with it and sets no height or scroll
    for s in selectors:
        if re.search(r"\.oturum-olaylari(?![\w-])", s):
            assert "olay-listesi" not in s, s
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", re.sub(r"/\*.*?\*/", "", css, flags=re.S)):
        if re.search(r"\.oturum-olaylari(?![\w-])", selector):
            assert "max-height" not in body and "overflow" not in body, selector


def test_the_drawing_leaves_room_for_the_focus_ring_of_a_block_at_its_edge(static_dir):
    """The drawing clips the travelling dot and the lanes box scrolls: both keep 4px of room (outline 2px at
    offset 2px) where a block touches their edge, given back by a negative margin so nothing moves."""
    css = re.sub(r"/\*.*?\*/", "", (static_dir / "panel.css").read_text(encoding="utf-8"), flags=re.S)
    drawing = next(b for b in _blocks(css, ".cizim") if "overflow" in b)
    assert "overflow: hidden" in drawing and "padding: 4px" in drawing and "margin: -4px" in drawing
    lanes = next(b for b in _blocks(css, ".seritler") if "overflow" in b)
    assert "padding: 4px 0 8px 4px" in lanes and "margin-left: -4px" in lanes
