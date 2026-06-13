"""Zero-config stack detection (ADR-0004).

`tracegate <dir>` with no flags must produce value. This module sniffs the target for
manifest/marker files, decides which apps exist and which language + framework adapters
each one needs, and returns ready-to-run `Config`s. `tracegate.toml` only overrides the
result; it is never required.

Detection is deliberately simple and deterministic (convention-over-configuration):
- a Maven `pom.xml` (with a `src/main/java`) marks a Java app;
- a `pyproject.toml` / `setup.py` / top-level package marks a Python app;
- framework markers (Spring dependency, Axon dependency, a `contracts/` dir, Flyway
  migrations, a Playwright config) flip the matching framework adapter on.

The aim is the 80% case at the first run, not a universal build-system model.
"""
from __future__ import annotations

import tomllib
from pathlib import Path

from .config import DEFAULT_PACKAGE_ROOT, Config

_SKIP_DIRS = {
    ".git", "node_modules", "target", "build", "dist", "_generated",
    ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache",
    ".ruff_cache", ".tox", ".gradle", "vendor",
}


def detect(target: str | Path, *, out: Path | None = None) -> list[Config]:
    """Return one `Config` per detected app in `target`.

    A `tracegate.toml` at the target root can declare apps explicitly and/or override
    languages/frameworks; otherwise apps are auto-discovered. Always returns at least
    one Config (a whole-repo fallback) so a run never silently does nothing.
    """
    target = Path(target).resolve()
    overrides = _load_toml(target)

    if overrides.get("apps"):
        return [_config_from_override(target, app, out) for app in overrides["apps"]]

    apps = _discover_apps(target)
    if not apps:
        # fallback: treat the whole repo as one app, detect by language only
        apps = [target]

    configs: list[Config] = []
    for app_root in apps:
        cfg = _build_config(target, app_root, out)
        _apply_global_overrides(cfg, overrides)
        configs.append(cfg)
    return configs


# --- discovery ----------------------------------------------------------

def _discover_apps(target: Path) -> list[Path]:
    """Find app roots: dirs that hold a recognized manifest. The target root counts."""
    roots: list[Path] = []
    if _is_app_root(target):
        roots.append(target)
    for path in _walk_dirs(target):
        if path == target:
            continue
        if _is_app_root(path):
            roots.append(path)
    # de-dup while preserving order; prefer the most specific (deepest) roots only when
    # there is no manifest at the target itself.
    seen: set[Path] = set()
    ordered: list[Path] = []
    for r in roots:
        if r not in seen:
            seen.add(r)
            ordered.append(r)
    return ordered


def _walk_dirs(target: Path, max_depth: int = 4):
    """Yield directories under target up to max_depth, skipping noise dirs."""
    stack = [(target, 0)]
    while stack:
        d, depth = stack.pop()
        if depth >= max_depth:
            continue
        try:
            children = sorted(p for p in d.iterdir() if p.is_dir())
        except OSError:
            continue
        for c in children:
            if c.name in _SKIP_DIRS:
                continue
            yield c
            stack.append((c, depth + 1))


def _is_app_root(path: Path) -> bool:
    return (
        (path / "pom.xml").is_file()
        or (path / "pyproject.toml").is_file()
        or (path / "setup.py").is_file()
        or (path / "build.gradle").is_file()
        or (path / "build.gradle.kts").is_file()
    )


# --- per-app config building -------------------------------------------

def _build_config(target: Path, app_root: Path, out: Path | None) -> Config:
    languages = detect_languages(app_root)
    frameworks = detect_frameworks(app_root)
    app_subdir = "." if app_root == target else app_root.relative_to(target).as_posix()
    label = target.name if app_root == target else app_subdir
    cfg = Config(
        repo_root=target,
        app_root=app_root,
        label=label,
        package_root=_infer_java_package_root(app_root) if "java" in languages else "",
        languages=languages,
        frameworks=frameworks,
    )
    if "python" in languages:
        cfg.src_python = _python_src_root(app_root)
    if out is not None:
        cfg.generated_dir = out
    return cfg


def detect_languages(app_root: Path) -> list[str]:
    langs: list[str] = []
    java_root = app_root / "src" / "main" / "java"
    if _has_files(java_root, ".java") or _has_files(app_root, ".java"):
        langs.append("java")
    if (app_root / "pyproject.toml").is_file() or (app_root / "setup.py").is_file() or _has_files(app_root, ".py"):
        langs.append("python")
    return langs


def detect_frameworks(app_root: Path) -> list[str]:
    fw: list[str] = []
    pom = app_root / "pom.xml"
    pom_txt = pom.read_text(encoding="utf-8", errors="replace") if pom.is_file() else ""
    if "spring-boot" in pom_txt or "springframework" in pom_txt:
        fw.append("spring")
    if "axon" in pom_txt.lower():
        fw.append("axon")
    if (app_root / "src" / "main" / "resources" / "db" / "migration").is_dir():
        fw.append("flyway")
    # Playwright: a config file or an e2e test dir with *.spec.ts
    if any((app_root / n).is_file() for n in ("playwright.config.ts", "playwright.config.js")) \
            or _has_files(app_root / "e2e", ".spec.ts"):
        fw.append("playwright")
    # vitest: a config file, a frontend package.json declaring vitest, or a frontend/src
    # tree with *.test.ts / *.spec.ts (the component/unit test layer beside the code).
    if _detect_vitest(app_root):
        fw.append("vitest")
    return fw


def _detect_vitest(app_root: Path) -> bool:
    """Frontend vitest present? config file OR a frontend package.json declaring it OR a
    `frontend/src` tree holding `*.test.ts` / `*.spec.ts`."""
    if any((app_root / n).is_file() for n in (
        "vitest.config.ts", "vitest.config.js", "vitest.config.mts",
        "frontend/vitest.config.ts", "frontend/vitest.config.js", "frontend/vitest.config.mts",
    )):
        return True
    pkg = app_root / "frontend" / "package.json"
    if pkg.is_file() and "vitest" in pkg.read_text(encoding="utf-8", errors="replace"):
        return True
    frontend_src = app_root / "frontend" / "src"
    return _has_files(frontend_src, ".test.ts") or _has_files(frontend_src, ".test.tsx") \
        or _has_files(frontend_src, ".spec.ts") or _has_files(frontend_src, ".spec.tsx")


def _has_files(root: Path, suffix: str) -> bool:
    if not root.is_dir():
        return False
    for p in _iter_files(root):
        if p.name.endswith(suffix):
            return True
    return False


def _iter_files(root: Path, max_depth: int = 12):
    stack = [(root, 0)]
    while stack:
        d, depth = stack.pop()
        if depth >= max_depth:
            continue
        try:
            for c in d.iterdir():
                if c.is_dir():
                    if c.name not in _SKIP_DIRS:
                        stack.append((c, depth + 1))
                else:
                    yield c
        except OSError:
            continue


def _python_src_root(app_root: Path) -> Path:
    """Prefer a `src/` layout when it holds packages, else the app root itself."""
    src = app_root / "src"
    if src.is_dir() and any(p.is_dir() for p in src.iterdir() if p.name not in _SKIP_DIRS):
        return src
    return app_root


def _infer_java_package_root(app_root: Path) -> str:
    """Deepest single-child package chain under src/main/java is the base package.

    `src/main/java/it/housetreespa/gest/{auth,activity,...}` -> `it.housetreespa.gest`.
    Stops at the first directory that branches (more than one sub-package) or holds a
    .java file directly: that is where the modules begin.
    """
    base = app_root / "src" / "main" / "java"
    if not base.is_dir():
        return ""
    parts: list[str] = []
    cur = base
    while True:
        subdirs = [p for p in cur.iterdir() if p.is_dir() and p.name not in _SKIP_DIRS]
        has_java_here = any(p.suffix == ".java" for p in cur.iterdir() if p.is_file())
        if has_java_here or len(subdirs) != 1:
            break
        parts.append(subdirs[0].name)
        cur = subdirs[0]
    return ".".join(parts)


# --- tracegate.toml overrides ------------------------------------------

def _load_toml(target: Path) -> dict:
    toml = target / "tracegate.toml"
    if not toml.is_file():
        return {}
    try:
        return tomllib.loads(toml.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _apply_global_overrides(cfg: Config, overrides: dict) -> None:
    if "languages" in overrides:
        cfg.languages = list(overrides["languages"])
    if "frameworks" in overrides:
        cfg.frameworks = list(overrides["frameworks"])
    if "package_root" in overrides:
        cfg.package_root = str(overrides["package_root"])
    if "label" in overrides:
        cfg.label = str(overrides["label"])
    if "exclude" in overrides:
        cfg.exclude = list(overrides["exclude"])


def _config_from_override(target: Path, app: dict, out: Path | None) -> Config:
    app_subdir = app.get("path", ".")
    app_root = target if app_subdir in (".", "") else (target / app_subdir).resolve()
    languages = list(app.get("languages", [])) or detect_languages(app_root)
    frameworks = list(app.get("frameworks", [])) or detect_frameworks(app_root)
    cfg = Config(
        repo_root=target,
        app_root=app_root,
        label=app.get("label", app_subdir if app_subdir not in (".", "") else target.name),
        package_root=app.get("package_root", _infer_java_package_root(app_root) if "java" in languages else ""),
        languages=languages,
        frameworks=frameworks,
        exclude=list(app.get("exclude", [])),
    )
    if "python" in languages:
        cfg.src_python = _python_src_root(app_root)
    if out is not None:
        cfg.generated_dir = out
    return cfg
