# ADR-0009 — The zero-config output IS the canonical catalog; explicit subcommands are views

Status: **accepted** 2026-06-08. Owner: Francesco. Scope: the relationship between `tracegate .` and the explicit `requirements` / `code-docs` subcommands.
Significativita': one-way-ish (the catalog shape + the E2E ID scheme appear in committed docs and the JSON contract).

## Context

v1.0 shipped two divergent code paths for the same repo:

- `tracegate .` (zero-config, the headline DX) ran the orchestrator: language adapters +
  framework adapters. It emitted `requirements.json` and derived E2E IDs with a `.spec`
  suffix kept (`E2E-e2e.screenshots.spec#...`), and it OMITTED the commodity sections
  (coverage, todo, adr-index, dependencies, MANIFEST), which lived only in
  `generate_code_docs` behind the explicit `code-docs` subcommand.
- The explicit `requirements` / `code-docs` subcommands called the Phase-0 generators
  directly (`generate_requirements.generate`, `CodeDocs.main`): different header prose,
  different requirement ordering, `.spec` STRIPPED in the E2E ID, no `requirements.json`,
  and a MANIFEST scanned from disk.

So `tracegate .` and `requirements`+`code-docs` produced DIFFERENT catalogs for the same
repo. The housetree migration could not use zero-config and had to wire the explicit
subcommands with flags — defeating "zero-config is the canonical DX" (PLAN §1, ADR-0004).

## Decision

**The zero-config catalog is the single canonical output. The explicit subcommands are
FILTERED VIEWS over the same engine, never a separate code path.**

- The orchestrator (`core.orchestrator.build_catalog` + `render_outputs`) is the one
  engine. It runs language adapters, framework adapters, and the commodity adapter
  (`commondocs`: coverage / todo / adr-index / dependencies), then renders requirements
  (md + JSON) and MANIFEST from the in-memory catalog.
- `tracegate requirements` and `tracegate code-docs` resolve a Config, run the SAME
  zero-config detection to populate adapters, build the SAME catalog, and write only their
  named subset of files (`_REQUIREMENTS_VIEW` / `_CODE_DOCS_VIEW`). A filtered run is
  therefore byte-identical to the same files in the full zero-config run.
- **One canonical E2E ID scheme**: the `.spec` suffix is stripped by the adapter
  (`ids.strip_category_suffix`), exactly like the Java/Python adapters strip their
  category suffixes. `E2E-e2e.screenshots#title` everywhere. The variant that kept `.spec`
  is gone.
- **`requirements.json` is always emitted** by both the auto path and the explicit
  `requirements` subcommand (it is the machine contract, ADR-0006), not opt-in.
- **Paths stay canonical repo-relative** (ADR-0007): both paths route `file_rel` through
  `core.paths.rel_to_repo` against the same repo root, so a documented app's paths are
  identical regardless of entry point.
- **MANIFEST has one renderer** (`core.render.manifest_md`) and one topic order
  (`core.render.MANIFEST_ORDER`); `generate_code_docs` imports both, so the auto path and
  the explicit `code-docs` MANIFEST are byte-identical.

Proof (genchi genbutsu): on the real `housetree` monorepo, `tracegate .` and
`requirements`+`code-docs` now produce the IDENTICAL set of 16 files, all byte-identical;
pinned by `tests/test_convergence.py` on the bundled fixtures.

## Alternatives considered

- **Keep two paths, document the difference**: rejected — it is the exact adoption
  friction the zero-config promise removes; "the headline path is second-class" is a bug,
  not a documentation gap.
- **Make the explicit subcommands the canonical one, auto a wrapper**: rejected — the
  zero-config path is the product's headline DX and the dogfood (`make self`); the
  canonical output must be the one a fresh user gets with no flags.

## Consequences

- + One engine, one catalog, one E2E ID scheme; the explicit subcommands can never again
  silently diverge (they are filters, tested for byte-equality on a fixture).
- + housetree (and any consumer) can adopt zero-config as promised; the explicit
  subcommands remain for emitting a narrower file subset.
- - A one-time re-render of consumer `_generated/` docs: the auto path now also writes the
  commodity sections + `requirements.json`, and the explicit `requirements` output picks
  up the canonical header/ordering. The diff is reviewed and committed once.
- - `generate_requirements.generate` / `CodeDocs.main` are no longer the CLI's path; they
  remain as the underlying collectors the adapters wrap (own vs wrap stays per ADR-0005).
