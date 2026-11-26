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
import subprocess
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
PARCA = BRAND / "js" / "parca.mjs"
LOGO_KUR = BRAND / "logo" / "council-logo-kur.html"

SITE_URL = "https://council.systems"
DILLER = ("tr", "en")
SAYFALAR = {"ana": {"tr": "", "en": "en/"}, "hafiza": {"tr": "hafiza/", "en": "en/memory/"}}
GITHUB = "https://github.com/musalkeremlboz/council"
OGRENME_ARACLARI = ("council_rule", "council_skill", "council_skill_feedback", "council_unlearn")
OZET_YER = "__ozet__"   # stands for the asset hash until the assets are copied
YARAR_SIMGELERI = ("hafiza", "ogrenme", "telefon", "not")   # one icon per "what it does" item, in order
YARDIMCI_DURUMLARI = {"tam": "tam", "kullanımda": "kullanimda", "denenmedi": "denenmedi"}   # veri/yardimcilar.json -> data-durum, metin key
KUR_UNIX = "curl -fsSL https://raw.githubusercontent.com/musalkeremlboz/council/main/install.sh | sh"
KUR_WINDOWS = "irm https://raw.githubusercontent.com/musalkeremlboz/council/main/install.ps1 | iex"
TUR_OZELLIK = {2: 0, 3: 1, 4: 2}   # Kurul turu panel index -> feature index whose status its label shows


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
        ("js/sahne", BRAND / "js" / "sahne", ["*.js"]),
        ("js", BRAND / "js", ["ozellikler.json", "metin.json", "denetim.js"]),
        ("css", SABLON, ["site.css"]),
        ("js", SABLON, ["site.js"]),
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


def sayfa_yaz(ad: str, dil: str, govde: str, m: dict, ozet: str) -> str:
    """Fill sablon/sayfa.html for page `ad` in language `dil`. m: that language's texts (metin_yukle()[dil])."""
    yol = SAYFALAR[ad][dil]
    diger = next(d for d in DILLER if d != dil)
    kok = _kok(yol)
    varlik = f"{kok}varlik/{ozet}/"
    s = m["site"]
    alternatifler = "\n".join(
        f'<link rel="alternate" hreflang="{d}" href="{SITE_URL}/{SAYFALAR[ad][d]}">' for d in DILLER
    ) + f'\n<link rel="alternate" hreflang="x-default" href="{SITE_URL}/{SAYFALAR[ad][DILLER[0]]}">'
    dil_bag = f'<a href="{_bag(yol, SAYFALAR[ad][diger])}" hreflang="{diger}" lang="{diger}">{_e(s["digerDil"])}</a>'
    github = f'<a href="{GITHUB}">{_e(s["gezinme"]["github"])}</a>'
    hafiza_simdi = ' aria-current="page"' if ad == "hafiza" else ""
    gezinme = (f'<a href="{_bag(yol, SAYFALAR["hafiza"][dil])}"{hafiza_simdi}>{_e(s["gezinme"]["hafiza"])}</a>'
               + github + dil_bag)
    sayfa = m["sayfalar"][ad]
    return Template((SABLON / "sayfa.html").read_text(encoding="utf-8")).substitute(
        lang=dil,
        baslik=_e(sayfa["baslik"]),
        aciklama=_e(sayfa["aciklama"]),
        kanonik=f"{SITE_URL}/{yol}",
        alternatifler=alternatifler,
        og_gorsel=f"{SITE_URL}/paylas-{dil}.png",
        og_yerel=_e(s["ogYerel"]),
        varlik=varlik,
        atla=_e(s["atla"]),
        ana=_bag(yol, SAYFALAR["ana"][dil]),
        logo=LOGO_KUR.read_text(encoding="utf-8").strip(),
        gezinme_etiket=_e(s["gezinme"]["etiket"]),
        gezinme=gezinme,
        govde=govde,
        altbilgi_etiket=_e(s["altbilgi"]["etiket"]),
        altbilgi_gezinme=github + dil_bag,
        lisans=_e(s["altbilgi"]["lisans"]),
    )


def _doldur(metin: str, degerler: dict) -> str:
    """Fill {ad} placeholders; an unknown one stops the build."""
    def koy(e):
        if e.group(1) not in degerler:
            raise SystemExit(f"metin: bilinmeyen yer tutucu {{{e.group(1)}}}: {metin!r}")
        return str(degerler[e.group(1)])
    return re.sub(r"\{(\w+)\}", koy, metin)


def _buyuk(metin: str, dil: str) -> str:
    """Upper case; Turkish i becomes İ."""
    return (metin.replace("i", "İ") if dil == "tr" else metin).upper()


def sahne_parcalari(dil: str) -> dict[str, str]:
    """The Çizgi ve söz figures as static SVG ({"cizgi", "soz"}), from node brand/js/parca.mjs <dil>."""
    try:
        r = subprocess.run(["node", str(PARCA), dil], capture_output=True, text=True, encoding="utf-8", check=True)
    except FileNotFoundError:
        raise SystemExit("parca: node bulunamadı (Çizgi ve söz sahnesinin durağan SVG'leri için gerekir)") from None
    except subprocess.CalledProcessError as hata:
        raise SystemExit(f"parca: {hata.stderr.strip()}") from None
    return json.loads(r.stdout)["cizgiSoz"]


def _simge(ad: str) -> str:
    """A brand/simge icon, inline (it draws in currentColor and is hidden from assistive technology)."""
    svg = (BRAND / "simge" / f"{ad}.svg").read_text(encoding="utf-8").strip()
    return svg.replace('<svg xmlns="http://www.w3.org/2000/svg" ', '<svg class="s-yarar__simge" focusable="false" ', 1)


def ana_govde(dil: str, m: dict, ozet: str) -> str:
    """Home body (sablon/ana.html): hero, Çizgi ve söz, what it does, Kurul turu, products strip."""
    yol = SAYFALAR["ana"][dil]
    varlik = f"{_kok(yol)}varlik/{ozet}/"
    a, kur, cs, kurul = m["ana"], m["ana"]["kurulum"], m["ana"]["cizgiSoz"], m["kurul"]
    sahne = _json(SAHNE_METIN)[dil]
    oz = ozellikler(dil)
    sayilar = {d: sum(o["durum"] == d for o in oz) for d in sahne["kurulTuru"]["durum"]}
    temel, ogrenme = arac_sayilari()
    parca = sahne_parcalari(dil)

    maddeler = "\n".join(
        f'    <li>{_simge(simge)}<h3 class="yazi-govde-l">{_e(md["baslik"])}</h3><p class="yazi-govde">{_e(md["cumle"])}</p></li>'
        for simge, md in zip(YARAR_SIMGELERI, a["yarar"]["maddeler"], strict=True))
    paneller = []
    for i, p in enumerate(kurul["paneller"]):
        etiket = p["etiket"]
        if i in TUR_OZELLIK:
            etiket += " · " + _buyuk(sahne["kurulTuru"]["durum"][oz[TUR_OZELLIK[i]]["durum"]], dil)
        paneller.append(f'<article class="s-tur__panel"><p class="yazi-etiket">{_e(etiket)}</p>'
                        f'<h3 class="yazi-baslik-m">{_e(p["baslik"])}</h3>'
                        f'<p class="yazi-govde-l">{_e(_doldur(p["govde"], sayilar))}</p></article>')
    if len(paneller) != 6:
        raise SystemExit(f"metin: {dil} kurul.paneller altı panel olmalı, {len(paneller)} var")
    urunler = []
    for u in _json(VERI / "urunler.json"):
        metin = m["urunler"][u["anahtar"]]
        urunler.append(
            f'    <li class="s-urun"><span class="s-urun__amblem">'
            f'<img class="ia" src="{varlik}logo/{u["amblem"]}.svg" alt="" width="64" height="64">'
            f'<img class="ik" src="{varlik}logo/{u["amblem"]}-koyu.svg" alt="" width="64" height="64"></span>'
            f'<div><h3 class="yazi-baslik-m"><a class="c-baglanti" href="{_bag(yol, SAYFALAR[u["sayfa"]][dil])}">'
            f'{_e(metin["ad"])}</a></h3><p class="yazi-govde">{_e(metin["cumle"])}</p></div></li>')

    return Template((SABLON / "ana.html").read_text(encoding="utf-8")).substitute(
        varlik=varlik,
        slogan=_e(m["sayfalar"]["ana"]["h1"]),
        tanim=_e(a["tanim"]),
        kur_onu=_e(kur["onu"]),
        kur_cumlesi=_e(kur["cumle"]),
        kopyala=_e(kur["kopyala"]),
        kopyalandi=_e(kur["kopyalandi"]),
        secin=_e(kur["secin"]),
        github=GITHUB,
        cs_etiket=_e(cs["etiket"]),
        cs_secici=_e(cs["secici"]),
        cs_ad_cizgi=_e(cs["cizgi"]),
        cs_ad_soz=_e(cs["soz"]),
        cs_etiket_cizgi=_e(sahne["cizgiSoz"]["etiketCizgi"]),
        cs_etiket_soz=_e(sahne["cizgiSoz"]["etiketSoz"]),
        cs_cizgi=parca["cizgi"],
        cs_soz=parca["soz"],
        yarar_baslik=_e(a["yarar"]["baslik"]),
        yarar_onu=_e(a["yarar"]["onu"]),
        yarar_maddeler=maddeler,
        kurul_baslik=_e(kurul["baslik"]),
        kurul_gorsel=_e(kurul["gorsel"]),
        kurul_paneller="\n".join(paneller),
        kurul_son=_e(_doldur(kurul["son"], {"surum": surum(), "temel": temel, "ogrenme": ogrenme})),
        urunler_baslik=_e(a["urunler"]),
        urunler="\n".join(urunler),
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
        ic_id=ic["id"], ic_baslik=_e(ic["baslik"]), ic_agac=_e(ic["agac"]), ic_son=_e(ic["son"]),
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


def govde_yap(ad: str, dil: str, m: dict, ozet: str) -> str:
    """Page body: the home page (sablon/ana.html) or the Hafıza page (sablon/hafiza.html)."""
    return (ana_govde if ad == "ana" else hafiza_govde)(dil, m, ozet)


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
    sayfalar = {(ad, dil): sayfa_yaz(ad, dil, govde_yap(ad, dil, metin[dil], OZET_YER), metin[dil], OZET_YER)
                for ad in SAYFALAR for dil in DILLER}
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
