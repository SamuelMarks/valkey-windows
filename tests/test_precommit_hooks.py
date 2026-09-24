#!/usr/bin/env python3
"""
Unit tests for pre-commit hooks and helper scripts.

Tests line ending and encoding verification per .gitattributes,
and multi-platform build and test matrix orchestration.
"""

import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Add scripts directory to path for import
SCRIPTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import enforce_gitattributes
import precommit_matrix
import build
import test

CRLF = bytes([13, 10])
LF = bytes([10])
CR = bytes([13])


class TestEnforceGitattributes(unittest.TestCase):
    """
    Test suite for enforce_gitattributes.py.
    """

    def test_is_binary_content(self):
        """
        Test binary content detection with NULL bytes.
        """
        self.assertFalse(enforce_gitattributes.is_binary_content(b"Hello world" + LF))
        self.assertTrue(enforce_gitattributes.is_binary_content(b"Hello\x00world" + LF))

    def test_normalize_line_endings_crlf(self):
        """
        Test normalizing to CRLF.
        """
        raw = b"line1" + LF + b"line2" + CRLF + b"line3" + CR + b"line4"
        normalized = enforce_gitattributes.normalize_line_endings(raw, "crlf")
        expected = b"line1" + CRLF + b"line2" + CRLF + b"line3" + CRLF + b"line4"
        self.assertEqual(normalized, expected)

    def test_normalize_line_endings_lf(self):
        """
        Test normalizing to LF.
        """
        raw = b"line1" + LF + b"line2" + CRLF + b"line3" + CR + b"line4"
        normalized = enforce_gitattributes.normalize_line_endings(raw, "lf")
        expected = b"line1" + LF + b"line2" + LF + b"line3" + LF + b"line4"
        self.assertEqual(normalized, expected)

    def test_inspect_and_fix_nonexistent_file(self):
        """
        Test handling of nonexistent files.
        """
        passed, issues = enforce_gitattributes.inspect_and_fix_file("nonexistent.xyz", {})
        self.assertTrue(passed)
        self.assertEqual(issues, [])

    def test_inspect_and_fix_empty_file(self):
        """
        Test handling of empty files.
        """
        with tempfile.NamedTemporaryFile() as tmp:
            passed, issues = enforce_gitattributes.inspect_and_fix_file(tmp.name, {"text": "set"})
            self.assertTrue(passed)
            self.assertEqual(issues, [])

    def test_inspect_and_fix_binary_file(self):
        """
        Test skipping binary files.
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"PNG\x00\x01\x02" + LF)
            tmp.flush()
            path = tmp.name

        try:
            passed, issues = enforce_gitattributes.inspect_and_fix_file(path, {"text": "auto"})
            self.assertTrue(passed)
            self.assertEqual(issues, [])

            passed, issues = enforce_gitattributes.inspect_and_fix_file(path, {"text": "unset"})
            self.assertTrue(passed)
            self.assertEqual(issues, [])
        finally:
            os.remove(path)

    def test_inspect_crlf_enforcement(self):
        """
        Test enforcing CRLF line endings.
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"@echo off" + CRLF + b"echo Hello" + CRLF)
            tmp.flush()
            path = tmp.name

        try:
            # Matches expected CRLF
            passed, issues = enforce_gitattributes.inspect_and_fix_file(path, {"text": "set", "eol": "crlf"})
            self.assertTrue(passed)
            self.assertEqual(issues, [])

            # Introduce LF violation
            with open(path, "wb") as f:
                f.write(b"@echo off" + LF + b"echo Hello" + CRLF)

            passed, issues = enforce_gitattributes.inspect_and_fix_file(path, {"text": "set", "eol": "crlf"}, fix=False)
            self.assertFalse(passed)
            self.assertTrue(any("expected CRLF" in issue for issue in issues))

            # Fix violation
            passed, issues = enforce_gitattributes.inspect_and_fix_file(path, {"text": "set", "eol": "crlf"}, fix=True)
            self.assertFalse(passed)  # returns False when modified in-place
            self.assertTrue(any("Fixed" in issue for issue in issues))

            # Verify it now passes
            passed, issues = enforce_gitattributes.inspect_and_fix_file(path, {"text": "set", "eol": "crlf"})
            self.assertTrue(passed)
        finally:
            os.remove(path)

    def test_inspect_lf_enforcement(self):
        """
        Test enforcing LF line endings.
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"patch header" + LF + b"--- a/file" + LF)
            tmp.flush()
            path = tmp.name

        try:
            # Matches expected LF
            passed, issues = enforce_gitattributes.inspect_and_fix_file(path, {"text": "set", "eol": "lf"})
            self.assertTrue(passed)
            self.assertEqual(issues, [])

            # Introduce CRLF violation
            with open(path, "wb") as f:
                f.write(b"patch header" + CRLF + b"--- a/file" + LF)

            passed, issues = enforce_gitattributes.inspect_and_fix_file(path, {"text": "set", "eol": "lf"}, fix=False)
            self.assertFalse(passed)
            self.assertTrue(any("expected LF" in issue for issue in issues))

            # Fix violation
            passed, issues = enforce_gitattributes.inspect_and_fix_file(path, {"text": "set", "eol": "lf"}, fix=True)
            self.assertFalse(passed)
            self.assertTrue(any("Fixed" in issue for issue in issues))

            # Verify it now passes
            passed, issues = enforce_gitattributes.inspect_and_fix_file(path, {"text": "set", "eol": "lf"})
            self.assertTrue(passed)
        finally:
            os.remove(path)

    def test_inspect_utf8_bom_removal(self):
        """
        Test detecting and fixing unwanted UTF-8 BOM.
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"\xef\xbb\xbfhello" + LF)
            tmp.flush()
            path = tmp.name

        try:
            passed, issues = enforce_gitattributes.inspect_and_fix_file(path, {"text": "set", "eol": "lf"}, fix=False)
            self.assertFalse(passed)
            self.assertTrue(any("BOM" in issue for issue in issues))

            # Fix BOM
            passed, issues = enforce_gitattributes.inspect_and_fix_file(path, {"text": "set", "eol": "lf"}, fix=True)
            self.assertFalse(passed)

            with open(path, "rb") as f:
                content = f.read()
            self.assertEqual(content, b"hello" + LF)
        finally:
            os.remove(path)

    def test_inspect_encoding_violation(self):
        """
        Test detection of non-decodable byte sequences.
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"\xff\xfe\xff" + LF)
            tmp.flush()
            path = tmp.name

        try:
            passed, issues = enforce_gitattributes.inspect_and_fix_file(path, {"text": "set", "eol": "lf"}, fix=False)
            self.assertFalse(passed)
            self.assertTrue(any("Encoding violation" in issue for issue in issues))
        finally:
            os.remove(path)

    @patch("subprocess.check_output")
    def test_get_tracked_files(self, mock_check_output):
        """
        Test get_tracked_files retrieves file lists properly.
        """
        mock_check_output.return_value = chr(10).join(["file1.txt", "file2.bat", ""])
        files = enforce_gitattributes.get_tracked_files()
        self.assertEqual(files, ["file1.txt", "file2.bat"])

        mock_check_output.side_effect = subprocess.CalledProcessError(1, "git")
        self.assertEqual(enforce_gitattributes.get_tracked_files(), [])

    @patch("subprocess.run")
    def test_query_git_attributes(self, mock_run):
        """
        Test batch querying of git attributes.
        """
        self.assertEqual(enforce_gitattributes.query_git_attributes([]), {})

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=chr(10).join([
                "f1.bat: text: set",
                "f1.bat: eol: crlf",
                "f1.bat: working-tree-encoding: unspecified",
                ""
            ])
        )
        attrs = enforce_gitattributes.query_git_attributes(["f1.bat"])
        self.assertEqual(attrs["f1.bat"]["text"], "set")
        self.assertEqual(attrs["f1.bat"]["eol"], "crlf")
        self.assertEqual(attrs["f1.bat"]["working-tree-encoding"], "unspecified")

        mock_run.side_effect = subprocess.CalledProcessError(1, "git")
        attrs_err = enforce_gitattributes.query_git_attributes(["f1.bat"])
        self.assertIn("f1.bat", attrs_err)

    def test_main_cli(self):
        """
        Test CLI execution of enforce_gitattributes.py.
        """
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"echo Hello" + CRLF)
            tmp.flush()
            path = tmp.name

        try:
            with patch("enforce_gitattributes.query_git_attributes") as mock_query:
                mock_query.return_value = {path: {"text": "set", "eol": "crlf"}}
                rc = enforce_gitattributes.main(["--verbose", path])
                self.assertEqual(rc, 0)

                mock_query.return_value = {path: {"text": "set", "eol": "lf"}}
                rc = enforce_gitattributes.main(["--check", path])
                self.assertEqual(rc, 1)

                rc = enforce_gitattributes.main(["--fix", path])
                self.assertEqual(rc, 1)

                rc = enforce_gitattributes.main(["--check", path])
                self.assertEqual(rc, 0)

            with patch("enforce_gitattributes.get_tracked_files", return_value=[]):
                rc = enforce_gitattributes.main(["--verbose"])
                self.assertEqual(rc, 0)
        finally:
            os.remove(path)


class TestPrecommitMatrix(unittest.TestCase):
    """
    Test suite for precommit_matrix.py, build.py, and test.py.
    """

    def test_is_tool(self):
        """
        Test tool detection utility.
        """
        self.assertTrue(precommit_matrix.is_tool("python") or precommit_matrix.is_tool("python3"))
        self.assertFalse(precommit_matrix.is_tool("nonexistent_tool_12345"))

    @patch("subprocess.run")
    def test_run_cmd_success(self, mock_run):
        """
        Test successful command execution.
        """
        mock_run.return_value = MagicMock(returncode=0)
        result = precommit_matrix.run_cmd(["echo", "hello"])
        self.assertEqual(result.returncode, 0)

    @patch("subprocess.run")
    def test_run_cmd_failure(self, mock_run):
        """
        Test failed command execution exits process when check=True.
        """
        mock_run.return_value = MagicMock(returncode=1)
        with self.assertRaises(SystemExit) as cm:
            precommit_matrix.run_cmd(["false"], check=True)
        self.assertEqual(cm.exception.code, 1)

    @patch("subprocess.run", side_effect=FileNotFoundError)
    def test_run_cmd_not_found(self, mock_run):
        """
        Test handling missing executable.
        """
        with self.assertRaises(SystemExit):
            precommit_matrix.run_cmd(["nonexistent_cmd"], check=True)

        res = precommit_matrix.run_cmd(["nonexistent_cmd"], check=False)
        self.assertEqual(res.returncode, 127)

    def test_find_cmake_source_dir(self):
        """
        Test locating CMakeLists.txt.
        """
        src_dir = precommit_matrix.find_cmake_source_dir()
        self.assertIn(src_dir, [".", "tests"])

        with patch("os.path.exists", return_value=False):
            self.assertIsNone(precommit_matrix.find_cmake_source_dir())

    @patch("os.name", "nt")
    @patch("precommit_matrix.is_tool", return_value=True)
    def test_has_native_msvc(self, mock_is_tool):
        """
        Test native MSVC detection on Windows.
        """
        self.assertTrue(precommit_matrix.has_native_msvc())

    @patch("os.name", "posix")
    def test_get_msvc_wine_env_none(self):
        """
        Test get_msvc_wine_env returns None when wine is missing.
        """
        with patch("precommit_matrix.is_tool", return_value=False):
            self.assertIsNone(precommit_matrix.get_msvc_wine_env())

    @patch("os.name", "posix")
    @patch("precommit_matrix.is_tool", return_value=True)
    def test_get_msvc_wine_env_detection(self, mock_is_tool):
        """
        Test get_msvc_wine_env successfully returns path and environment.
        """
        with tempfile.TemporaryDirectory() as td:
            bin_dir = os.path.join(td, "bin", "x64")
            os.makedirs(bin_dir)
            with patch.dict(os.environ, {"MSVC_WINE_PATH": td}):
                result = precommit_matrix.get_msvc_wine_env()
                self.assertIsNotNone(result)
                msvc_path, env = result
                self.assertEqual(msvc_path, td)
                self.assertIn(bin_dir, env["PATH"])

    @patch("os.name", "nt")
    @patch("precommit_matrix.find_cmake_source_dir", return_value=None)
    def test_run_build_no_cmake(self, mock_find):
        """
        Test run_build handles missing CMakeLists.txt.
        """
        rc = precommit_matrix.run_build()
        self.assertEqual(rc, 0)

    @patch("os.name", "nt")
    @patch("precommit_matrix.find_cmake_source_dir", return_value=".")
    @patch("precommit_matrix.has_native_msvc", return_value=False)
    def test_run_build_windows_missing_msvc(self, mock_has_msvc, mock_find):
        """
        Test skipping build on Windows when MSVC is not installed.
        """
        rc = precommit_matrix.run_build()
        self.assertEqual(rc, 0)

    @patch("os.name", "nt")
    @patch("precommit_matrix.find_cmake_source_dir", return_value=".")
    @patch("precommit_matrix.has_native_msvc", return_value=True)
    @patch("precommit_matrix.run_cmd")
    def test_run_build_windows_success(self, mock_run_cmd, mock_has_msvc, mock_find):
        """
        Test successful build on Windows with MSVC.
        """
        rc = precommit_matrix.run_build()
        self.assertEqual(rc, 0)
        self.assertEqual(mock_run_cmd.call_count, 2)

    @patch("os.name", "posix")
    @patch("precommit_matrix.find_cmake_source_dir", return_value=".")
    @patch("precommit_matrix.get_msvc_wine_env", return_value=None)
    def test_run_build_posix_missing_wine(self, mock_wine, mock_find):
        """
        Test skipping build on POSIX when Wine MSVC is not available.
        """
        rc = precommit_matrix.run_build()
        self.assertEqual(rc, 0)

    @patch("os.name", "posix")
    @patch("precommit_matrix.find_cmake_source_dir", return_value=".")
    @patch("precommit_matrix.get_msvc_wine_env", return_value=("/mock/msvc", {"PATH": ""}))
    @patch("precommit_matrix.run_cmd")
    def test_run_build_posix_wine_success(self, mock_run_cmd, mock_wine, mock_find):
        """
        Test successful build on POSIX with Wine MSVC.
        """
        rc = precommit_matrix.run_build()
        self.assertEqual(rc, 0)
        self.assertEqual(mock_run_cmd.call_count, 2)

    @patch("os.name", "nt")
    @patch("os.path.exists", return_value=False)
    def test_run_test_windows_missing_build_dir(self, mock_exists):
        """
        Test skipping test on Windows when build directory does not exist.
        """
        rc = precommit_matrix.run_test()
        self.assertEqual(rc, 0)

    @patch("os.name", "nt")
    @patch("os.path.exists", return_value=True)
    @patch("precommit_matrix.run_cmd")
    def test_run_test_windows_success(self, mock_run_cmd, mock_exists):
        """
        Test running ctest on Windows.
        """
        rc = precommit_matrix.run_test()
        self.assertEqual(rc, 0)
        mock_run_cmd.assert_called_once()

    @patch("os.name", "posix")
    @patch("os.path.exists", return_value=False)
    def test_run_test_posix_missing_build_dir(self, mock_exists):
        """
        Test skipping test on POSIX when build directory does not exist.
        """
        rc = precommit_matrix.run_test()
        self.assertEqual(rc, 0)

    @patch("os.name", "posix")
    @patch("os.path.exists", return_value=True)
    @patch("precommit_matrix.get_msvc_wine_env", return_value=None)
    def test_run_test_posix_missing_wine(self, mock_wine, mock_exists):
        """
        Test skipping test on POSIX when Wine is not found.
        """
        rc = precommit_matrix.run_test()
        self.assertEqual(rc, 0)

    @patch("os.name", "posix")
    @patch("os.path.exists", return_value=True)
    @patch("precommit_matrix.get_msvc_wine_env", return_value=("/mock/msvc", {}))
    @patch("precommit_matrix.run_cmd")
    def test_run_test_posix_wine_success(self, mock_run_cmd, mock_wine, mock_exists):
        """
        Test running ctest under Wine on POSIX.
        """
        rc = precommit_matrix.run_test()
        self.assertEqual(rc, 0)
        mock_run_cmd.assert_called_once()

    @patch("build.run_build", return_value=0)
    def test_build_script_entry(self, mock_build):
        """
        Test scripts/build.py entry point.
        """
        with patch.object(sys, "argv", ["build.py"]):
            rc = build.main()
            self.assertEqual(rc, 0)
            mock_build.assert_called_once_with(None)

    @patch("test.run_test", return_value=0)
    def test_test_script_entry(self, mock_test):
        """
        Test scripts/test.py entry point.
        """
        with patch.object(sys, "argv", ["test.py"]):
            rc = test.main()
            self.assertEqual(rc, 0)
            mock_test.assert_called_once_with(None)

    @patch("precommit_matrix.run_build", return_value=0)
    @patch("precommit_matrix.run_test", return_value=0)
    def test_precommit_matrix_cli(self, mock_test, mock_build):
        """
        Test CLI arguments handling in precommit_matrix.py.
        """
        with patch.object(sys, "argv", ["precommit_matrix.py"]):
            with self.assertRaises(SystemExit) as cm:
                precommit_matrix.main()
            self.assertEqual(cm.exception.code, 1)

        with patch.object(sys, "argv", ["precommit_matrix.py", "build"]):
            with self.assertRaises(SystemExit) as cm:
                precommit_matrix.main()
            self.assertEqual(cm.exception.code, 0)

        with patch.object(sys, "argv", ["precommit_matrix.py", "test"]):
            with self.assertRaises(SystemExit) as cm:
                precommit_matrix.main()
            self.assertEqual(cm.exception.code, 0)

        with patch.object(sys, "argv", ["precommit_matrix.py", "invalid_job"]):
            with self.assertRaises(SystemExit) as cm:
                precommit_matrix.main()
            self.assertEqual(cm.exception.code, 1)


class TestPackagingConfigs(unittest.TestCase):
    """
    Test suite for CPack configuration files and packaging patch integrity.
    """

    def test_cpack_cmake_syntax(self):
        """
        Verify that CPackConfig.cmake and CPackSourceConfig.cmake are syntactically valid CMake code.
        """
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        for cfg_name in ["CPackConfig.cmake", "CPackSourceConfig.cmake"]:
            cfg_path = os.path.join(repo_root, cfg_name)
            if os.path.exists(cfg_path):
                proc = subprocess.run(
                    ["cmake", "-P", cfg_path],
                    capture_output=True,
                    text=True
                )
                self.assertEqual(
                    proc.returncode, 0,
                    f"Syntax error in {cfg_name}:\n{proc.stderr}"
                )

    def test_patch_cpack_escaping(self):
        """
        Verify that patches/0001-Windows-native-builds.patch uses correct CMake escaping
        for CPACK_NSIS_EXTRA_* commands to avoid invalid escape characters in generated CPackConfig.cmake.
        """
        patch_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "patches", "0001-Windows-native-builds.patch")
        )
        self.assertTrue(os.path.isfile(patch_path))

        with open(patch_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Ensure problematic unescaped characters are not present in the patch
        self.assertNotIn(
            r"""$\"$INSTDIR\bin\valkey-service.exe$\"""",
            content,
            "Found invalid NSIS command string in patch file"
        )
        # Ensure proper escaping exists in the patch
        self.assertIn(
            "\\\\\\\\bin\\\\\\\\valkey-service.exe",
            content,
            "Patch must contain quadrupled backslashes for NSIS path in CMake string"
        )
        self.assertIn(
            "\\\\\\\"",
            content,
            "Patch must contain escaped quotes for NSIS command in CMake string"
        )


if __name__ == "__main__":
    unittest.main()
