"""The `structure.md` skeleton: a convention-driven tree snapshot of the repository.

Asserts the commodity `structure` section end-to-end (through the orchestrator, against the
non-git py-mini fixture so the filesystem-walk fallback is exercised) and the pure tree
helpers in isolation (deterministic, dirs-first).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from tracegate.core import detect, orchestrator  # noqa: E402
from tracegate.generate_code_docs import _build_path_tree, _render_tree_lines  # noqa: E402

FIXTURE_REPO = Path(__file__).resolve().parent / "fixtures" / "py-mini"


def test_structure_section_renders_a_convention_driven_tree(tmp_path: Path):
    """
    @spec.given a target repo (the py-mini fixture, no git, so the walk fallback runs)
    @spec.when  the orchestrator runs and emits the commodity structure section
    @spec.then  structure.md renders an ASCII tree of the repo skeleton (tree connectors,
                a fenced block) and excludes build/dep dirs, never crashing on a plain dir
    """
    cfg = detect.detect(FIXTURE_REPO, out=tmp_path)[0]
    assert orchestrator.run(cfg, check=False) == 0

    structure = (tmp_path / "structure.md").read_text(encoding="utf-8")
    assert structure.startswith("# Structure")
    assert "```" in structure
    assert "├── " in structure or "└── " in structure
    assert "__pycache__" not in structure  # default exclude set kept noise out


def test_structure_is_indexed_first_in_the_manifest(tmp_path: Path):
    """
    @spec.given a generated catalog
    @spec.when  the MANIFEST is rendered
    @spec.then  it lists structure.md under the read-first Map group, so a fresh session
                orients from the repo tree before anything else
    """
    cfg = detect.detect(FIXTURE_REPO, out=tmp_path)[0]
    orchestrator.run(cfg, check=False)

    manifest = (tmp_path / "MANIFEST.md").read_text(encoding="utf-8")
    assert "## Map" in manifest
    assert "structure.md" in manifest
    assert manifest.index("structure.md") < manifest.index("requirements.md")


def test_tree_helper_is_deterministic_and_lists_dirs_before_files():
    """
    @spec.given a flat list of repo-relative paths mixing directories and files
    @spec.when  the tree is built and rendered
    @spec.then  output is stable, nests by directory, and at each level directories come
                before files (so the snapshot reads like a `tree` command, not a flat dump)
    """
    paths = ["src/z.py", "src/sub/a.py", "README.md", "src/a.py"]
    lines = _render_tree_lines(_build_path_tree(paths))
    text = "\n".join(lines)

    # rendering is deterministic for the same input
    assert _render_tree_lines(_build_path_tree(paths)) == lines
    # root level: the src/ directory is listed before the README.md file
    assert text.index("src/") < text.index("README.md")
    # the nested directory and its file are present
    assert "sub/" in text and "a.py" in text


def test_tree_helper_handles_an_empty_repo():
    """
    @spec.given no paths at all (an empty or fully-ignored repo)
    @spec.when  the tree is built and rendered
    @spec.then  it yields an empty line list, never raising
    """
    assert _render_tree_lines(_build_path_tree([])) == []
