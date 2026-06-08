#!/usr/bin/env bash
# Drift-gate wrapper over the tracegate requirements generator.
#
# Scans the target's test tree for JUnit @Test methods, extracts the spec from their
# structured javadoc, and emits <app>/_generated/requirements.md (+ requirements-by-us.md)
# grouped by module + category. Single source of truth: the test code itself.
#
# Categories from class-name suffix (lock):
#   *Test.java          -> FR   (functional requirement, default)
#   *NfrTest.java       -> NFR  (non-functional: perf / sec / observability)
#   *InvariantTest.java -> INV  (domain invariant)
#   *ContractTest.java  -> CON  (HTTP-boundary contract)
#
# Each @Test method should carry @spec.given / @spec.when / @spec.then javadoc
# (optional @spec.adr, @spec.us). Undocumented tests still appear, tagged "(spec missing)".
#
# Phase 0: de-hardcoded. The target repo + layout come from env or args; defaults
# reproduce the historical housetree `apps/gest` layout.
#
# Usage:
#   TG_TARGET=/path/to/repo bin/generate-requirements.sh            # writes the docs
#   TG_TARGET=/path/to/repo bin/generate-requirements.sh --check    # exit 2 on drift
# Extra flags after --check/none are forwarded (e.g. --app-subdir . --package-root com.acme).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${TG_TARGET:-${CLAUDE_PROJECT_DIR:-$(pwd)}}"

CHECK=""
if [ "${1:-}" = "--check" ]; then
  CHECK="--check"
  shift
fi

exec python3 -m tracegate requirements --target "$TARGET" $CHECK "$@"
