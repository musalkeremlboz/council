"""COUNCIL promo site generator: site/metin + site/veri + brand/ → site/cikti/ (four pages, one hashed asset folder).

    python site/build.py [--cikti DIR]

Stdlib only. The output is reproducible (no dates, sorted walks) and committed.
"""
import argparse
import ast
import base64
import hashlib
import html
import importlib.util
import json
import re
import shutil
import sys
import tempfile
import tomllib
from pathlib import Path
from string import Template

KOK = Path(__file__).resolve().parent.parent
SITE = KOK / "site"
BRAND = KOK / "brand"
SABLON = SITE / "sablon"
METIN = SITE / "metin"
VERI = SITE / "veri"
CIKTI = SITE / "cikti"
SUNUCU = KOK / "council" / "server.py"
OZELLIKLER = BRAND / "js" / "ozellikler.json"
SAHNE_METIN = BRAND / "js" / "metin.json"
LOGO_KUR = BRAND / "logo" / "council-logo-kur.html"

SITE_URL = "https://council.systems"
DILLER = ("tr", "en")
SAYFALAR = {"ana": {"tr": "", "en": "en/"}, "hafiza": {"tr": "hafiza/", "en": "en/memory/"}}
GITHUB = "https://github.com/musalkeremlboz/council"
OGRENME_ARACLARI = ("council_rule", "council_skill", "council_skill_feedback", "council_unlearn")
OZET_YER = "__ozet__"   # stands for the asset hash until the assets are copied
YARDIMCI_DURUMLARI = {"tam": "tam", "kullanımda": "kullanimda", "denenmedi": "denenmedi"}   # veri/yardimcilar.json -> data-durum, metin key
KUR_UNIX = "curl -fsSL https://raw.githubusercontent.com/musalkeremlboz/council/main/install.sh | sh"
KUR_WINDOWS = "irm https://raw.githubusercontent.com/musalkeremlboz/council/main/install.ps1 | iex"


def _brand_denetle():
    """brand/denetle.py by path."""
    spec = importlib.util.spec_from_file_location("brand_denetle", BRAND / "denetle.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _brand_build():
    """brand/build.py by path (brand is not a package)."""
    spec = importlib.util.spec_from_file_location("brand_build", BRAND / "build.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _json(yol: Path):
    return json.loads(yol.read_text(encoding="utf-8"))


def _anahtarlar(veri, on: str = "") -> set[str]:
    """Every nested key path of a text tree ("a.b.c"; list items by index)."""
    if isinstance(veri, dict):
        cocuklar = veri.items()
    elif isinstance(veri, list):
        cocuklar = ((str(i), v) for i, v in enumerate(veri))
    else:
        return set()
    out = set()
    for k, v in cocuklar:
        yol = f"{on}.{k}" if on else k
        out |= {yol} | _anahtarlar(v, yol)
    return out


def metin_yukle() -> dict[str, dict]:
    """site/metin/<dil>.json for every language; the key trees must match the first language's."""
    metin = {dil: _json(METIN / f"{dil}.json") for dil in DILLER}
    temel = _anahtarlar(metin[DILLER[0]])
    for dil in DILLER[1:]:
        kendi = _anahtarlar(metin[dil])
        for tur, fark in (("eksik", temel - kendi), ("fazla", kendi - temel)):
            if fark:
                raise SystemExit(f"metin: {dil} {tur} anahtar: {min(fark)}")
    return metin


def surum() -> str:
    return tomllib.loads((KOK / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def _arac_mi(dekorator: ast.expr) -> bool:
    hedef = dekorator.func if isinstance(dekorator, ast.Call) else dekorator
    return (isinstance(hedef, ast.Attribute) and hedef.attr == "tool"
            and isinstance(hedef.value, ast.Name) and hedef.value.id == "mcp")


def arac_sayilari() -> tuple[int, int]:
    """(core, learning) tool counts from the @mcp.tool functions in council/server.py (read with ast, never imported)."""
    agac = ast.parse(SUNUCU.read_text(encoding="utf-8"))
    adlar = [d.name for d in ast.walk(agac)
             if isinstance(d, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(map(_arac_mi, d.decorator_list))]
    for ad in OGRENME_ARACLARI:
        if ad not in adlar:
            raise SystemExit(f"arac_sayilari: {ad} {SUNUCU.name} içinde yok")
    return len(adlar) - len(OGRENME_ARACLARI), len(OGRENME_ARACLARI)


def ozellikler(dil: str, yol: Path = OZELLIKLER) -> list[dict]:
    """The six features as {"ad", "aciklama", "durum"} in one language; an unnamed feature has ad None."""
    out = []
    for o in _json(yol):
        ad, aciklama = o["ad"], o.get("aciklama")
        if ad is not None and dil != "tr":
            if dil not in o:
                raise SystemExit(f"ozellikler: {ad} için {dil} yok")
            ad, aciklama = o[dil]["ad"], o[dil]["aciklama"]
        out.append({"ad": ad, "aciklama": aciklama, "durum": o["durum"]})
    return out


def glif_altkumesi(sayfalar_html: list[str]) -> str:
    """The glyph subset (JSON text) for every [data-yazi-kur] text and logo word on the given pages."""
    bb = _brand_build()
    metinler = [m for h in sayfalar_html for m in bb.kurulan_metinler(h)]
    alt = bb.glif_altkumesi(_json(bb.GLIFLER), metinler)
    return json.dumps(alt, ensure_ascii=False, separators=(",", ":")) + "\n"


def _varliklar() -> list[tuple[str, Path]]:
    """(path under varlik/<ozet>/, source) for every copied asset; css/ and font/ stay siblings for ../font/ urls."""
    secim = [
        ("css", BRAND / "css", ["*.css"]),
        ("font", BRAND / "font", ["*.woff2", "*.ttf", "OFL-*.txt"]),
        ("logo", BRAND / "logo", ["*.svg", "*.png"]),
        ("simge", BRAND / "simge", ["*.svg"]),
        ("js/sahne", BRAND / "js" / "sahne", ["ortak.js", "yazi-kur.js"]),   # the identity moment; the other scenes are not on the site
        ("js", BRAND / "js", ["denetim.js"]),
        ("css", SABLON, ["site.css", "masa.css"]),   # masa.css is loaded by the home page only
        ("js", SABLON, ["site.js", "masa.js"]),      # masa.js is imported by site.js where the canvas is
    ]
    out = []
    for hedef, kaynak, desenler in secim:
        for desen in desenler:
            for yol in sorted(kaynak.glob(desen)):
                if "kasa" not in yol.name:   # Kasa is archived and stays off the site
                    out.append((f"{hedef}/{yol.name}", yol))
    return out


def _bayt(yol: Path) -> bytes:
    """File bytes; text files with LF line ends, so a CRLF checkout builds the same site."""
    veri = yol.read_bytes()
    return veri if yol.suffix in (".woff2", ".ttf", ".png") else veri.replace(b"\r\n", b"\n")


def varlik_kopyala(hedef: Path, glifler: str) -> str:
    """Copy the assets and the glyph subset into hedef/varlik/<ozet>/ (old varlik/* removed first); returns <ozet>."""
    dosyalar = {ad: _bayt(yol) for ad, yol in _varliklar()}
    dosyalar["glifler.json"] = glifler.encode("utf-8")
    ozet = hashlib.sha256()
    for ad in sorted(dosyalar):
        ozet.update(f"{ad}\0{len(dosyalar[ad])}\0".encode("utf-8"))
        ozet.update(dosyalar[ad])
    ozet = ozet.hexdigest()[:10]
    varlik = hedef / "varlik"
    if varlik.exists():
        for eski in sorted(varlik.iterdir()):
            shutil.rmtree(eski) if eski.is_dir() else eski.unlink()
    for ad in sorted(dosyalar):
        yol = varlik / ozet / ad
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_bytes(dosyalar[ad])
    return ozet


def _e(metin: str) -> str:
    return html.escape(metin, quote=True)


def _kok(yol: str) -> str:
    """Relative prefix from a page folder ("", "en/", "en/memory/") back to the site root."""
    return "../" * yol.count("/")


def _bag(kimden: str, kime: str) -> str:
    return _kok(kimden) + kime or "./"


def _cizgi_sinirlari(d: str) -> tuple[float, float, float, float]:
    """(x0, y0, x1, y1) of the points in an absolute M/L/H/V/Q/Z path (control points included)."""
    xs, ys, komut, sayilar = [], [], "", []
    for t in re.findall(r"[A-Za-z]|-?\d+(?:\.\d+)?", d):
        if t.isalpha():
            if t not in "MLHVQZ":
                raise SystemExit(f"yazi_svg: desteklenmeyen yol komutu {t}")
            komut, sayilar = t, []
            continue
        sayilar.append(float(t))
        if komut in "MLQ" and len(sayilar) == 2:
            xs.append(sayilar[0]); ys.append(sayilar[1]); sayilar = []
        elif komut == "H":
            xs.append(sayilar[0]); sayilar = []
        elif komut == "V":
            ys.append(sayilar[0]); sayilar = []
    return min(xs), min(ys), max(xs), max(ys)


def yazi_svg(ad: str) -> str:
    """The header wordmark: the logo's text group (data-kur="yazi") from brand/logo/council-logo-kur.html as its own
    inline SVG. The mark is dropped (amblem_svg() does the opposite) and the view box shrinks to the letters, measured
    from the group's transform and glyph paths. Letters are outlines, so the 24 px floor of Council Halka text does not
    apply; the identity moment can still build them (the group keeps data-metin and data-ara)."""
    bulunan = re.search(r'<g data-kur="yazi"[^>]*transform="translate\(([\d.]+) ([\d.]+)\) scale\(([\d.]+) -([\d.]+)\)".*?</g>',
                        LOGO_KUR.read_text(encoding="utf-8"), re.S)
    if not bulunan:
        raise SystemExit(f"yazi_svg: {LOGO_KUR.name} içinde logo yazısı grubu bulunamadı")
    tx, ty, sx, sy = (float(v) for v in bulunan.groups())
    kutular = []
    for g in re.finditer(r'<path transform="translate\(([\d.]+) 0\)" d="([^"]+)"', bulunan.group(0)):
        x0, y0, x1, y1 = _cizgi_sinirlari(g.group(2))
        kutular.append((float(g.group(1)) + x0, y0, float(g.group(1)) + x1, y1))
    if not kutular:
        raise SystemExit(f"yazi_svg: {LOGO_KUR.name} içinde harf yolu yok")
    sol, alt, sag, ust = (min(k[0] for k in kutular), min(k[1] for k in kutular),
                          max(k[2] for k in kutular), max(k[3] for k in kutular))
    kutu = [tx + sx * sol, ty - sy * ust, sx * (sag - sol), sy * (ust - alt)]
    return (f'<svg focusable="false" viewBox="{" ".join(f"{v:.1f}" for v in kutu)}" role="img" aria-label="{_e(ad)}">'
            f'{bulunan.group(0)}</svg>')


def ust_yap(ad: str, dil: str, m: dict, ozet: str) -> str:
    """The header of every page: products on the left (veri/urunler.json), the wordmark linking home in the middle,
    GitHub and the same page in the other language on the right."""
    yol = SAYFALAR[ad][dil]
    diger = next(d for d in DILLER if d != dil)
    s = m["site"]
    urunler = "".join(
        f'<a href="{_bag(yol, SAYFALAR[u["sayfa"]][dil])}"{" aria-current=\"page\"" if u["sayfa"] == ad else ""}>'
        f'{_e(m["urunler"][u["anahtar"]]["ad"])}</a>' for u in _json(VERI / "urunler.json"))
    return (f'<header class="s-ust">\n  <div class="s-ust__ic">\n'
            f'    <nav class="c-gezinme s-ust__sol" aria-label="{_e(s["gezinme"]["urunler"])}">{urunler}</nav>\n'
            f'    <a class="s-logo" href="{_bag(yol, SAYFALAR["ana"][dil])}" data-yazi-kur data-denetim-logo '
            f'data-glifler="{kok_varlik(yol, ozet)}glifler.json">{yazi_svg(s["ad"])}</a>\n'
            f'    <nav class="c-gezinme s-ust__sag" aria-label="{_e(s["gezinme"]["etiket"])}">'
            f'<a href="{GITHUB}" rel="external" lang="en">{_e(s["gezinme"]["github"])}</a>'
            f'<a href="{_bag(yol, SAYFALAR[ad][diger])}" hreflang="{diger}" lang="{diger}">{_e(s["digerDil"])}</a></nav>\n'
            f'  </div>\n</header>')


def kok_varlik(yol: str, ozet: str) -> str:
    return f"{_kok(yol)}varlik/{ozet}/"


def sayfa_yaz(ad: str, dil: str, govde: str, m: dict, ozet: str, once: str = "") -> str:
    """Fill sablon/sayfa.html for page `ad` in language `dil`. m: that language's texts (metin_yukle()[dil]).
    once: markup between the header and <main> (the home page's canvas and seat row). The home page is dark and
    has no footer (the licence line closes its last section); the Hafıza pages follow the system theme."""
    yol = SAYFALAR[ad][dil]
    diger = next(d for d in DILLER if d != dil)
    varlik = kok_varlik(yol, ozet)
    s = m["site"]
    alternatifler = "\n".join(
        f'<link rel="alternate" hreflang="{d}" href="{SITE_URL}/{SAYFALAR[ad][d]}">' for d in DILLER
    ) + f'\n<link rel="alternate" hreflang="x-default" href="{SITE_URL}/{SAYFALAR[ad][DILLER[0]]}">'
    github = f'<a href="{GITHUB}">{_e(s["gezinme"]["github"])}</a>'
    dil_bag = f'<a href="{_bag(yol, SAYFALAR[ad][diger])}" hreflang="{diger}" lang="{diger}">{_e(s["digerDil"])}</a>'
    ana = ad == "ana"
    alt = "" if ana else (
        '<footer class="s-alt">\n  <div class="s-alt__ic">\n'
        f'    <a class="s-alt__logo" href="{_bag(yol, SAYFALAR["ana"][dil])}"><img class="ia" src="{varlik}logo/council-amblem.svg" alt="" width="24" height="24">'
        f'<img class="ik" src="{varlik}logo/council-amblem-koyu.svg" alt="" width="24" height="24"><span>COUNCIL</span></a>\n'
        f'    <nav class="c-gezinme" aria-label="{_e(s["altbilgi"]["etiket"])}">{github}{dil_bag}</nav>\n'
        f'    <p class="s-alt__lisans">{_e(s["altbilgi"]["lisans"])}</p>\n  </div>\n</footer>\n')
    sayfa = m["sayfalar"][ad]
    return Template((SABLON / "sayfa.html").read_text(encoding="utf-8")).substitute(
        lang=dil,
        tema=' data-theme="dark"' if ana else "",
        baslik=_e(sayfa["baslik"]),
        aciklama=_e(sayfa["aciklama"]),
        kanonik=f"{SITE_URL}/{yol}",
        alternatifler=alternatifler,
        og_gorsel=f"{SITE_URL}/paylas-{dil}.png",
        og_yerel=_e(s["ogYerel"]),
        varlik=varlik,
        stiller=f'<link rel="stylesheet" href="{varlik}css/masa.css">\n' if ana else "",
        atla=_e(s["atla"]),
        ust=ust_yap(ad, dil, m, ozet),
        once=once,
        ana_sinif="s-masa" if ana else "s-sayfa",
        govde=govde,
        alt=alt,
    )


def _doldur(metin: str, degerler: dict) -> str:
    """Fill {ad} placeholders; an unknown one stops the build."""
    def koy(e):
        if e.group(1) not in degerler:
            raise SystemExit(f"metin: bilinmeyen yer tutucu {{{e.group(1)}}}: {metin!r}")
        return str(degerler[e.group(1)])
    return re.sub(r"\{(\w+)\}", koy, metin)


def _vurgu(metin: str) -> str:
    """Escaped heading text: *x* becomes <em>x</em>, a line break becomes <br>."""
    return re.sub(r"\*([^*]+)\*", r"<em>\1</em>", _e(metin)).replace("\n", "<br>")


def _slogan_satirlari(slogan: str) -> str:
    """The h1 as three block lines (spans joined by spaces, so the text reads as the slogan): up to the comma,
    then the last word apart, then the word before it ("Tek hafıza," / "her" / "yardımcı.")."""
    bas, virgul, son = slogan.partition(", ")
    ilk, _, sonu = son.rpartition(" ")
    parcalar = [bas + virgul.strip(), ilk, sonu]
    if not virgul or not ilk:
        raise SystemExit(f"slogan: üç satıra bölünemiyor: {slogan!r}")
    return " ".join(f'<span{s}>{_e(p)}</span>' for s, p in zip(("", ' class="t2"', ' class="t3"'), parcalar))


def yol_haritasi(dil: str, m: dict) -> tuple[list[str], str]:
    """Roadmap rows and the per-feature statuses of the ring. Named features (brand/js/ozellikler.json) get a row of their
    own, a run of unnamed ones one row ("3–6 / Four features"); statuses and names come from the feature list."""
    y, sahne = m["ana"]["yol"], _json(SAHNE_METIN)[dil]["kurulTuru"]["durum"]
    oz = ozellikler(dil)
    cumleler = iter(y["cumleler"])
    satirlar, i = [], 0
    while i < len(oz):
        n = 1
        if oz[i]["ad"] is None:
            while i + n < len(oz) and oz[i + n]["ad"] is None and oz[i + n]["durum"] == oz[i]["durum"]:
                n += 1
            sayi = f"{i + 1}–{i + n}" if n > 1 else f"{i + 1}/{len(oz)}"
            ad = _doldur(y["yolda"]["baslik"], {"sayi": y["sayilar"][n]})
            cumle = y["yolda"]["cumle"]
        else:
            sayi, ad = f"{i + 1}/{len(oz)}", oz[i]["ad"]
            cumle = next(cumleler, oz[i]["aciklama"])
        durum = oz[i]["durum"]
        sinif = {"tamam": " rozet--tamam", "denemede": " rozet--denemede"}.get(durum, "")
        satirlar.append(
            f'      <li data-sira style="--sira:{3 + len(satirlar)}" data-i="{i}" data-n="{n}"><span class="n">{_e(sayi)}</span>'
            f'<h3>{_e(ad)}<span class="rozet{sinif}">{_e(sahne[durum].capitalize())}</span></h3><p>{_e(cumle)}</p></li>')
        i += n
    return satirlar, ",".join(o["durum"] for o in oz)


KONUSMA = (("a", "sen"), ("a", "sistem"), ("a", "yazdi"), ("a", "yardimci"),
           ("b", "sistem"), ("b", "sen"), ("b", "sistem"), ("b", "yardimci"))   # Canlı: which box and kind each line is


def ana_once(dil: str, m: dict, ozet: str) -> str:
    """Home page markup before <main>: the particle canvas, the dot grid and the row of five seats (a tablist; the
    section names are the seats' hidden text)."""
    b = m["ana"]["bolumler"]
    if len(b["adlar"]) != len(BOLUMLER):
        raise SystemExit(f"metin: {dil} ana.bolumler.adlar {len(BOLUMLER)} ad olmalı")
    yerler = ((48, 66), (104, 47), (160, 41), (216, 47), (272, 66))   # seats on the arc: x, y in a 320 x 104 box
    koltuklar = "\n".join(
        f'    <button class="koltuk" role="tab" id="r{i + 1}" aria-controls="{k}" aria-selected="{"true" if i == 0 else "false"}"'
        f'{"" if i == 0 else " tabindex=\"-1\""} style="--x:{x}px;--y:{y}px">0{i + 1}<span class="gizli"> {_e(ad)}</span></button>'
        for i, (k, ad, (x, y)) in enumerate(zip(BOLUMLER, b["adlar"], yerler, strict=True)))
    return (f'<canvas id="alan" data-denetim-sahne aria-hidden="true"></canvas>\n<div class="izgara" aria-hidden="true"></div>\n\n'
            f'<nav class="masa" aria-label="{_e(b["etiket"])}">\n'
            f'  <svg class="masa__kenar" viewBox="0 0 320 104" aria-hidden="true"><path d="M20 84 Q160 -6 300 84"/>'
            f'<path class="iz" d="M20 84 Q160 -6 300 84" pathLength="100"/></svg>\n'
            f'  <div role="tablist" aria-label="{_e(b["etiket"])}" aria-orientation="horizontal">\n{koltuklar}\n  </div>\n'
            f'  <p class="masa__ad" aria-hidden="true"><b id="masa-ad">{_e(b["adlar"][0])}</b></p>\n</nav>\n\n')


BOLUMLER = ("giris", "canli", "nasil", "kurul", "yardimcilar")   # section ids, in seat order (language-neutral anchors)


def ana_govde(dil: str, m: dict, ozet: str) -> str:
    """Home body (sablon/ana.html): the five sections of the Kurul Masası; the rows come from the feature list
    (brand/js/ozellikler.json), the helper list (veri/yardimcilar.json) and the counts (pyproject.toml, council/server.py)."""
    varlik = f"{_kok(SAYFALAR['ana'][dil])}varlik/{ozet}/"
    kur, c, nasil, yol, yar = (m["ana"][k] for k in ("kurulum", "canli", "nasil", "yol", "yardimcilar"))
    temel, ogrenme = arac_sayilari()
    satirlar_a, satirlar_b = [], []
    if len(c["satirlar"]) != len(KONUSMA):
        raise SystemExit(f"metin: {dil} ana.canli.satirlar {len(KONUSMA)} satır olmalı")
    for (kutu, tur), metin in zip(KONUSMA, c["satirlar"], strict=True):
        ad = f' data-ad="{_e(c["yardimci"])}"' if tur == "yardimci" else ""
        (satirlar_a if kutu == "a" else satirlar_b).append(f'<p class="satir {tur}"{ad}>{_kod(metin)}</p>')
    adimlar = "\n".join(
        f'      <li data-sira style="--sira:{2 + i}" data-i="{i}"><span class="n">0{i + 1}</span>'
        f'<h3>{_e(x["baslik"])}</h3><p>{_e(x["cumle"])}</p></li>' for i, x in enumerate(nasil["adimlar"]))
    satirlar, durumlar = yol_haritasi(dil, m)
    rozet = m["ana"]["yardimcilar"]["durum"]
    yardimcilar_satirlari = "\n".join(
        f'      <li data-sira style="--sira:{2 + i}"><span class="n">0{i + 1}</span><h3>{_e(o["ad"])}'
        f'<span class="rozet{" rozet--tamam" if o["durum"] == "tam" else ""}" data-durum="{o["durum"]}">{_e(rozet[o["durum"]])}</span></h3>'
        f'<p>{_e(o["destek"])}</p></li>' for i, o in enumerate(yardimcilar(dil)))
    return Template((SABLON / "ana.html").read_text(encoding="utf-8")).substitute(
        varlik=varlik,
        etiket=_e(m["ana"]["etiket"]), surum=_e(_doldur(m["ana"]["surum"], {"surum": surum()})),
        h1=_slogan_satirlari(m["sayfalar"]["ana"]["h1"]), tanim=_e(m["ana"]["tanim"]),
        kur_cumlesi=_e(kur["cumle"]), kur_onu=_e(kur["onu"]), kopyala=_e(kur["kopyala"]), kopyalandi=_e(kur["kopyalandi"]),
        secin=_e(kur["secin"]), komut=_e(kur["komut"]), unix_etiket=_e(kur["unix"]), windows_etiket=_e(kur["windows"]),
        kur_unix=_e(KUR_UNIX), kur_windows=_e(KUR_WINDOWS), komut_kopyala=_e(kur["komutKopyala"]), komut_secin=_e(kur["komutSecin"]),
        gerekenler=_e(kur["gerekenler"]),
        canli_etiket=_e(c["etiket"]), canli_calisiyor=_e(c["calisiyor"]), canli_bitti=_e(c["bitti"]),
        canli_baslik=_vurgu(c["baslik"]), telefon=_e(c["telefon"]), bilgisayar=_e(c["bilgisayar"]),
        satirlar_a="\n".join(satirlar_a), satirlar_b="\n".join(satirlar_b),
        canli_not=_e(c["not"]), yeniden=_e(c["yeniden"]),
        nasil_etiket=_e(nasil["etiket"]), nasil_baslik=_vurgu(nasil["baslik"]), nasil_adimlar=adimlar,
        yol_etiket=_e(yol["etiket"]), yol_baslik=_vurgu(yol["baslik"]), yol_onu=_e(yol["onu"]),
        yol_durumlar=durumlar, yol_satirlari="\n".join(satirlar), yol_son_sira=3 + len(satirlar),
        yol_bugun=_e(_doldur(yol["bugun"], {"surum": surum(), "temel": temel, "ogrenme": ogrenme})),
        yardimcilar_etiket=_e(yar["etiket"]), yardimcilar_baslik=_vurgu(yar["baslik"]),
        yardimcilar_satirlari=yardimcilar_satirlari, yardimcilar_son_sira=2 + len(yardimcilar(dil)),
        lisans=_e(m["site"]["altbilgi"]["lisans"]),
    ).rstrip("\n")


def _kod(metin: str) -> str:
    """Escaped text with `code` spans (backticks in the texts) as <code>."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", _e(metin))


def amblem_svg() -> str:
    """The Hafıza hero emblem (circle, C, wave; no wordmark) derived from brand/logo/council-logo-kur.html:
    the wordmark group is dropped, the view box shrinks to the emblem and the mask id is renamed (the header logo
    carries the same fragment, and an id must be unique in a page). Decorative: the h1 beside it names the page."""
    svg, adet = re.subn(r'<g data-kur="yazi".*?</g>', "", LOGO_KUR.read_text(encoding="utf-8").strip(), flags=re.S)
    if adet != 1:
        raise SystemExit(f"amblem: {LOGO_KUR.name} içinde logo yazısı grubu bulunamadı")
    for eski, yeni in (('viewBox="0 0 1762 400"', 'viewBox="0 0 400 400"'), ('role="img" aria-label="COUNCIL"', 'aria-hidden="true"'),
                       ("ust-kesik", "amblem-kesik")):
        if eski not in svg:
            raise SystemExit(f"amblem: {LOGO_KUR.name} içinde {eski} yok")
        svg = svg.replace(eski, yeni)
    return svg


def akis_cizimi(n: dict) -> str:
    """How it works: three session boxes, each reading from and writing to one memory (the only s-kor element).
    Strokes are currentColor; the arrows are 45-degree chevrons on straight lines."""
    parca = []
    for i in range(3):
        x, cx = 20 + 155 * i, 85 + 155 * i
        parca.append(f'<rect x="{x}" y="20" width="130" height="70"/>'
                     f'<text class="s-akis__yazi" x="{cx}" y="61" text-anchor="middle">{_e(n["oturum"])} {i + 1}</text>')
        parca.append(f'<path d="M{cx - 24} 90V210M{cx - 32} 198L{cx - 24} 210L{cx - 16} 198"/>')   # reads: memory -> session
        parca.append(f'<path d="M{cx + 24} 210V90M{cx + 16} 102L{cx + 24} 90L{cx + 32} 102"/>')   # writes: session -> memory
        if i < 2:
            parca.append(f'<path d="M{x + 134} 55H{x + 151}M{x + 143} 47L{x + 151} 55L{x + 143} 63"/>')   # next session continues
    parca.append('<rect class="s-kor" x="20" y="210" width="440" height="70" stroke-width="4"/>'
                 f'<text class="s-akis__yazi" x="240" y="251" text-anchor="middle">{_e(n["hafiza"])}</text>')
    return (f'    <svg class="s-akis" viewBox="0 0 480 300" role="img" aria-label="{_e(n["gorsel"])}" fill="none" '
            f'stroke="currentColor" stroke-width="2" stroke-linejoin="miter">{"".join(parca)}</svg>')


def _tablo(basliklar: list[str], satirlar: list[list[str]], sinif: str = "") -> str:
    """A data table; cells are HTML. Each cell carries its column name (data-etiket) for the narrow layout."""
    ust = "".join(f'<th scope="col">{_e(b)}</th>' for b in basliklar)
    govde = "\n".join("    <tr>" + "".join(f'<td data-etiket="{_e(b)}">{h}</td>' for b, h in zip(basliklar, satir, strict=True))
                      + "</tr>" for satir in satirlar)
    return (f'  <table class="s-tablo{" " + sinif if sinif else ""}">\n    <thead><tr>{ust}</tr></thead>\n'
            f'    <tbody>\n{govde}\n    </tbody>\n  </table>')


def _yol_kutusu(kimlik: str, baslik_kimlik: str, baslik: str, notu: str, kod: str, kur: dict) -> str:
    return (f'    <div class="s-yol"><h3 id="{baslik_kimlik}" class="yazi-govde-l">{_e(baslik)}</h3>'
            f'<p class="yazi-govde">{_kod(notu)}</p>\n'
            f'      <pre><code id="{kimlik}">{_e(kod)}</code></pre>\n'
            f'      <button type="button" class="c-dugme c-dugme--k c-dugme--hayalet" data-kopyala="{kimlik}" '
            f'data-tamam="{_e(kur["kopyalandi"])}" data-hata="{_e(kur["secin"])}" aria-describedby="{baslik_kimlik}" '
            f'aria-live="polite" hidden>{_e(kur["kopyala"])}</button></div>')


def yardimcilar(dil: str, yol: Path = VERI / "yardimcilar.json") -> list[dict]:
    """The supported-assistant rows in one language as {"ad", "destek", "durum"} (veri/yardimcilar.json)."""
    out = []
    for o in _json(yol):
        ad = o["ad"] if isinstance(o["ad"], str) else o["ad"][dil]
        if o["durum"] not in YARDIMCI_DURUMLARI:
            raise SystemExit(f"yardimcilar: {ad}: bilinmeyen durum {o['durum']!r}")
        out.append({"ad": ad, "destek": o["destek"][dil], "durum": YARDIMCI_DURUMLARI[o["durum"]]})
    return out


def hafiza_govde(dil: str, m: dict, ozet: str) -> str:
    """Hafıza page body (sablon/hafiza.html): hero with the emblem, then the nine sections."""
    varlik = f"{_kok(SAYFALAR['hafiza'][dil])}varlik/{ozet}/"
    h = m["hafiza"]
    nasil, kur, ilk, ic, olc, fark, yar, sss, bel = (h[k] for k in (
        "nasil", "kurulum", "ilk", "ic", "olcumler", "fark", "yardimcilar", "sss", "belgeler"))
    sec = kur["secenekler"]
    temel, ogrenme = arac_sayilari()

    adimlar = "\n".join(f'    <li><h3 class="yazi-govde-l">{_e(a["baslik"])}</h3><p class="yazi-govde">{_e(a["govde"])}</p></li>'
                        for a in nasil["adimlar"])
    kodlar = (m["ana"]["kurulum"]["cumle"], KUR_UNIX, KUR_WINDOWS)
    yollar = "\n".join(_yol_kutusu(k, f"{k}-b", y["baslik"], y["not"], kod, kur)
                       for k, y, kod in zip(("kur-cumlesi", "kur-unix", "kur-windows"), kur["yollar"], kodlar, strict=True))
    secenekler = _tablo([sec["sutunlar"]["secenek"], sec["sutunlar"]["ne"]],
                        [[f'<code>{_e(s["ad"])}</code>', _e(s["ne"])] for s in sec["satirlar"]])
    ilk_adimlar = "\n".join(
        f'    <li><h3 class="yazi-govde-l">{_e(a["baslik"])}</h3>'
        f'<p class="s-liste__yaz yazi-govde"><span class="yazi-etiket">{_e(ilk["etiketler"]["yaz"])}</span> “{_e(a["yaz"])}”</p>'
        f'<p class="yazi-govde"><span class="yazi-etiket">{_e(ilk["etiketler"]["olur"])}</span> {_kod(a["olur"])}</p></li>'
        for a in ilk["adimlar"])
    olcumler = _tablo([olc["sutunlar"]["olcum"], olc["sutunlar"]["sonuc"]],
                      [[_e(s["olcum"]), _e(s["sonuc"])] for s in olc["satirlar"]])
    maddeler = "\n".join(f'    <li><h3 class="yazi-govde-l">{_e(a["baslik"])}</h3><p class="yazi-govde">{_e(a["cumle"])}</p></li>'
                         for a in fark["maddeler"])
    satirlar = [[_e(o["ad"]), _e(o["destek"]),
                 f'<span class="c-rozet{" c-rozet--basari" if o["durum"] == "tam" else ""}" data-durum="{o["durum"]}">{_e(yar["durum"][o["durum"]])}</span>']
                for o in yardimcilar(dil)]
    ss = "\n".join(f'    <details>\n      <summary class="yazi-govde-l">{_e(q["s"])}</summary>\n'
                   f'      <p class="yazi-govde">{_kod(q["c"])}</p>\n    </details>' for q in sss["maddeler"])
    belgeler = "\n".join(
        f'    <li><a class="c-baglanti yazi-govde-l" href="{GITHUB}/blob/main/{b["yol"]}">{_e(b["ad"])}</a>'
        f'<p class="yazi-govde">{_e(b["aciklama"])}</p></li>' for b in bel["baglantilar"])

    return Template((SABLON / "hafiza.html").read_text(encoding="utf-8")).substitute(
        varlik=varlik, github=GITHUB, amblem=amblem_svg(),
        h1=_e(m["sayfalar"]["hafiza"]["h1"]), tanim=_e(h["tanim"]),
        nasil_id=nasil["id"], nasil_baslik=_e(nasil["baslik"]), nasil_onu=_e(nasil["onu"]), nasil_son=_e(nasil["son"]),
        nasil_cizim=akis_cizimi(nasil), nasil_adimlar=adimlar,
        kurulum_id=kur["id"], kurulum_baslik=_e(kur["baslik"]), kurulum_onu=_e(kur["onu"]), kurulum_yollar=yollar,
        kurulum_sonra=_e(kur["sonra"]), secenekler_baslik=_e(sec["baslik"]), secenekler_onu=_kod(sec["onu"]),
        secenekler_tablo=secenekler,
        ilk_id=ilk["id"], ilk_baslik=_e(ilk["baslik"]), ilk_adimlar=ilk_adimlar,
        ic_id=ic["id"], ic_baslik=_e(ic["baslik"]), ic_agac=_e(ic["agac"]), ic_agac_etiket=_e(ic["agac_etiket"]), ic_son=_e(ic["son"]),
        olcumler_id=olc["id"], olcumler_baslik=_e(olc["baslik"]), olcumler_onu=_e(olc["onu"]), olcumler_tablo=olcumler,
        olcumler_araclar=_e(_doldur(olc["araclar"], {"surum": surum(), "temel": temel, "ogrenme": ogrenme})),
        fark_id=fark["id"], fark_baslik=_e(fark["baslik"]), fark_maddeler=maddeler,
        yardimcilar_id=yar["id"], yardimcilar_baslik=_e(yar["baslik"]), yardimcilar_onu=_e(yar["onu"]),
        yardimcilar_tablo=_tablo([yar["sutunlar"]["yardimci"], yar["sutunlar"]["baglanti"], yar["sutunlar"]["durum"]],
                                 satirlar, "s-tablo--yardimci"),
        yardimcilar_son=_e(yar["son"]), yardimcilar_bildir=_e(yar["bildir"]),
        sss_id=sss["id"], sss_baslik=_e(sss["baslik"]), sss_maddeler=ss,
        belgeler_id=bel["id"], belgeler_baslik=_e(bel["baslik"]), belgeler_baglantilar=belgeler,
    ).rstrip("\n")


def govde_yap(ad: str, dil: str, m: dict, ozet: str) -> tuple[str, str]:
    """(markup before <main>, body): the home page (sablon/ana.html) or the Hafıza page (sablon/hafiza.html)."""
    return (ana_once(dil, m, ozet), ana_govde(dil, m, ozet)) if ad == "ana" else ("", hafiza_govde(dil, m, ozet))


def sitemap() -> str:
    """sitemap.xml: the four pages, each with its language alternates."""
    def bag(ad: str, dil: str) -> str:
        return f"{SITE_URL}/{SAYFALAR[ad][dil]}"

    satirlar = ['<?xml version="1.0" encoding="UTF-8"?>',
                '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for ad in SAYFALAR:
        for dil in DILLER:
            satirlar += ["  <url>", f"    <loc>{bag(ad, dil)}</loc>"]
            satirlar += [f'    <xhtml:link rel="alternate" hreflang="{d}" href="{bag(ad, d)}"/>' for d in DILLER]
            satirlar += [f'    <xhtml:link rel="alternate" hreflang="x-default" href="{bag(ad, DILLER[0])}"/>', "  </url>"]
    return "\n".join([*satirlar, "</urlset>", ""])


def robots() -> str:
    return f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"


def _yazi_tipi_adresi() -> str:
    """The Council Halka woff2 as a data: URL, so an SVG drawn as an image still has the face."""
    return "data:font/woff2;base64," + base64.b64encode((BRAND / "font" / "CouncilHalka.woff2").read_bytes()).decode("ascii")


# Tagline size per language: the line must fit between the 96 px margins (1008 px); EN is the longer line.
SLOGAN_BOYUT = {"tr": 88, "en": 80}


def paylas_svg(dil: str, m: dict) -> str:
    """sablon/paylas.svg for one language: dark theme colors from brand/tokens.json, the emblem, the tagline."""
    jetonlar = {t["name"]: t["value"]["dark"] for t in _json(BRAND / "tokens.json")["color"]["tokens"]}
    amblem = (BRAND / "logo" / "council-amblem-koyu.svg").read_text(encoding="utf-8")
    ic = re.search(r"<svg[^>]*>(.*)</svg>", amblem, re.S).group(1)
    return Template((SABLON / "paylas.svg").read_text(encoding="utf-8")).substitute(
        lang=dil, zemin=jetonlar["zemin"], murekkep=jetonlar["murekkep"], murekkep2=jetonlar["murekkep-2"],
        yazi_tipi=_yazi_tipi_adresi(), amblem=ic, slogan=_e(m["site"]["slogan"]), slogan_boyut=SLOGAN_BOYUT[dil], ad=_e(m["site"]["ad"]))


def paylas_gorselleri(hedef: Path, metin: dict[str, dict], yeniden: bool) -> None:
    """paylas-<dil>.png in hedef: rendered from paylas.svg with Chrome (--gorsel), else the committed files copied."""
    for dil in DILLER:
        png = hedef / f"paylas-{dil}.png"
        if yeniden:
            denetle = _brand_denetle()
            with tempfile.TemporaryDirectory() as gecici:
                svg = Path(gecici) / f"paylas-{dil}.svg"
                svg.write_text(paylas_svg(dil, metin[dil]), encoding="utf-8")
                denetle.png_yap(svg, png, 1200, 630)
        elif png != CIKTI / png.name:
            png.write_bytes((CIKTI / png.name).read_bytes())


def _argumanlar(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="build.py", description="Build the COUNCIL promo site.")
    ap.add_argument("--cikti", type=Path, default=CIKTI, help="output folder (default: site/cikti)")
    ap.add_argument("--gorsel", action="store_true", help="render the share images again (needs Chrome)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arg = _argumanlar(argv)
    hedef = arg.cikti.resolve()
    metin = metin_yukle()
    for dil in DILLER:
        ozellikler(dil)   # a named feature without this language stops the build
    arac_sayilari()
    sayfalar = {(ad, dil): sayfa_yaz(ad, dil, govde, metin[dil], OZET_YER, once)
                for ad in SAYFALAR for dil in DILLER for once, govde in [govde_yap(ad, dil, metin[dil], OZET_YER)]}
    ozet = varlik_kopyala(hedef, glif_altkumesi(list(sayfalar.values())))
    for (ad, dil), icerik in sayfalar.items():
        yol = hedef / SAYFALAR[ad][dil] / "index.html"
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_bytes(icerik.replace(OZET_YER, ozet).encode("utf-8"))   # same bytes on every system
    (hedef / "sitemap.xml").write_text(sitemap(), encoding="utf-8", newline="\n")
    (hedef / "robots.txt").write_text(robots(), encoding="utf-8", newline="\n")
    paylas_gorselleri(hedef, metin, arg.gorsel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
