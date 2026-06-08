"""tracegate CLI.

Zero-config is the headline path:

    tracegate [DIR]            auto-detect stack -> requirements + as-built catalog
    tracegate [DIR] --check    CI drift-gate: exit 2 if generated docs differ from disk
    tracegate [DIR] --json     print the machine catalog to stdout (no files written)

Explicit subcommands stay for power users and back-compat:

    tracegate requirements --target <repo> [--out DIR] [--check]
    tracegate code-docs    --target <repo> [--out DIR] [--check]
    tracegate dora         [--repo OWNER/NAME] ...
    tracegate diff         BASE_FILE HEAD_FILE
    tracegate check-spec   FILE [FILE ...]

The drift-gate (`--check`) is the product: exit 2 on drift (CI fails), 0 in sync.
Auto-detection (manifests/markers) chooses the language + framework adapters; a
`tracegate.toml` at the target root only overrides (ADR-0004).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import check_spec_javadoc as check_spec
from . import config as _config
from . import diff_requirements as diff
from . import generate_code_docs as code_docs
from . import generate_dora as dora
from . import generate_requirements as reqs
from .core import detect, orchestrator
from .core import render as core_render


# --- zero-config default path -------------------------------------------

def cmd_auto(args: argparse.Namespace) -> int:
    """`tracegate [DIR]`: detect the stack and generate (or gate) the catalog for
    every detected app. The DX headline: no flags, value at the first run."""
    target = Path(args.dir).resolve()
    if not target.is_dir():
        print(f"not a directory: {target}", file=sys.stderr)
        return 64
    out = Path(args.out).resolve() if args.out else None
    configs = detect.detect(target, out=out)

    if args.json:
        # machine view to stdout: union of every app's catalog (no files written)
        import json
        apps = []
        for cfg in configs:
            cat = orchestrator.build_catalog(cfg)
            apps.append(json.loads(core_render.requirements_json(cat)))
        print(json.dumps({"tracegate": {"schema": 1, "kind": "multi-app"}, "apps": apps},
                         indent=2, ensure_ascii=False))
        return 0

    worst = 0
    for cfg in configs:
        adapters = ", ".join(cfg.languages + cfg.frameworks) or "none"
        print(f"[{cfg.label}] adapters: {adapters}", file=sys.stderr)
        rc = orchestrator.run(cfg, check=args.check)
        worst = max(worst, rc)
    return worst


# --- explicit subcommands (back-compat / power users) -------------------

def _add_target_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--target", default=".", help="repo root to document (default: cwd)")
    p.add_argument("--app-subdir", default=_config.DEFAULT_APP_SUBDIR,
                   help="path under --target holding the source tree "
                        f"(default '{_config.DEFAULT_APP_SUBDIR}'; pass '.' for repo-root source)")
    p.add_argument("--package-root", default=_config.DEFAULT_PACKAGE_ROOT,
                   help="dotted base package the modules hang off "
                        f"(default '{_config.DEFAULT_PACKAGE_ROOT}')")
    p.add_argument("--label", default=None, help="human label in doc titles (default: the app-subdir)")
    p.add_argument("--out", default=None, help="output dir for generated docs (default: <app>/_generated)")
    p.add_argument("--check", action="store_true",
                   help="drift gate: exit 2 if docs differ from disk, 0 if in sync")


def _cfg_from(args: argparse.Namespace) -> _config.Config:
    return _config.resolve(
        args.target, out=args.out, app_subdir=args.app_subdir,
        package_root=args.package_root, label=args.label,
    )


def cmd_requirements(args: argparse.Namespace) -> int:
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
    cfg = _cfg_from(args)
    return code_docs.main(cfg, ["--check"] if args.check else [])


def cmd_dora(args: argparse.Namespace) -> int:
    sys.argv = ["tracegate-dora"] + args.dora_args
    return dora.main()


def cmd_diff(args: argparse.Namespace) -> int:
    return diff.main(["tracegate-diff", args.base, args.head])


def cmd_check_spec(args: argparse.Namespace) -> int:
    sys.argv = ["tracegate-check-spec"] + args.files
    return check_spec.main()


SUBCOMMANDS = ("requirements", "code-docs", "dora", "diff", "check-spec", "auto")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tracegate", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command")

    # zero-config path, also reachable explicitly as `tracegate auto DIR`
    p_auto = sub.add_parser("auto", help="zero-config: detect stack + generate/gate the catalog")
    p_auto.add_argument("dir", nargs="?", default=".",
                        help="target repo to document (default: cwd)")
    p_auto.add_argument("--check", action="store_true",
                        help="drift-gate: exit 2 if generated docs differ from disk")
    p_auto.add_argument("--json", action="store_true",
                        help="print the machine catalog to stdout (no files written)")
    p_auto.add_argument("--out", default=None,
                        help="output dir for generated docs (default: <app>/_generated)")
    p_auto.set_defaults(func=cmd_auto)

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
    raw = list(sys.argv[1:] if argv is None else argv)
    # Zero-config DX: `tracegate`, `tracegate DIR`, `tracegate DIR --check` with no
    # subcommand default to `auto`. If the first non-flag token is a known subcommand,
    # dispatch normally.
    first = next((a for a in raw if not a.startswith("-")), None)
    if first not in SUBCOMMANDS:
        raw = ["auto", *raw]
    args = parser.parse_args(raw)
    if getattr(args, "func", None) is None:
        parser.print_help()
        return 64
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
