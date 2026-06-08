# tracegate

> **Your tests are your requirements. tracegate proves they never drift — in any stack.**

[![ci](https://github.com/iambilotta/tracegate/actions/workflows/ci.yml/badge.svg)](https://github.com/iambilotta/tracegate/actions/workflows/ci.yml)
License: Apache-2.0 · Status: **v1.1**

tracegate is a polyglot, **zero-config** tool that turns your test suite into a
**machine-checked requirements catalog** and **gates drift in CI**. As a byproduct it
generates an always-true as-built documentation catalog (endpoints, events, schema,
modules, coverage, ADRs, ...).

It is **the gate**, not another doc generator. Its output is deterministic ground-truth —
never LLM-generated — so humans, agents, and CI can all trust it.

---

## 60-second start (zero config)

Install the binary for your OS (no Python needed — see [docs/INSTALL.md](./docs/INSTALL.md)),
then, from any repo:

```bash
tracegate            # auto-detect the stack → requirements catalog + as-built docs
tracegate --check    # CI: exit 2 if the catalog drifted from the code, 0 if in sync
tracegate --json     # the machine view (for CI / agents), no files written
```

That's it. No Gherkin, no bespoke spec file, no config to write. tracegate sniffs your
manifests, enables the right adapters, and writes the catalog to each app's
`_generated/`. A `tracegate.toml` exists only if you want to **override** detection — it
is never required.

What you get on the first run:

- `requirements.md` — every test, as a requirement, grouped by module and category
  (FR / NFR / INV / CON / E2E), with a stable traceability ID.
- `requirements-by-us.md` — the same tests grouped by the User Story they implement,
  with per-acceptance-criterion coverage.
- `requirements.json` — the deterministic machine contract (same catalog, CI-friendly).
- framework sections (when detected): HTTP endpoints, domain events, projections, Flyway
  schema, module canvas, ports matrix, ...
- commodity sections: coverage, TODO/tech-debt, ADR index, dependency tree, and a
  `MANIFEST.md` index of the whole catalog.

`tracegate .` (zero-config) is the **canonical output**: it emits the same full catalog the
explicit `requirements` / `code-docs` subcommands produce for the same repo (same files,
same bytes, same traceability IDs). The explicit subcommands are thin filtered views over
the one engine, not a different code path (see [`decisions/0009`](./decisions/0009-zero-config-canonical-output.md)).

## The convention is an enhancement, not a prerequisite

tracegate derives a requirement from the **name and structure** of every test, with no
annotations. A test called `verifies_a_plain_password_against_its_md5_hex_digest` already
becomes a documented requirement. If you want richer specs, add an optional doc-comment:

```java
/**
 * @spec.given a plaintext password and its known md5 hex digest
 * @spec.when  the verifier compares the plaintext against the stored digest
 * @spec.then  returns true: the password matches
 * @spec.us    US-001-parma-agent-can-login
 */
@Test
void verifies_a_plain_password_against_its_md5_hex_digest() { ... }
```

```python
def test_drift_gate_fails_on_a_stale_doc():
    """
    @spec.given a generated catalog on disk
    @spec.when  the drift-gate runs after a file is tampered
    @spec.then  it exits 2
    @spec.us    US-002-drift-gate
    """
```

Tests without a complete spec still appear — flagged `(spec missing)` so they are visible
and lintable, never hidden. Zero-config gives value on day one; the convention pays off
later. (Adoption is the riskiest assumption; this is the mitigation — see
[`decisions/0004`](./decisions/0004-config-and-autodetect.md).)

## The drift-gate (the product)

`tracegate --check` regenerates the catalog in memory, compares it to what's committed,
and **exits 2 on any drift** (0 when in sync), printing a unified diff of exactly what
changed. Wire it into CI and your requirements can never silently fall out of sync with
the code. The markdown is never the source of truth — to change a doc you change the code
(rename a test, add a `@spec` tag, comment a migration) and regenerate.

Sections derived from a **build artifact** (today `coverage.md`, from a JaCoCo CSV that
only exists after `mvn verify`) are gated *softly*: regenerated best-effort, but never a
false drift on a clean checkout with no `target/`. They are gated normally once the
artifact is present, so real coverage drift is still caught (see
[`decisions/0008`](./decisions/0008-build-artifact-soft-gate.md)).

## How it works

```
tracegate
├── core/        the IP, language- and framework-neutral
│   ├── detect       zero-config stack detection (manifests/markers → adapters)
│   ├── model        the catalog: Requirement + Spec + framework sections
│   ├── ids          traceability-ID schema, one shape for every language
│   ├── gate         the drift-gate engine (exit code + unified diff)
│   ├── render       one catalog, two renderings (markdown + JSON)
│   └── paths        canonical full repo-relative file paths
├── adapters/
│   ├── lang/        java · python            (tree-sitter per language)
│   └── framework/   spring · axon · flyway · playwright
└── self          tracegate documents tracegate (see docs/_generated/)
```

- Reads source via **tree-sitter AST** (real parse trees, no regex fragility).
- The **core owns** the non-commodity IP: tests-as-requirements, traceability IDs,
  per-User-Story coverage, the drift-gate, and the event-sourcing / Modulith /
  hexagonal-aware extractors no generic tool produces.
- It **wraps commodity** where good tools exist (JaCoCo, Flyway, dependency manifests;
  SchemaSpy / springdoc / Modulith-Documenter wrapping is on the v1.1 roadmap) rather
  than reinventing them — the value is the **unified, traceable, drift-gated** catalog
  above them.

Add a language or framework by dropping one adapter module (see
[`decisions/0002`](./decisions/0002-adapter-spi.md)).

## tracegate documents tracegate

The clearest proof of the product: its own catalog lives in
[`docs/_generated/`](./docs/_generated/), regenerated and **drift-gated in CI** on every
push (`make self-check`). The tool eats its own dog food.

## Develop

```bash
make setup        # install runtime + test deps (editable)
make test         # the test suite (golden + adapters + detection + orchestrator)
make self         # regenerate tracegate's own catalog into docs/_generated/
make self-check   # the dogfood drift-gate (what CI runs)
make binary       # build the standalone single-file binary (Nuitka)
```

## Docs

- Founding plan: [`PLAN.md`](./PLAN.md)
- Decisions (ADR): [`decisions/`](./decisions/)
- Install per ecosystem: [`docs/INSTALL.md`](./docs/INSTALL.md)
