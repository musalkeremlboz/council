"""The section scripts' pure functions, checked by node's own test runner when node is installed."""
import shutil
import subprocess
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent / "js" / "panel_pure.test.mjs"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_pure_functions_of_the_section_scripts():
    r = subprocess.run(["node", "--test", str(TESTS)], capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
