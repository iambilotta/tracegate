"""Python language adapter — extracts Requirements from pytest test functions.

New Phase-1 adapter (polyglot, ADR-0003 ID schema). pytest convention: `def test_*`
functions, with the spec carried in the function docstring (`@spec.*` tags). Category
from the file-name marker (`*invariant*` -> INV, `*nfr*` -> NFR, `*contract*` -> CON,
else FR); module from the dotted path of the test file.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from tracegate.adapters.lang import python as py_adapter  # noqa: E402
from tracegate.core.config import Config  # noqa: E402

FIXTURE_REPO = Path(__file__).resolve().parent / "fixtures" / "py-mini"


def _cfg() -> Config:
    return Config(repo_root=FIXTURE_REPO, app_root=FIXTURE_REPO, label="py-mini",
                  package_root="", languages=["python"])


def test_extracts_a_documented_python_requirement():
    reqs = list(py_adapter.extract(_cfg()))
    fr = next(r for r in reqs if r.method == "test_fully_documented_requirement_renders")
    assert fr.category == "FR"
    assert fr.spec.is_complete()
    assert fr.spec.us == "US-002-python-story"
    assert fr.file_rel == "tests/test_sample.py"
    assert fr.id == "FR-tests.test_sample#test_fully_documented_requirement_renders"


def test_invariant_filename_routes_to_inv_category():
    reqs = list(py_adapter.extract(_cfg()))
    inv = next(r for r in reqs if r.method == "test_invariant_holds")
    assert inv.category == "INV"


def test_undocumented_python_test_is_incomplete():
    reqs = list(py_adapter.extract(_cfg()))
    undoc = next(r for r in reqs if r.method == "test_undocumented_python_test_is_flagged")
    assert not undoc.spec.is_complete()
