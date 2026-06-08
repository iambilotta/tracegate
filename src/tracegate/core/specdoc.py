"""Parse `@spec.*` tags out of a doc-comment body into a `Spec`.

Shared by every adapter whose convention is the `@spec.given/when/then` doc tag
(Java javadoc, TypeScript JSDoc). The convention is an ENHANCEMENT: a test with no
spec still becomes a Requirement, just with an incomplete `Spec` (surfaced as
"spec missing").
"""
from __future__ import annotations

import re

from .model import Spec


def _field(body: str, tag: str) -> str:
    """First `@spec.<tag>` value from a doc-comment body (multi-line until next @tag)."""
    pattern = re.compile(
        rf"@spec\.{tag}\b\s*(?P<val>.*?)(?=^\s*\*\s*@|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    m = pattern.search(body)
    if not m:
        return ""
    cleaned = re.sub(r"^\s*\*\s?", "", m.group("val"), flags=re.MULTILINE)
    return " ".join(cleaned.split()).strip()


def parse(body: str | None) -> Spec:
    if not body:
        return Spec()
    return Spec(
        given=_field(body, "given"),
        when=_field(body, "when"),
        then=_field(body, "then"),
        adr=_field(body, "adr"),
        us=_field(body, "us"),
        ac=_field(body, "ac"),
    )
