"""Java language adapter — extracts Requirements from JUnit test sources.

New core/adapter surface (Phase 1). The behavior it must preserve is what the Phase-0
generator did; the difference is it returns core `Requirement` objects with the
CANONICAL repo-relative path (ADR-0007), not the truncated legacy form.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from tracegate.adapters.lang import java as java_adapter  # noqa: E402
from tracegate.core.config import Config  # noqa: E402

FIXTURE_REPO = Path(__file__).resolve().parent / "fixtures" / "gest-mini"


def _cfg() -> Config:
    return Config(
        repo_root=FIXTURE_REPO,
        app_root=FIXTURE_REPO,
        label="gest-mini",
        package_root="it.housetreespa.gest",
    )


def test_extracts_requirements_with_canonical_repo_relative_paths():
    reqs = list(java_adapter.extract(_cfg()))
    by_id = {r.id: r for r in reqs}
    fr = by_id["FR-sample.domain.Sample#fully_documented_test_renders_in_the_catalog"]
    # canonical path: relative to the repo root, NOT a truncated `gest-mini/...`-dropped form
    assert fr.file_rel == "src/test/java/it/housetreespa/gest/sample/domain/SampleTest.java"
    assert fr.spec.is_complete()
    assert fr.spec.us == "US-001-sample-story"
    assert fr.spec.ac == "AC1"


def test_class_name_suffix_drives_the_category():
    reqs = list(java_adapter.extract(_cfg()))
    inv = next(r for r in reqs if r.method == "suffix_routes_to_the_invariant_category")
    assert inv.category == "INV"
    assert inv.id == "INV-sample.domain.Sample#suffix_routes_to_the_invariant_category"


def test_undocumented_test_is_present_but_incomplete():
    reqs = list(java_adapter.extract(_cfg()))
    undoc = next(r for r in reqs if r.method == "undocumented_test_is_flagged_as_spec_missing")
    assert not undoc.spec.is_complete()
