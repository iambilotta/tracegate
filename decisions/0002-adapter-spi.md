# ADR-0002 — Adapter SPI: how a third party adds a language or framework

Status: **accepted** 2026-06-08. Owner: Francesco. Scope: the contract between `core` and `adapters`.
Significativita': one-way-ish (the SPI shape is what every adapter depends on; widening it later is easy, narrowing it breaks adapters).

## Context

tracegate is `core` (the IP: catalog model, IDs, drift-gate, renderers, detection) plus
`adapters` (per-language and per-framework extractors). For the project to scale past the
maintainer (and for community adapters), the seam between core and an adapter must be a
tiny, documented contract — not an implicit "import whatever you need from core".

## Decision

Two adapter kinds, each a plain Python module under a known package, discovered by name
from a registry in `core.orchestrator`:

- **Language adapter** (`tracegate.adapters.lang.<name>`): exposes
  `extract(cfg: Config) -> Iterator[Requirement]`. It parses the language's test sources
  (tree-sitter) and yields core `Requirement`s. That is its entire surface.
- **Framework adapter** (`tracegate.adapters.framework.<name>`): exposes any of
  - `sections(cfg) -> dict[str, str]` — name -> rendered-markdown as-built doc sections
    (e.g. `http-endpoints`, `events`, `schema`); the core writes them verbatim.
  - `requirements(cfg) -> Iterator[Requirement]` — when the framework's artifacts ARE
    requirements (e.g. Playwright E2E tests), not a doc section.

An adapter imports only `tracegate.core` (config, model, ids, paths, specdoc). It never
imports another adapter. The core never imports a specific adapter at module load; it
`importlib.import_module`s by name, so a missing optional grammar can't break unrelated
adapters.

## Alternatives considered

- **Entry-points / plugin registry (setuptools `entry_points`)**: deferred. Real value
  only once external adapters exist; the name-based registry is the dumbest thing that
  works for the in-tree adapters we ship now. `# TODO(v1.1)` to promote to entry-points
  when a third party ships one.
- **Abstract base classes**: rejected as ceremony. A module with the right function name
  is a smaller, more Pythonic contract than an ABC the author must subclass.

## Consequences

- + A new language is one file exposing `extract`; a new framework is one file exposing
  `sections`/`requirements`. The Java/Python/Spring/Axon/Flyway/Playwright adapters all
  fit this shape today.
- + The core stays language-agnostic: it knows `Requirement`s and opaque markdown blocks,
  nothing about Java or Spring.
- - Discovery is name-based, so an adapter must live in the right package. Acceptable for
  in-tree adapters; revisit for third-party distribution (see alternatives).
