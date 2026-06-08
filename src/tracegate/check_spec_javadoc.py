#!/usr/bin/env python3
"""Pre-commit hook: every @Test method in the given files must carry complete spec javadoc
(@spec.given + @spec.when + @spec.then). Each test IS a requirement; an undocumented test
shows up as "(spec missing)" in the generated catalog and this hook keeps that from landing.

Called by the pre-commit framework with staged filenames as argv (see
.pre-commit-config.yaml). Exit 0 = all documented, exit 1 = violations listed on stdout.

The matching is deliberately the same crude-but-aligned heuristic the requirements
generator uses; the build-time backstop (SpecJavadocBackstopTest) is the precise gate.
"""
import re
import sys


def file_has_undocumented_test(path: str) -> bool:
    text = open(path, encoding="utf-8", errors="replace").read()
    for m in re.finditer(r"\bvoid\s+(\w+)\s*\(", text):
        chunk = text[max(0, m.start() - 2000):m.start()]
        if not re.search(r"@Test\b", chunk):
            continue
        if not re.search(r"@Test\b[\s\S]{0,200}\Z", chunk):
            continue
        doc_matches = list(re.finditer(r"/\*\*([\s\S]*?)\*/", chunk))
        if not doc_matches:
            return True
        body = doc_matches[-1].group(1)
        if not (re.search(r"@spec\.given\b", body)
                and re.search(r"@spec\.when\b", body)
                and re.search(r"@spec\.then\b", body)):
            return True
    return False


def main() -> int:
    missing = [f for f in sys.argv[1:] if file_has_undocumented_test(f)]
    if not missing:
        return 0
    print("The following test files have at least one @Test method without complete")
    print("spec javadoc (@spec.given / @spec.when / @spec.then):")
    for f in missing:
        print(f"  - {f}")
    print()
    print("Each test = one requirement. Add the spec javadoc so it appears with content")
    print("in apps/gest/_generated/requirements.md instead of '(spec missing)'.")
    print("Emergency bypass: SKIP=spec-javadoc-check git commit ...")
    return 1


if __name__ == "__main__":
    sys.exit(main())
