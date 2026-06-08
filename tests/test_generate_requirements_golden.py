"""Golden-file test for the requirements generator — the drift alarm for the tooling that
generates ALL the as-is documentation.

Strategy: a tiny fixture tree (2 Java test classes: spec'd FR, spec-missing FR, INV via
class-name suffix) runs through walk_tests() + render(); the full markdown output is
compared byte-for-byte against the committed golden. Any behavioral change in the
generator (tree-sitter API drift after a dependency bump, a refactor that changes
rendering) fails HERE, in `make scripts-test`, instead of silently corrupting 15
generated docs at the next commit.

When a change is INTENTIONAL: regenerate the golden with
    python3 scripts/tests/test_generate_requirements_golden.py --update
review the diff, commit golden + generator together.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Phase 0 layout: the generators live under src/tracegate/ (was housetree/scripts/).
SRC = HERE.parent / "src" / "tracegate"
FIXTURE_TEST_ROOT = HERE / "fixtures" / "gest-mini" / "src" / "test" / "java"
GOLDEN = HERE / "fixtures" / "expected-requirements.md"


def _load_generator():
    """Plain import: the generators are snake_case modules (renamed from dashed names
    precisely so tests can import them without importlib gymnastics)."""
    sys.path.insert(0, str(SRC))
    import generate_requirements
    return generate_requirements


def _render_fixture() -> str:
    gen = _load_generator()
    reqs = list(gen.walk_tests(FIXTURE_TEST_ROOT))
    return gen.render(reqs)


def test_generator_output_matches_the_golden_file():
    actual = _render_fixture()
    assert GOLDEN.exists(), (
        f"golden file missing: {GOLDEN}\n"
        "generate it: python3 scripts/tests/test_generate_requirements_golden.py --update")
    expected = GOLDEN.read_text(encoding="utf-8")
    assert actual == expected, (
        "generator output drifted from the golden file.\n"
        "If the change is intentional, regenerate + review + commit:\n"
        "  python3 scripts/tests/test_generate_requirements_golden.py --update")


def test_fixture_covers_the_three_behaviors_the_golden_pins():
    """Belt-and-braces: the golden is only as good as what the fixture exercises."""
    out = _render_fixture()
    assert "FR-sample.domain.Sample#fully_documented_test_renders_in_the_catalog" in out
    assert "`inline code`" in out          # javadoc {@code} -> backticks
    assert "(spec missing)" in out         # undocumented test stays visible + lintable
    # the category suffix is stripped from the ID (SampleInvariantTest -> Sample)
    assert "INV-sample.domain.Sample#suffix_routes_to_the_invariant_category" in out
    assert "US-001-sample-story" in out    # @spec.us traceability


if __name__ == "__main__":
    if "--update" in sys.argv:
        GOLDEN.write_text(_render_fixture(), encoding="utf-8")
        print(f"golden updated: {GOLDEN}")
    else:
        print(__doc__)
