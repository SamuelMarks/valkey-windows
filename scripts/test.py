#!/usr/bin/env python3
"""
Test entry point for MSVC (Windows native) or Wine (POSIX cross-compilation).
"""

import sys
from precommit_matrix import run_test


def main():
    """
    Main entry point to execute CTest suite.

    Returns:
        int: Exit status code.
    """
    toolchain = sys.argv[1] if len(sys.argv) > 1 else None
    return run_test(toolchain)


if __name__ == "__main__":
    sys.exit(main())
