"""End-to-end orchestrator: detect -> adapters -> catalog -> render -> write/gate.

The integration seam of the whole tool. Runs against the py-mini fixture (zero-config
Python detection) and asserts the rendered markdown + JSON + the drift-gate behavior.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from tracegate.core import detect, orchestrator  # noqa: E402

FIXTURE_REPO = Path(__file__).resolve().parent / "fixtures" / "py-mini"


def test_zero_config_run_produces_md_and_json(tmp_path: Path):
    cfg = detect.detect(FIXTURE_REPO, out=tmp_path)[0]
    rc = orchestrator.run(cfg, check=False)
    assert rc == 0
    md = (tmp_path / "requirements.md").read_text(encoding="utf-8")
    assert "# Requirements" in md
    assert "FR-tests.test_sample#test_fully_documented_requirement_renders" in md
    data = json.loads((tmp_path / "requirements.json").read_text(encoding="utf-8"))
    assert data["tracegate"]["kind"] == "requirements-catalog"
    ids = {r["id"] for r in data["requirements"]}
    assert "INV-tests.test_invariant_sample#test_invariant_holds" in ids
    assert data["coverage"]["total"] == 3


def test_drift_gate_passes_when_in_sync_and_fails_after_edit(tmp_path: Path):
    cfg = detect.detect(FIXTURE_REPO, out=tmp_path)[0]
    orchestrator.run(cfg, check=False)
    # in sync -> 0
    assert orchestrator.run(cfg, check=True) == 0
    # tamper with a generated file -> drift -> 2
    (tmp_path / "requirements.md").write_text("tampered\n", encoding="utf-8")
    assert orchestrator.run(cfg, check=True) == 2


def test_check_on_missing_dir_reports_drift(tmp_path: Path):
    cfg = detect.detect(FIXTURE_REPO, out=tmp_path / "nope")[0]
    assert orchestrator.run(cfg, check=True) == 2
