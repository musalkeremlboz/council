import importlib.util
import pathlib
import re

SIMGE = pathlib.Path(__file__).resolve().parent.parent / "brand" / "simge"
ISIMLER = set("""menu kapat ara ayarlar telefon bilgisayar sunucu not gecmis baglanti indir kopyala
uyari bilgi onay ekle sil duzenle disari geri ileri yukari asagi kilit anahtar hafiza ogrenme
yardimci takvim paylas""".split())


def _load():
    spec = importlib.util.spec_from_file_location("build_simge", SIMGE / "build_simge.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_thirty_icons():
    assert set(_load().SIMGELER) == ISIMLER and len(ISIMLER) == 30
    assert {p.stem for p in SIMGE.glob("*.svg")} == ISIMLER


def test_icon_rules():
    assert len(list(SIMGE.glob("*.svg"))) == 30
    for p in SIMGE.glob("*.svg"):
        s = p.read_text()
        for needle in ('viewBox="0 0 24 24"', 'fill="none"', 'stroke="currentColor"',
                       'stroke-width="2"', 'stroke-linecap="butt"'):
            assert needle in s, (p.name, needle)
        tags = set(re.findall(r"<([a-zA-Z]+)", s)) - {"svg"}
        assert tags <= {"path", "line", "circle"}, (p.name, tags)
        assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgb\(|hsl\(", s), p.name


def test_icons_current(tmp_path):
    yazilan = _load().yaz(tmp_path)
    assert {p.name for p in yazilan} == {f"{n}.svg" for n in ISIMLER}
    for p in yazilan:
        assert p.read_bytes() == (SIMGE / p.name).read_bytes(), p.name


def test_disari_points_top_right():
    parcalar = _load().SIMGELER["disari"]
    assert any(
        q["t"] == "cizgi" and (q["x1"], q["y1"]) == (12, 12)
        and q["x2"] > 12 and q["x2"] - 12 == 12 - q["y2"]
        for q in parcalar
    )
