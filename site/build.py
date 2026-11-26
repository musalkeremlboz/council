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
import shutil
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
LOGO_KUR = BRAND / "logo" / "council-logo-kur.html"

SITE_URL = "https://council.systems"
DILLER = ("tr", "en")
SAYFALAR = {"ana": {"tr": "", "en": "en/"}, "hafiza": {"tr": "hafiza/", "en": "en/memory/"}}
GITHUB = "https://github.com/musalkeremlboz/council"
OGRENME_ARACLARI = ("council_rule", "council_skill", "council_skill_feedback", "council_unlearn")
OZET_YER = "__ozet__"   # stands for the asset hash until the assets are copied


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


def govde_yap(ad: str, dil: str, m: dict, ozet: str) -> str:
    """Page body. Placeholder heading until the home and Hafıza bodies arrive."""
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
