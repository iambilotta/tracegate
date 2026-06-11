"""Architecture diagrams (Mermaid): domain-model, event-choreography, module-map, state-machine.

Deterministic, pure-AST diagram generators. Asserted end-to-end through the orchestrator
against the gest-mini fixture (which ships a pom.xml so spring + axon detect on), so the
diagrams ride the SAME engine as every other section. The diagrams are Mermaid fenced
blocks (render natively on GitHub + the Next.js intranet), never LLM-generated.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from tracegate.core import detect, orchestrator  # noqa: E402

FIXTURE_REPO = Path(__file__).resolve().parent / "fixtures" / "gest-mini"


def _generate(tmp_path: Path) -> dict[str, str]:
    cfg = detect.detect(FIXTURE_REPO, out=tmp_path)[0]
    assert "spring" in cfg.frameworks and "axon" in cfg.frameworks, (
        f"fixture must detect spring+axon, got {cfg.frameworks}")
    assert orchestrator.run(cfg, check=False) == 0
    return {p.name: p.read_text(encoding="utf-8") for p in tmp_path.iterdir() if p.is_file()}


def test_domain_model_diagram_renders_records_sealed_and_enums(tmp_path: Path):
    """
    @spec.given a domain with a sealed interface (Status + permits), records, and enums
    @spec.when  the domain-model diagram is generated
    @spec.then  domain-model.md is a Mermaid classDiagram with the sealed hierarchy (`<|--`),
                record fields, and `<<enumeration>>`-tagged enums with their constants
    @spec.us    US-005-architecture-diagrams
    """
    files = _generate(tmp_path)
    dm = files["domain-model.md"]
    assert dm.startswith("# Domain model")
    assert "```mermaid" in dm and "classDiagram" in dm
    # sealed interface + its permits -> inheritance edges, each drawn exactly once
    assert "<<sealed>>" in dm
    assert "Status <|-- Planned" in dm
    assert "Status <|-- Cancelled" in dm
    assert "Status <|-- Executed" in dm
    assert dm.count("<|-- Planned") == 1  # no duplicate permits/implements edge
    assert "Status <|.. Planned" not in dm  # realization suppressed (already a permits edge)
    # records carry their components as fields
    assert "<<record>>" in dm
    assert "+String reason" in dm
    assert "+Instant cancelledAt" in dm
    # enums tagged + constants listed
    assert "<<enumeration>>" in dm
    for const in ("PLANNED", "CANCELLED", "EXECUTED", "APPOINTMENT", "CALL", "VISIT"):
        assert const in dm


def test_event_choreography_diagram_wires_emitter_event_projection(tmp_path: Path):
    """
    @spec.given a domain event with an emitter call-site and a projection handler
    @spec.when  the event-choreography diagram is generated
    @spec.then  events-graph.md is a Mermaid flowchart with emitter --emits--> event
                --handled by--> projection (group name shown), all derived from the AST
    @spec.us    US-005-architecture-diagrams
    """
    files = _generate(tmp_path)
    eg = files["events-graph.md"]
    assert eg.startswith("# Event choreography")
    assert "```mermaid" in eg and "flowchart LR" in eg
    assert "em_CreateSampleService -->|emits| ev_SampleCreated" in eg
    assert "ev_SampleCreated -->|handled by| pr_SampleAuditProjection" in eg
    assert "group: sample-audit" in eg


def test_module_map_diagram_renders_cross_module_dependencies(tmp_path: Path):
    """
    @spec.given two modules where `audit` imports from `sample`
    @spec.when  the module-map diagram is generated
    @spec.then  modules-graph.md is a Mermaid flowchart with the cross-module arc, derived
                from the SAME import data modules.md lists (no new parsing), and a cycle
                verdict line
    @spec.us    US-005-architecture-diagrams
    """
    files = _generate(tmp_path)
    mg = files["modules-graph.md"]
    assert mg.startswith("# Module map")
    assert "```mermaid" in mg and "flowchart TD" in mg
    assert "audit --> sample" in mg
    assert "No module cycles" in mg  # the fixture is acyclic


def test_diagrams_are_indexed_in_the_manifest(tmp_path: Path):
    """
    @spec.given a generated catalog
    @spec.when  the MANIFEST is rendered
    @spec.then  it lists the three architecture diagrams under their topic groups
    @spec.us    US-005-architecture-diagrams
    """
    files = _generate(tmp_path)
    manifest = files["MANIFEST.md"]
    for name in ("domain-model.md", "modules-graph.md", "events-graph.md"):
        assert name in manifest, f"MANIFEST missing {name}"


def test_diagrams_are_drift_gated(tmp_path: Path):
    """
    @spec.given the generated diagrams on disk
    @spec.when  one diagram is tampered and `--check` runs
    @spec.then  the drift-gate exits 2: the diagrams are hard-gated like every other doc
    @spec.us    US-005-architecture-diagrams
    """
    cfg = detect.detect(FIXTURE_REPO, out=tmp_path)[0]
    orchestrator.run(cfg, check=False)
    assert orchestrator.run(cfg, check=True) == 0
    (tmp_path / "domain-model.md").write_text("tampered\n", encoding="utf-8")
    assert orchestrator.run(cfg, check=True) == 2
