#!/usr/bin/env python3
"""
Parse Java JUnit test files under a root directory via tree-sitter and emit a
requirements catalog as markdown to stdout.

What it extracts per @Test method:
  - module      = test package relative to it.housetreespa.gest.*
                  ("auth.legacy" for tests in .../auth/legacy/...)
  - category    = from class name suffix
                  *Test=FR, *NfrTest=NFR, *InvariantTest=INV, *ContractTest=CON
  - id          = derived from package + class + method
                  e.g. FR-auth.legacy.LegacyPasswordVerifier#verifies_md5_match
  - given/when/then = from javadoc tags @spec.given/when/then
  - adr/us           = from javadoc tags @spec.adr / @spec.us (optional)
  - source file path

Convention enforced (tests without spec javadoc appear with "(spec missing)" in
the output, so a human / lint catches them; the hard gate lives in the
git pre-commit + ArchUnit backstop).
"""
from __future__ import annotations

import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import tree_sitter_java
import tree_sitter_typescript
from tree_sitter import Language, Node, Parser

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:  # works both as a package module (tracegate.javadoc_render) and standalone
    from . import javadoc_render
    from .config import Config, DEFAULT_PACKAGE_ROOT, DEFAULT_APP_SUBDIR
except ImportError:  # noqa: E402 — standalone import (sys.path points at this dir)
    import javadoc_render  # type: ignore[no-redef]
    from config import Config, DEFAULT_PACKAGE_ROOT, DEFAULT_APP_SUBDIR  # type: ignore[no-redef]


JAVA_LANGUAGE = Language(tree_sitter_java.language())
PARSER = Parser(JAVA_LANGUAGE)

TS_LANGUAGE = Language(tree_sitter_typescript.language_typescript())
TS_PARSER = Parser(TS_LANGUAGE)


# Java suffix -> category. The *IT.java suffix is orthogonal: it means "requires
# Spring + Testcontainers", not a category. So Foo*IT.java with a category prefix
# (NfrIT, InvariantIT, ContractIT) is classified by the prefix; plain *IT is FR.
CATEGORY_BY_SUFFIX = (
    ("InvariantTest", "INV"),
    ("InvariantIT", "INV"),
    ("ContractTest", "CON"),
    ("ContractIT", "CON"),
    ("NfrTest", "NFR"),
    ("NfrIT", "NFR"),
    ("Test", "FR"),  # default fallback for plain *Test.java
    ("IT", "FR"),    # default fallback for plain *IT.java
)


@dataclass
class Spec:
    given: str = ""
    when: str = ""
    then: str = ""
    adr: str = ""
    us: str = ""
    ac: str = ""  # acceptance criterion id (AC1, AC2, ...) within the cited US

    def is_complete(self) -> bool:
        return bool(self.given and self.when and self.then)


@dataclass
class Requirement:
    category: str          # FR / NFR / INV / CON / E2E
    module: str            # e.g. auth.legacy (Java) or "e2e" (Playwright)
    class_simple: str      # e.g. LegacyPasswordVerifierTest (Java) or screenshots.spec (TS)
    method: str            # @Test method name (Java) or test() title (TS)
    file_rel: str          # path relative to the repo root
    spec: Spec = field(default_factory=Spec)

    @property
    def id(self) -> str:
        cls = self.class_simple
        # strip category suffix for a clean ID (works for Java Test/IT suffixes)
        for suffix in (
            "InvariantTest", "InvariantIT",
            "ContractTest", "ContractIT",
            "NfrTest", "NfrIT",
            "Test", "IT",
            ".spec",  # TS Playwright files
        ):
            if cls.endswith(suffix):
                cls = cls[: -len(suffix)]
                break
        return f"{self.category}-{self.module}.{cls}#{self.method}"


def classify(class_simple: str) -> str:
    for suffix, cat in CATEGORY_BY_SUFFIX:
        if class_simple.endswith(suffix):
            return cat
    return "FR"


def derive_module(file_path: Path, test_root: Path,
                  package_root: str = DEFAULT_PACKAGE_ROOT) -> str:
    """
    "src/test/java/it/housetreespa/gest/auth/legacy/Foo.java" -> "auth.legacy"

    `package_root` is the dotted base package to strip (default the historical
    housetree value so the un-parameterized call path is unchanged).
    """
    rel = file_path.relative_to(test_root)
    parts = rel.parts[:-1]
    prefix = tuple(p for p in package_root.split(".") if p)
    if prefix and parts[: len(prefix)] == prefix:
        parts = parts[len(prefix) :]
    return ".".join(parts) if parts else "(root)"


def extract_javadoc_field(body: str, tag: str) -> str:
    """
    Pull the first @spec.<tag> line value from a javadoc body. Multi-line values
    supported until the next @tag or end-of-block.
    """
    pattern = re.compile(
        rf"@spec\.{tag}\b\s*(?P<val>.*?)(?=^\s*\*\s*@|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    m = pattern.search(body)
    if not m:
        return ""
    raw = m.group("val")
    cleaned = re.sub(r"^\s*\*\s?", "", raw, flags=re.MULTILINE)
    return " ".join(cleaned.split()).strip()


def node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def annotations_of(method_node: Node, source: bytes) -> list[str]:
    """All annotation names directly on the method (including 'Test' for @Test)."""
    out: list[str] = []
    for child in method_node.children:
        if child.type == "modifiers":
            for grand in child.children:
                if grand.type in ("annotation", "marker_annotation"):
                    name_node = grand.child_by_field_name("name")
                    if name_node is not None:
                        out.append(node_text(name_node, source))
        elif child.type in ("annotation", "marker_annotation"):
            # in some grammars annotations sit as siblings of modifiers; cover both
            name_node = child.child_by_field_name("name")
            if name_node is not None:
                out.append(node_text(name_node, source))
    return out


def preceding_javadoc(method_node: Node, source: bytes) -> str | None:
    """
    Walk previous siblings of the method (and of its enclosing modifiers block)
    looking for the last block_comment that starts with /** and sits immediately
    before, separated only by whitespace.
    """
    # tree-sitter exposes prev sibling at the same parent level. We're inside class_body.
    cursor: Node | None = method_node.prev_sibling
    # also climb modifiers if javadoc is before annotations
    while cursor is not None and cursor.type in ("line_comment",):
        cursor = cursor.prev_sibling
    if cursor is None:
        return None
    if cursor.type != "block_comment":
        return None
    text = node_text(cursor, source)
    if not text.startswith("/**"):
        return None
    # strip leading /** and trailing */
    return text[3:-2]


def is_test_method(annotations: list[str]) -> bool:
    return any(a == "Test" or a.endswith(".Test") for a in annotations)


def iter_methods(root: Node) -> Iterator[Node]:
    """Walk the AST yielding every method_declaration node (including inner classes)."""
    stack: list[Node] = [root]
    while stack:
        n = stack.pop()
        if n.type == "method_declaration":
            yield n
        stack.extend(n.children)


def parse_file(file_path: Path, test_root: Path,
               cfg: Config | None = None) -> Iterator[Requirement]:
    source = file_path.read_bytes()
    tree = PARSER.parse(source)
    if tree.root_node.has_error:
        # we still try; tree-sitter is resilient and produces partial trees.
        # If it can't find @Test methods we'll just yield nothing for this file.
        pass

    package_root = cfg.package_root if cfg else DEFAULT_PACKAGE_ROOT
    # repo root: from config when targeting an arbitrary repo, else inferred as the
    # ancestor 4 levels above .../src/test/java (the historical housetree heuristic).
    repo_root = cfg.repo_root if cfg else test_root.parents[3]

    class_simple = file_path.stem
    category = classify(class_simple)
    module = derive_module(file_path, test_root, package_root)
    file_rel = str(file_path.relative_to(repo_root))

    for method_node in iter_methods(tree.root_node):
        anns = annotations_of(method_node, source)
        if not is_test_method(anns):
            continue
        name_node = method_node.child_by_field_name("name")
        if name_node is None:
            continue
        method = node_text(name_node, source)

        doc_body = preceding_javadoc(method_node, source)
        if doc_body is None:
            spec = Spec()
        else:
            spec = Spec(
                given=extract_javadoc_field(doc_body, "given"),
                when=extract_javadoc_field(doc_body, "when"),
                then=extract_javadoc_field(doc_body, "then"),
                adr=extract_javadoc_field(doc_body, "adr"),
                us=extract_javadoc_field(doc_body, "us"),
                ac=extract_javadoc_field(doc_body, "ac"),
            )
        yield Requirement(
            category=category,
            module=module,
            class_simple=class_simple,
            method=method,
            file_rel=file_rel,
            spec=spec,
        )


def walk_tests(test_root: Path, cfg: Config | None = None) -> Iterator[Requirement]:
    for p in sorted(test_root.rglob("*.java")):
        if "/testfixture/" in str(p) or p.name == "package-info.java":
            continue
        yield from parse_file(p, test_root, cfg)


# --- Playwright E2E (TypeScript) parsing ----------------------------------

def parse_ts_file(file_path: Path, e2e_root: Path, repo_root: Path) -> Iterator[Requirement]:
    """
    Parse a Playwright spec.ts file and yield one Requirement per top-level test()
    call. We DON'T recurse into test.describe nesting yet (walking skeleton);
    nesting can be added later if it becomes a readability gap.

    Each Requirement gets category=E2E. The "class" is the file stem (e.g.
    "screenshots" from "screenshots.spec.ts"); the "method" is the test title
    string verbatim (preserving whatever the human wrote).
    """
    source = file_path.read_bytes()
    tree = TS_PARSER.parse(source)
    class_simple = file_path.stem  # "screenshots.spec" -> stays as is; .spec stripped in id
    module = "e2e"
    file_rel = str(file_path.relative_to(repo_root))

    # find every call_expression whose callee is the identifier "test" or "test.only" etc.
    # tree-sitter typescript: call_expression(function: identifier "test", arguments: ...)
    stack: list[Node] = [tree.root_node]
    while stack:
        n = stack.pop()
        stack.extend(n.children)
        if n.type != "call_expression":
            continue
        fn = n.child_by_field_name("function")
        if fn is None:
            continue
        fn_text = node_text(fn, source)
        # accept: test(...), test.only(...), test.skip(...) -- exclude test.describe
        # ("test.describe" wraps a group, not a single requirement).
        if fn_text != "test" and not (fn_text.startswith("test.") and fn_text not in ("test.describe",)):
            continue
        args = n.child_by_field_name("arguments")
        if args is None:
            continue
        # first argument = test title (string literal)
        first_arg = next((c for c in args.named_children if c.type == "string"), None)
        if first_arg is None:
            continue
        title = strip_quotes(node_text(first_arg, source))

        # walk up to find the JSDoc that precedes the statement enclosing this call
        doc_body = preceding_ts_jsdoc(n, source)
        if doc_body is None:
            spec = Spec()
        else:
            spec = Spec(
                given=extract_javadoc_field(doc_body, "given"),
                when=extract_javadoc_field(doc_body, "when"),
                then=extract_javadoc_field(doc_body, "then"),
                adr=extract_javadoc_field(doc_body, "adr"),
                us=extract_javadoc_field(doc_body, "us"),
                ac=extract_javadoc_field(doc_body, "ac"),
            )
        yield Requirement(
            category="E2E",
            module=module,
            class_simple=class_simple,
            method=title,
            file_rel=file_rel,
            spec=spec,
        )


def strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] in ("'", '"', "`") and s[-1] == s[0]:
        return s[1:-1]
    return s


def preceding_ts_jsdoc(call_node: Node, source: bytes) -> str | None:
    """
    Find the JSDoc /** ... */ comment that sits immediately before the statement
    enclosing this call_expression. TS tree-sitter places comments as siblings of
    expression_statement at the program / block level.
    """
    # climb to the enclosing statement (expression_statement or expression at top level)
    cursor: Node | None = call_node
    while cursor is not None and cursor.type not in ("expression_statement", "program", "statement_block"):
        cursor = cursor.parent
    if cursor is None or cursor.type == "program":
        return None
    # walk previous siblings looking for a comment node starting with /**
    sib = cursor.prev_sibling
    while sib is not None and sib.type == "comment":
        text = node_text(sib, source)
        if text.startswith("/**"):
            return text[3:-2]
        sib = sib.prev_sibling
    return None


def walk_e2e_tests(e2e_root: Path, repo_root: Path) -> Iterator[Requirement]:
    if not e2e_root.is_dir():
        return
    for p in sorted(e2e_root.rglob("*.spec.ts")):
        yield from parse_ts_file(p, e2e_root, repo_root)


def render(reqs: list[Requirement], label: str = DEFAULT_APP_SUBDIR) -> str:
    lines: list[str] = []
    lines.append(f"# Requirements — {label}")
    lines.append("")
    lines.append(
        "Auto-generated from JUnit test sources by `scripts/generate-requirements.sh`. "
        "Do NOT edit by hand: edit the test javadoc instead and rerun. Single source of "
        "truth is the test code."
    )
    lines.append("")
    lines.append(
        "**Convention**: category from class-name suffix "
        "(`*Test`=FR, `*NfrTest`=NFR, `*InvariantTest`=INV, `*ContractTest`=CON; "
        "the `*IT` Spring/Testcontainers variant suffix is orthogonal: "
        "`*NfrIT`/`*InvariantIT`/`*ContractIT` get the matching category). "
        f"Frontend vitest tests (`{label}/frontend/src/**/*.{{test,spec}}.ts`) join as **FE**; "
        f"Playwright E2E tests (`{label}/e2e/tests/*.spec.ts`) join as **E2E**. "
        "Spec from javadoc / JSDoc tags `@spec.given` / `@spec.when` / `@spec.then` "
        "(plus optional `@spec.adr` / `@spec.us`). "
        "Tests without a complete spec are listed with `(spec missing)` so they're "
        "visible and lintable."
    )
    lines.append("")

    total = len(reqs)
    with_spec = sum(1 for r in reqs if r.spec.is_complete())
    by_cat: dict[str, int] = defaultdict(int)
    for r in reqs:
        by_cat[r.category] += 1
    lines.append("## Coverage")
    lines.append("")
    lines.append(f"- Total tests scanned: **{total}**")
    lines.append(f"- With complete spec javadoc: **{with_spec}** ({pct(with_spec, total)})")
    for cat in ("FR", "NFR", "INV", "CON", "FE", "E2E"):
        if by_cat[cat]:
            lines.append(f"- {cat}: {by_cat[cat]}")
    lines.append("")

    by_mod: dict[str, list[Requirement]] = defaultdict(list)
    for r in reqs:
        by_mod[r.module].append(r)

    for module in sorted(by_mod):
        lines.append(f"## Module `{module}`")
        lines.append("")
        by_cat_in_mod: dict[str, list[Requirement]] = defaultdict(list)
        for r in by_mod[module]:
            by_cat_in_mod[r.category].append(r)
        for category in ("FR", "NFR", "INV", "CON", "FE", "E2E"):
            cat_reqs = by_cat_in_mod.get(category, [])
            if not cat_reqs:
                continue
            lines.append(f"### {long_name(category)}")
            lines.append("")
            for r in sorted(cat_reqs, key=lambda x: (x.class_simple, x.method)):
                lines.append(f"#### `{r.id}`")
                lines.append("")
                if r.spec.is_complete():
                    lines.append(f"- **Given**: {javadoc_render.to_inline(r.spec.given)}")
                    lines.append(f"- **When**: {javadoc_render.to_inline(r.spec.when)}")
                    lines.append(f"- **Then**: {javadoc_render.to_inline(r.spec.then)}")
                else:
                    lines.append("- _(spec missing — add `@spec.given` / `@spec.when` / `@spec.then` javadoc)_")
                if r.spec.adr:
                    lines.append(f"- **ADR**: {r.spec.adr}")
                if r.spec.us:
                    lines.append(f"- **User Story**: {r.spec.us}")
                lines.append(f"- **File**: `{r.file_rel}`")
                lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_by_user_story(reqs: list[Requirement], label: str = DEFAULT_APP_SUBDIR,
                         cfg: Config | None = None) -> str:
    """
    Alternative view: requirements grouped by the User Story they implement
    (via @spec.us=US-NNN-slug). FRs without @spec.us go under "implementation
    detail (no user story link)" so they remain visible.
    """
    lines: list[str] = []
    lines.append(f"# Requirements — {label}, grouped by User Story")
    lines.append("")
    lines.append(
        "Auto-generated companion to `requirements.md`. Tests link to a User Story "
        "via the javadoc tag `@spec.us=US-NNN-slug` (the slug points to a User Story "
        "defined in `PRODUCT.md`). Implementation-detail tests with no `@spec.us` are "
        "collected at the bottom; declared User Stories in PRODUCT.md with zero linked "
        "tests are listed as **not implemented yet**."
    )
    lines.append("")

    by_us: dict[str, list[Requirement]] = defaultdict(list)
    no_us: list[Requirement] = []
    for r in reqs:
        if r.spec.us:
            by_us[r.spec.us].append(r)
        else:
            no_us.append(r)

    declared_us = set(scan_product_md_user_stories(cfg))

    lines.append("## Coverage")
    lines.append("")
    lines.append(f"- Total tests scanned: **{len(reqs)}**")
    lines.append(f"- Tests linked to a User Story: **{sum(len(v) for v in by_us.values())}**")
    lines.append(f"- Tests without `@spec.us` (implementation detail): **{len(no_us)}**")
    lines.append(f"- User Stories declared in PRODUCT.md: **{len(declared_us)}**")
    lines.append(f"- User Stories with at least one linked test: **{len(set(by_us.keys()) & declared_us)}**")
    not_yet = sorted(declared_us - set(by_us.keys()))
    lines.append(f"- User Stories declared but **not yet implemented**: **{len(not_yet)}**")
    lines.append("")

    if not_yet:
        lines.append("## User Stories declared but NOT yet implemented")
        lines.append("")
        for us in not_yet:
            lines.append(f"- `{us}`")
        lines.append("")

    ac_by_us = scan_product_md_acceptance_criteria(cfg)
    for us in sorted(by_us):
        marker = "" if us in declared_us else "  _(unknown to PRODUCT.md)_"
        lines.append(f"## `{us}`{marker}")
        lines.append("")

        declared_ac = ac_by_us.get(us, [])
        if declared_ac:
            # Bucket tests by the AC they cite; tests with no @spec.ac end up under "(no AC)"
            tests_by_ac: dict[str, list[Requirement]] = defaultdict(list)
            for r in by_us[us]:
                key = r.spec.ac if r.spec.ac else "(no AC)"
                tests_by_ac[key].append(r)
            ac_covered = sum(1 for ac_id, _ in declared_ac if tests_by_ac.get(ac_id))
            ac_total = len(declared_ac)
            us_done = "**DONE**" if ac_covered == ac_total else f"**{ac_covered}/{ac_total} AC covered**"
            lines.append(f"_AC coverage_: {us_done}")
            lines.append("")
            for ac_id, ac_txt in declared_ac:
                tests = tests_by_ac.get(ac_id, [])
                badge = "✓" if tests else "✗"
                lines.append(f"### {badge} `{ac_id}` — {ac_txt}")
                lines.append("")
                if not tests:
                    lines.append("_no test cites this AC yet_")
                    lines.append("")
                    continue
                for r in sorted(tests, key=lambda x: x.id):
                    lines.append(f"- `{r.id}`")
                    if r.spec.is_complete():
                        lines.append(f"  - **Then**: {javadoc_render.to_inline(r.spec.then)}")
                lines.append("")
            if tests_by_ac.get("(no AC)"):
                lines.append("### Tests linked to this US but with no `@spec.ac`")
                lines.append("")
                for r in sorted(tests_by_ac["(no AC)"], key=lambda x: x.id):
                    lines.append(f"- `{r.id}`")
                    if r.spec.is_complete():
                        lines.append(f"  - **Then**: {javadoc_render.to_inline(r.spec.then)}")
                lines.append("")
        else:
            # No AC declared in PRODUCT.md (yet) — render the flat list, like before.
            for r in sorted(by_us[us], key=lambda x: x.id):
                lines.append(f"- `{r.id}`")
                if r.spec.is_complete():
                    lines.append(f"  - **Then**: {javadoc_render.to_inline(r.spec.then)}")
            lines.append("")

    if no_us:
        lines.append("## Implementation detail (no `@spec.us` link)")
        lines.append("")
        lines.append("These tests are valid requirements but exist below the user-story horizon "
                     "(unit-level mechanism, internal invariant, white-box assertion). Add "
                     "`@spec.us` if a user story should claim them.")
        lines.append("")
        by_mod: dict[str, list[Requirement]] = defaultdict(list)
        for r in no_us:
            by_mod[r.module].append(r)
        for module in sorted(by_mod):
            lines.append(f"### Module `{module}`")
            lines.append("")
            for r in sorted(by_mod[module], key=lambda x: x.id):
                lines.append(f"- `{r.id}`")
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def scan_product_md_user_stories(cfg: Config | None = None) -> set[str]:
    """
    Parse the target's PRODUCT.md for user-story IDs of the form `US-NNN-slug`
    declared as third-level headers (`### US-NNN-slug ...`).
    Returns an empty set if the file is missing.
    """
    product = _product_md_path(cfg)
    if not product.is_file():
        return set()
    txt = product.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(r"^###\s+`?(US-[A-Za-z0-9_-]+)`?", re.MULTILINE)
    return set(pattern.findall(txt))


def _product_md_path(cfg: Config | None) -> Path:
    """Locate the target PRODUCT.md. From config when targeting an arbitrary repo,
    else the historical housetree path relative to the source tree."""
    if cfg is not None:
        return cfg.product_md
    return Path(__file__).resolve().parent.parent / "apps" / "gest" / "PRODUCT.md"


def scan_product_md_acceptance_criteria(cfg: Config | None = None) -> dict[str, list[tuple[str, str]]]:
    """
    Parse apps/gest/PRODUCT.md for each US, extracting its declared AC list.

    Returns: { US-slug: [(AC1, "criterion text"), (AC2, ...), ...] }

    The AC section is the block between a US header and the next US header (or
    end-of-file). AC entries look like:
        - **AC1**: text...
        - **AC2**: more text...
    The bold markers are required (it's our convention; bullet lists without
    the **ACn** prefix are skipped).
    """
    product = _product_md_path(cfg)
    if not product.is_file():
        return {}
    txt = product.read_text(encoding="utf-8", errors="replace")

    out: dict[str, list[tuple[str, str]]] = {}
    # Split into US blocks by `### \`?US-...\`?` headers
    us_header = re.compile(r"^###\s+`?(US-[A-Za-z0-9_-]+)`?", re.MULTILINE)
    matches = list(us_header.finditer(txt))
    for i, m in enumerate(matches):
        us = m.group(1)
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(txt)
        block = txt[start:end]
        # Pull `**ACn**: text` bullets — the text spans until the next bullet or blank line
        ac_pat = re.compile(
            r"^[-*]\s+\*\*(AC\d+)\*\*\s*:\s*(.+?)(?=^[-*]\s+\*\*AC|\n\n|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        for ac_m in ac_pat.finditer(block):
            ac_id = ac_m.group(1)
            ac_txt = " ".join(ac_m.group(2).split()).strip()
            out.setdefault(us, []).append((ac_id, ac_txt))
    return out


def long_name(cat: str) -> str:
    return {
        "FR": "Functional Requirements",
        "NFR": "Non-Functional Requirements",
        "INV": "Domain Invariants",
        "CON": "HTTP Boundary Contracts",
        "FE": "Frontend Component/Unit (vitest)",
        "E2E": "End-to-End Acceptance (Playwright)",
    }.get(cat, cat)


def pct(num: int, denom: int) -> str:
    if denom == 0:
        return "0%"
    return f"{round(100 * num / denom)}%"


def generate(cfg: Config, by_us: bool = False) -> str:
    """Build the requirements catalog markdown for a configured target.

    Scans `cfg.test_java` for JUnit tests and `cfg.e2e_tests` for Playwright specs,
    then renders either the flat catalog or the by-user-story view. This is the
    config-driven entry point the tracegate CLI uses; `main` keeps the legacy
    positional contract the bash wrapper relies on.
    """
    reqs = list(walk_tests(cfg.test_java, cfg))
    reqs.extend(walk_e2e_tests(cfg.e2e_tests, cfg.repo_root))
    if by_us:
        return render_by_user_story(reqs, cfg.label, cfg)
    return render(reqs, cfg.label)


def main(argv: list[str]) -> int:
    """Legacy positional CLI kept for the bash wrapper:

        generate_requirements.py <test-root-dir> [--by-us]

    The test-root is the absolute `.../src/test/java`; repo root, e2e dir and
    PRODUCT.md are inferred the historical way (4 levels up) so existing callers
    are unchanged. The richer `--target`-based entry lives in `tracegate.cli`.
    """
    if len(argv) not in (2, 3):
        print(f"usage: {argv[0]} <test-root-dir> [--by-us]", file=sys.stderr)
        return 64
    test_root = Path(argv[1]).resolve()
    if not test_root.is_dir():
        print(f"not a directory: {test_root}", file=sys.stderr)
        return 64
    by_us = len(argv) == 3 and argv[2] == "--by-us"
    # ADR-0007: every file path is CANONICAL — relative to the true repo root. The
    # Phase-0 quirk where Java tests were based at `test_root.parents[3]` (dropping the
    # `apps/` segment, giving `gest/src/...`) is gone; both Java and E2E now anchor on
    # the true repo root, so this positional path matches the `tracegate.cli` output.
    app_root = test_root.parents[2]                  # .../<app> (e.g. .../apps/gest)
    repo_root = test_root.parents[4]                 # true repo root (e.g. .../housetree)
    cfg_java = Config(
        repo_root=repo_root, app_root=app_root,
        label=DEFAULT_APP_SUBDIR, package_root=DEFAULT_PACKAGE_ROOT,
        test_java=test_root, product_md=app_root / "PRODUCT.md",
    )
    reqs = list(walk_tests(test_root, cfg_java))
    e2e_root = repo_root / "apps" / "gest" / "e2e" / "tests"
    reqs.extend(walk_e2e_tests(e2e_root, repo_root))
    if by_us:
        sys.stdout.write(render_by_user_story(reqs, DEFAULT_APP_SUBDIR, cfg_java))
    else:
        sys.stdout.write(render(reqs, DEFAULT_APP_SUBDIR))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
