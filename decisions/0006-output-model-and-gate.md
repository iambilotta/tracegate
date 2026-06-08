# ADR-0006 — Output model (markdown + JSON) and the drift-gate contract

Status: **accepted** 2026-06-08. Owner: Francesco. Scope: what tracegate emits and how `--check` behaves.
Significativita': one-way-ish (the JSON schema and the exit-code contract are consumed by CI; changing them is a breaking change).

## Context

The same catalog must serve humans (readable docs) and machines (CI, agents). And the
drift-gate is the product (PLAN §1), so its exit-code + diff contract must be crisp and
deterministic.

## Decision

**One catalog, two renderings** (`core.render`):
- **Markdown** (`requirements.md`, `requirements-by-us.md`, plus framework sections like
  `http-endpoints.md`, `events.md`, `schema.md`) for humans. Byte-compatible with the
  Phase-0 output where it already existed, so the gate on existing repos stays stable.
- **JSON** (`requirements.json`) for machines: `{tracegate:{schema,kind}, label, coverage,
  requirements:[...], sections:[...]}`, requirements sorted by ID, deterministic
  (`sort_keys` off but stable construction, fixed indent). `schema: 1` is the version
  knob. This is the contract a CI step or an agent parses; the markdown is the human face.

**Drift-gate contract** (`core.gate`, surfaced by `--check`):
- Regenerate every output in memory, compare to disk.
- A file missing or differing = **drift**. Any drift -> process exit **2**. In sync ->
  exit **0**. (2, not 1, to distinguish drift from a crash/usage error, which use 64/!=2.)
- On drift, print a unified diff per stale file to stderr — the human/PR-bot reads exactly
  what changed, not a 700-line markdown diff.

The markdown is never the source of truth; to change a doc you change the code (a javadoc,
a test name, a migration comment) and regenerate.

## Alternatives considered

- **Markdown-only** (parse the md back for CI): rejected — brittle; machines deserve a
  real schema. **JSON-only**: rejected — humans deserve readable docs and PR review.
- **Exit 1 on drift**: rejected — 1 collides with generic failure; 2 is an unambiguous
  "drift detected" the CI can branch on.

## Consequences

- + CI gets a stable JSON contract and an unambiguous exit code; humans get readable docs
  and a precise diff.
- + The two renderings can't disagree: they're projections of one in-memory catalog.
- - The JSON schema is now a compatibility surface (`schema: 1`); evolve it with a version
  bump, not a silent shape change.
