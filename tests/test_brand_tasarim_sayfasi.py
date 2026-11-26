import importlib.util
import json
from pathlib import Path

BRAND = Path(__file__).resolve().parent.parent / "brand"
ISIMLER = "Dugme Alan Kart Rozet Durum Halka Serit Gezinme Sekme Menu Secim Cover".split()
INDEKS = {"v": 3, "layout": "files", "createdOnFiles": {"v": 1, "at": "2026-11-17T12:40:00Z"},
          "title": "COUNCIL", "namespace": "COUNCIL", "libraries": [], "sections": {},
          "groups": ["Logolar"],
          "assetGroups": {"Logolar": {"name": "Logolar", "tile": "l", "order": [], "files": {}}},
          "blobs": {}, "docs": {"readme": "project/README.md", "sections": []}}


def _yaz(tmp_path, indeks=INDEKS):
    spec = importlib.util.spec_from_file_location("tasarim_sayfasi", BRAND / "tasarim_sayfasi.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.yaz(tmp_path, indeks, zaman="2026-11-26T10:00:00Z")


def test_tokens_copied_verbatim(tmp_path):
    _yaz(tmp_path)
    assert (tmp_path / "project/tokens.json").read_bytes() == (BRAND / "tokens.json").read_bytes()
    assert (tmp_path / "project/README.md").read_bytes() == (BRAND / "README.md").read_bytes()


def test_index_keeps_marker_and_sets_code_editing(tmp_path):
    _yaz(tmp_path)
    s = json.loads((tmp_path / "project/design-system.json").read_text(encoding="utf-8"))
    assert s["createdOnFiles"] == INDEKS["createdOnFiles"]
    assert s["editing"] == "code"
    assert s["lastChange"]["at"] == "2026-11-26T10:00:00Z"
    assert s["lastChange"]["note"] == "0.2 koddan üretildi"
    assert {k: v for k, v in s.items() if k not in ("editing", "lastChange")} == INDEKS


def test_every_component_has_readme_and_preview(tmp_path):
    _yaz(tmp_path)
    for ad in ISIMLER:
        d = tmp_path / "project/components" / ad
        assert (d / "README.md").read_text(encoding="utf-8").startswith(f"# {ad}")
        ilk = (d / "preview.html").read_text(encoding="utf-8").splitlines()[0]
        assert ilk.startswith("<!-- @dsCard group=\"") and " height=" in ilk and ilk.endswith("-->")
    css = (tmp_path / "project/components/bundle.css").read_text(encoding="utf-8")
    assert "../fonts/CouncilHalka.woff2" in css and "../../fonts" not in css and "../font/" not in css
    for f in ("CouncilHalka.woff2", "DMSans.ttf", "DMMono-Regular.ttf"):
        assert (tmp_path / "project/fonts" / f).is_file()


def test_no_generated_files_written(tmp_path):
    yazilan = _yaz(tmp_path)
    assert not (tmp_path / "project/tokens.css").exists()
    assert not (tmp_path / "project/manifest.json").exists()
    assert not (tmp_path / "project/api").exists()
    assert all(p.is_file() for p in yazilan)


def _adlar(o):
    if isinstance(o, dict):
        if isinstance(o.get("name"), str) and "value" in o:
            yield o
        for v in o.values():
            yield from _adlar(v)
    elif isinstance(o, list):
        for v in o:
            yield from _adlar(v)


def test_preview_css_variables_are_defined(tmp_path):
    import re
    _yaz(tmp_path)
    tokenlar = {"--" + t["name"] for t in _adlar(json.loads((BRAND / "tokens.json").read_text(encoding="utf-8")))}
    css = (tmp_path / "project/components/bundle.css").read_text(encoding="utf-8")
    # --u ve --s sahne öğelerinde satır içi verilir (sahne betiği/işaretleme), CSS içinde tanımlı değildir
    tanimli = tokenlar | {"--u", "--s"} | set(re.findall(r"(--[\w-]+)\s*:", css))
    kullanilan = {}
    dosyalar = list((tmp_path / "project/components").glob("*/preview.html")) + [tmp_path / "project/components/bundle.css"]
    for p in dosyalar:
        for v in re.findall(r"var\((--[\w-]+)", p.read_text(encoding="utf-8")):
            kullanilan.setdefault(v, p.name)
    eksik = {v: p for v, p in kullanilan.items() if v not in tanimli}
    assert not eksik, eksik


# Form controls carry only the control classes; wrapper classes (c-alan) go on the surrounding block.
KONTROL = {"c-alan__giris", "c-isaret", "c-radyo"}


def _sinif_agaci(html):
    """Every element as (tag, its c- classes, the c- classes of its ancestors)."""
    from html.parser import HTMLParser

    BOS = {"input", "img", "br", "meta", "link", "hr", "circle", "rect", "path"}
    out, yigin = [], []

    class P(HTMLParser):
        def handle_starttag(self, tag, attrs):
            sinif = {c for c in (dict(attrs).get("class") or "").split() if c.startswith("c-")}
            ata = set().union(*(s for _, s in yigin)) if yigin else set()
            out.append((tag, sinif, ata))
            if tag not in BOS:
                yigin.append((tag, sinif))

        def handle_startendtag(self, tag, attrs):
            sinif = {c for c in (dict(attrs).get("class") or "").split() if c.startswith("c-")}
            out.append((tag, sinif, set().union(*(s for _, s in yigin)) if yigin else set()))

        def handle_endtag(self, tag):
            while yigin:
                if yigin.pop()[0] == tag:
                    break

    P().feed(html)
    return out


def test_preview_classes_sit_on_the_right_elements(tmp_path):
    import re
    _yaz(tmp_path)
    css = (BRAND / "css" / "council.css").read_text(encoding="utf-8")
    tanimli = set(re.findall(r"\.(c-[\w-]+)", css))
    for p in (tmp_path / "project/components").glob("*/preview.html"):
        for tag, sinif, ata in _sinif_agaci(p.read_text(encoding="utf-8")):
            assert sinif <= tanimli, (p.parent.name, sinif - tanimli)
            if tag in ("input", "textarea", "select"):
                assert sinif and sinif <= KONTROL, (p.parent.name, tag, sinif)
            for c in sinif:
                if "__" in c:   # a BEM part lives inside its block
                    assert c.split("__")[0] in ata, (p.parent.name, c)


def test_alan_preview_is_the_field_component(tmp_path):
    _yaz(tmp_path)
    html = (tmp_path / "project/components/Alan/preview.html").read_text(encoding="utf-8")
    assert '<div class="c-alan" ' in html and '<label class="c-alan__etiket" for="a1">' in html
    assert '<input id="a1" class="c-alan__giris"' in html


def test_bundle_css_font_urls_resolve_to_written_files(tmp_path):
    import re
    yazilan = {p.resolve() for p in _yaz(tmp_path)}
    kok = tmp_path / "project"
    css = (kok / "components/bundle.css").read_text(encoding="utf-8")
    adresler = re.findall(r'url\("?([^")]+)"?\)', css)
    assert adresler
    for a in adresler:
        hedef = (kok / "components" / a).resolve()
        assert hedef.is_relative_to((kok / "fonts").resolve()), a
        assert hedef in yazilan and hedef.is_file(), a
