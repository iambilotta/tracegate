"""Java language adapter: JUnit test sources -> core Requirements.

Parses `src/test/java/**/*.java` via tree-sitter-java, yields one `Requirement` per
`@Test` method. The category comes from the class-name suffix (ids.classify), the
module from the package relative to `cfg.package_root`, the spec from the method's
`@spec.*` javadoc. Paths are CANONICAL repo-relative (ADR-0007).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import tree_sitter_java
from tree_sitter import Language, Node, Parser

from ...core import ids, paths, specdoc
from ...core.config import Config
from ...core.model import Requirement

_LANGUAGE = Language(tree_sitter_java.language())
_PARSER = Parser(_LANGUAGE)


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _iter_methods(root: Node) -> Iterator[Node]:
    stack: list[Node] = [root]
    while stack:
        n = stack.pop()
        if n.type == "method_declaration":
            yield n
        stack.extend(n.children)


def _annotation_names(method_node: Node, source: bytes) -> list[str]:
    out: list[str] = []
    for child in method_node.children:
        if child.type == "modifiers":
            for grand in child.children:
                if grand.type in ("annotation", "marker_annotation"):
                    nm = grand.child_by_field_name("name")
                    if nm is not None:
                        out.append(_node_text(nm, source))
        elif child.type in ("annotation", "marker_annotation"):
            nm = child.child_by_field_name("name")
            if nm is not None:
                out.append(_node_text(nm, source))
    return out


def _is_test_method(annotations: list[str]) -> bool:
    return any(a == "Test" or a.endswith(".Test") for a in annotations)


def _preceding_javadoc(method_node: Node, source: bytes) -> str | None:
    cursor: Node | None = method_node.prev_sibling
    while cursor is not None and cursor.type in ("line_comment",):
        cursor = cursor.prev_sibling
    if cursor is None or cursor.type != "block_comment":
        return None
    text = _node_text(cursor, source)
    if not text.startswith("/**"):
        return None
    return text[3:-2]


def _derive_module(file_path: Path, test_root: Path, package_root: str) -> str:
    rel = file_path.relative_to(test_root)
    parts = rel.parts[:-1]
    prefix = tuple(p for p in package_root.split(".") if p)
    if prefix and parts[: len(prefix)] == prefix:
        parts = parts[len(prefix):]
    return ".".join(parts) if parts else "(root)"


def _parse_file(file_path: Path, cfg: Config) -> Iterator[Requirement]:
    source = file_path.read_bytes()
    tree = _PARSER.parse(source)
    class_simple = file_path.stem
    category = ids.classify(class_simple)
    unit = ids.strip_category_suffix(class_simple)
    module = _derive_module(file_path, cfg.test_java, cfg.package_root)
    file_rel = paths.rel_to_repo(file_path, cfg.repo_root)

    for method_node in _iter_methods(tree.root_node):
        if not _is_test_method(_annotation_names(method_node, source)):
            continue
        name_node = method_node.child_by_field_name("name")
        if name_node is None:
            continue
        method = _node_text(name_node, source)
        spec = specdoc.parse(_preceding_javadoc(method_node, source))
        yield Requirement(
            category=category, module=module, unit=unit,
            method=method, file_rel=file_rel, spec=spec,
        )


def extract(cfg: Config) -> Iterator[Requirement]:
    """Yield every JUnit @Test method under `cfg.test_java` as a Requirement."""
    test_root = cfg.test_java
    if not test_root.is_dir():
        return
    for p in sorted(test_root.rglob("*.java")):
        if "/testfixture/" in str(p) or p.name == "package-info.java":
            continue
        yield from _parse_file(p, cfg)
