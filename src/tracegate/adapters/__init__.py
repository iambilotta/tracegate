"""tracegate adapters.

`lang/` parses a language's test + source AST (tree-sitter); `framework/` extracts
framework-specific facts (Spring endpoints, Axon events/projections, Flyway schema,
Playwright E2E). Adapters feed the language-neutral `tracegate.core` model. They are
enabled per-app by `core.detect`, never hardcoded.
"""
