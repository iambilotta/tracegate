"""tracegate CLI — single entrypoint over the harvested generators.

    tracegate requirements --target <repo> [--out DIR] [--check]
    tracegate code-docs    --target <repo> [--out DIR] [--check]
    tracegate dora         [--repo OWNER/NAME] [--workflow NAME ...] [--out FILE]
    tracegate diff         BASE_FILE HEAD_FILE
    tracegate check-spec   FILE [FILE ...]

Phase 0: the generators were hardcoded to housetree's `apps/gest` layout. The
`--target` (repo root) plus `--app-subdir`, `--package-root`, `--label` flags
de-hardcode them. Defaults reproduce the housetree values so an un-flagged run on
that repo is byte-for-byte identical to the original scripts.

`--check` is the drift-gate: exit 2 if the generated docs differ from what is on
disk (CI gate), exit 0 if in sync.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:  # package or standalone
    from . import config as _config
    from . import generate_requirements as reqs
    from . import generate_code_docs as code_docs
    from . import generate_dora as dora
    from . import diff_requirements as diff
    from . import check_spec_javadoc as check_spec
except ImportError:  # standalone (sys.path points at this dir)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import config as _config  # type: ignore[no-redef]
    import generate_requirements as reqs  # type: ignore[no-redef]
    import generate_code_docs as code_docs  # type: ignore[no-redef]
    import generate_dora as dora  # type: ignore[no-redef]
    import diff_requirements as diff  # type: ignore[no-redef]
    import check_spec_javadoc as check_spec  # type: ignore[no-redef]


def _add_target_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--target", default=".", help="repo root to document (default: cwd)")
    p.add_argument("--app-subdir", default=_config.DEFAULT_APP_SUBDIR,
                   help="path under --target holding the source tree "
                        f"(default '{_config.DEFAULT_APP_SUBDIR}'; pass '.' for repo-root source)")
    p.add_argument("--package-root", default=_config.DEFAULT_PACKAGE_ROOT,
                   help="dotted base package the modules hang off "
                        f"(default '{_config.DEFAULT_PACKAGE_ROOT}')")
    p.add_argument("--label", default=None,
                   help="human label in doc titles (default: the app-subdir)")
    p.add_argument("--out", default=None, help="output dir for generated docs "
                                               "(default: <app>/_generated)")
    p.add_argument("--check", action="store_true",
                   help="drift gate: exit 2 if docs differ from disk, 0 if in sync")


def _cfg_from(args: argparse.Namespace) -> _config.Config:
    return _config.resolve(
        args.target, out=args.out, app_subdir=args.app_subdir,
        package_root=args.package_root, label=args.label,
    )


def cmd_requirements(args: argparse.Namespace) -> int:
    """Generate requirements.md + requirements-by-us.md (the bash wrapper's job,
    now config-driven). With --check, exit 2 on drift without writing."""
    cfg = _cfg_from(args)
    if not cfg.test_java.is_dir():
        print(f"no test source tree at: {cfg.test_java}", file=sys.stderr)
        return 64
    main_md = reqs.generate(cfg, by_us=False)
    by_us_md = reqs.generate(cfg, by_us=True)
    out_main = cfg.generated_dir / "requirements.md"
    out_byus = cfg.generated_dir / "requirements-by-us.md"

    if args.check:
        drift = False
        for path, content in ((out_main, main_md), (out_byus, by_us_md)):
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                print(f"out of date: {path}", file=sys.stderr)
                drift = True
        return 2 if drift else 0

    cfg.generated_dir.mkdir(parents=True, exist_ok=True)
    out_main.write_text(main_md, encoding="utf-8")
    out_byus.write_text(by_us_md, encoding="utf-8")
    print(f"wrote {out_main} ({len(main_md.splitlines())} lines)")
    print(f"wrote {out_byus} ({len(by_us_md.splitlines())} lines)")
    return 0


def cmd_code_docs(args: argparse.Namespace) -> int:
    """Generate the AS-IS code docs (http-endpoints, events, modules, schema, ...).
    Delegates to the harvested generate_code_docs after pointing its globals at
    the target via configure()."""
    cfg = _cfg_from(args)
    code_docs.configure(cfg)
    return code_docs.main(["--check"] if args.check else [])


def cmd_dora(args: argparse.Namespace) -> int:
    # generate_dora parses its own argv; forward the remaining args verbatim.
    sys.argv = ["tracegate-dora"] + args.dora_args
    return dora.main()


def cmd_diff(args: argparse.Namespace) -> int:
    return diff.main(["tracegate-diff", args.base, args.head])


def cmd_check_spec(args: argparse.Namespace) -> int:
    sys.argv = ["tracegate-check-spec"] + args.files
    return check_spec.main()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tracegate", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_req = sub.add_parser("requirements", help="tests-as-requirements catalog (+ by-US view)")
    _add_target_args(p_req)
    p_req.set_defaults(func=cmd_requirements)

    p_code = sub.add_parser("code-docs", help="AS-IS code documentation set")
    _add_target_args(p_code)
    p_code.set_defaults(func=cmd_code_docs)

    p_dora = sub.add_parser("dora", help="DORA metrics from GitHub Actions deploy history")
    p_dora.add_argument("dora_args", nargs=argparse.REMAINDER,
                        help="forwarded to the DORA generator (--repo, --workflow, --out, --label)")
    p_dora.set_defaults(func=cmd_dora)

    p_diff = sub.add_parser("diff", help="PR-comment diff between two requirements.md files")
    p_diff.add_argument("base")
    p_diff.add_argument("head")
    p_diff.set_defaults(func=cmd_diff)

    p_chk = sub.add_parser("check-spec", help="fail if a test file has @Test without @spec javadoc")
    p_chk.add_argument("files", nargs="+")
    p_chk.set_defaults(func=cmd_check_spec)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
