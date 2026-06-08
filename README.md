# tracegate

> **Your tests are your requirements. tracegate proves they never drift — in any stack.**

Status: **early / founding** (work in progress). License: Apache-2.0.

tracegate is a polyglot, zero-config tool that turns your test suite into a
**machine-checked requirements catalog** and **gates drift in CI**. It also
generates an always-true as-built documentation catalog (endpoints, events,
schema, modules, coverage, ADRs, ...) as a byproduct.

## Why

In the agentic era, generated *prose* context can mislead an agent (it is
redundant with the code the agent already reads). tracegate is different: its
output is **deterministic ground-truth**, **drift-gated**, and it keeps human
intent (the requirements your tests encode) and the code **in lockstep** —
verifiable by humans, agents, and CI alike.

It is **the gate**, not another doc generator.

## How it works

- Reads source via **tree-sitter AST** (Java, TypeScript/Playwright, Python, PHP, ...).
- **Auto-detects your stack**, zero-config (at most a `tracegate.toml`).
- **Wraps commodity tools** where they are good (SchemaSpy, springdoc/OpenAPI,
  Spring Modulith Documenter, log4brains, JaCoCo) under one **unified, traceable,
  drift-gated** catalog — it does not reinvent them.
- Owns the non-commodity layer: **tests-as-requirements**, auto-derived
  **traceability IDs**, per-user-story coverage, the **drift-gate**, and the
  event-sourcing / Modulith / hexagonal-aware extractors no generic tool does.

## Quickstart (target DX)

```bash
tracegate            # auto-detect stack -> requirements + as-built catalog
tracegate --check    # CI: fail on drift between tests-as-requirements and code
```

No Gherkin, no bespoke spec to maintain: your existing tests are the spec. The
optional `@spec` convention is an enhancement, not a prerequisite.

## Docs

Founding plan: [`PLAN.md`](./PLAN.md). Decisions: [`decisions/`](./decisions/).
