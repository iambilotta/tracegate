"""The drift-gate engine (ADR-0006). The gate is the product.

`check()` compares freshly-rendered content against what is on disk and returns the set
of drifted files with a unified diff for each. `--check` exits 2 on any drift, 0 when in
sync. The diff output is what a human or a PR bot reads to see exactly what changed.
"""
from __future__ import annotations

import difflib
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Drift:
    path: Path
    reason: str          # "missing" | "stale"
    diff: str            # unified diff (empty for a missing file)


def check(rendered: dict[Path, str]) -> list[Drift]:
    """Return one Drift per file whose on-disk content differs from `rendered`."""
    drifts: list[Drift] = []
    for path, content in sorted(rendered.items(), key=lambda kv: str(kv[0])):
        if not path.is_file():
            drifts.append(Drift(path=path, reason="missing", diff=""))
            continue
        on_disk = path.read_text(encoding="utf-8")
        if on_disk != content:
            diff = "".join(
                difflib.unified_diff(
                    on_disk.splitlines(keepends=True),
                    content.splitlines(keepends=True),
                    fromfile=f"a/{path.name} (on disk)",
                    tofile=f"b/{path.name} (regenerated)",
                    n=1,
                )
            )
            drifts.append(Drift(path=path, reason="stale", diff=diff))
    return drifts


def report(drifts: list[Drift], stream=sys.stderr, show_diff: bool = True) -> None:
    """Human-readable drift report on stderr (the CI gate's voice)."""
    print(f"DRIFT: {len(drifts)} generated file(s) out of date", file=stream)
    for d in drifts:
        print(f"  - {d.reason}: {d.path}", file=stream)
    if show_diff:
        for d in drifts:
            if d.diff:
                print(file=stream)
                print(d.diff, file=stream, end="")
    print(
        "\nRun tracegate without --check to regenerate, review the diff, and commit.",
        file=stream,
    )
