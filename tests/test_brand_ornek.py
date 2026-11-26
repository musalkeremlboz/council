"""The living example page (brand/ornek/index.html): no horizontal overflow, checked in headless Chrome."""
import importlib.util
from pathlib import Path

import pytest

BRAND = Path(__file__).resolve().parent.parent / "brand"
ORNEK = BRAND / "ornek" / "index.html"


def _load():
    spec = importlib.util.spec_from_file_location("denetle", BRAND / "denetle.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


denetle = _load()
pytestmark = pytest.mark.skipif(denetle.chrome_yolu() is None, reason="Chrome is not installed")


def test_no_horizontal_overflow_on_phone():
    assert denetle.tasma_var_mi(ORNEK, 375) is False


def test_no_horizontal_overflow_on_desktop():
    assert denetle.tasma_var_mi(ORNEK, 1280) is False
