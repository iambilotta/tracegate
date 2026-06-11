# Changelog

All notable changes to tracegate are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.4.0] — 2026-06-11

### Changed
- **`requirements.json` is no longer written as a file by default (flipped convention).**
  The markdown (`requirements.md`) is the canonical, human- and LLM-facing artifact
  (semantically denser); the verbose JSON twin was churn no file consumer reads (`tracegate
  diff` parses the markdown). The machine catalog stays fully SUPPORTED on demand via
  `tracegate --json` (stdout), rendered from the same catalog — only the auto-written file
  is dropped. Consumers that committed `requirements.json` should remove it.

## [1.3.0] — 2026-06-11

### Added
- **Architecture diagrams (Mermaid), deterministic and drift-gated.** Three new
  as-built sections, each a pure function of the AST/declared data (no prose, no LLM):
  - `domain-model.md` — a Mermaid `classDiagram` of every type under `**/domain/**`:
    records become classes with their components as fields, a `sealed interface` and its
    `permits` list become an inheritance hierarchy (`<|--`), enums are tagged
    `<<enumeration>>` with their constants. (Spring/Java adapter.)
  - `events-graph.md` — a Mermaid `flowchart` event choreography: emitter → event →
    projection (with the `@ProcessingGroup` name), reusing the Axon collectors that
    already know emitters, `@EventHandler`s, and processing groups. (Axon adapter.)
  - `modules-graph.md` — a Mermaid `flowchart` of cross-module `import` dependencies with
    cycles highlighted, from the same data `modules.md` already lists as PlantUML.
    Mermaid so it renders inline on GitHub and the Next.js intranet. (Spring adapter.)
- **State-machine diagram** `state-machine.md` — a Mermaid `stateDiagram-v2` derived from
  a declared transition table in the domain (a type under `**/domain/**` whose enum
  constants carry a `from`/`operation`/`to` shape). Renders only when such a table is
  present; absent otherwise (never invented). (Spring adapter.)
- All four are registered in `MANIFEST_ORDER` and gated by `--check` like every other doc.
- `gest-mini` fixture grew a `src/main/java` domain + a `pom.xml` (so spring + axon detect
  on) and a state-transition table, with golden tests for every diagram.

## [1.2.0] — 2026-06-09

### Added
- `structure.md` — a convention-driven repository tree (the git-tracked skeleton,
  respecting `.gitignore`), rendered read-first in the MANIFEST so a fresh session orients
  from the file layout before anything else.

### Changed
- Zero-config `tracegate .` is the canonical output: the explicit `requirements` /
  `code-docs` subcommands are thin filtered views over the one engine (ADR-0009).
- Build-artifact sections (coverage, from a JaCoCo CSV) are soft-gated when the artifact
  is absent, so a clean checkout never reports a false drift (ADR-0008).

## [1.1.0] — earlier

- Core + adapter SPI, zero-config stack detection, drift-gate, traceability IDs,
  tests-as-requirements, per-User-Story coverage, the as-built code-docs set.

[Unreleased]: https://github.com/iambilotta/tracegate/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/iambilotta/tracegate/compare/v1.1.0...v1.3.0
[1.2.0]: https://github.com/iambilotta/tracegate/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/iambilotta/tracegate/releases/tag/v1.1.0
