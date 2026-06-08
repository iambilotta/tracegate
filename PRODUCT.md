# PRODUCT.md — tracegate

Product management bridge for tracegate's own dogfooding: tracegate documents tracegate.
User Stories declared here are linked from the test suite via `@spec.us` and surfaced in
`docs/_generated/requirements-by-us.md`. This closes the loop the tool exists to close.

## Epic-001 — Zero-config, drift-gated, polyglot catalog

### US-001-zero-config-run

As a developer dropping tracegate on a repo,
I want a single no-flag command to produce a real requirements + as-built catalog,
So that I get value at the first run without instrumenting anything.

### US-002-drift-gate

As a CI pipeline,
I want a `--check` gate that fails when the generated catalog drifts from the code,
So that requirements and code stay in lockstep, machine-checked.

### US-003-stack-detection

As a user of a polyglot or unfamiliar repo,
I want tracegate to detect the languages and frameworks and enable the right adapters,
So that I do not hand-configure the toolchain.

### US-004-canonical-paths

As a consumer of the catalog (human or agent),
I want every file path to be canonical full repo-relative,
So that paths are globally unique and link correctly across the monorepo.
