"""COUNCIL promo site generator: site/metin + site/veri + brand/ → site/cikti/ (four pages, one hashed asset folder).

    python site/build.py [--cikti DIR]

Stdlib only. The output is reproducible (no dates, sorted walks) and committed.
"""
import argparse
import ast
import hashlib
import html
import importlib.util
import json
import re
import shutil
import subprocess
import sys
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
TUR_OZELLIK = {2: 0, 3: 1, 4: 2}   # Kurul turu panel index -> feature index whose status its label shows


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


def govde_yap(ad: str, dil: str, m: dict, ozet: str) -> str:
    """Page body: the home page from sablon/ana.html; a placeholder heading until the Hafıza body arrives."""
    if ad == "ana":
        return ana_govde(dil, m, ozet)
    return f'<h1 class="yazi-baslik-xl" data-yazi-kur>{_e(m["sayfalar"][ad]["h1"])}</h1>'


def _argumanlar(argv: list[str] | None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="build.py", description="Build the COUNCIL promo site.")
    ap.add_argument("--cikti", type=Path, default=CIKTI, help="output folder (default: site/cikti)")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    hedef = _argumanlar(argv).cikti.resolve()
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
