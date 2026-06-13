"""Target configuration for tracegate.

A `Config` locates one app's source trees inside a target repo and names it. The
historical housetree values live here as DEFAULTS so the un-parameterized call path
(and the Java golden test) reproduce the original output. Zero-config detection
(`core.detect`) builds `Config`s automatically by sniffing manifests; `tracegate.toml`
only overrides.

Phase-1 note: the module-global mutation seam the Phase-0 code-docs generator used is
gone. Every collector now takes a `Config` argument explicitly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Historical housetree defaults — keep them so the un-parameterized call path
# (and the Java golden test) reproduce the original behavior exactly.
DEFAULT_APP_SUBDIR = "apps/gest"
DEFAULT_PACKAGE_ROOT = "it.housetreespa.gest"


@dataclass
class Config:
    """Everything an adapter needs to locate a target app's source tree + name it.

    All paths are resolved absolute. `package_root` is the dotted base package the
    modules hang off (Java/JVM); module names are derived by stripping it. `label` is
    the human name printed in the doc titles. `languages` lists the language adapters
    enabled for this app; `frameworks` the framework adapters (both auto-detected by
    `core.detect`, overridable via `tracegate.toml`).
    """

    repo_root: Path
    app_root: Path
    label: str = DEFAULT_APP_SUBDIR
    package_root: str = DEFAULT_PACKAGE_ROOT
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    # path substrings to skip when scanning sources (e.g. test fixtures of a tool whose
    # fixtures are themselves test files). Matched against the repo-relative POSIX path.
    exclude: list[str] = field(default_factory=list)

    # Derived locations under the app root. Resolved in __post_init__ but overridable.
    src_main_java: Path = field(default=None)        # type: ignore[assignment]
    test_java: Path = field(default=None)            # type: ignore[assignment]
    contracts_dir: Path = field(default=None)        # type: ignore[assignment]
    generated_dir: Path = field(default=None)        # type: ignore[assignment]
    e2e_tests: Path = field(default=None)            # type: ignore[assignment]
    # Frontend (vitest) component/unit test tree. Defaults to the app's `frontend/src`
    # (the housetree convention: vitest specs sit beside the components they test).
    frontend_tests: Path = field(default=None)       # type: ignore[assignment]
    product_md: Path = field(default=None)           # type: ignore[assignment]
    # Python source tree (for the Python language adapter). Defaults to the app root;
    # detection narrows it to e.g. the `src/` layout.
    src_python: Path = field(default=None)           # type: ignore[assignment]

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
        if self.frontend_tests is None:
            self.frontend_tests = self.app_root / "frontend" / "src"
        if self.product_md is None:
            self.product_md = self.app_root / "PRODUCT.md"
        if self.src_python is None:
            self.src_python = self.app_root

    @property
    def package_root_path(self) -> tuple[str, ...]:
        """`it.housetreespa.gest` -> ('it', 'housetreespa', 'gest'). Empty if unset."""
        return tuple(p for p in self.package_root.split(".") if p)


def resolve(target: str | Path, *, out: str | Path | None = None,
            app_subdir: str = DEFAULT_APP_SUBDIR,
            package_root: str = DEFAULT_PACKAGE_ROOT,
            label: str | None = None,
            languages: list[str] | None = None,
            frameworks: list[str] | None = None) -> Config:
    """Build a Config from CLI-level inputs (the explicitly-flagged path).

    `target` is the repo root. `app_subdir` is the path under it that holds the source
    tree (default `apps/gest`; pass `.` for a repo whose source is at the root). `out`
    overrides the generated-docs dir. `label` defaults to the app_subdir.
    """
    repo_root = Path(target).resolve()
    app_root = (repo_root / app_subdir).resolve() if app_subdir not in (".", "") else repo_root
    cfg = Config(
        repo_root=repo_root,
        app_root=app_root,
        label=label if label is not None else (app_subdir if app_subdir not in (".", "") else repo_root.name),
        package_root=package_root,
        languages=list(languages) if languages else [],
        frameworks=list(frameworks) if frameworks else [],
    )
    if out is not None:
        cfg.generated_dir = Path(out).resolve()
    return cfg
