"""vitest framework adapter — frontend component/unit tests as FE Requirements.

Mirrors test_adapter_python: a tiny fixture (the gest-mini `frontend/src` tree) runs
through the vitest adapter; the assertions pin the category (FE), the ID scheme
(`FE-frontend.<unit>#<describe > it>`, `.test` suffix stripped), the spec parsing
(JSDoc `@spec.*`, shared with Java/Playwright), and the spec-missing visibility.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from tracegate.adapters.framework import vitest as vitest_adapter  # noqa: E402
from tracegate.core.config import Config  # noqa: E402

FIXTURE_REPO = Path(__file__).resolve().parent / "fixtures" / "gest-mini"


def _cfg() -> Config:
    return Config(repo_root=FIXTURE_REPO, app_root=FIXTURE_REPO, label="gest-mini",
                  package_root="it.housetreespa.gest", frameworks=["vitest"])


def test_extracts_a_documented_frontend_requirement():
    reqs = list(vitest_adapter.requirements(_cfg()))
    fr = next(r for r in reqs if r.method == "ht-calendar > renders the week grid")
    assert fr.category == "FE"
    assert fr.module == "frontend"
    assert fr.unit == "ht-calendar"  # `ht-calendar.test` -> `.test` stripped
    assert fr.spec.is_complete()
    assert fr.spec.us == "US-001-sample-story"
    assert fr.file_rel == "frontend/src/components/ht-calendar.test.ts"
    assert fr.id == "FE-frontend.ht-calendar#ht-calendar > renders the week grid"


def test_describe_path_is_folded_into_the_method_slug():
    reqs = list(vitest_adapter.requirements(_cfg()))
    # every test under `describe("ht-calendar")` carries that title in its method slug
    assert all(r.method.startswith("ht-calendar > ") for r in reqs)


def test_undocumented_frontend_test_is_incomplete_but_visible():
    reqs = list(vitest_adapter.requirements(_cfg()))
    undoc = next(r for r in reqs if r.method.endswith("undocumented_frontend_test_is_flagged"))
    assert not undoc.spec.is_complete()
    assert undoc.category == "FE"


def test_no_frontend_tree_yields_nothing():
    cfg = Config(repo_root=FIXTURE_REPO, app_root=FIXTURE_REPO / "nope", label="x")
    assert list(vitest_adapter.requirements(cfg)) == []
