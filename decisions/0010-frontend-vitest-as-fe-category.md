# ADR-0010 — Frontend vitest tests are their own category (FE)

Status: **accepted** 2026-06-13. Owner: Francesco. Scope: how frontend component/unit tests enter the catalog.
Significativita': one-way (the category letter and the ID shape leak into PR diffs, links, dashboards; changing them renames everything — same constraint as ADR-0003).

## Context

tracegate catalogues Java/Python unit tests (language adapters) and Playwright e2e tests
(framework adapter, category E2E). The frontend component/unit layer — vitest specs at
`frontend/src/**/*.{test,spec}.ts` (`describe` / `it` / `test`) — was invisible: a whole
class of requirements (how the islands/components behave) had no traceability ID and no
drift-gate. Consumers (housetree's `apps/gest/frontend`) write these tests but they never
reached `requirements.md`.

## Decision

A new framework adapter `tracegate.adapters.framework.vitest` exposes `requirements(cfg)`
(the same SPI as Playwright, ADR-0002), reusing the **same tree-sitter-typescript engine**
the Playwright adapter already uses (no second TS engine). It emits a new category:

    FE  — "Frontend Component/Unit (vitest)"

added to `core.ids` and the renderer's category order/long-name, after CON and before E2E.

ID scheme, mirroring Playwright's E2E derivation (ADR-0003):

    FE-frontend.<unit>#<describe-path > it-title>

- **category** `FE`. Framework-contributed (like E2E), not class-suffix derived.
- **module** `frontend` — a constant, the parallel to Playwright's `e2e`.
- **unit** the spec file stem with its `.test` / `.spec` suffix stripped via
  `ids.strip_category_suffix` (`ht-calendar.test` -> `ht-calendar`), the one clean-unit
  scheme every adapter shares.
- **method** the enclosing `describe(...)` titles folded into the `it(...)` title with
  ` > ` (vitest's own reporter convention), so nesting is stable in the ID.

The spec is the test's preceding JSDoc `@spec.*` (same `core.specdoc` as Java/Playwright).
Zero-config detection enables the adapter on a vitest config file, a `frontend/package.json`
declaring vitest, or a `frontend/src` tree holding `*.{test,spec}.{ts,tsx}`. It is registered
in `core.orchestrator._FRAMEWORK_ADAPTERS`, so both `tracegate .` and the explicit
`requirements` / `code-docs` views pick it up identically (ADR-0009 convergence holds).

## Alternatives considered

- **Fold vitest into E2E.** Rejected: E2E is the cross-process acceptance layer (a running
  app, a browser); FE is the in-process component/unit layer. Collapsing them loses the
  pyramid distinction the catalog exists to make visible, and would mis-attribute the
  `frontend` module to `e2e`.
- **Fold vitest into FR via a language adapter for TypeScript.** Rejected: a TS *language*
  adapter would also have to claim Playwright's `*.spec.ts` and decide ownership; keeping
  vitest a *framework* adapter (like Playwright) sidesteps that and matches the SPI already
  proven for browser tests. FR is reserved for the backend functional unit tests.
- **Use only the `it` title as the method (drop the describe path).** Rejected: two
  `it("renders")` under different `describe`s would collide on one ID. Folding the describe
  path is how vitest itself disambiguates.

## Consequences

- + Frontend component/unit tests are now first-class requirements with stable IDs, drift-
  gated like every other test, and joinable by `@spec.us` to the same User Stories the
  backend tests cite (one namespace, ADR-0003).
- + One TS engine, one ID scheme, one SPI: the adapter is ~one file, the canon is unchanged.
- - A renamed `describe`/`it` title is a "removed + added" pair in the requirements diff —
  honest signal, identical to the rename behavior ADR-0003 already accepts for every test.
- - `.tsx` specs are scanned too (React-style component tests); the typescript grammar
  parses TSX call expressions, so no extra engine is needed.
