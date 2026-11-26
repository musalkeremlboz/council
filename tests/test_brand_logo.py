import importlib.util
import pathlib
import re

import pytest

LOGO = pathlib.Path(__file__).resolve().parent.parent / "brand" / "logo"
INK, PAPER, KOR = "#111416", "#F4F5F3", "#E8421F"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, LOGO / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _body(svg_text):
    return re.search(r"<svg[^>]*>(.*)</svg>", svg_text, re.S).group(1)


def test_logo_set_is_byte_identical(tmp_path):
    pytest.importorskip("fontTools")
    _load("build_logo").main(tmp_path)
    made = sorted(p.name for p in tmp_path.iterdir())
    assert made
    for name in made:
        assert (tmp_path / name).read_bytes() == (LOGO / name).read_bytes(), name


def test_hafiza_emblem_matches_current():
    amblem = _load("amblem")
    current = _body((LOGO / "council-amblem.svg").read_text())
    assert amblem.amblem_svg("hafiza", INK, KOR, "kesik") == current


def test_kasa_keyhole_geometry():
    amblem = _load("amblem")
    kasa = amblem.amblem_svg("kasa", INK, KOR, "kesik")
    hafiza = amblem.amblem_svg("hafiza", INK, KOR, "kesik")
    assert 'cx="200" cy="182" r="34"' in kasa
    assert 'x="186" y="182" width="28" height="76"' in kasa
    # The C is identical for every product.
    part = r'<path[^>]*rotate\(45\)[^>]*/>'
    assert re.search(part, kasa).group(0) == re.search(part, hafiza).group(0)


def test_kasa_o_is_a_full_ring():
    amblem = _load("amblem")
    kasa = amblem.amblem_svg("kasa", INK, KOR, "kesik")
    o = re.search(r'<circle cx="200" cy="200" r="112"[^>]*/>', kasa).group(0)
    assert "mask" not in o
    assert "<mask" not in kasa
    assert "mask=" not in kasa
    assert "<mask" in amblem.amblem_svg("hafiza", INK, KOR, "kesik")


def test_marker_icon():
    amblem = _load("amblem")
    for isaret in amblem.ISARETLER:
        icon = amblem.isaret_simgesi(isaret)
        assert 'viewBox="0 0 24 24"' in icon
        assert 'stroke="currentColor"' in icon
        assert 'stroke-width="2"' in icon
