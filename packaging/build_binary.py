#!/usr/bin/env python3
"""Build the tracegate standalone single-file binary with Nuitka (ADR-0001).

Nuitka compiles the Python core to C and bundles the interpreter + deps into one
executable, so a Laravel/Next.js/Spring dev installs and runs tracegate with no Python
environment. The real risk called out in ADR-0001 is bundling the tree-sitter grammar
`.so`/`.pyd` files (tree_sitter_java / _python / _typescript ship native extensions); we
include their packages explicitly so Nuitka pulls the native libs in.

Usage:
    python packaging/build_binary.py            # build for the current OS
    pip install nuitka                          # prerequisite (kept out of runtime deps)

Output: dist/tracegate (or dist/tracegate.exe on Windows).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENTRY = REPO / "packaging" / "entry.py"
DIST = REPO / "dist"


def main() -> int:
    DIST.mkdir(exist_ok=True)
    cmd = [
        sys.executable, "-m", "nuitka",
        "--onefile",                       # single self-contained binary
        "--standalone",
        "--assume-yes-for-downloads",
        # tree-sitter grammars ship native extensions: include the whole packages so
        # Nuitka resolves their .so/.pyd (the ADR-0001 bundling risk, handled).
        "--include-package=tree_sitter",
        "--include-package=tree_sitter_java",
        "--include-package=tree_sitter_python",
        "--include-package=tree_sitter_typescript",
        # our own package (the entry imports tracegate.* lazily via importlib)
        "--include-package=tracegate",
        f"--output-dir={DIST}",
        "--output-filename=tracegate",
        "--company-name=iambilotta",
        "--product-name=tracegate",
        # the entry point
        str(ENTRY),
    ]
    print("running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=REPO)


if __name__ == "__main__":
    raise SystemExit(main())
