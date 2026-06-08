"""
Shared javadoc → markdown helpers used by both code-docs and requirements generators.

Why a separate module: both generators render javadoc into markdown and previously
duplicated the logic; a fix in one place left the other broken. One module, two
imports.

Two modes:
- `to_inline(text)`: single line. <p>/<li> → " — " so a table cell stays readable.
- `to_block(text)`:  multi-paragraph. <p> → paragraph, <ul>/<ol><li> → bullet list.

Both translate {@code X} → `X` and {@link X[#meth(A,B)] [label]} → `label` or
backticked last-segment. Paren-balanced split so method signatures with multiple
parameters don't break the link parser.
"""
from __future__ import annotations

import re

_LINK_RE = re.compile(r"\{@(?:link|linkplain|literal)\s+([^}]+)\}")
_CODE_RE = re.compile(r"\{@code\s+([^}]+)\}")


def _resolve_link(target: str) -> str:
    """Map a {@link X} target to a readable label. Paren-balanced split so method
    signatures with multiple parameters don't get cut at the comma's space."""
    t = target.strip()
    depth = 0
    split = -1
    for i, ch in enumerate(t):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif depth == 0 and ch.isspace():
            split = i
            break
    if split >= 0:
        return f"`{t[split:].strip()}`"
    if "#" in t:
        cls, _, meth = t.partition("#")
        cls_last = cls.rsplit(".", 1)[-1] if cls else ""
        return f"`{cls_last}#{meth}`" if cls_last else f"`{meth}`"
    return f"`{t.rsplit('.', 1)[-1]}`"


def _strip_javadoc_tags(text: str) -> str:
    s = _CODE_RE.sub(lambda m: f"`{m.group(1).strip()}`", text)
    s = _LINK_RE.sub(lambda m: _resolve_link(m.group(1)), s)
    return s


def to_inline(text: str) -> str:
    """For markdown table cells / single-line contexts."""
    if not text:
        return text
    s = _strip_javadoc_tags(text)
    s = re.sub(r"<p\s*/?>", " — ", s, flags=re.IGNORECASE)
    s = re.sub(r"</p>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"<li>\s*", " — ", s, flags=re.IGNORECASE)
    s = re.sub(r"</li>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"</?(ol|ul)\s*>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(?:\s*—\s*){2,}", " — ", s)
    s = re.sub(r"^\s*—\s*|\s*—\s*$", "", s)
    return s


def to_block(text: str) -> str:
    """For markdown body sections that can carry paragraphs and bullet lists."""
    if not text:
        return text
    s = _strip_javadoc_tags(text)
    s = re.sub(r"<p\s*/?>", "\n\n", s, flags=re.IGNORECASE)
    s = re.sub(r"</p>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"</?(ol|ul)\s*>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*<li>\s*", "\n- ", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*</li>", "", s, flags=re.IGNORECASE)
    lines = [re.sub(r"[ \t]+", " ", ln).strip() for ln in s.splitlines()]
    s = "\n".join(lines)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()
