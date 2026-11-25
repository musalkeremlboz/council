"""council.css: düz metin denetimleri (yasaklı süs, köşe, düğme ölçüleri, hareket, odak)."""
import re
from pathlib import Path

CSS = (Path(__file__).resolve().parent.parent / "brand" / "css" / "council.css").read_text()


def strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def rules(css):
    """Her kuralı (seçici, gövde) olarak döndürür; @media içindekiler de dahil."""
    css = strip_comments(css)
    out, i = [], 0
    while i < len(css):
        o = css.find("{", i)
        if o < 0:
            break
        head = css[i:o].strip()
        depth, j = 1, o + 1
        while depth:
            depth += {"{": 1, "}": -1}.get(css[j], 0)
            j += 1
        body = css[o + 1:j - 1]
        if head.startswith("@media") or head.startswith("@supports"):
            out += rules(body)
        else:
            out.append((head, body))
        i = j
    return out


def blocks(css, prefix):
    """@media bloklarının gövdeleri."""
    css = strip_comments(css)
    res = []
    for m in re.finditer(r"@media\s*" + re.escape(prefix) + r"[^{]*\{", css):
        depth, j = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(css[j], 0)
            j += 1
        res.append(css[m.end():j - 1])
    return res


def n(s):
    return re.sub(r"\s+", "", s)


def body_of(selector):
    return [n(b) for s, b in rules(CSS) if n(s) == n(selector)]


def test_no_forbidden_decoration():
    c = strip_comments(CSS)
    assert "box-shadow" not in c
    assert "-gradient(" not in c
    assert not re.search(r"#[0-9a-fA-F]{3,8}\b", c)
    assert not re.search(r"\b(rgb|rgba|hsl|hsla)\(", c)


def test_only_allowed_radii():
    vals = re.findall(r"border-radius\s*:\s*([^;}]+)", strip_comments(CSS))
    assert vals
    assert {v.strip() for v in vals} <= {"0", "50%", "var(--kose-0)", "var(--kose-tam)"}


def test_button_sizes():
    assert any("--h:44px;" in b and "--k0:12px;" in b for b in body_of(".c-dugme"))
    assert any("--h:32px;--k0:9px" in b for b in body_of(".c-dugme--k"))
    assert any("--h:56px;--k0:16px" in b for b in body_of(".c-dugme--b"))
    assert "min-width:96px" in "".join(body_of(".c-dugme"))
    coarse = "".join(blocks(CSS, "(pointer:coarse)") + blocks(CSS, "(pointer: coarse)"))
    assert ".c-dugme--k{--h:44px;--k0:12px" in n(coarse)
    assert "@property--k" in n(CSS) and 'syntax:"<length>"' in n(CSS)


def test_button_motion():
    hover = "".join(blocks(CSS, "(hover:hover)") + blocks(CSS, "(hover: hover)"))
    assert ".c-dugme:hover{--k:calc(var(--k0)+4px)" in n(hover)
    active = "".join(body_of(".c-dugme:active"))
    assert "--k:calc(var(--k0)-4px)" in active
    assert "var(--sure-bas)" in active
    base = "".join(body_of(".c-dugme"))
    assert "transition:--kvar(--sure-tepki)var(--egri-ac)" in base
    dis = "".join(body_of(".c-dugme:is(:disabled,[aria-disabled=\"true\"])"))
    assert "--k:0px" in dis


def test_focus_and_fallbacks():
    focus = "".join(body_of(".c-dugme::after"))
    assert "var(--kor-metin)" in focus
    assert body_of(".c-dugme:focus-visible::after")
    assert blocks(CSS, "(forced-colors: active)") or blocks(CSS, "(forced-colors:active)")
    forced = n("".join(blocks(CSS, "(forced-colors: active)") + blocks(CSS, "(forced-colors:active)")))
    assert "outline:2pxsolidButtonText" in forced and "clip-path:none" in forced
    rm = n("".join(blocks(CSS, "(prefers-reduced-motion: reduce)") + blocks(CSS, "(prefers-reduced-motion:reduce)")))
    assert "transition:0ms" in rm or "transition:none" in rm
    assert any("[dir=\"rtl\"]" in s and "scaleX(-1)" in b for s, b in rules(CSS))


def test_fonts_are_local():
    c = strip_comments(CSS)
    for fam in ("Council Halka", "DM Sans", "DM Mono"):
        assert f'font-family: "{fam}"' in c
    assert "http" not in c
    assert all("../font/" in u for u in re.findall(r'url\("([^"]+)"\)', c))
