"""Canonical path-base (ADR-0007).

Every `file` path tracegate emits is relative to the **target repo root** (the dir
passed as `--target` / the cwd of a zero-config run). Full repo-relative paths are
the canonical, correct form: `apps/gest/src/main/java/.../Foo.java`, never a truncated
`gest/src/...` that drops a leading segment.

The Phase-0 legacy positional entry had a quirk where Java file paths were computed
relative to `test_root.parents[3]` (the `apps/` dir), dropping the `apps/` segment,
while the `--target` path used the true root. This module is the single chokepoint
that makes the canonical form consistent across every generator and language.
"""
from __future__ import annotations

from pathlib import Path


def rel_to_repo(path: Path, repo_root: Path) -> str:
    """Repo-relative POSIX path of `path` under `repo_root`.

    Falls back to the absolute POSIX path if `path` is not under the root (e.g. a
    custom `--out` outside the target): a path we cannot anchor is printed in full
    rather than guessed.
    """
    path = Path(path).resolve()
    repo_root = Path(repo_root).resolve()
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()
