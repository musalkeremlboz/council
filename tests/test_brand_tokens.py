import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "brand"
_spec = importlib.util.spec_from_file_location("brand_build", BRAND / "build.py")
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)

load_tokens = build.load_tokens
contrast = build.contrast
T = load_tokens(BRAND / "tokens.json")


def by_name(family):
    return {t["name"]: t["value"] for t in T[family]["tokens"]}


def test_every_family_is_a_token_list():
    names = []
    for fam in ("color", "spacing", "radius", "motion"):
        assert isinstance(T[fam]["tokens"], list)
        for t in T[fam]["tokens"]:
            assert t["name"] and t["value"] and t["usage"]
            names.append(t["name"])
    assert [t["id"] for t in T["color"]["themes"]] == ["light", "dark"]
    assert len(names) == len(set(names))


def test_spec_values():
    c = by_name("color")
    assert c["kor"] == {"light": "#E8421F", "dark": "#E8421F"}
    assert c["kor-ustu"] == {"light": "#111416", "dark": "#111416"}
    assert c["murekkep-bas"] == {"light": "#2E3438", "dark": "#D3D7D2"}
    assert c["kor-bas"] == {"light": "#F25A38", "dark": "#F25A38"}
    assert c["pasif-zemin"] == {"light": "#E2E4E1", "dark": "#23282B"}
    assert c["pasif-yazi"] == {"light": "#5B6166", "dark": "#9AA0A4"}
    assert c["ton"] == {"light": "rgb(17 20 22 / .07)", "dark": "rgb(244 245 243 / .08)"}
    old = {
        "zemin": ("#F4F5F3", "#111416"), "yuzey": ("#FFFFFF", "#1A1E21"),
        "yuzey-2": ("#E9EBE8", "#23282C"), "murekkep": ("#111416", "#F4F5F3"),
        "murekkep-2": ("#4A5157", "#B4BBC0"), "murekkep-3": ("#656D74", "#8A9299"),
        "cizgi": ("#D5D8D4", "#2E3438"), "cizgi-guclu": ("#848B91", "#6A737A"),
        "kor": ("#E8421F", "#E8421F"), "kor-metin": ("#C2330F", "#FF7A5C"),
        "kor-zemin": ("#FBE4DD", "#3A1A12"), "kor-ustu": ("#111416", "#111416"),
        "basari": ("#1F7A4D", "#4CC38A"), "uyari": ("#8A5A00", "#E3B341"),
        "hata": ("#B3123F", "#FF6B8B"),
    }
    for name, (light, dark) in old.items():
        assert c[name] == {"light": light, "dark": dark}, name
    assert set(by_name("radius")) == {"kose-0", "kose-tam"}
    assert by_name("spacing") == {f"ara-{n}": f"{v}px" for n, v in
                                  zip((1, 2, 3, 4, 6, 8, 12, 16), (4, 8, 12, 16, 24, 32, 48, 64))}
    m = by_name("motion")
    assert m == {"sure-bas": "70ms", "sure-tepki": "140ms", "sure-panel": "240ms",
                 "sure-sahne": "420ms", "sure-gecis-en-cok": "840ms",
                 "egri-ac": "cubic-bezier(.2,0,0,1)", "egri-kapa": "cubic-bezier(.4,0,1,1)"}


def _styles():
    return {s["name"]: (g["family"], s["fontSize"], s["lineHeight"], s["fontWeight"], s.get("letterSpacing"))
            for g in T["type"]["groups"] for s in g["styles"]}


def test_text_styles():
    assert _styles() == {
        "baslik-xl": ("display", "64px", 1.05, 500, "0.04em"),
        "baslik-l": ("display", "40px", 1.1, 500, "0.04em"),
        "baslik-m": ("display", "24px", 1.2, 500, "0.05em"),
        "etiket": ("sans", "12px", 1.3, 600, "0.08em"),
        "govde-l": ("sans", "18px", "28px", 400, None),
        "govde": ("sans", "16px", "24px", 400, None),
        "govde-k": ("sans", "14px", "20px", 400, None),
        "kod": ("mono", "14px", "22px", 400, None),
    }
    assert [(f["family"], f["file"], f["weight"]) for f in T["type"]["fonts"]] == [
        ("Council Halka", "fonts/CouncilHalka.woff2", "500"), ("DM Sans", "fonts/DMSans.ttf", "100 1000"),
        ("DM Mono", "fonts/DMMono-Regular.ttf", "400"), ("DM Mono", "fonts/DMMono-Medium.ttf", "500")]


def test_type_follows_page_grammar():
    ad = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
    ty = T["type"]
    assert isinstance(ty["families"], dict) and set(ty["families"]) == {"display", "sans", "mono"}
    for f in ty["fonts"]:
        assert {"family", "file", "weight"} <= set(f) and isinstance(f["weight"], str)
    for g in ty["groups"]:
        assert {"name", "family", "styles"} <= set(g) and g["family"] in ty["families"]
        for s in g["styles"]:
            assert {"name", "fontSize", "lineHeight", "fontWeight"} <= set(s)
            assert ad.match(s["name"])


def test_contrast_function():
    assert round(contrast("#111416", "#F4F5F3"), 1) >= 16.9  # brief said 17.0; true WCAG ratio is 16.91
    assert contrast("#FFFFFF", "#E8421F") < 4.5
    assert contrast("#111416", "#E8421F") >= 4.5


def test_no_contrast_failures():
    assert build.contrast_failures(T) == []
    pairs = {(f, b): m for f, b, m in build.CONTRAST_PAIRS}
    for fg in ("murekkep", "murekkep-2", "murekkep-3", "kor-metin", "basari", "uyari", "hata"):
        for bg in ("zemin", "yuzey"):
            assert pairs[(fg, bg)] == 4.5
    assert pairs[("kor-ustu", "kor")] == 4.5
    assert pairs[("kor-ustu", "kor-bas")] == 4.5
    assert pairs[("pasif-yazi", "pasif-zemin")] == 4.5
    assert pairs[("cizgi-guclu", "zemin")] == 3.0


def test_generated_css_is_current():
    css = (BRAND / "css" / "tokens.css").read_text(encoding="utf-8")
    assert build.css_from_tokens(T) == css
    assert css.splitlines()[0] == "/* COUNCIL — generated from tokens.json */"
    assert ':root[data-theme="dark"]' in css
