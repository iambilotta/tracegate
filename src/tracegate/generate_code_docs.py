#!/usr/bin/env python3
"""
Auto-generate AS-IS documentation of `apps/gest` from the source code itself.

Emits markdown into `apps/gest/_generated/`:
  - http-endpoints.md   one row per @*Mapping route + javadoc + Spring Cloud Contract
  - events.md           domain event records (auth/.../domain/event/*.java) + fields
  - projections.md      classes carrying @ProcessingGroup + their @EventHandler / @ResetHandler

The single source of truth is the code; this script reads it via tree-sitter-java
(same AST parser the requirements generator uses) and never edits anything.

Usage:
  scripts/generate_code_docs.py            # writes all three to _generated/
  scripts/generate_code_docs.py --check    # exit 2 if any file is stale (CI gate)
"""
from __future__ import annotations

import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import tree_sitter_java
from tree_sitter import Language, Node, Parser

# Shared javadoc → markdown rendering (also used by generate_requirements.py).
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:  # works both as a package module and standalone
    from . import javadoc_render
    from .config import Config, DEFAULT_PACKAGE_ROOT, DEFAULT_APP_SUBDIR
except ImportError:  # noqa: E402  (after path manipulation)
    import javadoc_render  # type: ignore[no-redef]
    from config import Config, DEFAULT_PACKAGE_ROOT, DEFAULT_APP_SUBDIR  # type: ignore[no-redef]


JAVA_LANGUAGE = Language(tree_sitter_java.language())
PARSER = Parser(JAVA_LANGUAGE)

# Phase 1: the module-global path state (REPO_ROOT/GEST_ROOT/...) and the
# `configure()` mutation seam are gone. Path-/label-bearing functions are now methods
# of `CodeDocs`, whose `__init__(cfg)` builds the state once from a Config. Pure
# AST/string helpers below stay module-level free functions.


def node_text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


# --- shared helpers ------------------------------------------------------

def parse(path: Path) -> tuple[bytes, Node]:
    source = path.read_bytes()
    tree = PARSER.parse(source)
    return source, tree.root_node


def walk(node: Node) -> Iterator[Node]:
    stack = [node]
    while stack:
        n = stack.pop()
        yield n
        stack.extend(n.children)


def preceding_javadoc(target: Node, source: bytes) -> str:
    cursor: Node | None = target.prev_sibling
    while cursor is not None and cursor.type in ("line_comment",):
        cursor = cursor.prev_sibling
    if cursor is None or cursor.type != "block_comment":
        return ""
    text = node_text(cursor, source)
    if not text.startswith("/**"):
        return ""
    # strip /** ... */ and leading * per line, collapse whitespace
    body = text[3:-2]
    cleaned = re.sub(r"^\s*\*\s?", "", body, flags=re.MULTILINE)
    # take first paragraph only (until first blank or @tag)
    first_para = re.split(r"\n\s*\n|\n\s*@", cleaned, maxsplit=1)[0]
    return " ".join(first_para.split()).strip()


def javadoc_to_inline(text: str) -> str:
    return javadoc_render.to_inline(text)


def javadoc_to_block(text: str) -> str:
    return javadoc_render.to_block(text)


def annotations_on(node: Node, source: bytes) -> list[tuple[str, Node]]:
    """Return [(name, annotation_node)] for direct annotations on the given node."""
    out: list[tuple[str, Node]] = []
    for child in node.children:
        if child.type in ("modifiers",):
            for grand in child.children:
                if grand.type in ("annotation", "marker_annotation"):
                    nm = grand.child_by_field_name("name")
                    if nm is not None:
                        out.append((node_text(nm, source), grand))
        elif child.type in ("annotation", "marker_annotation"):
            nm = child.child_by_field_name("name")
            if nm is not None:
                out.append((node_text(nm, source), child))
    return out


# --- HTTP endpoints ------------------------------------------------------

MAPPING_ANNOTATIONS = {"GetMapping", "PostMapping", "PutMapping", "DeleteMapping", "PatchMapping", "RequestMapping"}
HTTP_METHOD_BY_ANN = {
    "GetMapping": "GET",
    "PostMapping": "POST",
    "PutMapping": "PUT",
    "DeleteMapping": "DELETE",
    "PatchMapping": "PATCH",
    "RequestMapping": "*",  # method derived from `method = RequestMethod.X` if present
}


@dataclass
class Endpoint:
    http_method: str
    url: str
    controller_class: str
    controller_method: str
    summary: str
    file_rel: str
    contracts: list[tuple[str, str]] = field(default_factory=list)  # (file, description)
    condition: str = ""  # class-level @Conditional / @Profile (mutual exclusion signal)


def extract_annotation_first_string_arg(ann_node: Node, source: bytes, route_constants: dict[str, str]) -> str:
    """
    From @GetMapping("/login") or @GetMapping(ActivityRoutes.BASE) return the resolved URL.
    Returns the raw expression if it can't be resolved.
    """
    args = ann_node.child_by_field_name("arguments")
    if args is None:
        return ""
    # arguments node is "annotation_argument_list"; find first child of interest
    for child in args.named_children:
        if child.type == "string_literal":
            return node_text(child, source).strip('"')
        if child.type == "field_access":
            # e.g. ActivityRoutes.BASE
            key = node_text(child, source)
            return route_constants.get(key, key)
        if child.type == "identifier":
            key = node_text(child, source)
            return route_constants.get(key, key)
        # element_value_pair like `value = "/foo"` or `path = "/foo"`
        if child.type == "element_value_pair":
            name_node = child.child_by_field_name("key")
            val_node = child.child_by_field_name("value")
            if name_node is None or val_node is None:
                continue
            key = node_text(name_node, source)
            if key in ("value", "path"):
                if val_node.type == "string_literal":
                    return node_text(val_node, source).strip('"')
                if val_node.type in ("field_access", "identifier"):
                    k = node_text(val_node, source)
                    return route_constants.get(k, k)
    return ""


_CONDITION_ANNOTATIONS = {
    "Conditional", "ConditionalOnProperty", "ConditionalOnBean",
    "ConditionalOnMissingBean", "ConditionalOnExpression", "Profile",
}


def _class_level_condition(source: bytes, root: Node) -> str:
    """Return a short label like 'ConditionalOnProperty(...)' if the outer class carries one.
    Walking-skeleton: dump the annotation text; the reader resolves the meaning.

    Matches on the simple name suffix so a FQN annotation
    `@org.springframework.context.annotation.Conditional(...)` resolves the same as
    `@Conditional(...)` — tree-sitter exposes the name field as a scoped_identifier in
    the FQN case.
    """
    for n in walk(root):
        if n.type != "class_declaration":
            continue
        labels: list[str] = []
        for ann_name, ann in annotations_on(n, source):
            simple = ann_name.rsplit(".", 1)[-1]
            if simple in _CONDITION_ANNOTATIONS:
                args = ann.child_by_field_name("arguments")
                arg_txt = node_text(args, source) if args else ""
                arg_txt = " ".join(arg_txt.split())
                if len(arg_txt) > 60:
                    arg_txt = arg_txt[:57] + "…"
                labels.append(f"@{simple}{arg_txt}")
        return " + ".join(labels)
    return ""


# --- Domain events -------------------------------------------------------

@dataclass
class DomainEvent:
    name: str
    fields: list[tuple[str, str]]  # (name, type)
    summary: str
    file_rel: str
    handlers: list[str] = field(default_factory=list)  # FQ class refs
    emitters: list[str] = field(default_factory=list)  # FQ file refs


# --- Projections ---------------------------------------------------------

@dataclass
class ProjectionHandler:
    event_type: str
    method: str
    summary: str


@dataclass
class Projection:
    class_simple: str
    processing_group: str
    handlers: list[ProjectionHandler]
    has_reset_handler: bool
    summary: str
    file_rel: str


# --- Modules canvas (Modulith-style, Python-side) -----------------------

@dataclass
class Module:
    name: str                       # e.g. "auth", "activity", "platform"
    sub_packages: list[str]         # e.g. ["auth.config", "auth.domain", ...]
    types: list[str]                # simple class names
    depends_on: set[str]            # other top-level module names
    file_count: int
    exposed: list[tuple[str, str]] = field(default_factory=list)  # [(subpackage, named_interface)]


def detect_module_cycles(modules: list[Module]) -> list[list[str]]:
    """Tarjan-light: any strongly connected component of size > 1 is a cycle.
    For our scale (single-digit modules) a brute-force DFS is fine."""
    graph = {m.name: set(m.depends_on) for m in modules}
    cycles: list[list[str]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for start in graph:
        stack = [(start, [start])]
        while stack:
            node, path = stack.pop()
            for nxt in graph.get(node, set()):
                if nxt == start and len(path) >= 1:
                    key = tuple(sorted({path[0], path[-1]}))
                    if key not in seen_pairs:
                        seen_pairs.add(key)
                        cycles.append(path + [nxt])
                elif nxt not in path and len(path) < 6:
                    stack.append((nxt, path + [nxt]))
    return cycles


# --- Flyway schema inventory --------------------------------------------

@dataclass
class FlywayMigration:
    file: str                # V<N>__<name>.sql
    version: str
    name: str
    leading_comment: str     # SQL `-- ...` lines at the top
    tables: list[tuple[str, list[str], str]]  # (table_name, raw columns, trailing comment)


# --- Configuration properties inventory ---------------------------------

@dataclass
class ConfigProperty:
    key: str
    defaults: dict[str, str]   # file -> default value (per-profile)
    used_by: list[str]         # repo-relative paths of Java files referencing the key


def parse_properties_file(path: Path) -> dict[str, tuple[str, str]]:
    """Return {key: (value, leading_comment)}.

    Block-comment semantics: a comment block introduces a *paragraph* of keys, and the
    comment is the "role" of ALL keys in that paragraph (until the next blank line).
    Previously only the first key in the block received the comment — which made keys
    in the middle of a documented group appear "no role" in config.md. Fix tracks the
    current paragraph's leading comment and assigns it to every key until the
    paragraph ends (blank line).
    """
    out: dict[str, tuple[str, str]] = {}
    if not path.is_file():
        return out
    comment_buf: list[str] = []          # accumulating, becomes paragraph_comment on first key
    paragraph_comment: str = ""          # applies to every key in the current paragraph
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            # paragraph break: clear both contexts
            comment_buf = []
            paragraph_comment = ""
            continue
        if s.startswith("#"):
            comment_buf.append(s.lstrip("# ").strip())
            continue
        if "=" in s:
            if comment_buf:
                # first key of a new paragraph: promote the accumulated comment
                paragraph_comment = " ".join(comment_buf)
                comment_buf = []
            k, _, v = s.partition("=")
            out[k.strip()] = (v.strip(), paragraph_comment)
    return out


# --- Port ↔ Adapter matrix ----------------------------------------------

@dataclass
class PortIface:
    name: str
    package: str
    file_rel: str
    summary: str
    methods: list[str]
    impls: list[str]  # file paths


# --- JTE template tree ---------------------------------------------------

@dataclass
class JteTemplate:
    name: str          # e.g. "activity/list" or "_partials/shell"
    file_rel: str
    params: list[tuple[str, str, str]]  # (type, name, default-or-empty)
    includes: list[str]                  # other template names invoked


# --- Coverage (JaCoCo CSV + full-file walk) -----------------------------

@dataclass
class CoverageRow:
    package: str
    class_simple: str
    file_rel: str
    lines_missed: int
    lines_covered: int
    branches_missed: int
    branches_covered: int
    methods_missed: int
    methods_covered: int

    @property
    def total_lines(self) -> int:
        return self.lines_missed + self.lines_covered

    @property
    def line_pct(self) -> float:
        return (self.lines_covered / self.total_lines * 100) if self.total_lines else 0.0

    @property
    def total_branches(self) -> int:
        return self.branches_missed + self.branches_covered

    @property
    def branch_pct(self) -> float:
        return (self.branches_covered / self.total_branches * 100) if self.total_branches else 0.0


# --- TODO / FIXME / @Deprecated inventory ------------------------------

TODO_MARKER_RE = re.compile(r"\b(TODO|FIXME|XXX|HACK)\b\s*:?\s*(.*)$")

# Roots scanned for human-authored markers. Generated and vendored trees are excluded.
TODO_EXCLUDE_DIRS = {"node_modules", "target", "_generated", "dist"}


# --- repo structure (the `structure.md` skeleton: a convention-driven tree snapshot) ---

# Build / dependency / VCS / tooling dirs that are never structural signal. Used ONLY by the
# filesystem-walk fallback; the primary path is `git ls-files`, which respects the repo's own
# .gitignore (so node_modules / target / build / generated coverage drop out by convention).
STRUCTURE_EXCLUDE_DIRS = {
    ".git", "node_modules", "target", "dist", "build", ".venv", "venv",
    "__pycache__", ".pytest_cache", ".gradle", ".idea", ".mvn", ".next", ".nuxt",
    ".terraform", "site", ".cache", ".tox", ".mypy_cache", ".ruff_cache",
}
STRUCTURE_MAX_ENTRIES = 6000


def _build_path_tree(paths: list[str]) -> dict:
    """Nest sorted repo-relative POSIX paths into a {dir: {...}, file: None} tree."""
    root: dict = {}
    for p in paths:
        parts = [seg for seg in p.split("/") if seg]
        node = root
        for seg in parts[:-1]:
            nxt = node.get(seg)
            if not isinstance(nxt, dict):
                nxt = {}
                node[seg] = nxt
            node = nxt
        if parts:
            node.setdefault(parts[-1], None)  # leave a dir already at this name untouched
    return root


def _render_tree_lines(node: dict, prefix: str = "") -> list[str]:
    """ASCII tree (`tree`-command style), dirs first then files, each alphabetical."""
    entries = sorted(node.items(), key=lambda kv: (kv[1] is None, kv[0].lower()))
    lines: list[str] = []
    for i, (name, child) in enumerate(entries):
        last = i == len(entries) - 1
        connector = "└── " if last else "├── "
        is_dir = isinstance(child, dict)
        lines.append(f"{prefix}{connector}{name}{'/' if is_dir else ''}")
        if is_dir:
            lines.extend(_render_tree_lines(child, prefix + ("    " if last else "│   ")))
    return lines


@dataclass
class TodoItem:
    kind: str           # TODO / FIXME / XXX / HACK / @Deprecated
    file_rel: str
    line: int
    text: str
    author: str = ""
    age_days: int = -1


# --- ADR index + auto-detected candidates -------------------------------

@dataclass
class AdrEntry:
    id: str               # ADR-0001
    file_rel: str
    title: str
    status: str           # accepted / proposed / superseded / draft
    status_date: str
    supports_us: list[str]


# --- Dependencies (Maven + npm + Python) --------------------------------

@dataclass
class Dep:
    ecosystem: str        # maven / npm / python
    group: str            # groupId or scope (@scope) or ""
    name: str
    version: str
    scope: str            # compile/test/runtime, dev, prod, etc.
    source_file: str


# --- MANIFEST (index of all _generated/*.md) ----------------------------

# Canonical home of the topic order + the MANIFEST renderer is `core.render`, so the
# explicit `code-docs` subcommand and the zero-config auto path index the SAME set in the
# SAME order (ADR-0009 convergence). Imported here for the standalone code-docs path.
try:  # package context
    from .core.render import MANIFEST_ORDER, manifest_md  # noqa: F401
except ImportError:  # standalone (src/tracegate on sys.path)
    from core.render import MANIFEST_ORDER, manifest_md  # type: ignore[no-redef]  # noqa: F401


# --- main ----------------------------------------------------------------

class CodeDocs:
    """As-is code-docs generator for one configured target.

    Phase-1: the Phase-0 module-global mutation seam (configure() reassigning ~10
    module globals) is gone. State is built once from `cfg` in __init__ and read via
    `self.`; nothing global is mutated. The pure AST/string helpers stay module-level
    free functions; only the path-/label-bearing functions became methods.
    """

    def __init__(self, cfg: Config) -> None:
        self.REPO_ROOT = cfg.repo_root
        self.GEST_ROOT = cfg.app_root
        self.SRC_MAIN_JAVA = cfg.src_main_java
        self.CONTRACTS_DIR = cfg.contracts_dir
        self.GENERATED_DIR = cfg.generated_dir
        self.APP_LABEL = cfg.label
        self.GEST_PACKAGE_ROOT = cfg.package_root
        self.JACOCO_CSV = cfg.app_root / "target" / "site" / "jacoco" / "jacoco.csv"
        self.ADR_DIR = cfg.app_root / "decisions"
        self.TODO_SCAN_ROOTS = [
            cfg.app_root / "src",
            cfg.app_root / "e2e" / "tests",
            cfg.app_root / "frontend" / "src",
        ]
    def collect_route_constants(self) -> dict[str, str]:
        """
        Scan *Routes.java files for `public static final String NAME = "/path";` so we can
        resolve @GetMapping(ActivityRoutes.BASE) → "/attivita" without a JVM.
        """
        out: dict[str, str] = {}
        for f in self.SRC_MAIN_JAVA.rglob("*Routes.java"):
            src = f.read_text(encoding="utf-8")
            cls = f.stem
            # naive but enough: public static final String NAME = "literal";
            for m in re.finditer(
                r'public\s+static\s+final\s+String\s+(\w+)\s*=\s*"([^"]*)"\s*;',
                src,
            ):
                out[f"{cls}.{m.group(1)}"] = m.group(2)
        return out


    def load_contracts(self) -> list[tuple[str, str, str, str]]:
        """
        Parse Groovy Spring Cloud Contract files into (file_rel, http_method, url_pattern, description).
        Walking-skeleton: regex on `method GET()`, `url "..."`, `description "..."`.
        """
        out: list[tuple[str, str, str, str]] = []
        if not self.CONTRACTS_DIR.is_dir():
            return out
        for f in sorted(self.CONTRACTS_DIR.rglob("*.groovy")):
            txt = f.read_text(encoding="utf-8")
            m_method = re.search(r"method\s+(GET|POST|PUT|DELETE|PATCH)\s*\(\s*\)", txt)
            m_url = re.search(r"url\s+\"([^\"]+)\"", txt)
            m_desc = re.search(r"description\s+\"([^\"]+)\"", txt)
            if not (m_method and m_url):
                continue
            out.append((
                str(f.relative_to(self.REPO_ROOT)),
                m_method.group(1),
                m_url.group(1),
                m_desc.group(1) if m_desc else "",
            ))
        return out


    def collect_endpoints(self, route_constants: dict[str, str], contracts: list[tuple[str, str, str, str]]) -> list[Endpoint]:
        endpoints: list[Endpoint] = []
        for jf in sorted(self.SRC_MAIN_JAVA.rglob("*.java")):
            source, root = parse(jf)
            # find class-level @RequestMapping prefix (rare but possible)
            class_prefix = ""
            class_condition = _class_level_condition(source, root)
            # walk top-level class declarations
            for n in walk(root):
                if n.type == "class_declaration":
                    for ann_name, ann in annotations_on(n, source):
                        if ann_name == "RequestMapping":
                            class_prefix = extract_annotation_first_string_arg(ann, source, route_constants) or ""
                    break  # outer class only
            # find every method with an *@Mapping annotation
            for n in walk(root):
                if n.type != "method_declaration":
                    continue
                anns = annotations_on(n, source)
                for ann_name, ann in anns:
                    if ann_name not in MAPPING_ANNOTATIONS:
                        continue
                    http_method = HTTP_METHOD_BY_ANN.get(ann_name, "?")
                    url = extract_annotation_first_string_arg(ann, source, route_constants)
                    full_url = (class_prefix + url) if (class_prefix and url.startswith("/")) else url
                    cls_node = jf.stem
                    method_name = ""
                    name_node = n.child_by_field_name("name")
                    if name_node is not None:
                        method_name = node_text(name_node, source)
                    summary = preceding_javadoc(n, source)
                    ep = Endpoint(
                        http_method=http_method,
                        url=full_url or "(unresolved)",
                        controller_class=cls_node,
                        controller_method=method_name,
                        summary=summary,
                        file_rel=str(jf.relative_to(self.REPO_ROOT)),
                        condition=class_condition,
                    )
                    # attach matching contracts
                    for cf, cm, cu, cd in contracts:
                        if cm == http_method and cu == ep.url:
                            ep.contracts.append((cf, cd))
                    endpoints.append(ep)
        endpoints.sort(key=lambda e: (e.url, e.http_method))
        return endpoints


    def render_endpoints(self, endpoints: list[Endpoint]) -> str:
        lines = [f"# HTTP endpoints — {self.APP_LABEL} (as-is)", ""]
        lines.append(
            "Auto-generated from `@GetMapping` / `@PostMapping` / `@RequestMapping` annotations under "
            "`apps/gest/src/main/java`. Spring Cloud Contracts matched on (method, URL) are linked "
            "inline. Run `make code-docs` to regenerate; the pre-commit hook does it for you."
        )
        lines.append("")
        lines.append(f"**Total routes**: {len(endpoints)}")
        lines.append("")
        lines.append("| Method | URL | Controller | Condition | Purpose |")
        lines.append("|---|---|---|---|---|")
        for ep in endpoints:
            purpose = javadoc_to_inline(ep.summary).replace("|", "\\|") if ep.summary else "_(no javadoc)_"
            cond = f"`{ep.condition}`" if ep.condition else "—"
            lines.append(f"| `{ep.http_method}` | `{ep.url}` | `{ep.controller_class}#{ep.controller_method}` | {cond} | {purpose} |")
        lines.append("")
        lines.append("## Detail")
        lines.append("")
        for ep in endpoints:
            lines.append(f"### `{ep.http_method} {ep.url}`")
            lines.append("")
            lines.append(f"- **Controller**: `{ep.controller_class}#{ep.controller_method}`")
            lines.append(f"- **File**: `{ep.file_rel}`")
            if ep.condition:
                lines.append(f"- **Active when**: `{ep.condition}` — mutual exclusion with siblings sharing the same URL")
            if ep.summary:
                lines.append(f"- **Purpose** (from javadoc): {javadoc_to_inline(ep.summary)}")
            else:
                lines.append(f"- **Purpose**: _(no javadoc on the controller method — add one)_")
            if ep.contracts:
                for cf, cd in ep.contracts:
                    lines.append(f"- **Contract**: `{cf}` — {cd or '_(no description)_'}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


    def collect_events(self) -> list[DomainEvent]:
        out: list[DomainEvent] = []
        for jf in sorted(self.SRC_MAIN_JAVA.rglob("*.java")):
            if "/domain/event/" not in str(jf):
                continue
            source, root = parse(jf)
            # find record_declaration or class_declaration
            for n in walk(root):
                if n.type not in ("record_declaration", "class_declaration"):
                    continue
                name_node = n.child_by_field_name("name")
                if name_node is None:
                    continue
                ev_name = node_text(name_node, source)
                # parse record parameters
                fields: list[tuple[str, str]] = []
                params = n.child_by_field_name("parameters")
                if params is not None:
                    for p in params.named_children:
                        if p.type != "formal_parameter":
                            continue
                        t_node = p.child_by_field_name("type")
                        n_node = p.child_by_field_name("name")
                        if t_node is None or n_node is None:
                            continue
                        fields.append((node_text(n_node, source), node_text(t_node, source)))
                summary = preceding_javadoc(n, source)
                out.append(DomainEvent(
                    name=ev_name,
                    fields=fields,
                    summary=summary,
                    file_rel=str(jf.relative_to(self.REPO_ROOT)),
                ))
                break  # one event per file by convention
        # populate emitters/handlers via grep (cheap, deterministic)
        for ev in out:
            ev.handlers = self.grep_files(rf"@EventHandler[\s\S]*?\b{ev.name}\b", self.SRC_MAIN_JAVA)
            ev.emitters = self.grep_files(rf"new\s+{ev.name}\s*\(", self.SRC_MAIN_JAVA)
        return out


    def grep_files(self, pattern: str, root: Path) -> list[str]:
        """Return repo-relative paths of files containing the regex."""
        try:
            # use git grep when possible (fast + respects .gitignore)
            result = subprocess.run(
                ["git", "grep", "-l", "-E", pattern, "--", str(root)],
                cwd=self.REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return sorted(result.stdout.strip().split("\n"))
        except FileNotFoundError:
            pass
        # fallback: rglob + per-file regex
        out: list[str] = []
        rx = re.compile(pattern)
        for f in root.rglob("*.java"):
            if rx.search(f.read_text(encoding="utf-8", errors="ignore")):
                out.append(str(f.relative_to(self.REPO_ROOT)))
        return sorted(out)


    def render_events(self, events: list[DomainEvent]) -> str:
        lines = [f"# Domain events — {self.APP_LABEL} (as-is)", ""]
        lines.append(
            "Auto-generated from records / classes under `**/domain/event/*.java`. The event store is "
            "the only source of truth; this catalog is the map of every fact the system can record. "
            "Emitters are call sites of `new EventName(...)`; handlers carry `@EventHandler` on the "
            "event type. Run `make code-docs` to regenerate."
        )
        lines.append("")
        lines.append(f"**Total events**: {len(events)}")
        lines.append("")
        for ev in events:
            lines.append(f"## `{ev.name}`")
            lines.append("")
            if ev.summary:
                lines.append(javadoc_to_block(ev.summary))
                lines.append("")
            else:
                lines.append("_(no javadoc on the event — add one)_")
                lines.append("")
            if ev.fields:
                lines.append("Fields:")
                lines.append("")
                for fn, ft in ev.fields:
                    lines.append(f"- `{fn}: {ft}`")
                lines.append("")
            lines.append(f"- **File**: `{ev.file_rel}`")
            if ev.emitters:
                lines.append("- **Emitted by**:")
                for e in ev.emitters:
                    lines.append(f"  - `{e}`")
            else:
                lines.append("- **Emitted by**: _(no call sites found — orphan event?)_")
            if ev.handlers:
                lines.append("- **Handled by**:")
                for h in ev.handlers:
                    lines.append(f"  - `{h}`")
            else:
                lines.append("- **Handled by**: _(no `@EventHandler` matches — event has no projection)_")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


    def collect_projections(self) -> list[Projection]:
        out: list[Projection] = []
        for jf in sorted(self.SRC_MAIN_JAVA.rglob("*.java")):
            source, root = parse(jf)
            # find class with @ProcessingGroup
            for n in walk(root):
                if n.type != "class_declaration":
                    continue
                pg = None
                for ann_name, ann in annotations_on(n, source):
                    if ann_name == "ProcessingGroup":
                        args = ann.child_by_field_name("arguments")
                        if args is not None:
                            for c in args.named_children:
                                if c.type == "string_literal":
                                    pg = node_text(c, source).strip('"')
                if pg is None:
                    continue
                cls_name = jf.stem
                cls_summary = preceding_javadoc(n, source)
                handlers: list[ProjectionHandler] = []
                has_reset = False
                for m in walk(n):
                    if m.type != "method_declaration":
                        continue
                    ms = annotations_on(m, source)
                    ann_names = [a[0] for a in ms]
                    if "ResetHandler" in ann_names:
                        has_reset = True
                    if "EventHandler" not in ann_names:
                        continue
                    # event type: first parameter's type
                    method_name_node = m.child_by_field_name("name")
                    params = m.child_by_field_name("parameters")
                    event_type = "?"
                    if params is not None:
                        for p in params.named_children:
                            if p.type == "formal_parameter":
                                t = p.child_by_field_name("type")
                                if t is not None:
                                    event_type = node_text(t, source)
                                    break
                    handlers.append(ProjectionHandler(
                        event_type=event_type,
                        method=node_text(method_name_node, source) if method_name_node else "?",
                        summary=preceding_javadoc(m, source),
                    ))
                out.append(Projection(
                    class_simple=cls_name,
                    processing_group=pg,
                    handlers=handlers,
                    has_reset_handler=has_reset,
                    summary=cls_summary,
                    file_rel=str(jf.relative_to(self.REPO_ROOT)),
                ))
                break  # one projection class per file
        return out


    def render_projections(self, projections: list[Projection]) -> str:
        lines = [f"# Projections — {self.APP_LABEL} (as-is)", ""]
        lines.append(
            "Auto-generated from classes carrying `@ProcessingGroup`. Each projection is a read model "
            "rebuildable from the event stream (`/rebuild <group>`). A projection without "
            "`@ResetHandler` is flagged: replay would stack on top of stale rows. Run `make code-docs`."
        )
        lines.append("")
        lines.append(f"**Total projections**: {len(projections)}")
        lines.append("")
        for p in projections:
            lines.append(f"## `{p.class_simple}` (group `{p.processing_group}`)")
            lines.append("")
            if p.summary:
                lines.append(javadoc_to_block(p.summary))
                lines.append("")
            lines.append(f"- **File**: `{p.file_rel}`")
            lines.append(f"- **Rebuild idempotent?** {'✓ has @ResetHandler' if p.has_reset_handler else '✗ NO @ResetHandler — replay drifts'}")
            if p.handlers:
                lines.append("- **Handlers**:")
                for h in p.handlers:
                    summary = javadoc_to_inline(h.summary) if h.summary else "_(no javadoc)_"
                    lines.append(f"  - `{h.method}({h.event_type})` — {summary}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


    def collect_modules(self) -> list[Module]:
        """
        Modulith convention: the top-level package under {@link GestApplication} is a module.
        We walk every *.java under that root, group by top-level subdir, collect simple type
        names, and infer cross-module dependencies from `import it.housetreespa.gest.<other>.*`.
        """
        java_files = sorted(self.SRC_MAIN_JAVA.rglob("*.java"))
        pkg_parts = tuple(p for p in self.GEST_PACKAGE_ROOT.split(".") if p)
        gest_root_path = self.SRC_MAIN_JAVA.joinpath(*pkg_parts) if pkg_parts else self.SRC_MAIN_JAVA
        import_re = re.compile(
            r"^import\s+(?:static\s+)?"
            + re.escape(self.GEST_PACKAGE_ROOT)
            + r"\.([a-z][a-zA-Z0-9_]*)\.",
            re.MULTILINE,
        )
        by_module: dict[str, Module] = {}

        for jf in java_files:
            if not str(jf).startswith(str(gest_root_path)):
                continue
            rel = jf.relative_to(gest_root_path)
            parts = rel.parts
            if len(parts) < 2:
                # this is GestApplication.java at the root — assign to "(root)"
                module_name = "(root)"
                sub_package = "(root)"
            else:
                module_name = parts[0]
                sub_package = ".".join(parts[:-1])
            mod = by_module.setdefault(module_name, Module(
                name=module_name, sub_packages=[], types=[], depends_on=set(), file_count=0,
            ))
            if sub_package not in mod.sub_packages:
                mod.sub_packages.append(sub_package)
            mod.types.append(jf.stem)
            mod.file_count += 1
            # parse imports for cross-module deps
            try:
                txt = jf.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            for im in import_re.finditer(txt):
                target = im.group(1)
                if target != module_name:
                    mod.depends_on.add(target)
        # Second pass: scan package-info.java for @NamedInterface declarations (Modulith
        # exports). Surfaces "this module's Published Language" alongside the file count.
        _NI_RE = re.compile(r"@(?:org\.springframework\.modulith\.)?NamedInterface\s*\(\s*\"([^\"]+)\"\s*\)")
        for pi in sorted(self.SRC_MAIN_JAVA.rglob("package-info.java")):
            if not str(pi).startswith(str(gest_root_path)):
                continue
            rel = pi.parent.relative_to(gest_root_path)
            if not rel.parts:
                continue
            mod_name = rel.parts[0]
            subpkg = ".".join(rel.parts)
            try:
                ni_match = _NI_RE.search(pi.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
            if ni_match and mod_name in by_module:
                by_module[mod_name].exposed.append((subpkg, ni_match.group(1)))
        return sorted(by_module.values(), key=lambda m: m.name)


    def render_modules(self, modules: list[Module]) -> str:
        lines = [f"# Modules — {self.APP_LABEL} (as-is)", ""]
        lines.append(
            "Auto-generated. Modulith convention: each top-level package under "
            "`it.housetreespa.gest` is a module. Cross-module dependencies are inferred from "
            "`import it.housetreespa.gest.<other>.*` statements. A cycle in the graph below "
            "is a Modulith violation: open the offending module file and re-route the dependency "
            "through a port or an event."
        )
        lines.append("")
        lines.append(f"**Total modules**: {len(modules)}")
        lines.append("")
        cycles = detect_module_cycles(modules)
        if cycles:
            lines.append(f"> ⚠ **{len(cycles)} module cycle(s) detected** — see *Violations* below. These prevent clean Modulith boundary checks.")
            lines.append("")
        else:
            lines.append("✓ No module cycles.")
            lines.append("")
        lines.append("## Module summary")
        lines.append("")
        lines.append("| Module | Files | Sub-packages | Exposed API (@NamedInterface) | Depends on |")
        lines.append("|---|---|---|---|---|")
        for m in modules:
            deps = ", ".join(f"`{d}`" for d in sorted(m.depends_on)) or "_(none)_"
            exposed = ", ".join(f"`{sp}`" for sp, _ in sorted(m.exposed)) or "_(none)_"
            lines.append(f"| `{m.name}` | {m.file_count} | {len(m.sub_packages)} | {exposed} | {deps} |")
        lines.append("")
        if cycles:
            lines.append("## Violations")
            lines.append("")
            for cyc in cycles:
                lines.append(f"- cycle: `{' → '.join(cyc)}`")
            lines.append("")
        lines.append("## Dependency graph (PlantUML, copy-pasteable)")
        lines.append("")
        lines.append("```plantuml")
        lines.append("@startuml")
        lines.append("skinparam componentStyle rectangle")
        for m in modules:
            lines.append(f'component "{m.name}"')
        for m in modules:
            for d in sorted(m.depends_on):
                lines.append(f'"{m.name}" --> "{d}"')
        lines.append("@enduml")
        lines.append("```")
        lines.append("")
        lines.append("## Detail")
        lines.append("")
        for m in modules:
            lines.append(f"### `{m.name}`")
            lines.append("")
            lines.append(f"- **Files**: {m.file_count}")
            lines.append(f"- **Sub-packages** ({len(m.sub_packages)}):")
            for sp in sorted(m.sub_packages):
                lines.append(f"  - `{sp}`")
            if m.exposed:
                lines.append("- **Exposed API** (`@NamedInterface`, cross-module-accessible):")
                for subpkg, name in sorted(m.exposed):
                    lines.append(f"  - `{subpkg}` (named: `{name}`)")
            else:
                lines.append("- **Exposed API**: _(only the top-level package; no inner exports)_")
            if m.depends_on:
                lines.append("- **Depends on**:")
                for d in sorted(m.depends_on):
                    lines.append(f"  - `{d}`")
            else:
                lines.append("- **Depends on**: _(no other gest module)_")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


    def parse_flyway_files(self) -> list[FlywayMigration]:
        mig_dir = self.GEST_ROOT / "src" / "main" / "resources" / "db" / "migration"
        out: list[FlywayMigration] = []
        if not mig_dir.is_dir():
            return out
        for f in sorted(mig_dir.glob("V*.sql"), key=lambda p: int(re.match(r"V(\d+)", p.name).group(1))):
            txt = f.read_text(encoding="utf-8")
            m = re.match(r"V(\d+)__([^.]+)\.sql", f.name)
            version = m.group(1) if m else "?"
            name = m.group(2).replace("_", " ") if m else f.stem
            # leading comments (consecutive lines starting with --)
            leading: list[str] = []
            for line in txt.splitlines():
                stripped = line.strip()
                if stripped.startswith("--"):
                    leading.append(stripped.lstrip("- ").strip())
                elif not stripped:
                    continue
                else:
                    break
            # extract CREATE TABLE blocks
            tables: list[tuple[str, list[str], str]] = []
            for ct in re.finditer(
                r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\((.*?)\)\s*;",
                txt, re.IGNORECASE | re.DOTALL,
            ):
                tname = ct.group(1)
                body = ct.group(2)
                # naive column split: top-level commas (not inside parens)
                cols: list[str] = []
                depth = 0
                cur = ""
                for ch in body:
                    if ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                    if ch == "," and depth == 0:
                        cols.append(cur.strip())
                        cur = ""
                    else:
                        cur += ch
                if cur.strip():
                    cols.append(cur.strip())
                # filter out trailing constraint lines for the column list but keep all in raw
                tables.append((tname, [c for c in cols if c], ""))
            out.append(FlywayMigration(
                file=f.name, version=version, name=name,
                leading_comment=" ".join(leading).strip(),
                tables=tables,
            ))
        return out


    def render_schema(self, migrations: list[FlywayMigration]) -> str:
        lines = [f"# Database schema — {self.APP_LABEL} (as-is)", ""]
        lines.append(
            "Auto-generated from Flyway migrations under "
            "`apps/gest/src/main/resources/db/migration/V*.sql`, parsed in version order. "
            "Each migration's leading `--` comment is the intent; CREATE TABLE statements are "
            "extracted with their column list (raw text, untouched). For schema **drift** "
            "(what's actually in prod) consult `\\d <table>` against the deployed Postgres."
        )
        lines.append("")
        tcount = sum(len(m.tables) for m in migrations)
        lines.append(f"**Migrations**: {len(migrations)} · **Tables created across them**: {tcount}")
        lines.append("")
        lines.append("## Migration sequence")
        lines.append("")
        lines.append("| V | File | Intent | Tables |")
        lines.append("|---|---|---|---|")
        for m in migrations:
            intent = m.leading_comment.replace("|", "\\|") or "_(no leading comment)_"
            # truncate for readability
            if len(intent) > 120:
                intent = intent[:117] + "…"
            tlist = ", ".join(f"`{t[0]}`" for t in m.tables) or "_(no CREATE TABLE)_"
            lines.append(f"| V{m.version} | `{m.file}` | {intent} | {tlist} |")
        lines.append("")
        lines.append("## Detail per migration")
        lines.append("")
        for m in migrations:
            lines.append(f"### `V{m.version} — {m.name}` (`{m.file}`)")
            lines.append("")
            if m.leading_comment:
                lines.append(f"_{m.leading_comment}_")
                lines.append("")
            for tname, cols, _ in m.tables:
                lines.append(f"#### Table `{tname}`")
                lines.append("")
                lines.append("```sql")
                for c in cols:
                    # one column per line, no further parsing (raw)
                    lines.append(c)
                lines.append("```")
                lines.append("")
            if not m.tables:
                lines.append("_(no CREATE TABLE — alters, grants, or one-off updates)_")
                lines.append("")
        return "\n".join(lines).rstrip() + "\n"


    def _collect_profile_overrides(self, props: list[ConfigProperty]) -> "dict[str, list[tuple[str, str, str, str]]]":
        """
        For each non-canonical .properties file, return the list of (key, canonical_value,
        override_value, rationale) tuples — the rationale is the leading comment IN THAT FILE,
        re-parsed here because the canonical scan attaches the canonical comment as 'role' and
        we want the LOCAL rationale instead.

        Empty rationale = override exists but lacks a comment in its own source: that's the
        signal the audit table flags.
        """
        res_dir = self.GEST_ROOT / "src" / "main" / "resources"
        canonical_path = res_dir / "application.properties"
        canonical_kv: dict[str, str] = {}
        if canonical_path.is_file():
            canonical_kv = {k: v for k, (v, _c) in parse_properties_file(canonical_path).items()}
        out: dict[str, list[tuple[str, str, str, str]]] = {}
        for pf in sorted(res_dir.glob("application-*.properties")):
            kv = parse_properties_file(pf)
            if not kv:
                continue
            rows: list[tuple[str, str, str, str]] = []
            for key, (val, comment) in sorted(kv.items()):
                canon = canonical_kv.get(key, "_(absent)_")
                if val == canon:
                    continue  # not an actual override (same value declared in both)
                rows.append((key, canon, val, comment))
            if rows:
                out[pf.name] = rows
        return out


    def collect_config_properties(self) -> list[ConfigProperty]:
        res_dir = self.GEST_ROOT / "src" / "main" / "resources"
        files = sorted(res_dir.glob("application*.properties"))
        # Process the canonical `application.properties` FIRST so its comments become the "role"
        # of each key. Profile-specific files (`application-local.properties` etc.) override the
        # VALUE in their own column but never the description of what the key is for.
        canonical = res_dir / "application.properties"
        if canonical in files:
            files = [canonical] + [f for f in files if f != canonical]
        by_key: dict[str, ConfigProperty] = {}
        comments_by_key: dict[str, str] = {}
        for pf in files:
            kv = parse_properties_file(pf)
            for k, (v, comment) in kv.items():
                cp = by_key.setdefault(k, ConfigProperty(key=k, defaults={}, used_by=[]))
                cp.defaults[pf.name] = v
                if comment and k not in comments_by_key:
                    comments_by_key[k] = comment
        # find usages: @Value("${key}"), @Value("${key:default}"), @ConfigurationProperties(prefix="...")
        # use git grep on the keys
        for k, cp in by_key.items():
            cp.used_by = self.grep_files(rf"\$\{{\s*{re.escape(k)}\b", self.SRC_MAIN_JAVA)
        # also @ConfigurationProperties(prefix="gest.foo.bar") catches gest.foo.bar.* keys
        return sorted(by_key.values(), key=lambda c: c.key), comments_by_key


    def render_config(self, items: tuple[list[ConfigProperty], dict[str, str]]) -> str:
        props, comments = items
        lines = [f"# Configuration properties — {self.APP_LABEL} (as-is)", ""]
        lines.append(
            "Auto-generated from `application*.properties`. Comments above each key are surfaced "
            "as 'role'; usages are the Java files that reference `${key}` via `@Value` or any "
            "string interpolation. Keys defined in `application.properties` are the canonical "
            "shape; per-profile overrides appear in their own column."
        )
        lines.append("")
        lines.append(
            "**Env parity model**: the canonical `application.properties` is **prod-safe by "
            "default**; every value is either a literal default or `${ENV_VAR:default}`. "
            "Staging and prod ship NO properties file — they inject the env-vars via Terraform / "
            "Cloud Run / Secret Manager. The only profile file is `application-local.properties`, "
            "activated by `-Dspring-boot.run.profiles=local`. The 'Profile overrides' section below "
            "audits each override against the canonical to make the local-vs-deploy delta explicit."
        )
        lines.append("")
        lines.append(f"**Total keys**: {len(props)}")
        lines.append("")
        # Profile-override audit BEFORE the flat table. Highest signal first.
        overrides = self._collect_profile_overrides(props)
        if overrides:
            lines.append("## Profile overrides (audit)")
            lines.append("")
            lines.append(
                "Every profile-specific file is a deliberate departure from the canonical "
                "`application.properties`. An override without a leading comment in its source "
                "file is flagged: a future reader cannot tell whether the override is "
                "**ambient-necessary** (the env literally needs a different value, e.g. a "
                "localhost MySQL URL) or **dev-convenience** (something developers want, e.g. "
                "JTE hot-reload). Comment it. The pre-commit hook does not enforce this yet — "
                "it is a doc signal, not a gate, until a real bite happens."
            )
            lines.append("")
            for profile_file, deltas in overrides.items():
                lines.append(f"### `{profile_file}` ({len(deltas)} overrides vs canonical)")
                lines.append("")
                lines.append("| Key | Canonical | Override | Rationale (block comment) |")
                lines.append("|---|---|---|---|")
                for key, canon, ovr, rationale in deltas:
                    rat = rationale if rationale else "⚠ _(no comment in source — document why this differs)_"
                    lines.append(f"| `{key}` | `{canon}` | `{ovr}` | {rat} |")
                lines.append("")
        lines.append("## All keys (flat table)")
        lines.append("")
        profile_files = sorted({fn for p in props for fn in p.defaults.keys()})
        header_cols = ["Key"] + profile_files + ["Used by"]
        lines.append("| " + " | ".join(header_cols) + " |")
        lines.append("|" + "|".join(["---"] * len(header_cols)) + "|")
        for p in props:
            row = [f"`{p.key}`"]
            for pf in profile_files:
                v = p.defaults.get(pf, "")
                row.append(f"`{v}`" if v else "_(unset)_")
            used = ", ".join(f"`{Path(u).name}`" for u in p.used_by) if p.used_by else "_(unused or only in template)_"
            row.append(used)
            lines.append("| " + " | ".join(row) + " |")
        lines.append("")
        lines.append("## Detail")
        lines.append("")
        for p in props:
            lines.append(f"### `{p.key}`")
            lines.append("")
            role = comments.get(p.key, "")
            if role:
                lines.append(f"_{role}_")
                lines.append("")
            for pf in profile_files:
                v = p.defaults.get(pf)
                if v is not None:
                    lines.append(f"- **`{pf}`** = `{v}`")
            if p.used_by:
                lines.append("- **Used by**:")
                for u in p.used_by:
                    lines.append(f"  - `{u}`")
            else:
                lines.append("- **Used by**: _(no Java reference found — dead property?)_")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


    def collect_ports(self) -> list[PortIface]:
        out: list[PortIface] = []
        # find interfaces in any directory named "port"
        for jf in sorted(self.SRC_MAIN_JAVA.rglob("*.java")):
            if "/port/" not in str(jf):
                continue
            source, root = parse(jf)
            for n in walk(root):
                if n.type != "interface_declaration":
                    continue
                name_node = n.child_by_field_name("name")
                if name_node is None:
                    continue
                iface_name = node_text(name_node, source)
                # extract package from the file
                pkg = ""
                for m in walk(root):
                    if m.type == "package_declaration":
                        for c in m.children:
                            if c.type == "scoped_identifier" or c.type == "identifier":
                                pkg = node_text(c, source)
                        break
                summary = preceding_javadoc(n, source)
                # method signatures: walk method_declaration inside the body
                methods: list[str] = []
                for m in walk(n):
                    if m.type != "method_declaration":
                        continue
                    name = m.child_by_field_name("name")
                    params = m.child_by_field_name("parameters")
                    if name is None:
                        continue
                    sig = node_text(name, source)
                    if params is not None:
                        sig += node_text(params, source)
                    methods.append(sig)
                out.append(PortIface(
                    name=iface_name, package=pkg,
                    file_rel=str(jf.relative_to(self.REPO_ROOT)),
                    summary=summary, methods=methods, impls=[],
                ))
                break  # one top-level interface per file
        # find implementors: classes with `implements <Iface>` (single-line search is enough)
        for port in out:
            port.impls = self.grep_files(rf"\bimplements\b[^;{{]*\b{re.escape(port.name)}\b", self.SRC_MAIN_JAVA)
            # also accept class signatures spanning multiple lines: use a permissive match
            if not port.impls:
                port.impls = self.grep_files(rf"implements\s+{re.escape(port.name)}\b", self.SRC_MAIN_JAVA)
        return out


    def render_ports(self, ports: list[PortIface]) -> str:
        lines = [f"# Ports ↔ Adapters — {self.APP_LABEL} (as-is)", ""]
        lines.append(
            "Auto-generated. A **port** is an interface declared under any `port` package "
            "(domain-driven hexagonal architecture: the domain owns the contract, the adapter "
            "lives in `infrastructure/`). This matrix shows each port with its declared method "
            "signatures and the concrete `implements` sites."
        )
        lines.append("")
        lines.append(f"**Total ports**: {len(ports)}")
        lines.append("")
        for p in ports:
            lines.append(f"## `{p.name}`")
            lines.append("")
            if p.summary:
                lines.append(javadoc_to_block(p.summary))
                lines.append("")
            else:
                lines.append("_(no javadoc on the interface — add one)_")
                lines.append("")
            lines.append(f"- **Package**: `{p.package}`")
            lines.append(f"- **File**: `{p.file_rel}`")
            if p.methods:
                lines.append("- **Methods**:")
                for m in p.methods:
                    lines.append(f"  - `{m}`")
            if p.impls:
                lines.append("- **Implementations**:")
                for im in p.impls:
                    lines.append(f"  - `{im}`")
            else:
                lines.append("- **Implementations**: _(no `implements` site found — orphan port?)_")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


    def collect_jte_templates(self) -> list[JteTemplate]:
        jte_root = self.GEST_ROOT / "src" / "main" / "jte"
        if not jte_root.is_dir():
            return []
        out: list[JteTemplate] = []
        for f in sorted(jte_root.rglob("*.jte")):
            name = str(f.relative_to(jte_root)).removesuffix(".jte")
            txt = f.read_text(encoding="utf-8")
            params: list[tuple[str, str, str]] = []
            for m in re.finditer(r"^@param\s+(.+?)$", txt, re.MULTILINE):
                decl = m.group(1).strip()
                # forms: "Type name", "Type name = default", "Type<Generic> name"
                if "=" in decl:
                    left, _, default = decl.partition("=")
                    left = left.strip(); default = default.strip()
                else:
                    left, default = decl, ""
                # split type and name by last whitespace (handles generics fine)
                sp = left.rstrip().rsplit(maxsplit=1)
                if len(sp) == 2:
                    typ, pname = sp
                    params.append((typ.strip(), pname.strip(), default))
                else:
                    params.append((left, "", default))
            includes: list[str] = []
            # JTE includes look like `@template._partials.calendar-toolbar(args)`.
            # Allow hyphens in segment names (template files like `calendar-toolbar.jte`).
            for m in re.finditer(r"@template\.([A-Za-z0-9_.\-/]+)", txt):
                tname = m.group(1).replace(".", "/")
                if tname not in includes:
                    includes.append(tname)
            out.append(JteTemplate(
                name=name, file_rel=str(f.relative_to(self.REPO_ROOT)),
                params=params, includes=includes,
            ))
        return out


    def render_templates(self, templates: list[JteTemplate]) -> str:
        lines = [f"# JTE templates — {self.APP_LABEL} (as-is)", ""]
        lines.append(
            "Auto-generated from `apps/gest/src/main/jte/**/*.jte`. Each template lists its "
            "required `@param`s (with declared default if any) and the partials / sub-templates "
            "it pulls in via `@template....`. Missing a `@param` at render time = NPE; this "
            "tree is the contract between Java controllers and the view layer."
        )
        lines.append("")
        lines.append(f"**Total templates**: {len(templates)}")
        lines.append("")
        lines.append("## Inclusion graph (PlantUML)")
        lines.append("")
        lines.append("```plantuml")
        lines.append("@startuml")
        for t in templates:
            lines.append(f'rectangle "{t.name}"')
        for t in templates:
            for inc in t.includes:
                lines.append(f'"{t.name}" --> "{inc}"')
        lines.append("@enduml")
        lines.append("```")
        lines.append("")
        lines.append("## Detail")
        lines.append("")
        for t in templates:
            lines.append(f"### `{t.name}`")
            lines.append("")
            lines.append(f"- **File**: `{t.file_rel}`")
            if t.params:
                lines.append("- **Params**:")
                for typ, pname, default in t.params:
                    d = f" = `{default}`" if default else ""
                    lines.append(f"  - `{typ} {pname}`{d}")
            else:
                lines.append("- **Params**: _(none)_")
            if t.includes:
                lines.append("- **Includes**:")
                for inc in t.includes:
                    lines.append(f"  - `{inc}`")
            else:
                lines.append("- **Includes**: _(leaf template)_")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


    def parse_jacoco_csv(self) -> dict[tuple[str, str], CoverageRow]:
        """Return { (package, class_simple): row } from the JaCoCo CSV. Empty if CSV absent."""
        out: dict[tuple[str, str], CoverageRow] = {}
        if not self.JACOCO_CSV.is_file():
            return out
        import csv as _csv
        with self.JACOCO_CSV.open(encoding="utf-8") as fh:
            reader = _csv.DictReader(fh)
            for row in reader:
                pkg = row["PACKAGE"]
                cls = row["CLASS"]
                # JaCoCo reports per-class incl. nested ($), JTE precompiled, etc.
                if self.GEST_PACKAGE_ROOT and not pkg.startswith(self.GEST_PACKAGE_ROOT):
                    continue
                if pkg.startswith("gg.jte"):
                    continue
                out[(pkg, cls)] = CoverageRow(
                    package=pkg, class_simple=cls, file_rel="",
                    lines_missed=int(row["LINE_MISSED"]),
                    lines_covered=int(row["LINE_COVERED"]),
                    branches_missed=int(row["BRANCH_MISSED"]),
                    branches_covered=int(row["BRANCH_COVERED"]),
                    methods_missed=int(row["METHOD_MISSED"]),
                    methods_covered=int(row["METHOD_COVERED"]),
                )
        return out


    def collect_all_main_files(self) -> list[tuple[str, str, str]]:
        """Return [(package, class_simple, file_rel)] for every .java under src/main/java."""
        out: list[tuple[str, str, str]] = []
        for jf in sorted(self.SRC_MAIN_JAVA.rglob("*.java")):
            rel = jf.relative_to(self.SRC_MAIN_JAVA)
            pkg = ".".join(rel.parts[:-1])
            cls = jf.stem
            out.append((pkg, cls, str(jf.relative_to(self.REPO_ROOT))))
        return out


    def render_coverage(self) -> str:
        cov = self.parse_jacoco_csv()
        files = self.collect_all_main_files()

        # join: every production file gets a row, with coverage data if JaCoCo saw the class
        rows: list[CoverageRow] = []
        for pkg, cls, file_rel in files:
            # JaCoCo's CLASS column is the simple name; inner classes come as Outer$Inner.
            # We aggregate inner classes into the outer file: sum their counters.
            agg = CoverageRow(
                package=pkg, class_simple=cls, file_rel=file_rel,
                lines_missed=0, lines_covered=0,
                branches_missed=0, branches_covered=0,
                methods_missed=0, methods_covered=0,
            )
            matched = False
            for (cpkg, ccls), c in cov.items():
                if cpkg != pkg:
                    continue
                top = ccls.split("$", 1)[0]
                if top != cls:
                    continue
                matched = True
                agg.lines_missed += c.lines_missed
                agg.lines_covered += c.lines_covered
                agg.branches_missed += c.branches_missed
                agg.branches_covered += c.branches_covered
                agg.methods_missed += c.methods_missed
                agg.methods_covered += c.methods_covered
            if not matched:
                # JaCoCo didn't see this class at all (likely interface, annotation, or 0-call code path)
                pass
            rows.append(agg)

        total_lines = sum(r.total_lines for r in rows)
        covered_lines = sum(r.lines_covered for r in rows)
        overall_pct = (covered_lines / total_lines * 100) if total_lines else 0.0

        lines = [f"# Coverage — {self.APP_LABEL} (as-is)", ""]
        if not cov:
            lines.append(
                "⚠ **No JaCoCo CSV found** at `apps/gest/target/site/jacoco/jacoco.csv`. "
                "Run `make coverage` (alias for `./mvnw test` + regen) and try again. "
                "Without the CSV every file below shows 0% — that's the absence of data, not a result."
            )
            lines.append("")
        else:
            import datetime as _dt
            mtime = _dt.datetime.fromtimestamp(self.JACOCO_CSV.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            lines.append(
                "Auto-generated by joining a walk of `apps/gest/src/main/java` with JaCoCo's CSV at "
                "`target/site/jacoco/jacoco.csv`. EVERY production file appears, including those JaCoCo "
                "never saw (0% column) — the complete file list is the point. Inner-class counters are "
                "aggregated into the outer file. JTE precompiled classes (`gg.jte.*`) are excluded as "
                "generated code, not authored."
            )
            lines.append("")
            lines.append(f"**Data freshness**: jacoco.csv written {mtime} (run `make coverage` to refresh).")
            lines.append("**Test scope**: whatever the last `./mvnw test` ran — typically the `-Dgroups=unit` lane. Run `./mvnw verify` for IT + contract coverage.")
            lines.append("")
        lines.append(f"**Files**: {len(rows)} · **Overall line coverage**: {overall_pct:.1f}% ({covered_lines}/{total_lines})")
        lines.append("")

        # by-package summary
        lines.append("## By package")
        lines.append("")
        by_pkg: dict[str, list[CoverageRow]] = defaultdict(list)
        for r in rows:
            by_pkg[r.package].append(r)
        lines.append("| Package | Files | Lines covered | Line % | Branch % |")
        lines.append("|---|---|---|---|---|")
        for pkg in sorted(by_pkg):
            bucket = by_pkg[pkg]
            t = sum(b.total_lines for b in bucket)
            c = sum(b.lines_covered for b in bucket)
            bt = sum(b.total_branches for b in bucket)
            bc = sum(b.branches_covered for b in bucket)
            lpct = (c / t * 100) if t else 0.0
            bpct = (bc / bt * 100) if bt else 0.0
            lines.append(f"| `{pkg}` | {len(bucket)} | {c}/{t} | {lpct:.1f}% | {bpct:.1f}% |")
        lines.append("")

        # zero-coverage list — fast-scan for "what's never been tested"
        zero = [r for r in rows if r.lines_covered == 0 and r.total_lines > 0]
        if zero:
            lines.append(f"## Zero-coverage files ({len(zero)})")
            lines.append("")
            lines.append("These authored production files have at least one executable line and ZERO line coverage.")
            lines.append("Either add a test, or move the type to a category that is dead code by design (records-with-no-logic, enums, marker interfaces).")
            lines.append("")
            for r in zero:
                lines.append(f"- `{r.file_rel}` — {r.total_lines} lines, {r.methods_missed + r.methods_covered} methods")
            lines.append("")

        # full per-file table
        lines.append("## Per file (all production sources)")
        lines.append("")
        lines.append("| File | Lines | Line % | Branch % | Methods |")
        lines.append("|---|---|---|---|---|")
        for r in sorted(rows, key=lambda x: x.file_rel):
            l = r.total_lines
            if l == 0:
                line_cell = "_(no executable lines — interface / annotation / enum constants only)_"
            else:
                line_cell = f"{r.lines_covered}/{l} · {r.line_pct:.1f}%"
            b = r.total_branches
            branch_cell = f"{r.branch_pct:.1f}%" if b else "—"
            meth_cell = f"{r.methods_covered}/{r.methods_missed + r.methods_covered}"
            lines.append(f"| `{r.file_rel.removeprefix(f'{self.APP_LABEL}/src/main/java/')}` | {l or '—'} | {line_cell if l else '—'} | {branch_cell} | {meth_cell} |")
        return "\n".join(lines).rstrip() + "\n"


    def git_blame_one(self, file: Path, lineno: int) -> tuple[str, int]:
        """Return (author_name, age_in_days). Empty/-1 if git unavailable or file untracked."""
        try:
            r = subprocess.run(
                ["git", "blame", "-L", f"{lineno},{lineno}", "--porcelain", str(file)],
                cwd=self.REPO_ROOT, capture_output=True, text=True, check=False,
            )
            if r.returncode != 0:
                return "", -1
            author = ""
            author_time = 0
            for ln in r.stdout.splitlines():
                if ln.startswith("author "):
                    author = ln[len("author "):].strip()
                elif ln.startswith("author-time "):
                    author_time = int(ln.split()[1])
            import time as _t
            age = int((_t.time() - author_time) / 86400) if author_time else -1
            return author, age
        except Exception:
            return "", -1


    def collect_structure_paths(self) -> "tuple[list[str], bool]":
        """Repo-relative POSIX paths of the structural files, convention-driven.

        Primary: `git ls-files` (respects the repo's own .gitignore, so node_modules /
        target / build / generated coverage never appear: the convention IS the gitignore).
        Fallback (non-git target, e.g. a fixture dir): a filesystem walk with the default
        exclude set. Returns (sorted unique paths capped at STRUCTURE_MAX_ENTRIES, truncated?)."""
        paths = self._git_tracked_paths()
        if paths is None:
            paths = self._walked_paths()
        ordered = sorted(set(paths))
        truncated = len(ordered) > STRUCTURE_MAX_ENTRIES
        return ordered[:STRUCTURE_MAX_ENTRIES], truncated

    def _git_tracked_paths(self) -> "list[str] | None":
        """Git-tracked files under the repo root, or None when the target is not a git repo."""
        try:
            r = subprocess.run(
                ["git", "ls-files", "--cached", "--exclude-standard"],
                cwd=self.REPO_ROOT, capture_output=True, text=True, check=False,
            )
        except Exception:
            return None
        if r.returncode != 0:
            return None
        files = [ln for ln in r.stdout.splitlines() if ln.strip()]
        return files or None

    def _walked_paths(self) -> list[str]:
        """Filesystem-walk fallback: every file minus the default build/dep/vcs excludes."""
        out: list[str] = []
        for f in self.REPO_ROOT.rglob("*"):
            if not f.is_file():
                continue
            if set(f.parts) & STRUCTURE_EXCLUDE_DIRS:
                continue
            if any(p.endswith(".egg-info") for p in f.parts):
                continue
            out.append(f.relative_to(self.REPO_ROOT).as_posix())
        return out

    def render_structure(self) -> str:
        """The `structure.md` skeleton: a convention-driven tree snapshot of the repo.

        Deterministic (sorted), so it only drifts when the tracked file set changes (add /
        remove / rename), which is exactly when the snapshot should be refreshed."""
        paths, truncated = self.collect_structure_paths()
        root_name = self.REPO_ROOT.name or "."
        lines = [
            f"# Structure — `{root_name}`",
            "",
            "Convention-driven skeleton of the repository: the git-tracked files (respecting "
            "`.gitignore`, so no `node_modules` / `target` / build output), rendered as a tree. "
            "A single readable snapshot of where everything lives, for a human or an agent "
            "orienting in a fresh session. Regenerated on every commit like every `_generated` "
            "doc; the source of truth is the filesystem, never this markdown.",
            "",
            f"_{len(paths)} tracked paths._",
            "",
            "```",
            f"{root_name}/",
            *_render_tree_lines(_build_path_tree(paths)),
            "```",
        ]
        if truncated:
            lines += ["", f"_(truncated at {STRUCTURE_MAX_ENTRIES} entries — the repo has more)_"]
        return "\n".join(lines) + "\n"

    def collect_todos(self) -> list[TodoItem]:
        out: list[TodoItem] = []
        for root in self.TODO_SCAN_ROOTS:
            if not root.is_dir():
                continue
            for f in sorted(root.rglob("*")):
                if not f.is_file():
                    continue
                parts = set(f.parts)
                if parts & TODO_EXCLUDE_DIRS:
                    continue
                if f.suffix not in (".java", ".ts", ".tsx", ".js", ".jte", ".css", ".sql", ".groovy", ".sh", ".py"):
                    continue
                try:
                    txt = f.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                for i, line in enumerate(txt.splitlines(), start=1):
                    m = TODO_MARKER_RE.search(line)
                    if m:
                        kind = m.group(1)
                        msg = m.group(2).strip()[:200] or "_(empty marker)_"
                        author, age = self.git_blame_one(f, i)
                        out.append(TodoItem(
                            kind=kind, file_rel=str(f.relative_to(self.REPO_ROOT)), line=i,
                            text=msg, author=author, age_days=age,
                        ))
                        continue
                    # also catch @Deprecated annotations on the next non-blank declaration
                    if line.strip() == "@Deprecated" or line.strip().startswith("@Deprecated("):
                        author, age = self.git_blame_one(f, i)
                        out.append(TodoItem(
                            kind="@Deprecated", file_rel=str(f.relative_to(self.REPO_ROOT)), line=i,
                            text=line.strip(), author=author, age_days=age,
                        ))
        return out


    def render_todos(self, items: list[TodoItem]) -> str:
        lines = [f"# Tech debt inventory — {self.APP_LABEL} (as-is)", ""]
        lines.append(
            "Auto-generated. Every `TODO` / `FIXME` / `XXX` / `HACK` marker plus every `@Deprecated` "
            "in the authored sources is listed below, with `git blame` author and age in days. The "
            "purpose is **visibility**: nothing here is automatically blocking, but a marker that "
            "ages past 90 days is usually either done-by-other-means (delete the marker) or stale "
            "debt that should become an ADR or an issue."
        )
        lines.append("")
        lines.append(f"**Total markers**: {len(items)}")
        lines.append("")
        if not items:
            lines.append("✓ Zero markers in the authored sources right now.")
            lines.append("")
            return "\n".join(lines).rstrip() + "\n"
        by_kind: dict[str, list[TodoItem]] = defaultdict(list)
        for it in items:
            by_kind[it.kind].append(it)
        lines.append("## By kind")
        lines.append("")
        for k in ("FIXME", "HACK", "XXX", "TODO", "@Deprecated"):
            if by_kind.get(k):
                lines.append(f"- **{k}**: {len(by_kind[k])}")
        lines.append("")
        for k in ("FIXME", "HACK", "XXX", "TODO", "@Deprecated"):
            bucket = by_kind.get(k, [])
            if not bucket:
                continue
            lines.append(f"## {k} ({len(bucket)})")
            lines.append("")
            lines.append("| File:line | Age | Author | Note |")
            lines.append("|---|---|---|---|")
            for it in sorted(bucket, key=lambda x: (-x.age_days if x.age_days >= 0 else 0, x.file_rel)):
                age = f"{it.age_days}d" if it.age_days >= 0 else "—"
                author = it.author or "—"
                note = it.text.replace("|", "\\|")
                lines.append(f"| `{it.file_rel}:{it.line}` | {age} | {author} | {note} |")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


    def parse_adrs(self) -> list[AdrEntry]:
        out: list[AdrEntry] = []
        if not self.ADR_DIR.is_dir():
            return out
        for f in sorted(self.ADR_DIR.glob("*.md")):
            m = re.match(r"^(\d+)[-_]?(.*)\.md$", f.name)
            if not m:
                continue
            adr_id = f"ADR-{int(m.group(1)):04d}"
            txt = f.read_text(encoding="utf-8")
            # H1 title
            title_m = re.search(r"^#\s+ADR-\d+\s*[-—:]\s*(.+)$", txt, re.MULTILINE)
            if not title_m:
                title_m = re.search(r"^#\s+(.+)$", txt, re.MULTILINE)
            title = title_m.group(1).strip() if title_m else f.stem
            # Status: **accepted** YYYY-MM-DD ...
            status_m = re.search(r"Status:\s*\*?\*?(\w+)\*?\*?\s*(\d{4}-\d{2}-\d{2})?", txt)
            status = status_m.group(1).lower() if status_m else "unknown"
            status_date = status_m.group(2) if (status_m and status_m.group(2)) else ""
            # supports US: scan for US-NNN-slug citations
            supports = sorted(set(re.findall(r"US-\d+-[a-z0-9-]+", txt)))
            out.append(AdrEntry(
                id=adr_id, file_rel=str(f.relative_to(self.REPO_ROOT)),
                title=title, status=status, status_date=status_date,
                supports_us=supports,
            ))
        return out


    def detect_adr_candidates(self) -> list[tuple[str, str, str]]:
        """
        Return [(signal, file_rel, hint)] for load-bearing decisions in the codebase that are not yet
        documented as ADRs. Heuristic: a pattern usually worth an ADR.
          - @Conditional / @ConditionalOnProperty on a class
          - Class ending with *InvariantTest / *InvariantIT (an invariant IS a decision)
          - bean with defaultCandidate=false (isolation choice)
          - @ProcessingGroup (projection architecture choice)
          - Spring Cloud Contract files (boundary contract choices)
        """
        out: list[tuple[str, str, str]] = []
        for f in sorted(self.SRC_MAIN_JAVA.rglob("*.java")):
            txt = f.read_text(encoding="utf-8", errors="replace")
            rel = str(f.relative_to(self.REPO_ROOT))
            if re.search(r"@Conditional(OnProperty|OnMissingBean|OnBean)?\b", txt):
                out.append(("conditional bean wiring", rel, "@Conditional* present: feature flag / runtime branch — usually load-bearing"))
            if "defaultCandidate = false" in txt or "defaultCandidate=false" in txt:
                out.append(("explicit qualifier isolation", rel, "bean defined with defaultCandidate=false — isolation choice"))
            if re.search(r"@ProcessingGroup", txt):
                out.append(("projection processing group", rel, "@ProcessingGroup present: event-sourcing projection architecture"))
        # Invariant tests
        for f in sorted((self.GEST_ROOT / "src" / "test" / "java").rglob("*InvariantTest.java")):
            out.append(("invariant test", str(f.relative_to(self.REPO_ROOT)),
                        "*InvariantTest — invariants ARE decisions; consider documenting in an ADR"))
        for f in sorted((self.GEST_ROOT / "src" / "test" / "java").rglob("*InvariantIT.java")):
            out.append(("invariant integration test", str(f.relative_to(self.REPO_ROOT)),
                        "*InvariantIT — see above"))
        # contracts
        if self.CONTRACTS_DIR.is_dir():
            for f in sorted(self.CONTRACTS_DIR.rglob("*.groovy")):
                out.append(("HTTP boundary contract", str(f.relative_to(self.REPO_ROOT)),
                            "Spring Cloud Contract: the boundary IS a decision (was the rule from legacy or to-be?)"))
        return out


    def render_adr_index(self, adrs: list[AdrEntry], candidates: list[tuple[str, str, str]]) -> str:
        lines = [f"# ADR index — {self.APP_LABEL} (as-is)", ""]
        lines.append(
            "Auto-generated from `apps/gest/decisions/NNNN-*.md`. Title comes from the H1; status "
            "from a `Status: ...` line in the body; supported user stories from `US-NNN-slug` "
            "citations anywhere in the file. The 'Candidates' section is a heuristic scan of the "
            "codebase for load-bearing decisions (feature flags, invariants, contracts, projections) "
            "that have NO matching ADR yet — surface, don't autofix."
        )
        lines.append("")
        lines.append(f"**Total ADRs**: {len(adrs)}")
        lines.append("")
        if adrs:
            lines.append("## Index")
            lines.append("")
            lines.append("| ID | Status | Date | Title | Supports |")
            lines.append("|---|---|---|---|---|")
            for a in adrs:
                sup = ", ".join(f"`{u}`" for u in a.supports_us) or "—"
                date = a.status_date or "—"
                lines.append(f"| `{a.id}` | {a.status} | {date} | [{a.title}]({a.file_rel.removeprefix(f'{self.APP_LABEL}/')}) | {sup} |")
            lines.append("")
        else:
            lines.append("_No ADR files found under `apps/gest/decisions/`._")
            lines.append("")
        # candidates
        lines.append(f"## Candidates (auto-detected, {len(candidates)} signals)")
        lines.append("")
        lines.append(
            "Heuristic. Each signal usually warrants an ADR (a feature flag, an invariant, a contract, "
            "a projection design choice are all decisions you'll want to defend in 6 months). Open the "
            "file, decide if it's already covered by an existing ADR, otherwise consider writing a new one."
        )
        lines.append("")
        by_signal: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
        for sig, file_rel, hint in candidates:
            by_signal[sig].append((sig, file_rel, hint))
        for sig in sorted(by_signal):
            lines.append(f"### {sig} ({len(by_signal[sig])})")
            lines.append("")
            for _, file_rel, hint in sorted(by_signal[sig]):
                lines.append(f"- `{file_rel}` — {hint}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


    def parse_pom_deps(self) -> list[Dep]:
        pom = self.GEST_ROOT / "pom.xml"
        if not pom.is_file():
            return []
        # XXE does not apply: the parsed XML is OUR OWN pom.xml / build artifacts from this
        # repo, never untrusted input. defusedxml would add a dependency for zero real risk.
        import xml.etree.ElementTree as ET  # nosemgrep: python.lang.security.use-defused-xml.use-defused-xml
        txt = pom.read_text(encoding="utf-8")
        # strip xmlns to make ET happy without namespaces
        txt = re.sub(r"\sxmlns=\"[^\"]+\"", "", txt, count=1)
        root = ET.fromstring(txt)
        deps: list[Dep] = []
        parent = root.find("parent")
        if parent is not None:
            g = (parent.findtext("groupId") or "").strip()
            n = (parent.findtext("artifactId") or "").strip()
            v = (parent.findtext("version") or "").strip()
            deps.append(Dep("maven (parent)", g, n, v, "parent", str(pom.relative_to(self.REPO_ROOT))))
        for d in root.findall(".//dependencies/dependency"):
            g = (d.findtext("groupId") or "").strip()
            n = (d.findtext("artifactId") or "").strip()
            v = (d.findtext("version") or "").strip() or "(from parent / bom)"
            s = (d.findtext("scope") or "compile").strip()
            deps.append(Dep("maven", g, n, v, s, str(pom.relative_to(self.REPO_ROOT))))
        return deps


    def parse_npm_deps(self, pkg_json: Path) -> list[Dep]:
        if not pkg_json.is_file():
            return []
        import json as _json
        data = _json.loads(pkg_json.read_text(encoding="utf-8"))
        out: list[Dep] = []
        src = str(pkg_json.relative_to(self.REPO_ROOT))
        for k, v in (data.get("dependencies") or {}).items():
            group = "@" + k.split("/")[0][1:] if k.startswith("@") else ""
            name = k
            out.append(Dep("npm", group, name, str(v), "prod", src))
        for k, v in (data.get("devDependencies") or {}).items():
            group = "@" + k.split("/")[0][1:] if k.startswith("@") else ""
            out.append(Dep("npm", group, k, str(v), "dev", src))
        return out


    def parse_python_deps(self) -> list[Dep]:
        req = self.REPO_ROOT / "scripts" / "requirements.txt"
        if not req.is_file():
            return []
        out: list[Dep] = []
        for line in req.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            m = re.match(r"^([A-Za-z0-9_.\-]+)\s*([<>=!~]+\s*[\w.\-]+)?", s)
            if not m:
                continue
            out.append(Dep("python", "", m.group(1), (m.group(2) or "").strip() or "unpinned",
                           "scripts", str(req.relative_to(self.REPO_ROOT))))
        return out


    def collect_dependencies(self) -> list[Dep]:
        return (
            self.parse_pom_deps()
            + self.parse_npm_deps(self.GEST_ROOT / "frontend" / "package.json")
            + self.parse_npm_deps(self.GEST_ROOT / "e2e" / "package.json")
            + self.parse_python_deps()
        )


    def render_dependencies(self, deps: list[Dep]) -> str:
        lines = [f"# Dependencies — {self.APP_LABEL} (as-is)", ""]
        lines.append(
            "Auto-generated from `pom.xml` (Maven), `frontend/package.json` + `e2e/package.json` (npm), "
            "and `scripts/requirements.txt` (Python). Empty version = inherited from Spring Boot parent "
            "BOM. Pre-commit refreshes this; if you bump a version anywhere, the diff lands here too."
        )
        lines.append("")
        by_eco: dict[str, list[Dep]] = defaultdict(list)
        for d in deps:
            by_eco[d.ecosystem].append(d)
        lines.append(f"**Total**: {len(deps)} ({', '.join(f'{k}={len(v)}' for k,v in sorted(by_eco.items()))})")
        lines.append("")
        for eco in sorted(by_eco):
            lines.append(f"## {eco} ({len(by_eco[eco])})")
            lines.append("")
            lines.append("| Group | Name | Version | Scope | Source |")
            lines.append("|---|---|---|---|---|")
            for d in sorted(by_eco[eco], key=lambda x: (x.group, x.name)):
                lines.append(f"| `{d.group or '—'}` | `{d.name}` | `{d.version}` | `{d.scope}` | `{d.source_file}` |")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


    def render_manifest(self, present: "set[str] | None" = None) -> str:
        """Render MANIFEST via the shared core renderer so it is byte-identical to the
        zero-config auto path (ADR-0009). `present` is the set of generated filenames; it
        defaults to the requirements + framework + commodity .md files the code-docs path
        always writes, so a `--check` run does not depend on what is already on disk."""
        if present is None:
            present = {name for _topic, docs in MANIFEST_ORDER for name, _desc in docs}
        return manifest_md(self.APP_LABEL, present)


    def _display_path(self, path: Path) -> Path | str:
        """Print paths relative to the repo root when they live under it, else absolute.
        A custom --out (e.g. a temp dir outside the target) must not crash the printer."""
        try:
            return path.relative_to(self.REPO_ROOT)
        except ValueError:
            return path


    def write_or_check(self, path: Path, content: str, check: bool) -> bool:
        """Return False if --check and content differs from on-disk."""
        if check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                print(f"stale: {self._display_path(path)}", file=sys.stderr)
                return False
            return True
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"wrote {self._display_path(path)} ({len(content.splitlines())} lines)")
        return True


    def main(self, argv: list[str]) -> int:
        check = "--check" in argv

        route_constants = self.collect_route_constants()
        contracts = self.load_contracts()
        endpoints = self.collect_endpoints(route_constants, contracts)
        events = self.collect_events()
        projections = self.collect_projections()
        modules = self.collect_modules()
        migrations = self.parse_flyway_files()
        config = self.collect_config_properties()
        ports = self.collect_ports()
        templates = self.collect_jte_templates()

        targets = [
            (self.GENERATED_DIR / "http-endpoints.md", self.render_endpoints(endpoints)),
            (self.GENERATED_DIR / "events.md", self.render_events(events)),
            (self.GENERATED_DIR / "projections.md", self.render_projections(projections)),
            (self.GENERATED_DIR / "modules.md", self.render_modules(modules)),
            (self.GENERATED_DIR / "schema.md", self.render_schema(migrations)),
            (self.GENERATED_DIR / "config.md", self.render_config(config)),
            (self.GENERATED_DIR / "ports.md", self.render_ports(ports)),
            (self.GENERATED_DIR / "templates.md", self.render_templates(templates)),
            (self.GENERATED_DIR / "coverage.md", self.render_coverage()),
            (self.GENERATED_DIR / "todo.md", self.render_todos(self.collect_todos())),
            (self.GENERATED_DIR / "adr-index.md", self.render_adr_index(self.parse_adrs(), self.detect_adr_candidates())),
            (self.GENERATED_DIR / "dependencies.md", self.render_dependencies(self.collect_dependencies())),
        ]
        # MANIFEST is rendered LAST so it sees all freshly-written sibling files
        # (the manifest is just an index that points at the others).
        targets.append((self.GENERATED_DIR / "MANIFEST.md", ""))
        ok = True
        # write everything except MANIFEST first
        for path, content in targets[:-1]:
            if not self.write_or_check(path, content, check):
                ok = False
        # then render MANIFEST against the freshly-written set
        manifest_path, _ = targets[-1]
        if not self.write_or_check(manifest_path, self.render_manifest(), check):
            ok = False
        return 0 if ok else 2


# --- legacy module entry points (kept for the CLI + standalone use) ----------

def configure(cfg: Config) -> "CodeDocs":
    """Build a CodeDocs for `cfg`; returns it. No module globals are mutated."""
    return CodeDocs(cfg)


def main(cfg: Config, argv: list[str]) -> int:
    """Generate (or --check) all code docs for `cfg`."""
    return CodeDocs(cfg).main(argv)
