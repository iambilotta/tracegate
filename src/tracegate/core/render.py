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
