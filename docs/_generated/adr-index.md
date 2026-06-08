# ADR index — tracegate (as-is)

Auto-generated from `apps/gest/decisions/NNNN-*.md`. Title comes from the H1; status from a `Status: ...` line in the body; supported user stories from `US-NNN-slug` citations anywhere in the file. The 'Candidates' section is a heuristic scan of the codebase for load-bearing decisions (feature flags, invariants, contracts, projections) that have NO matching ADR yet — surface, don't autofix.

**Total ADRs**: 9

## Index

| ID | Status | Date | Title | Supports |
|---|---|---|---|---|
| `ADR-0001` | accepted | — | [Implementation language: Python core + binary packaging](decisions/0001-implementation-language.md) | — |
| `ADR-0002` | accepted | 2026-06-08 | [Adapter SPI: how a third party adds a language or framework](decisions/0002-adapter-spi.md) | — |
| `ADR-0003` | accepted | 2026-06-08 | [Traceability-ID schema, generalized to any language](decisions/0003-traceability-id-schema.md) | — |
| `ADR-0004` | accepted | 2026-06-08 | [Config format + stack auto-detection](decisions/0004-config-and-autodetect.md) | — |
| `ADR-0005` | accepted | — | [Commodity boundary: what we own vs what we wrap](decisions/0005-commodity-boundary.md) | — |
| `ADR-0006` | accepted | 2026-06-08 | [Output model (markdown + JSON) and the drift-gate contract](decisions/0006-output-model-and-gate.md) | — |
| `ADR-0007` | accepted | 2026-06-08 | [Canonical file paths: full repo-relative, everywhere](decisions/0007-canonical-file-paths.md) | — |
| `ADR-0008` | accepted | 2026-06-08 | [Build-artifact-derived sections are soft in the drift-gate](decisions/0008-build-artifact-soft-gate.md) | — |
| `ADR-0009` | accepted | 2026-06-08 | [The zero-config output IS the canonical catalog; explicit subcommands are views](decisions/0009-zero-config-canonical-output.md) | — |

## Candidates (auto-detected, 0 signals)

Heuristic. Each signal usually warrants an ADR (a feature flag, an invariant, a contract, a projection design choice are all decisions you'll want to defend in 6 months). Open the file, decide if it's already covered by an existing ADR, otherwise consider writing a new one.
