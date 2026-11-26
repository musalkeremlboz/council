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
    assert "../../fonts/CouncilHalka.woff2" in css and "../font/" not in css
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
