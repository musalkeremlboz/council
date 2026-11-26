"""Council Halka 0.2: 0.1 glifleri aynı kalır; küçük harf, Türkçe i, yeni işaretler, kerning."""
import importlib.util
import json
from pathlib import Path

import pytest

pytest.importorskip("fontTools")
pytest.importorskip("pathops")
from fontTools.pens.boundsPen import BoundsPen  # noqa: E402
from fontTools.pens.svgPathPen import SVGPathPen  # noqa: E402
from fontTools.ttLib import TTFont  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "brand" / "font"
_spec = importlib.util.spec_from_file_location("build_font", FONT_DIR / "build_font.py")
build_font = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_font)

FONT = TTFont(FONT_DIR / "CouncilHalka.ttf")
GLYPHS, CMAP, HMTX = FONT.getGlyphSet(), FONT.getBestCmap(), FONT["hmtx"]
OLD = json.loads((ROOT / "tests" / "fixtures" / "halka-0.1-buyuk.json").read_text())

LOWER = {**{c: c for c in "abcdefghijklmnopqrstuvwxyz"},
         "ç": "ccedilla", "ğ": "gbreve", "ı": "dotlessi", "ö": "odieresis", "ş": "scedilla", "ü": "udieresis"}


def commands(name):
    pen = SVGPathPen(GLYPHS)
    GLYPHS[name].draw(pen)
    return pen.getCommands()


def bounds(name):
    pen = BoundsPen(GLYPHS)
    GLYPHS[name].draw(pen)
    return pen.bounds


def kern(left, right):
    """Sum of the GPOS kern x-advance adjustments for the pair (0 if none)."""
    total = 0
    gpos = FONT["GPOS"].table
    for fr in gpos.FeatureList.FeatureRecord:
        if fr.FeatureTag != "kern":
            continue
        for li in fr.Feature.LookupListIndex:
            for st in gpos.LookupList.Lookup[li].SubTable:
                if st.Format == 1 and left in st.Coverage.glyphs:
                    ps = st.PairSet[st.Coverage.glyphs.index(left)]
                    total += sum(r.Value1.XAdvance for r in ps.PairValueRecord if r.SecondGlyph == right)
                elif st.Format == 2 and left in st.Coverage.glyphs:
                    c1 = st.ClassDef1.classDefs.get(left, 0)
                    c2 = st.ClassDef2.classDefs.get(right, 0)
                    v = st.Class1Record[c1].Class2Record[c2].Value1
                    total += getattr(v, "XAdvance", 0) or 0
    return total


def test_existing_glyphs_unchanged():
    for name, old in OLD.items():
        assert commands(name) == old["d"], name
        assert HMTX[name][0] == old["advance"], name


def test_lowercase_is_its_own():
    for ch, name in LOWER.items():
        assert CMAP[ord(ch)] == name, ch
        assert name[0].islower()
        assert CMAP[ord(ch)] != CMAP[ord(ch.upper())], ch


def test_turkish_i():
    assert CMAP[ord("İ")] == "Idotaccent"
    assert CMAP[ord("i")] == "i"
    assert CMAP[ord("I")] == "I"
    assert CMAP[ord("ı")] == "dotlessi"


def test_new_punctuation():
    for ch in "&@#%+=()\"';…→":
        assert ord(ch) in CMAP, ch
        assert commands(CMAP[ord(ch)]), ch


def test_kerning_pairs():
    for pair in (("L", "A"), ("T", "o"), ("r", "o")):
        assert kern(*pair) < 0, pair


def test_kerned_pairs_do_not_collide():
    """After advance + kern, the right glyph's ink must not reach into the left glyph's ink."""
    def spans(name):
        """Per 10-unit row: (min x, max x) of the glyph's ink, from its filled outline."""
        import pathops
        path = pathops.Path()
        GLYPHS[name].draw(path.getPen())
        rows = {}
        for y in range(-100, 1100, 10):
            xs = []
            for x in range(-100, 1400, 5):
                if path.contains((x, y)):
                    xs.append(x)
            if xs:
                rows[y] = (min(xs), max(xs))
        return rows

    bad = []
    seen = set()
    gpos_pairs = [(a, b) for (a, b) in build_font.KERN if a in CMAP.values() and b in CMAP.values()]
    for a, b in gpos_pairs:
        if (a, b) in seen:
            continue
        seen.add((a, b))
        sa, sb = spans(a), spans(b)
        shift = HMTX[a][0] + kern(a, b)
        for y in set(sa) & set(sb):
            if shift + sb[y][0] <= sa[y][1]:
                bad.append((a, b, y))
                break
    assert not bad, bad


def test_version():
    assert "0.2" in FONT["name"].getDebugName(5)


def test_lowercase_metrics():
    assert build_font.XH == 500
    assert bounds("x")[3] == build_font.XH
    assert bounds("b")[3] == 700
    assert bounds("p")[1] == -200


GEO = FONT_DIR / "glifler.json"


def test_geometry_matches_font():
    geo = json.loads(GEO.read_text(encoding="utf-8"))
    assert geo["surum"] == build_font.VERSION and geo["birim"] == 1000
    assert (geo["cizgi"], geo["buyuk"], geo["x"]) == (100, 700, 500)
    glyf = FONT["glyf"]
    assert set(geo["glifler"]) == set(FONT.getGlyphOrder()) - {".notdef"}
    for name, g in geo["glifler"].items():
        assert g["genislik"] == HMTX[name][0], name
        assert g["sol"] == HMTX[name][1], name
        gl = build_font.replay(g["ilkeller"], lsb=g["sol"])
        redrawn = build_font.ttglyph(gl)
        pen_a, pen_b = SVGPathPen(None), SVGPathPen(None)
        redrawn.draw(pen_a, glyf)
        glyf[name].draw(pen_b, glyf)
        assert pen_a.getCommands() == pen_b.getCommands(), name


def test_geometry_covers_cmap():
    geo = json.loads(GEO.read_text(encoding="utf-8"))
    assert geo["harita"] == {chr(cp): n for cp, n in CMAP.items()}
