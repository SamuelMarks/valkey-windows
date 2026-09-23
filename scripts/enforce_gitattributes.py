#!/usr/bin/env python3
"""
Enforce line endings and encoding based on .gitattributes.

This script parses git attributes using `git check-attr` to verify and optionally
fix line endings (LF vs CRLF) and text file encodings (e.g. UTF-8 without BOM or
custom working-tree-encoding) across tracked files.
"""

import argparse
import os
import subprocess
import sys

CRLF = bytes([13, 10])
LF = bytes([10])
CR = bytes([13])
UTF8_BOM = bytes([0xEF, 0xBB, 0xBF])


def get_tracked_files():
    """
    Retrieve all tracked files in the current git repository.

    Returns:
        list[str]: A list of tracked file paths relative to repository root.
    """
    try:
        output = subprocess.check_output(["git", "ls-files"], text=True)
        return [f for f in output.splitlines() if f.strip()]
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []


def query_git_attributes(file_paths):
    """
    Query git attributes for a list of file paths.

    Args:
        file_paths (list[str]): List of relative file paths to check.

    Returns:
        dict[str, dict[str, str]]: Mapping from file path to attribute dictionary
                                   containing keys 'text', 'eol', and 'working-tree-encoding'.
    """
    attrs = {f: {"text": "unspecified", "eol": "unspecified", "working-tree-encoding": "unspecified"} for f in file_paths}
    if not file_paths:
        return attrs

    # Batch queries to avoid argument length limits
    batch_size = 500
    for i in range(0, len(file_paths), batch_size):
        batch = file_paths[i:i + batch_size]
        try:
            cmd = ["git", "check-attr", "text", "eol", "working-tree-encoding", "--"] + batch
            proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
            for line in proc.stdout.splitlines():
                parts = line.split(": ")
                if len(parts) == 3:
                    f_path, attr_name, attr_val = parts
                    if f_path in attrs:
                        attrs[f_path][attr_name] = attr_val
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    return attrs


def is_binary_content(raw_bytes):
    """
    Check if byte content appears to be binary by detecting NULL bytes.

    Args:
        raw_bytes (bytes): The raw file bytes to inspect.

    Returns:
        bool: True if binary content is detected, False otherwise.
    """
    return b"\x00" in raw_bytes


def normalize_line_endings(raw_bytes, target_eol):
    """
    Convert all line endings in raw_bytes to the target line ending.

    Args:
        raw_bytes (bytes): The raw bytes of the file.
        target_eol (str): Either 'crlf' or 'lf'.

    Returns:
        bytes: Converted bytes with normalized line endings.
    """
    # First normalize all line breaks (CRLF and CR) to LF
    content = raw_bytes.replace(CRLF, LF).replace(CR, LF)
    if target_eol == "crlf":
        return content.replace(LF, CRLF)
    return content


def inspect_and_fix_file(file_path, file_attrs, fix=False):
    """
    Inspect a single file for line ending and encoding compliance.

    Args:
        file_path (str): Path to the file.
        file_attrs (dict[str, str]): Git attributes for the file.
        fix (bool): If True, automatically modifies the file to fix violations.

    Returns:
        tuple[bool, list[str]]: (passed, issues) where passed is True if compliant,
                                and issues contains description strings of any issues.
    """
    if not os.path.isfile(file_path):
        return True, []

    with open(file_path, "rb") as f:
        raw_bytes = f.read()

    # Skip empty files
    if not raw_bytes:
        return True, []

    text_attr = file_attrs.get("text", "unspecified")
    eol_attr = file_attrs.get("eol", "unspecified")
    encoding_attr = file_attrs.get("working-tree-encoding", "unspecified")

    # If text is explicitly unset, treat as binary
    if text_attr == "unset":
        return True, []

    # If text is auto/unspecified, verify if it's binary
    if text_attr != "set" and is_binary_content(raw_bytes):
        return True, []

    issues = []
    modified_bytes = raw_bytes

    # 1. Encoding check
    expected_encoding = "utf-8" if encoding_attr == "unspecified" else encoding_attr.lower()

    # Check for UTF-8 Byte Order Mark (BOM) when using default UTF-8
    if expected_encoding == "utf-8" and modified_bytes.startswith(UTF8_BOM):
        issues.append("Unexpected UTF-8 BOM detected")
        if fix:
            modified_bytes = modified_bytes[len(UTF8_BOM):]

    try:
        modified_bytes.decode(expected_encoding)
    except (UnicodeDecodeError, LookupError) as e:
        issues.append(f"Encoding violation: cannot decode as {expected_encoding} ({e})")
        # Cannot fix unknown decoding issues automatically
        return False, issues

    # 2. Line ending check
    # Expected line ending determination:
    # Explicit eol=crlf -> CRLF
    # Explicit eol=lf -> LF
    # eol=unspecified and text in (set, auto) -> LF (default git repo normalization)
    target_eol = None
    if eol_attr == "crlf":
        target_eol = "crlf"
    elif eol_attr == "lf":
        target_eol = "lf"
    elif text_attr in ("set", "auto"):
        target_eol = "lf"

    if target_eol:
        crlf_count = modified_bytes.count(CRLF)
        total_lf = modified_bytes.count(LF)
        total_cr = modified_bytes.count(CR)
        bare_lf = total_lf - crlf_count
        bare_cr = total_cr - crlf_count

        if target_eol == "crlf":
            if bare_lf > 0 or bare_cr > 0:
                issues.append(f"Line ending violation: expected CRLF but found {bare_lf} bare LF / {bare_cr} bare CR")
                if fix:
                    modified_bytes = normalize_line_endings(modified_bytes, "crlf")
        elif target_eol == "lf":
            if crlf_count > 0 or bare_cr > 0:
                issues.append(f"Line ending violation: expected LF but found {crlf_count} CRLF / {bare_cr} bare CR")
                if fix:
                    modified_bytes = normalize_line_endings(modified_bytes, "lf")

    if fix and modified_bytes != raw_bytes:
        with open(file_path, "wb") as f:
            f.write(modified_bytes)
        return False, [f"Fixed: {', '.join(issues)}"]

    passed = len(issues) == 0
    return passed, issues


def main(argv=None):
    """
    Entry point for line endings and encoding verification.

    Args:
        argv (list[str], optional): Command line arguments. Defaults to sys.argv[1:].

    Returns:
        int: 0 if all files comply, 1 if any violations were found or fixed.
    """
    parser = argparse.ArgumentParser(
        description="Enforce line endings and encoding based on .gitattributes."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix line endings and strip invalid BOMs in-place.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check and report violations without modifying files (default).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print verbose output for all checked files.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Files to check. If omitted, all tracked files are checked.",
    )

    args = parser.parse_args(argv)
    files = args.files or get_tracked_files()

    if not files:
        if args.verbose:
            print("No files to inspect.")
        return 0

    attrs = query_git_attributes(files)
    total_violations = 0

    for file_path in files:
        file_attrs = attrs.get(file_path, {})
        passed, issues = inspect_and_fix_file(file_path, file_attrs, fix=args.fix)
        if not passed:
            total_violations += 1
            action = "FIXED" if args.fix else "ERROR"
            print(f"[{action}] {file_path}: {'; '.join(issues)}", file=sys.stderr)
        elif args.verbose:
            print(f"[OK] {file_path}")

    if total_violations > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
