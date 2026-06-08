# ADR-0005 — Commodity boundary: what we own vs what we wrap

Status: **accepted (lean)** 2026-06-08. Owner: Francesco. Scope: where the core stops and a wrapped tool begins.
Significativita': two-way per item (each delegation can be added/removed independently).

## Context

The doc-generation space is crowded (SchemaSpy, springdoc/OpenAPI, Spring Modulith
Documenter, log4brains, JaCoCo). Re-implementing them is over-engineering and a
maintenance sink (PLAN §6). The wedge is the **unified, traceable, drift-gated catalog
ABOVE** them, not the extractors themselves.

## Decision

**The core OWNS** the non-commodity IP, because no generic tool produces it:
tests-as-requirements, traceability IDs, per-User-Story coverage, the drift-gate, and the
event-sourcing / Modulith / hexagonal-aware extractors (events, projections with
`@ResetHandler` idempotence flagging, ports matrix, module cycles).

**The core WRAPS / DELEGATES** the commodity, surfacing it as a catalog section rather
than re-deriving it: schema (SchemaSpy), OpenAPI (springdoc), module docs (Modulith
Documenter), ADR log (log4brains), coverage (JaCoCo CSV).

For v1.0 the wrapped tools are consumed at the level we already had working in housetree
(JaCoCo CSV join, Flyway SQL parse, pom/npm dep parse). Shelling out to SchemaSpy /
springdoc / Modulith-Documenter as first-class commodity adapters is **`# TODO(v1.1)`**:
real, planned, but not faked for the MMP. The boundary (own vs wrap) is what this ADR
locks; the specific wrappers land as the dogfooded consumers need them.

## Alternatives considered

- **Re-implement every extractor**: rejected (PLAN risk "manutenzione di N adapter da
  soli"). Wrapping keeps the maintainer's surface small.
- **Wrap everything, own nothing**: rejected — then tracegate is "another doc generator",
  the exact me-too the positioning refuses. The owned layer is the product.

## Consequences

- + Small surface to maintain; the value compounds in the unified+gated layer.
- + Clear contributor guidance: new commodity = a wrapping adapter, not a rewrite.
- - Until the commodity wrappers land (v1.1), some sections use our own lean extractors
  (Flyway SQL parse, dep parse) rather than the canonical tool. Honest and documented.
