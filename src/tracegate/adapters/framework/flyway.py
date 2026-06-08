"""Flyway framework adapter: per-migration schema inventory.

Wraps the proven Phase-0 collector: parses `db/migration/V*.sql` in version order and
emits a table inventory with each migration's leading-comment intent.
"""
from __future__ import annotations

from ...core.config import Config
from ... import generate_code_docs as cd


def sections(cfg: Config) -> dict[str, str]:
    g = cd.CodeDocs(cfg)
    return {"schema": g.render_schema(g.parse_flyway_files())}
