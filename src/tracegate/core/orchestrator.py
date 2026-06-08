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


def _load_lang(name: str):
    from importlib import import_module
    return import_module(f"tracegate.adapters.lang.{name}")


def _load_framework(name: str):
    from importlib import import_module
    return import_module(f"tracegate.adapters.framework.{name}")


# TODO(v1.1): the zero-config path emits requirements + framework sections (the IP).
# The cross-cutting commodity sections (coverage, todo, adr-index, dependencies, MANIFEST)
# still live in `generate_code_docs` and are reachable via the explicit `code-docs`
# subcommand; fold them into the auto path as a `common` adapter once the commodity-wrap
# boundary (ADR-0005) lands its first wrapped tool.
def build_catalog(cfg: Config) -> Catalog:
    """Run every enabled adapter and assemble the catalog for one app."""
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
        if hasattr(mod, "requirements"):
            catalog.requirements.extend(mod.requirements(cfg))
        if hasattr(mod, "sections"):
            for name, body in mod.sections(cfg).items():
                catalog.sections[name] = body
    return catalog


def render_outputs(cfg: Config, catalog: Catalog) -> dict[str, str]:
    """Return {relative-filename: content} for the whole catalog (md + JSON + sections)."""
    out: dict[str, str] = {}
    out["requirements.md"] = render.requirements_md(catalog.requirements, catalog.label)
    out["requirements-by-us.md"] = render.requirements_by_us_md(
        catalog.requirements, catalog.label, cfg)
    out["requirements.json"] = render.requirements_json(catalog)
    for name, body in catalog.sections.items():
        out[f"{name}.md"] = body
    return out


def run(cfg: Config, *, check: bool) -> int:
    """Write (or gate) the catalog for one app. Returns a process exit code."""
    catalog = build_catalog(cfg)
    files = render_outputs(cfg, catalog)
    out_dir = cfg.generated_dir
    paths_content = {out_dir / name: content for name, content in files.items()}

    if check:
        drift = gate.check(paths_content)
        if drift:
            gate.report(drift)
            return 2
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)
    for path, content in paths_content.items():
        path.write_text(content, encoding="utf-8")
        print(f"wrote {path} ({len(content.splitlines())} lines)")
    return 0
