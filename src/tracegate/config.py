"""Target configuration for the tracegate generators.

Phase 0 harvest: the generators were extracted from the housetree monorepo where
every path was hardcoded to `apps/gest` and every package to `it.housetreespa.gest`.
This module turns those hardcodes into a single resolved `Config` so the same code
runs against ANY target repo's source tree.

Design goal for Phase 0 (engineering port, not redesign): keep behavior identical.
The historical housetree values live here as DEFAULTS, so a caller that passes no
overrides reproduces the original output byte-for-byte (this is what keeps the
golden test green). A caller targeting another repo overrides `--target`,
`--package-root`, `--label`, etc.

Phase 1 will replace the explicit `package_root` / `label` with auto-detection
(stack sniffing, deepest-common-package inference). Not now.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Historical housetree defaults — keep them so the un-parameterized call path
# (and the golden test) reproduce the original behavior exactly.
DEFAULT_APP_SUBDIR = "apps/gest"
DEFAULT_PACKAGE_ROOT = "it.housetreespa.gest"


@dataclass
class Config:
    """Everything the generators need to locate a target's source tree + name it.

    All paths are resolved absolute. `package_root` is the dotted base package the
    Modulith modules hang off (e.g. `it.housetreespa.gest`); module names are derived
    by stripping it. `label` is the human name printed in the doc titles
    (e.g. `apps/gest`); it is cosmetic but part of the deterministic output.
    """

    repo_root: Path
    app_root: Path
    label: str = DEFAULT_APP_SUBDIR
    package_root: str = DEFAULT_PACKAGE_ROOT

    # Derived locations under the app root. Resolved in __post_init__ but overridable.
    src_main_java: Path = field(default=None)        # type: ignore[assignment]
    test_java: Path = field(default=None)            # type: ignore[assignment]
    contracts_dir: Path = field(default=None)        # type: ignore[assignment]
    generated_dir: Path = field(default=None)        # type: ignore[assignment]
    e2e_tests: Path = field(default=None)            # type: ignore[assignment]
    product_md: Path = field(default=None)           # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.repo_root = Path(self.repo_root).resolve()
        self.app_root = Path(self.app_root).resolve()
        if self.src_main_java is None:
            self.src_main_java = self.app_root / "src" / "main" / "java"
        if self.test_java is None:
            self.test_java = self.app_root / "src" / "test" / "java"
        if self.contracts_dir is None:
            self.contracts_dir = self.app_root / "src" / "test" / "resources" / "contracts"
        if self.generated_dir is None:
            self.generated_dir = self.app_root / "_generated"
        if self.e2e_tests is None:
            self.e2e_tests = self.app_root / "e2e" / "tests"
        if self.product_md is None:
            self.product_md = self.app_root / "PRODUCT.md"

    @property
    def package_root_path(self) -> tuple[str, ...]:
        """`it.housetreespa.gest` -> ('it', 'housetreespa', 'gest'). Empty tuple if
        no package root is set (then module names come straight off the package tree)."""
        return tuple(p for p in self.package_root.split(".") if p)


def resolve(target: str | Path, *, out: str | Path | None = None,
            app_subdir: str = DEFAULT_APP_SUBDIR,
            package_root: str = DEFAULT_PACKAGE_ROOT,
            label: str | None = None) -> Config:
    """Build a Config from CLI-level inputs.

    `target` is the repo root. `app_subdir` is the path under it that holds the
    Maven/source tree (default `apps/gest`, the historical housetree layout; pass
    `.` for a repo whose source tree is at the root). `out` overrides the generated
    docs directory (default `<app_root>/_generated`). `label` defaults to the
    app_subdir so titles read sensibly.
    """
    repo_root = Path(target).resolve()
    app_root = (repo_root / app_subdir).resolve() if app_subdir not in (".", "") else repo_root
    cfg = Config(
        repo_root=repo_root,
        app_root=app_root,
        label=label if label is not None else (app_subdir if app_subdir not in (".", "") else repo_root.name),
        package_root=package_root,
    )
    if out is not None:
        cfg.generated_dir = Path(out).resolve()
    return cfg
