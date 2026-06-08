"""Golden-file test for the requirements generator — the drift alarm for the tooling that
generates ALL the as-is documentation.

Strategy: a tiny fixture tree (2 Java test classes: spec'd FR, spec-missing FR, INV via
class-name suffix) runs through the Java adapter + the core requirements renderer; the
full markdown output is compared byte-for-byte against the committed golden. Any
behavioral change in the generator (tree-sitter API drift after a dependency bump, a
refactor that changes rendering) fails HERE instead of silently corrupting the
generated docs at the next commit.

Paths are CANONICAL repo-relative (ADR-0007): relative to the fixture repo root, never
a truncated form that drops a leading segment.

When a change is INTENTIONAL: regenerate the golden with
    python3 tests/test_generate_requirements_golden.py --update
review the diff, commit golden + generator together.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
FIXTURE_REPO = HERE / "fixtures" / "gest-mini"
GOLDEN = HERE / "fixtures" / "expected-requirements.md"

sys.path.insert(0, str(SRC))


def _cfg():
    from tracegate.core.config import Config
    return Config(
        repo_root=FIXTURE_REPO,
        app_root=FIXTURE_REPO,
        label="gest-mini",
        package_root="it.housetreespa.gest",
    )


def _render_fixture() -> str:
    from tracegate.adapters.lang import java as java_adapter
    from tracegate.core import render
    cfg = _cfg()
    reqs = list(java_adapter.extract(cfg))
    return render.requirements_md(reqs, cfg.label)


def test_generator_output_matches_the_golden_file():
    actual = _render_fixture()
    assert GOLDEN.exists(), (
        f"golden file missing: {GOLDEN}\n"
        "generate it: python3 tests/test_generate_requirements_golden.py --update")
    expected = GOLDEN.read_text(encoding="utf-8")
    assert actual == expected, (
        "generator output drifted from the golden file.\n"
        "If the change is intentional, regenerate + review + commit:\n"
        "  python3 tests/test_generate_requirements_golden.py --update")


def test_fixture_covers_the_three_behaviors_the_golden_pins():
    """Belt-and-braces: the golden is only as good as what the fixture exercises."""
    out = _render_fixture()
    assert "FR-sample.domain.Sample#fully_documented_test_renders_in_the_catalog" in out
    assert "`inline code`" in out          # javadoc {@code} -> backticks
    assert "(spec missing)" in out         # undocumented test stays visible + lintable
    # the category suffix is stripped from the ID (SampleInvariantTest -> Sample)
    assert "INV-sample.domain.Sample#suffix_routes_to_the_invariant_category" in out
    assert "US-001-sample-story" in out    # @spec.us traceability
    # canonical path: relative to the fixture repo root, with no dropped segment
    assert "src/test/java/it/housetreespa/gest/sample/domain/SampleTest.java" in out
    assert "gest-mini/src/test/java" not in out  # the old truncation must not reappear


if __name__ == "__main__":
    if "--update" in sys.argv:
        GOLDEN.write_text(_render_fixture(), encoding="utf-8")
        print(f"golden updated: {GOLDEN}")
    else:
        print(__doc__)
