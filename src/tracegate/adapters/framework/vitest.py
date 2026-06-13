"""vitest framework adapter: frontend component/unit tests as requirements.

vitest `it()` / `test()` calls are requirements (category **FE**, "Frontend"), not a
doc section, so this adapter exposes `requirements(cfg)` (the same SPI shape as the
Playwright adapter, ADR-0002). It parses `frontend/src/**/*.{test,spec}.ts` via the
SAME tree-sitter-typescript engine the Playwright adapter uses (no second TS engine).

Taxonomy choice (ADR-0010): frontend vitest tests get their own category **FE**, parallel
to **E2E** (Playwright). Both are framework-contributed categories rather than class-suffix
derived; FE is the in-process component/unit layer, E2E the cross-process acceptance layer.

ID scheme, mirroring Playwright's E2E derivation:
    FE-frontend.<unit>#<describe-path > it-title>
- module  = `frontend` (constant, the parallel to Playwright's `e2e`).
- unit    = the spec file stem with its `.test` / `.spec` suffix stripped (`ids`).
- method  = the enclosing `describe(...)` titles joined to the `it(...)` title with ` > `
            (vitest's own reporter convention), so nesting stays in the stable ID.
The spec comes from the test's preceding JSDoc `@spec.*` tags (same `specdoc.parse` as
Java/Playwright). Paths are canonical repo-relative (ADR-0007).
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

import tree_sitter_typescript
from tree_sitter import Language, Node, Parser

from ...core import ids, paths, specdoc
from ...core.config import Config
from ...core.model import Requirement

_LANGUAGE = Language(tree_sitter_typescript.language_typescript())
_PARSER = Parser(_LANGUAGE)

# Test-declaring callees. `it`/`test` declare a test; their `.only`/`.skip`/`.each`
# variants still declare one (`it.todo` declares a pending test with no body, skipped).
_TEST_NAMES = ("it", "test")
_DESCRIBE_NAMES = ("describe",)


def _node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] in ("'", '"', "`") and s[-1] == s[0]:
        return s[1:-1]
    return s


def _callee_base(fn_text: str) -> str:
    """`it` -> `it`; `it.only` -> `it`; `test.each` -> `test`; `describe.skip` -> `describe`."""
    return fn_text.split(".", 1)[0]


def _first_string_arg(call_node: Node, source: bytes) -> str | None:
    args = call_node.child_by_field_name("arguments")
    if args is None:
        return None
    first = next((c for c in args.named_children if c.type == "string"), None)
    if first is None:
        return None
    return _strip_quotes(_node_text(first, source))


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


def _walk(node: Node, source: bytes, describe_path: tuple[str, ...]) -> Iterator[tuple[Node, str]]:
    """Yield (it-call-node, method-slug) for every test call, carrying the enclosing
    describe titles. Recurses so nested `describe(...)` blocks accumulate their titles."""
    if node.type == "call_expression":
        fn = node.child_by_field_name("function")
        if fn is not None:
            base = _callee_base(_node_text(fn, source))
            if base in _DESCRIBE_NAMES:
                title = _first_string_arg(node, source)
                child_path = describe_path + (title,) if title is not None else describe_path
                # recurse into the describe callback body with the extended path, do not
                # double-walk this node's children with the old path
                for child in node.children:
                    yield from _walk(child, source, child_path)
                return
            if base in _TEST_NAMES:
                title = _first_string_arg(node, source)
                if title is not None:
                    method = " > ".join((*describe_path, title))
                    yield node, method
                # an it() arg can itself contain calls, but a test title is a leaf here;
                # fall through to still walk children for any nested declarations
    for child in node.children:
        yield from _walk(child, source, describe_path)


def _parse_file(path: Path, repo_root: Path) -> Iterator[Requirement]:
    source = path.read_bytes()
    tree = _PARSER.parse(source)
    # `ht-calendar.test.ts` -> stem `ht-calendar.test` -> strip `.test` -> `ht-calendar`
    # (the `.spec` variant strips the same way; one clean unit scheme like every adapter).
    unit = ids.strip_category_suffix(path.stem)
    file_rel = paths.rel_to_repo(path, repo_root)
    for call_node, method in _walk(tree.root_node, source, ()):
        spec = specdoc.parse(_preceding_jsdoc(call_node, source))
        yield Requirement(
            category="FE", module="frontend", unit=unit,
            method=method, file_rel=file_rel, spec=spec,
        )


def requirements(cfg: Config) -> Iterator[Requirement]:
    root = cfg.frontend_tests
    if not root.is_dir():
        return
    found: set[Path] = set()
    for pattern in ("*.test.ts", "*.spec.ts", "*.test.tsx", "*.spec.tsx"):
        found.update(root.rglob(pattern))
    for p in sorted(found):
        rel = paths.rel_to_repo(p, cfg.repo_root)
        if any(ex in rel for ex in cfg.exclude):
            continue
        yield from _parse_file(p, cfg.repo_root)


def sections(cfg: Config) -> dict[str, str]:
    # vitest contributes requirements (FE), not a doc section.
    return {}
