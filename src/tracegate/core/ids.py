"""Traceability-ID derivation (ADR-0003).

The ID schema generalizes the original Java `<CAT>-<module>.<Class>#<method>` to any
language: a category, a dotted module path, the unit (class/file) the test lives in,
and the test method/title. The unit name has its category suffix already stripped by
the adapter before it reaches here, so renaming a test method changes its ID by design
(the spec follows the code).

    FR-auth.legacy.LegacyPasswordVerifier#verifies_md5_match     (Java)
    FR-core.detect.detect#enables_python_adapter_on_pyproject    (Python)
    E2E-e2e.screenshots#home_renders                             (Playwright)
"""
from __future__ import annotations

# Category suffixes stripped from a unit name to get its clean form. Ordered longest
# first so `InvariantTest` wins over `Test`. Shared by every language adapter that
# encodes the category in the class/file name.
CATEGORY_SUFFIXES = (
    "InvariantTest", "InvariantIT",
    "ContractTest", "ContractIT",
    "NfrTest", "NfrIT",
    "Test", "IT",
    ".spec",  # TypeScript Playwright spec files
)

# Suffix -> category. First match wins (same ordering rationale as above).
CATEGORY_BY_SUFFIX = (
    ("InvariantTest", "INV"),
    ("InvariantIT", "INV"),
    ("ContractTest", "CON"),
    ("ContractIT", "CON"),
    ("NfrTest", "NFR"),
    ("NfrIT", "NFR"),
    ("Test", "FR"),
    ("IT", "FR"),
)


def classify(unit_name: str) -> str:
    """Category from a class/file name's suffix (FR default)."""
    for suffix, cat in CATEGORY_BY_SUFFIX:
        if unit_name.endswith(suffix):
            return cat
    return "FR"


def strip_category_suffix(unit_name: str) -> str:
    """`LegacyPasswordVerifierTest` -> `LegacyPasswordVerifier`; `screenshots.spec` -> `screenshots`."""
    for suffix in CATEGORY_SUFFIXES:
        if unit_name.endswith(suffix):
            return unit_name[: -len(suffix)]
    return unit_name


# Filename markers (lowercase, snake_case languages like Python). First match wins.
_FILE_CATEGORY_MARKERS = (
    ("invariant", "INV"),
    ("contract", "CON"),
    ("nfr", "NFR"),
)


def classify_filename(stem: str) -> str:
    """Category from a snake_case test file name (`test_invariant_x` -> INV; FR default)."""
    low = stem.lower()
    for marker, cat in _FILE_CATEGORY_MARKERS:
        if marker in low:
            return cat
    return "FR"


def requirement_id(category: str, module: str, unit: str, method: str) -> str:
    """Compose the canonical ID. `unit` is assumed already suffix-stripped."""
    return f"{category}-{module}.{unit}#{method}"
