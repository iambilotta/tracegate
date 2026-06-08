"""Back-compat shim: config moved to `tracegate.core.config` in Phase 1.

Works both as a package module and when imported standalone (the generators add
`src/tracegate` to sys.path and do `import config`).
"""
from __future__ import annotations

try:  # package context
    from .core.config import (  # noqa: F401
        DEFAULT_APP_SUBDIR,
        DEFAULT_PACKAGE_ROOT,
        Config,
        resolve,
    )
except ImportError:  # standalone: src/tracegate on sys.path, core/ importable
    from core.config import (  # type: ignore[no-redef]  # noqa: F401
        DEFAULT_APP_SUBDIR,
        DEFAULT_PACKAGE_ROOT,
        Config,
        resolve,
    )
