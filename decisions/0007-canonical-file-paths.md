# ADR-0007 — Canonical file paths: full repo-relative, everywhere

Status: **accepted** 2026-06-08. Owner: Francesco. Scope: the `file` path every generator emits.
Significativita': one-way-ish (paths appear in committed docs and the JSON contract; changing the base re-writes every path).

## Context

Phase-0 verification found an inconsistency. The CLI `--target` path emitted
`apps/gest/src/...` (full, relative to the repo root), while the legacy positional path
emitted `gest/src/...` — a quirk that dropped the leading `apps/` segment because Java
file paths were computed relative to `test_root.parents[3]` (the `apps/` dir) instead of
the true repo root. Two code paths, two different path bases, for the same file.

## Decision

**Every emitted `file` path is relative to the target REPO ROOT** — the directory passed
as `--target` (or the cwd of a zero-config `tracegate <dir>` run). Full repo-relative is
the canonical, correct form: `apps/gest/src/main/java/.../Foo.java`, never a truncated
`gest/src/...`.

- The single chokepoint is `core.paths.rel_to_repo(path, repo_root)`; every adapter routes
  its `file_rel` through it. A path that cannot be anchored under the root (e.g. a custom
  `--out` outside the target) is printed absolute rather than guessed.
- The legacy positional `generate_requirements.main` was corrected to anchor Java tests on
  the true repo root, so it now matches the CLI byte-for-byte.
- The golden fixture was regenerated to the canonical form, and the golden test asserts the
  canonical path is present AND that the old truncation (`gest-mini/src/...`) does not
  reappear — the assertion was strengthened, not weakened.

## Alternatives considered

- **App-root-relative paths** (`src/main/java/...`, dropping `apps/gest/`): rejected. In a
  monorepo with several apps the same `src/main/java/...` would be ambiguous across apps;
  repo-relative is globally unique.
- **Keep the legacy quirk for back-compat**: rejected. It was a bug, the legacy path had no
  external consumers depending on the truncated form, and consistency across the one tool is
  worth the one-time golden regeneration.

## Consequences

- + One path base across every generator, language, and entry point; paths are globally
  unique within the repo and link correctly from the JSON catalog.
- + The drift-gate is stable: the two former code paths no longer disagree.
- - A one-time re-render of any previously-committed `_generated/` docs on a consumer repo
  (the diff is purely the path prefix; reviewed once, committed once).
