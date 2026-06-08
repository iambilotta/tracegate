"""Renderers: the same catalog, two renderings (markdown for humans, JSON for machines).

ADR-0006. The markdown requirements view is byte-compatible with the Phase-0 output so
the drift-gate on existing repos stays stable. The JSON view is the machine/CI contract:
a stable, sorted, deterministic dump of the requirement catalog.
"""
from __future__ import annotations

import json
from collections import defaultdict

from . import javadoc_render
from .model import Catalog, Requirement

_CAT_ORDER = ("FR", "NFR", "INV", "CON", "E2E")


def _long_name(cat: str) -> str:
    return {
        "FR": "Functional Requirements",
        "NFR": "Non-Functional Requirements",
        "INV": "Domain Invariants",
        "CON": "HTTP Boundary Contracts",
        "E2E": "End-to-End Acceptance (Playwright)",
    }.get(cat, cat)


def _pct(num: int, denom: int) -> str:
    if denom == 0:
        return "0%"
    return f"{round(100 * num / denom)}%"


def requirements_md(reqs: list[Requirement], label: str) -> str:
    lines: list[str] = []
    lines.append(f"# Requirements — {label}")
    lines.append("")
    lines.append(
        "Auto-generated from test sources by tracegate. Do NOT edit by hand: edit the "
        "test javadoc / docstring instead and rerun. Single source of truth is the test code."
    )
    lines.append("")
    lines.append(
        "**Convention**: category from the test name "
        "(`*Test`=FR, `*NfrTest`=NFR, `*InvariantTest`=INV, `*ContractTest`=CON; "
        "Python file markers `*invariant*`/`*nfr*`/`*contract*` map the same way; "
        "Playwright E2E tests join as **E2E**). "
        "Spec from doc-comment tags `@spec.given` / `@spec.when` / `@spec.then` "
        "(plus optional `@spec.adr` / `@spec.us`). "
        "Tests without a complete spec are listed with `(spec missing)` so they're "
        "visible and lintable."
    )
    lines.append("")

    total = len(reqs)
    with_spec = sum(1 for r in reqs if r.spec.is_complete())
    by_cat: dict[str, int] = defaultdict(int)
    for r in reqs:
        by_cat[r.category] += 1
    lines.append("## Coverage")
    lines.append("")
    lines.append(f"- Total tests scanned: **{total}**")
    lines.append(f"- With complete spec javadoc: **{with_spec}** ({_pct(with_spec, total)})")
    for cat in _CAT_ORDER:
        if by_cat[cat]:
            lines.append(f"- {cat}: {by_cat[cat]}")
    lines.append("")

    by_mod: dict[str, list[Requirement]] = defaultdict(list)
    for r in reqs:
        by_mod[r.module].append(r)

    for module in sorted(by_mod):
        lines.append(f"## Module `{module}`")
        lines.append("")
        by_cat_in_mod: dict[str, list[Requirement]] = defaultdict(list)
        for r in by_mod[module]:
            by_cat_in_mod[r.category].append(r)
        for category in _CAT_ORDER:
            cat_reqs = by_cat_in_mod.get(category, [])
            if not cat_reqs:
                continue
            lines.append(f"### {_long_name(category)}")
            lines.append("")
            for r in sorted(cat_reqs, key=lambda x: (x.unit, x.method)):
                lines.append(f"#### `{r.id}`")
                lines.append("")
                if r.spec.is_complete():
                    lines.append(f"- **Given**: {javadoc_render.to_inline(r.spec.given)}")
                    lines.append(f"- **When**: {javadoc_render.to_inline(r.spec.when)}")
                    lines.append(f"- **Then**: {javadoc_render.to_inline(r.spec.then)}")
                else:
                    lines.append("- _(spec missing — add `@spec.given` / `@spec.when` / `@spec.then` javadoc)_")
                if r.spec.adr:
                    lines.append(f"- **ADR**: {r.spec.adr}")
                if r.spec.us:
                    lines.append(f"- **User Story**: {r.spec.us}")
                lines.append(f"- **File**: `{r.file_rel}`")
                lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def requirements_by_us_md(reqs: list[Requirement], label: str, cfg) -> str:
    """The per-User-Story coverage view. Delegates to the proven grouping logic in
    `generate_requirements` (the core Requirement model is duck-compatible with it:
    same `.id`, `.spec`, `.module`)."""
    from .. import generate_requirements as gr
    return gr.render_by_user_story(reqs, label, cfg)


def requirements_json(catalog: Catalog) -> str:
    """Deterministic machine view: sorted requirement dicts + a coverage summary."""
    reqs = sorted(catalog.requirements, key=lambda r: r.id)
    by_cat: dict[str, int] = defaultdict(int)
    for r in reqs:
        by_cat[r.category] += 1
    doc = {
        "tracegate": {"schema": 1, "kind": "requirements-catalog"},
        "label": catalog.label,
        "coverage": {
            "total": len(reqs),
            "with_complete_spec": sum(1 for r in reqs if r.spec.is_complete()),
            "by_category": {c: by_cat[c] for c in _CAT_ORDER if by_cat[c]},
        },
        "requirements": [r.to_dict() for r in reqs],
        "sections": sorted(catalog.sections.keys()),
    }
    return json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


# --- MANIFEST (session-startup index of every generated doc) -------------

# Hand-curated topic grouping. Order = read priority for a fresh LLM session. Canonical
# home (the code-docs generator imports it from here) so the auto path and the explicit
# `code-docs` subcommand index the same set in the same order (ADR-0009).
MANIFEST_ORDER = [
    ("Scope & roadmap", [
        ("requirements.md", "tests-as-requirements catalog (FR/NFR/INV/CON/E2E), 100% spec javadoc"),
        ("requirements-by-us.md", "tests grouped per User Story with AC coverage gate"),
    ]),
    ("Architecture", [
        ("modules.md", "Modulith canvas + cross-module dependency graph + cycle detection"),
        ("ports.md", "hexagonal ports → adapters matrix"),
        ("templates.md", "JTE template tree (params + include graph)"),
    ]),
    ("Behavior", [
        ("http-endpoints.md", "every HTTP route with javadoc + contract reference"),
        ("events.md", "domain events with emitters + handlers"),
        ("projections.md", "@ProcessingGroup + read models + ResetHandler idempotence flag"),
    ]),
    ("State", [
        ("schema.md", "Flyway migrations + per-table column inventory"),
        ("config.md", "application properties per profile + Java usages"),
        ("dependencies.md", "Maven + npm + Python dependency tree"),
    ]),
    ("Quality & debt", [
        ("coverage.md", "JaCoCo per-file coverage with full file list (incl. 0% files)"),
        ("todo.md", "TODO/FIXME/HACK/@Deprecated inventory with git blame"),
        ("adr-index.md", "Architecture Decision Record index + auto-detected ADR candidates"),
    ]),
]


def manifest_md(label: str, present: set[str]) -> str:
    """Render MANIFEST.md from the SET of generated filenames (in-memory, not disk).

    `present` is the set of files the catalog will write (e.g. {"requirements.md",
    "coverage.md", ...}). Topic order is curated; any generated file not in the curated
    order is listed under 'Other'. JSON outputs are excluded (the manifest indexes the
    human-readable docs)."""
    lines = [f"# MANIFEST — {label} auto-generated docs", ""]
    lines.append(
        "Read this **first** in a fresh session. Every doc below is regenerated from the code "
        "(or tests / migrations / properties / pom) on every commit; the markdown is never the "
        "source of truth. Path-only links so any tool that opens the manifest can lazy-load."
    )
    lines.append("")
    md_present = {n for n in present if n.endswith(".md") and n != "MANIFEST.md"}
    seen: set[str] = set()
    for topic, docs in MANIFEST_ORDER:
        rows = [(name, desc) for name, desc in docs if name in md_present]
        if not rows:
            continue
        lines.append(f"## {topic}")
        lines.append("")
        for name, desc in rows:
            seen.add(name)
            lines.append(f"- [`{name}`](./{name}) — {desc}")
        lines.append("")
    extras = sorted(md_present - seen)
    if extras:
        lines.append("## Other generated docs (uncatalogued)")
        lines.append("")
        for name in extras:
            lines.append(f"- [`{name}`](./{name})")
        lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("**Convention**: `_generated/` is gitignored at the repo root (pattern `**/_generated/`) "
                 "but the tracked `_generated/` of a documented app IS the docs. Pre-commit "
                 "regenerates everything; never hand-edit a file in this directory.")
    return "\n".join(lines).rstrip() + "\n"
