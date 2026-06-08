# ADR-0003 — Traceability-ID schema, generalized to any language

Status: **accepted** 2026-06-08. Owner: Francesco. Scope: the shape of a requirement ID.
Significativita': one-way (IDs leak into PR diffs, dashboards, links; changing the schema renames everything).

## Context

The original housetree IDs were Java-shaped: `<CAT>-<module>.<Class>#<method>`
(`FR-auth.legacy.LegacyPasswordVerifier#verifies_md5_match`). tracegate is polyglot, so
the schema must work for Python and TypeScript too without a per-language special case.

## Decision

One schema for every language:

    <CATEGORY>-<module>.<unit>#<method>

- **CATEGORY** ∈ {FR, NFR, INV, CON, E2E}, derived from the test name/marker:
  - Java/TS class suffix: `*InvariantTest`->INV, `*ContractTest`->CON, `*NfrTest`->NFR,
    `*Test`/`*IT`->FR (the `*IT` Spring/Testcontainers variant is orthogonal).
  - Python file marker: `*invariant*`->INV, `*contract*`->CON, `*nfr*`->NFR, else FR.
- **module**: the dotted module the test lives in — package minus `cfg.package_root`
  (Java), or the dotted dir path of the test file (Python), or `e2e` (Playwright).
- **unit**: the class/file the test belongs to, with the category suffix already stripped
  (`LegacyPasswordVerifierTest`->`LegacyPasswordVerifier`; `screenshots.spec`->`screenshots`).
- **method**: the test method name (Java/Python) or the `test()` title (Playwright).

Derivation lives in `core.ids` (`classify`, `classify_filename`, `strip_category_suffix`,
`requirement_id`); every adapter calls it, so the schema has exactly one implementation.

Renaming a test method changes its ID **by design**: the spec follows the code.

## Alternatives considered

- **A stable surrogate ID (hash / UUID stored in an annotation)**: rejected. It survives
  renames but needs a registry the human maintains — exactly the bespoke spec tracegate
  refuses. The code-derived ID is the point.
- **Per-language ID schemas**: rejected. Cross-language traceability (a Playwright E2E
  test citing the same `@spec.us` as a Java FR) needs one comparable namespace.

## Consequences

- + One ID namespace across Java, Python, TypeScript; the by-US coverage view joins them.
- + No registry to maintain; the ID is a pure function of the code.
- - A rename is a "removed + added" pair in the requirements diff. That is honest signal,
  and the PR diff comment shows it explicitly.
