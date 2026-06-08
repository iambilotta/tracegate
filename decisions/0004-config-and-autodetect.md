# ADR-0004 — Config format + stack auto-detection

Status: **accepted** 2026-06-08. Owner: Francesco. Scope: how tracegate decides what to run with no flags.
Significativita': two-way (detection heuristics and the toml shape are easy to evolve).

## Context

The riskiest adoption assumption (PLAN §1) is that a convention is a barrier. The
mitigation is **zero-config that gives value at the first run** on an un-instrumented
repo. So `tracegate <dir>` with no flags must detect the stack and enable the right
adapters by itself; config is an override, never a prerequisite (convention-over-
configuration, DHH).

## Decision

**Auto-detection** (`core.detect`), deterministic and simple:
- An **app root** is a dir holding a recognized manifest (`pom.xml`, `pyproject.toml`,
  `setup.py`, `build.gradle[.kts]`). The target root counts; nested app roots are
  discovered up to a bounded depth, skipping noise dirs (`.git`, `node_modules`,
  `target`, `.venv`, ...). An empty repo still yields one whole-repo Config so a run
  never silently no-ops.
- **Languages**: `java` if `src/main/java` or `.java` files exist; `python` if a
  `pyproject.toml`/`setup.py` or `.py` files exist.
- **Frameworks**: `spring`/`axon` from `pom.xml` dependency strings; `flyway` from a
  `db/migration/` dir; `playwright` from a `playwright.config.*` or an `e2e/**/*.spec.ts`.
- **Java package root** inferred from the deepest single-child package chain under
  `src/main/java` (stops where the tree first branches: that's where modules begin).

**Config format**: an optional `tracegate.toml` at the target root. Top-level keys
(`languages`, `frameworks`, `package_root`, `label`) override detection globally; an
`[[apps]]` array declares apps explicitly (each with `path` + optional overrides). Absent
file = pure auto-detection. Chosen `toml` for parity with `pyproject.toml`/Cargo and a
stdlib parser (`tomllib`), no dependency.

## Alternatives considered

- **Mandatory config file**: rejected — it is the adoption barrier we are removing.
- **Build-tool introspection (invoke Maven/Gradle/pip to enumerate deps)**: rejected for
  v1.0 — slow, needs the toolchains installed, defeats "scarica-ed-esegui". Marker
  sniffing covers the 80% case; `# TODO(v1.1)` for richer dep detection if it bites.

## Consequences

- + `tracegate <dir>` produces a real catalog on a repo it has never seen.
- + Overrides exist for the cases detection gets wrong, without making them mandatory.
- - Heuristics will misfire on exotic layouts; the override path and explicit `[[apps]]`
  are the escape hatch, and detection is pure/testable so fixes are cheap.
