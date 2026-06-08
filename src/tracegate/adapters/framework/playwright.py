"""Playwright framework adapter: E2E acceptance tests as requirements.

Playwright `test()` calls are requirements (category E2E), not a doc section, so this
adapter exposes `requirements(cfg)`. Parses `e2e/tests/**/*.spec.ts` via
tree-sitter-typescript; the spec comes from the test's preceding JSDoc `@spec.*` tags.
Paths are canonical repo-relative (ADR-0007).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import tree_sitter_typescript
from tree_sitter import Language, Node, Parser

from ...core import paths, specdoc
from ...core.config import Config
from ...core.model import Requirement

_LANGUAGE = Language(tree_sitter_typescript.language_typescript())
_PARSER = Parser(_LANGUAGE)


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] in ("'", '"', "`") and s[-1] == s[0]:
        return s[1:-1]
    return s


def _preceding_jsdoc(call_node: Node, source: bytes) -> str | None:
    cursor: Node | None = call_node
    while cursor is not None and cursor.type not in ("expression_statement", "program", "statement_block"):
        cursor = cursor.parent
    if cursor is None or cursor.type == "program":
        return None
    sib = cursor.prev_sibling
    while sib is not None and sib.type == "comment":
        text = _node_text(sib, source)
        if text.startswith("/**"):
            return text[3:-2]
        sib = sib.prev_sibling
    return None


def _parse_file(path: Path, repo_root: Path) -> Iterator[Requirement]:
    source = path.read_bytes()
    tree = _PARSER.parse(source)
    unit = path.stem  # "screenshots.spec"; .spec stripped by ids
    file_rel = paths.rel_to_repo(path, repo_root)
    stack: list[Node] = [tree.root_node]
    while stack:
        n = stack.pop()
        stack.extend(n.children)
        if n.type != "call_expression":
            continue
        fn = n.child_by_field_name("function")
        if fn is None:
            continue
        fn_text = _node_text(fn, source)
        if fn_text != "test" and not (fn_text.startswith("test.") and fn_text != "test.describe"):
            continue
        args = n.child_by_field_name("arguments")
        if args is None:
            continue
        first_arg = next((c for c in args.named_children if c.type == "string"), None)
        if first_arg is None:
            continue
        title = _strip_quotes(_node_text(first_arg, source))
        spec = specdoc.parse(_preceding_jsdoc(n, source))
        yield Requirement(
            category="E2E", module="e2e", unit=unit,
            method=title, file_rel=file_rel, spec=spec,
        )


def requirements(cfg: Config) -> Iterator[Requirement]:
    e2e_root = cfg.e2e_tests
    if not e2e_root.is_dir():
        return
    for p in sorted(e2e_root.rglob("*.spec.ts")):
        yield from _parse_file(p, cfg.repo_root)


def sections(cfg: Config) -> dict[str, str]:
    # Playwright contributes requirements (E2E), not a doc section.
    return {}
