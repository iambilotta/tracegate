"""Convergence + build-artifact-gate tests (ADR-0008, ADR-0009).

Pins the two defects the housetree migration surfaced:

1. The zero-config `tracegate .` catalog MUST equal what the explicit `requirements` +
   `code-docs` subcommands produce for the same repo: same files, same bytes, same E2E
   ID derivation (no `.spec` divergence). The explicit subcommands are thin VIEWS over
   the one engine, never a separate code path.
2. A build-artifact-derived section (coverage, from a JaCoCo CSV that only exists after a
   build) must NOT false-positive the drift-gate when its input is absent, while still
   catching real code-derived drift and real coverage drift when the CSV is present.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
sys.path.insert(0, str(SRC))

from tracegate import cli  # noqa: E402
from tracegate.adapters.framework import playwright  # noqa: E402
from tracegate.core import detect, orchestrator  # noqa: E402

GEST_MINI = HERE / "fixtures" / "gest-mini"
PY_MINI = HERE / "fixtures" / "py-mini"


# --- Bug 1: zero-config == explicit subcommands ------------------------------

def _auto_files(repo: Path, out: Path) -> dict[str, str]:
    cfg = detect.detect(repo, out=out)[0]
    orchestrator.run(cfg, check=False)
    return {p.name: p.read_text(encoding="utf-8") for p in out.iterdir() if p.is_file()}


def _explicit_files(repo: Path, out: Path) -> dict[str, str]:
    cli.main(["requirements", "--target", str(repo), "--app-subdir", ".", "--out", str(out)])
    cli.main(["code-docs", "--target", str(repo), "--app-subdir", ".", "--out", str(out)])
    return {p.name: p.read_text(encoding="utf-8") for p in out.iterdir() if p.is_file()}


def test_zero_config_catalog_equals_explicit_subcommands(tmp_path: Path):
    """
    @spec.given a repo with tests + framework + commodity sources
    @spec.when  `tracegate .` runs and the explicit requirements + code-docs subcommands run
    @spec.then  both produce the IDENTICAL set of files with byte-identical content
    @spec.us    US-003-zero-config-convergence
    """
    auto = _auto_files(GEST_MINI, tmp_path / "auto")
    explicit = _explicit_files(GEST_MINI, tmp_path / "explicit")
    assert set(auto) == set(explicit), (
        f"file set diverged\nauto-only: {sorted(set(auto) - set(explicit))}\n"
        f"explicit-only: {sorted(set(explicit) - set(auto))}")
    diffs = [name for name in auto if auto[name] != explicit[name]]
    assert not diffs, f"content diverged for: {diffs}"


def test_zero_config_emits_markdown_catalog_and_commodity_sections(tmp_path: Path):
    """
    @spec.given a repo detected with zero config
    @spec.when  `tracegate .` runs
    @spec.then  the written catalog is the markdown set (requirements.md + by-us) AND the
                commodity sections (coverage, todo, adr-index, dependencies, MANIFEST), and it
                does NOT write the verbose requirements.json twin as a file (the flipped
                convention; the JSON catalog stays available via `tracegate --json`)
    @spec.us    US-003-zero-config-convergence
    """
    auto = _auto_files(GEST_MINI, tmp_path / "auto")
    for name in ("requirements.md", "requirements-by-us.md", "coverage.md", "todo.md",
                 "adr-index.md", "dependencies.md", "MANIFEST.md"):
        assert name in auto, f"zero-config catalog is missing {name}"
    assert "requirements.json" not in auto, "requirements.json must not be written as a file"


# --- Bug 1: one canonical E2E ID scheme (no `.spec` divergence) --------------

def test_e2e_id_strips_spec_suffix_like_every_other_adapter(tmp_path: Path):
    """
    @spec.given a Playwright `*.spec.ts` E2E test
    @spec.when  the playwright adapter derives its requirement ID
    @spec.then  the `.spec` suffix is stripped (`E2E-e2e.smoke#...`, not `...smoke.spec#...`)
    @spec.us    US-003-zero-config-convergence
    """
    cfg = detect.detect(GEST_MINI)[0]
    e2e_ids = [r.id for r in playwright.requirements(cfg)]
    assert e2e_ids, "fixture must contain at least one E2E test"
    assert "E2E-e2e.smoke#home_page_renders" in e2e_ids
    assert all(".spec#" not in i for i in e2e_ids), f"`.spec` leaked into an ID: {e2e_ids}"


# --- Bug 2: build-artifact section does not false-positive the gate ----------

def _jacoco_csv(repo: Path) -> Path:
    return repo / "target" / "site" / "jacoco" / "jacoco.csv"


def test_check_is_green_without_jacoco_csv_but_still_catches_code_drift(tmp_path: Path):
    """
    @spec.given a clean checkout with NO build artifact (no target/jacoco.csv)
    @spec.when  the catalog is generated then `--check` runs, first in sync then after a
                code-derived file is tampered
    @spec.then  the gate is GREEN in sync (coverage is soft-skipped, not a false drift)
                yet still exits 2 when a code-derived requirement is tampered
    @spec.us    US-004-build-artifact-soft-gate
    """
    out = tmp_path / "gen"
    cfg = detect.detect(PY_MINI, out=out)[0]
    assert not _jacoco_csv(PY_MINI).exists(), "fixture must ship without a JaCoCo CSV"
    orchestrator.run(cfg, check=False)
    # in sync, no build -> coverage soft-skipped -> GREEN
    assert orchestrator.run(cfg, check=True) == 0
    # tampering a code-derived doc is still caught
    (out / "requirements.md").write_text("tampered\n", encoding="utf-8")
    assert orchestrator.run(cfg, check=True) == 2


def test_coverage_is_hard_gated_once_the_csv_is_present(tmp_path: Path):
    """
    @spec.given a JaCoCo CSV present on disk (a build ran)
    @spec.when  the catalog is generated then coverage.md is tampered and `--check` runs
    @spec.then  the gate exits 2: coverage IS gated when its input exists
    @spec.us    US-004-build-artifact-soft-gate
    """
    out = tmp_path / "gen"
    csv = _jacoco_csv(PY_MINI)
    csv.parent.mkdir(parents=True, exist_ok=True)
    csv.write_text(
        "GROUP,PACKAGE,CLASS,INSTRUCTION_MISSED,INSTRUCTION_COVERED,BRANCH_MISSED,"
        "BRANCH_COVERED,LINE_MISSED,LINE_COVERED,COMPLEXITY_MISSED,COMPLEXITY_COVERED,"
        "METHOD_MISSED,METHOD_COVERED\n",
        encoding="utf-8",
    )
    try:
        cfg = detect.detect(PY_MINI, out=out)[0]
        orchestrator.run(cfg, check=False)
        assert orchestrator.run(cfg, check=True) == 0
        (out / "coverage.md").write_text("tampered\n", encoding="utf-8")
        assert orchestrator.run(cfg, check=True) == 2
    finally:
        import shutil
        shutil.rmtree(PY_MINI / "target", ignore_errors=True)
