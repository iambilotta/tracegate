"""Python language adapter: pytest test functions -> core Requirements.

Parses every `test_*.py` / `*_test.py` under the app via tree-sitter-python, yields one
`Requirement` per top-level `def test_*` function (and per `def test_*` method inside a
`class Test*`). The spec is the function's docstring (`@spec.*` tags). Category from the
file-name marker (ids.classify_filename); module is the dotted path of the test file
relative to the repo root, with the `.py` and the file name folded into unit/method.
Paths are canonical repo-relative (ADR-0007).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import tree_sitter_python
from tree_sitter import Language, Node, Parser

from ...core import ids, paths, specdoc
from ...core.config import Config
from ...core.model import Requirement

_LANGUAGE = Language(tree_sitter_python.language())
_PARSER = Parser(_LANGUAGE)

_SKIP_DIRS = {
    ".git", "node_modules", "target", "build", "dist", "_generated",
    ".venv", "venv", "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
}


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _is_test_file(path: Path) -> bool:
    name = path.name
    return name.startswith("test_") or name.endswith("_test.py")


def _docstring(func_node: Node, source: bytes) -> str | None:
    """First string-literal statement in the function body = its docstring."""
    body = func_node.child_by_field_name("body")
    if body is None:
        return None
    for stmt in body.named_children:
        if stmt.type == "expression_statement" and stmt.named_children:
            first = stmt.named_children[0]
            if first.type == "string":
                raw = _node_text(first, source)
                # strip the python string quotes (''' / """ / ' / ")
                for q in ('"""', "'''", '"', "'"):
                    if raw.startswith(q) and raw.endswith(q) and len(raw) >= 2 * len(q):
                        return raw[len(q):-len(q)]
                return raw
        # only the first statement can be a docstring
        break
    return None


def _module_for(path: Path, repo_root: Path) -> str:
    """Dotted path of the test file's PARENT package, repo-relative.

    `tests/test_sample.py` -> module `tests`, unit `test_sample`.
    A file at the repo root -> module `(root)`.
    """
    rel = path.relative_to(repo_root)
    parent_parts = rel.parts[:-1]
    return ".".join(parent_parts) if parent_parts else "(root)"


def _iter_test_functions(root: Node) -> Iterator[Node]:
    """Yield every `function_definition` (top-level or inside a class)."""
    stack: list[Node] = [root]
    while stack:
        n = stack.pop()
        stack.extend(n.children)
        if n.type == "function_definition":
            yield n


def _parse_file(path: Path, cfg: Config) -> Iterator[Requirement]:
    source = path.read_bytes()
    tree = _PARSER.parse(source)
    stem = path.stem
    category = ids.classify_filename(stem)
    unit = stem
    module = _module_for(path, cfg.repo_root)
    file_rel = paths.rel_to_repo(path, cfg.repo_root)

    for fn in _iter_test_functions(tree.root_node):
        name_node = fn.child_by_field_name("name")
        if name_node is None:
            continue
        method = _node_text(name_node, source)
        if not method.startswith("test_"):
            continue
        spec = specdoc.parse(_docstring(fn, source))
        yield Requirement(
            category=category, module=module, unit=unit,
            method=method, file_rel=file_rel, spec=spec,
        )


def extract(cfg: Config) -> Iterator[Requirement]:
    """Yield every pytest test function in the app as a Requirement."""
    # tests usually live in tests/, not src/, so search the whole app root
    search_root = cfg.app_root
    seen: set[Path] = set()
    for path in sorted(search_root.rglob("*.py")):
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if not _is_test_file(path) or path in seen:
            continue
        rel = paths.rel_to_repo(path, cfg.repo_root)
        if any(ex in rel for ex in cfg.exclude):
            continue
        seen.add(path)
        yield from _parse_file(path, cfg)
