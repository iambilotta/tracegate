"""Commodity code-docs adapter: coverage · todo · adr-index · dependencies.

These are the cross-cutting, language-/framework-neutral sections that the explicit
`code-docs` subcommand always produced but the zero-config path used to omit (the
divergence ADR-0009 closes). Folding them in here makes `tracegate .` emit the SAME
catalog the explicit subcommands do.

`coverage` is special: it is derived from a BUILD ARTIFACT (the JaCoCo CSV, present only
after `mvn verify`), so it is declared via `build_artifact_sections(cfg)` and the
drift-gate treats it softly when the CSV is absent (ADR-0008). The other three are
code-derived and hard-gated like every other section.

MANIFEST is NOT produced here: the orchestrator renders it last, from the full catalog,
so it can index every section regardless of which adapter contributed it.
"""
from __future__ import annotations

from ...core.config import Config
from ... import generate_code_docs as cd


# Section names this adapter derives from a build artifact, with the predicate that says
# whether that artifact is present for a given target. Kept as data so the orchestrator
# can ask "is this section's input present?" without knowing what the artifact is.
_BUILD_ARTIFACTS = {
    "coverage": lambda g: g.JACOCO_CSV.is_file(),
}


def sections(cfg: Config) -> dict[str, str]:
    g = cd.CodeDocs(cfg)
    return {
        "coverage": g.render_coverage(),
        "todo": g.render_todos(g.collect_todos()),
        "adr-index": g.render_adr_index(g.parse_adrs(), g.detect_adr_candidates()),
        "dependencies": g.render_dependencies(g.collect_dependencies()),
    }


def build_artifact_sections(cfg: Config) -> dict[str, bool]:
    """Return {section_name: input_present} for the build-artifact-derived sections this
    adapter owns. The orchestrator uses `input_present=False` to skip the section from
    the hard drift-gate (regenerate best-effort, gate only when buildable)."""
    g = cd.CodeDocs(cfg)
    return {name: present(g) for name, present in _BUILD_ARTIFACTS.items()}
