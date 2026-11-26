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


def all_bodies(prefix):
    """Seçicisi prefix ile başlayan bütün kuralların gövdeleri (boşluksuz, birleşik)."""
    return "".join(n(b) for s, b in rules(CSS) if n(s).startswith(n(prefix)))


def test_field_has_no_cut():
    assert all_bodies(".c-alan")
    assert "clip-path" not in all_bodies(".c-alan")
    assert "min-height:44px" in "".join(body_of(".c-alan__giris")) or "height:44px" in "".join(body_of(".c-alan__giris"))
    focus = "".join(body_of(".c-alan__giris:focus-visible"))
    assert "var(--kor-metin)" in focus
    assert "var(--cizgi-guclu)" in "".join(body_of(".c-alan__giris"))
    assert "var(--hata)" in all_bodies(".c-alan--hata")


def test_card_cut_only_when_clickable():
    assert "clip-path" not in "".join(body_of(".c-kart"))
    assert "--k:24px" in "".join(body_of(".c-kart--tik"))
    hover = n("".join(blocks(CSS, "(hover:hover)") + blocks(CSS, "(hover: hover)")))
    assert ".c-kart--tik:hover{--k:32px" in hover
    assert "clip-path" in all_bodies(".c-kart--tik::before")


def test_status_vocabulary():
    for d in ("bekliyor", "calisiyor", "tamam", "hafizada", "hata"):
        assert body_of(f'.c-durum[data-durum="{d}"]'), d
    assert "animation:" in "".join(body_of('.c-durum[data-durum="calisiyor"]'))
    rm = n("".join(blocks(CSS, "(prefers-reduced-motion: reduce)") + blocks(CSS, "(prefers-reduced-motion:reduce)")))
    assert '.c-durum[data-durum="calisiyor"]{animation:none' in rm
    assert "border-right-color:currentColor" in rm.split('.c-durum[data-durum="calisiyor"]')[1]
    assert "border-top-color:transparent" in rm.split('.c-durum[data-durum="calisiyor"]')[1]
    assert "270" in CSS  # açıklama: 270° durağan C


def test_badge_shape():
    b = "".join(body_of(".c-rozet"))
    assert "border-start-start-radius:var(--kose-tam)" in b
    assert "border-end-start-radius:var(--kose-tam)" in b
    assert "clip-path" not in b
    for m in ("kor", "basari", "uyari", "hata"):
        assert body_of(f".c-rozet--{m}")


def test_progress_strip():
    assert "block-size:6px" in "".join(body_of(".c-serit")) or "height:6px" in "".join(body_of(".c-serit"))
    fill = "".join(body_of(".c-serit::before"))
    assert "var(--deger)" in fill
    assert "clip-path:polygon(0 0,100% 0,calc(100% - 6px) 100%,0 100%)".replace(" ", "") in fill
    caps = "".join(n(b) for sel, b in rules(CSS) if ".c-halka__iz" in sel and ".c-halka__dolu" in sel)
    assert "stroke-linecap:butt" in caps


def test_check_and_radio_and_link():
    assert "border-radius:50%" in all_bodies(".c-radyo") or "border-radius:var(--kose-tam)" in all_bodies(".c-radyo")
    assert "border-radius" not in "".join(body_of(".c-isaret::before"))
    link = "".join(body_of(".c-baglanti"))
    assert "text-decoration" in link and "var(--murekkep)" in link and "clip-path" not in link


def test_hiding_only_under_js():
    hide = re.compile(r"opacity:0(?![.\d])|visibility:hidden|display:none")
    for s, b in rules(CSS):
        if hide.search(n(b)):
            assert all(p.strip().startswith(".js ") or p.strip() == "[hidden]" for p in s.split(",")), s


def test_idle_button_ring_takes_no_gap():
    idle = "".join(body_of(".c-dugme__halka"))
    assert "margin-inline-end:calc(var(--ara-3)*-1)" in idle.replace(" ", "")
    for sel in ('.c-dugme[aria-busy="true"] .c-dugme__halka', '.c-dugme[data-durum="hafizada"] .c-dugme__halka'):
        assert "margin-inline-end:0" in "".join(body_of(sel)).replace(" ", "")


def test_checked_radio_visible_in_forced_colors():
    fc = CSS[CSS.index("@media (forced-colors: active)", CSS.index(".c-radyo:checked::after")):]
    assert re.search(r"\.c-radyo:checked::after\s*\{[^}]*background:\s*CanvasText", fc)


def test_current_page_dot():
    dot = "".join(body_of('.c-gezinme [aria-current="page"]::before'))
    assert "inline-size:6px" in dot and "block-size:6px" in dot
    assert "border-radius:var(--kose-tam)" in dot or "border-radius:50%" in dot


def test_selected_tab_has_cut():
    sel = "".join(body_of('.c-sekmeler [role="tab"][aria-selected="true"]'))
    assert "clip-path:polygon(0 0,calc(100% - var(--k)) 0,100% var(--k),100% 100%,0 100%)".replace(" ", "") in sel.replace(" ", "")
    plain = "".join(body_of('.c-sekmeler [role="tab"]'))
    assert "clip-path" not in plain and "min-block-size:44px" in plain


def test_menu_opens_with_cut():
    base = "".join(b for s, b in map(lambda r: (r[0], n(r[1])), rules(CSS)) if ".c-menu" in s and ".c-panel" in s and "data-acik" not in s and "@" not in s)
    assert "transition:clip-pathvar(--sure-panel)var(--egri-kapa)" in base
    opened = "".join(b for s, b in map(lambda r: (r[0], n(r[1])), rules(CSS)) if "[data-acik]" in s and ".c-menu" in s)
    assert "transition:clip-pathvar(--sure-panel)var(--egri-ac)" in opened
    assert "clip-path:polygon(" in opened
    rm = "".join(n(b) for blk in blocks(CSS, "(prefers-reduced-motion") for s, b in rules(blk) if ".c-menu" in s)
    assert "transition:0ms" in rm


def test_kor_marks_not_kor_on_kor():
    """Kor dolgu üstündeki durum işareti kor olamaz: düğmede ve rozette kor-ustu."""
    dugme = "".join(body_of('.c-dugme--kor[data-durum="hafizada"] .c-dugme__halka'))
    assert "background:var(--kor-ustu)" in dugme
    rozet = "".join(body_of('.c-rozet--kor .c-durum[data-durum="hafizada"]'))
    assert "border-color:var(--kor-ustu)" in rozet
