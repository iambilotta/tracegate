"""Zero-config stack detection (ADR-0004). New Phase-1 logic, so test-first.

Detection must turn a bare directory into the right set of language + framework
adapters with no flags. These tests build tiny synthetic repos in a tmp dir and assert
on the resulting Config(s).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from tracegate.core import detect  # noqa: E402


def _write(p: Path, content: str = "") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_detects_a_python_app_from_pyproject(tmp_path: Path):
    """
    @spec.given a directory with a pyproject.toml and .py files
    @spec.when  zero-config detection runs
    @spec.then  it enables the python language adapter and not java
    @spec.us    US-003-stack-detection
    """
    _write(tmp_path / "pyproject.toml", "[project]\nname='x'\n")
    _write(tmp_path / "src" / "pkg" / "mod.py", "def f(): ...\n")
    configs = detect.detect(tmp_path)
    assert len(configs) == 1
    assert "python" in configs[0].languages
    assert "java" not in configs[0].languages


def test_detects_a_java_spring_app_with_flyway_and_axon(tmp_path: Path):
    """
    @spec.given a Maven repo with Spring + Axon deps and a Flyway migration dir
    @spec.when  zero-config detection runs
    @spec.then  it enables the java language and the spring, axon and flyway adapters
    @spec.us    US-003-stack-detection
    """
    _write(
        tmp_path / "pom.xml",
        "<project><dependencies>"
        "<dependency><groupId>org.springframework.boot</groupId>"
        "<artifactId>spring-boot-starter</artifactId></dependency>"
        "<dependency><groupId>org.axonframework</groupId>"
        "<artifactId>axon-spring-boot-starter</artifactId></dependency>"
        "</dependencies></project>",
    )
    _write(tmp_path / "src" / "main" / "java" / "com" / "acme" / "App.java", "package com.acme;\n")
    _write(tmp_path / "src" / "main" / "resources" / "db" / "migration" / "V1__init.sql", "CREATE TABLE t (id int);")
    configs = detect.detect(tmp_path)
    assert len(configs) == 1
    cfg = configs[0]
    assert "java" in cfg.languages
    assert {"spring", "axon", "flyway"} <= set(cfg.frameworks)


def test_infers_the_java_package_root_from_the_single_child_chain(tmp_path: Path):
    _write(tmp_path / "pom.xml", "<project/>")
    _write(tmp_path / "src" / "main" / "java" / "it" / "acme" / "app" / "auth" / "Login.java", "package it.acme.app.auth;")
    _write(tmp_path / "src" / "main" / "java" / "it" / "acme" / "app" / "billing" / "Bill.java", "package it.acme.app.billing;")
    cfg = detect.detect(tmp_path)[0]
    # chain it -> acme -> app branches (auth, billing) at `app`, so the root is it.acme.app
    assert cfg.package_root == "it.acme.app"


def test_detects_vitest_from_a_frontend_test_tree(tmp_path: Path):
    """
    @spec.given a Maven app whose frontend/src holds a *.test.ts vitest file
    @spec.when  zero-config detection runs
    @spec.then  it enables the vitest framework adapter
    @spec.us    US-003-stack-detection
    """
    _write(tmp_path / "pom.xml", "<project/>")
    _write(tmp_path / "src" / "main" / "java" / "com" / "acme" / "App.java", "package com.acme;")
    _write(tmp_path / "frontend" / "src" / "components" / "widget.test.ts",
           "import {it} from 'vitest'; it('renders', () => {});")
    cfg = detect.detect(tmp_path)[0]
    assert "vitest" in cfg.frameworks


def test_detects_vitest_from_a_frontend_package_json(tmp_path: Path):
    _write(tmp_path / "pom.xml", "<project/>")
    _write(tmp_path / "src" / "main" / "java" / "com" / "acme" / "App.java", "package com.acme;")
    _write(tmp_path / "frontend" / "package.json", '{"devDependencies":{"vitest":"^2.0.0"}}')
    cfg = detect.detect(tmp_path)[0]
    assert "vitest" in cfg.frameworks


def test_tracegate_toml_overrides_detected_frameworks(tmp_path: Path):
    _write(tmp_path / "pyproject.toml", "[project]\nname='x'\n")
    _write(tmp_path / "mod.py", "def f(): ...\n")
    _write(tmp_path / "tracegate.toml", 'languages = ["python"]\nframeworks = ["playwright"]\n')
    cfg = detect.detect(tmp_path)[0]
    assert cfg.frameworks == ["playwright"]
    assert cfg.languages == ["python"]


def test_empty_dir_still_returns_one_config_so_a_run_never_no_ops(tmp_path: Path):
    cfg = detect.detect(tmp_path)
    assert len(cfg) == 1
    assert cfg[0].repo_root == tmp_path.resolve()
