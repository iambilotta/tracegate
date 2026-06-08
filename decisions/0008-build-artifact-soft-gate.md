# ADR-0008 — Build-artifact-derived sections are soft in the drift-gate

Status: **accepted** 2026-06-08. Owner: Francesco. Scope: how `--check` treats sections derived from a build artifact (coverage today).
Significativita': one-way-ish (the gate's exit-code contract is consumed by CI; loosening it for a section class is a behavioral change consumers rely on).

## Context

`coverage.md` is derived from a JaCoCo CSV (`target/site/jacoco/jacoco.csv`) — a BUILD
artifact, absent unless `mvn verify` ran. The drift-gate (ADR-0006) regenerates every
output in memory and compares it to disk. So in any environment without a fresh CSV
(a clean checkout, a pre-commit that did not just build, a lint-only CI lane) the
regenerated `coverage.md` is the "⚠ No JaCoCo CSV found" placeholder, which differs from
the committed coverage written after a real build. Result: `tracegate --check` reports a
PERMANENT FALSE DRIFT on `coverage.md`, breaking gates that never intended to run a build.

This surfaced in the housetree migration: CI / pre-commit lanes that don't build still had
to pass the gate, and a build-artifact section made that impossible.

## Decision

Split generated sections into two classes:

- **Code-derived** (the default): requirements, http-endpoints, events, projections,
  modules, schema, config, ports, templates, todo, adr-index, dependencies. Their input
  is the source tree, always present. **Hard-gated**: any drift exits 2.
- **Build-artifact-derived**: a section whose input is a build output that may be absent
  (today only `coverage`, from the JaCoCo CSV). **Soft-gated**: regenerated best-effort on
  a write run, but EXCLUDED from the drift-gate when its input is absent. When the input
  IS present, the section is gated like any other, so real coverage drift is still caught.

Mechanism (deterministic, no heuristics in the gate):
- An adapter that owns a build-artifact section declares it via the optional SPI
  `build_artifact_sections(cfg) -> {section_name: input_present}` (a pure predicate over
  the artifact's existence). `commondocs` declares `coverage` this way.
- The orchestrator records the flags on the `Catalog`. At `--check`, a section whose flag
  is `False` (input absent) is dropped from the gated file set and reported on stderr as
  `soft-skip (build artifact absent, not gated)`. Everything else is gated unchanged.

So: `tracegate --check` is **deterministic and green on a clean checkout with no
`target/`**, yet still catches real code-derived drift and real coverage drift once a
build has produced the CSV.

## Alternatives considered

- **Never write coverage in `--check` and always skip it**: rejected — then a real
  coverage regression after a build would never be gated; the section would be
  informational only, losing the gate value when it CAN be had.
- **Make the absent-CSV placeholder byte-equal to a "no data" committed file**: rejected —
  forces a meaningless committed artifact and still drifts the moment someone commits real
  coverage.
- **A `--no-coverage` flag the caller must remember**: rejected — poka-yoke over memory;
  the gate should be correct by default, not by the operator remembering a flag.

## Consequences

- + The gate is honest: it fails only on drift the environment could actually have fixed.
  Code-derived drift is always caught; build-artifact drift is caught when buildable.
- + The classification is extensible: any future artifact-derived section (e.g. a
  benchmark JSON, an OpenAPI dump from a running app) declares itself the same way.
- - A coverage regression introduced WITHOUT running a build locally is not caught until a
  lane that builds runs the gate. Acceptable: that lane exists in CI (`mvn verify`), and
  the alternative (false drift everywhere) is worse.
