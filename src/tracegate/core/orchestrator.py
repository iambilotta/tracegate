"""The orchestrator: detection -> adapters -> catalog -> render -> write/gate.

This is the spine the CLI drives. For one `Config` it runs the enabled language adapters
to build the requirement catalog, runs the enabled framework adapters to attach their
as-built sections, then renders markdown + JSON and either writes them or runs the
drift-gate (`--check`).

Zero-config: `build_configs(target)` asks `core.detect`; the CLI passes the result here.
"""
from __future__ import annotations

from pathlib import Path

from . import gate, render
from .config import Config
from .model import Catalog, Requirement

# Language adapter registry: name -> extract(cfg) -> Iterator[Requirement].
# Imported lazily so a missing optional grammar never breaks unrelated adapters.
_LANG_ADAPTERS = ("java", "python")
# Framework adapters: name -> module exposing `sections(cfg) -> dict[name, markdown]`.
_FRAMEWORK_ADAPTERS = ("spring", "axon", "flyway", "playwright")
# Commodity adapters: cross-cutting, language-/framework-neutral sections (coverage,
# todo, adr-index, dependencies). Always run so the zero-config catalog matches what the
# explicit `code-docs` subcommand produces (ADR-0009 convergence). They expose the same
# `sections(cfg)` SPI plus an optional `build_artifact_sections(cfg)` (ADR-0008).
_COMMODITY_ADAPTERS = ("commondocs",)


def _load_lang(name: str):
    from importlib import import_module
    return import_module(f"tracegate.adapters.lang.{name}")


def _load_framework(name: str):
    from importlib import import_module
    return import_module(f"tracegate.adapters.framework.{name}")


def build_catalog(cfg: Config) -> Catalog:
    """Run every enabled adapter and assemble the catalog for one app.

    The zero-config catalog is the canonical output: requirements (language + Playwright
    adapters) + framework sections (spring/axon/flyway) + the cross-cutting commodity
    sections (commondocs: coverage/todo/adr-index/dependencies). The explicit subcommands
    are thin views over this same engine (ADR-0009)."""
    catalog = Catalog(label=cfg.label)
    reqs: list[Requirement] = []
    for lang in cfg.languages:
        if lang not in _LANG_ADAPTERS:
            continue
        mod = _load_lang(lang)
        reqs.extend(mod.extract(cfg))
    catalog.requirements = reqs

    for fw in cfg.frameworks:
        if fw not in _FRAMEWORK_ADAPTERS:
            continue
        mod = _load_framework(fw)
        _attach(catalog, cfg, mod)

    # Commodity sections always run (they are language-/framework-neutral). On a target
    # with none of their inputs the sections render their own "absent" placeholder, never
    # crash. This is what makes `tracegate .` == `code-docs` for the same repo.
    for name in _COMMODITY_ADAPTERS:
        _attach(catalog, cfg, _load_framework(name))
    return catalog


def _attach(catalog: Catalog, cfg: Config, mod) -> None:
    """Attach one adapter's contributions (requirements + sections + build-artifact flags)."""
    if hasattr(mod, "requirements"):
        catalog.requirements.extend(mod.requirements(cfg))
    if hasattr(mod, "sections"):
        for name, body in mod.sections(cfg).items():
            catalog.sections[name] = body
    if hasattr(mod, "build_artifact_sections"):
        for name, present in mod.build_artifact_sections(cfg).items():
            catalog.build_artifact_sections[name] = present


def render_outputs(cfg: Config, catalog: Catalog) -> dict[str, str]:
    """Return {relative-filename: content} for the whole catalog (md + JSON + sections).

    `requirements.json` is always part of the canonical output (the machine contract,
    ADR-0006); both the auto path and the explicit `requirements` subcommand emit it.
    MANIFEST is rendered last, from the full file set, so it indexes every section."""
    out: dict[str, str] = {}
    out["requirements.md"] = render.requirements_md(catalog.requirements, catalog.label)
    out["requirements-by-us.md"] = render.requirements_by_us_md(
        catalog.requirements, catalog.label, cfg)
    out["requirements.json"] = render.requirements_json(catalog)
    for name, body in catalog.sections.items():
        out[f"{name}.md"] = body
    out["MANIFEST.md"] = render.manifest_md(catalog.label, set(out))
    return out


# Named file-set views over the one catalog, for the explicit subcommands. They are
# FILTERS over `render_outputs`, never a separate code path: `tracegate requirements` and
# `tracegate code-docs` are the same engine, narrowed (ADR-0009). `None` = the full
# canonical catalog (the zero-config default).
_REQUIREMENTS_VIEW = ("requirements.md", "requirements-by-us.md", "requirements.json")
_CODE_DOCS_VIEW = (
    "http-endpoints.md", "events.md", "projections.md", "modules.md", "schema.md",
    "config.md", "ports.md", "templates.md", "coverage.md", "todo.md", "adr-index.md",
    "dependencies.md", "MANIFEST.md",
)


def run(cfg: Config, *, check: bool, only: "tuple[str, ...] | None" = None) -> int:
    """Write (or gate) the catalog for one app. Returns a process exit code.

    `only` restricts the emitted files to a named subset (the explicit-subcommand views);
    the catalog is still built by the one engine, so a filtered run is byte-identical to
    the same files in the full zero-config run."""
    catalog = build_catalog(cfg)
    files = render_outputs(cfg, catalog)
    if only is not None:
        files = {name: content for name, content in files.items() if name in only}
    out_dir = cfg.generated_dir
    paths_content = {out_dir / name: content for name, content in files.items()}

    if check:
        # Build-artifact sections whose input is absent are soft: regenerate best-effort
        # on a write run, but NEVER hard-fail the gate when there is no build (ADR-0008).
        # On a clean checkout with no `target/`, coverage would otherwise be a permanent
        # false drift. When the input IS present, the section is gated like any other, so
        # real drift is still caught.
        gated = {p: c for p, c in paths_content.items()
                 if not _is_soft_skipped(p.name, catalog)}
        skipped = sorted(p.name for p in paths_content if _is_soft_skipped(p.name, catalog))
        drift = gate.check(gated)
        if skipped:
            import sys
            print("soft-skip (build artifact absent, not gated): " + ", ".join(skipped),
                  file=sys.stderr)
        if drift:
            gate.report(drift)
            return 2
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    for path, content in paths_content.items():
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path} ({len(content.splitlines())} lines)")
    return 0


def _is_soft_skipped(filename: str, catalog: Catalog) -> bool:
    """True if `filename` is a build-artifact section whose input was absent at
    generation time, so the drift-gate must not hard-fail on it (ADR-0008)."""
    name = filename[:-3] if filename.endswith(".md") else filename
    return catalog.build_artifact_sections.get(name) is False
