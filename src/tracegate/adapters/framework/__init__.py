"""Framework adapters.

Each exposes `sections(cfg) -> dict[name, markdown]` (as-built doc sections) and may
expose `requirements(cfg) -> Iterator[Requirement]` (e.g. Playwright E2E tests are
requirements, not a doc section). The orchestrator calls whichever is present.

These wrap the proven Phase-0 collectors in `tracegate.generate_code_docs` (Pareto:
the Spring/Axon/Flyway extractors already work; the adapter is the seam, not a rewrite).
"""
