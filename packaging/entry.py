"""Binary entry point for the Nuitka build.

A flat module (not a package `__main__`) so Nuitka's onefile build has an unambiguous
top-level script that imports the installed `tracegate` package.
"""
import sys

from tracegate.cli import main

if __name__ == "__main__":
    sys.exit(main())
