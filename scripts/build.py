#!/usr/bin/env python3
"""
Build entry point for MSVC (Windows native) or Wine (POSIX cross-compilation).
"""

import sys
from precommit_matrix import run_build


def main():
    """
    Main entry point to execute build.

    Returns:
        int: Exit status code.
    """
    toolchain = sys.argv[1] if len(sys.argv) > 1 else None
    return run_build(toolchain)


if __name__ == "__main__":
    sys.exit(main())
