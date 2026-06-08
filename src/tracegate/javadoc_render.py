"""Back-compat shim: javadoc_render moved to `tracegate.core.javadoc_render` in Phase 1.

Works both as a package module (`tracegate.javadoc_render`) and when imported standalone
(the generators add `src/tracegate` to sys.path and do `import javadoc_render`).
"""
from __future__ import annotations

try:  # package context
    from .core.javadoc_render import to_block, to_inline  # noqa: F401
except ImportError:  # standalone: src/tracegate is on sys.path, so core/ is importable
    from core.javadoc_render import to_block, to_inline  # type: ignore[no-redef]  # noqa: F401
