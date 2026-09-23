#!/usr/bin/env python3
"""
Pre-commit build and test runner for MSVC / Wine cross-compilation environments.

Provides multi-platform automation for building and testing Valkey Windows artifacts:
- Uses native MSVC toolchain if running on Windows.
- Uses Wine-based MSVC toolchain if running on non-Windows (POSIX/macOS/Linux).
- Gracefully skips if required toolchains are not available.
"""

import os
import shutil
import subprocess
import sys

# Strip git environment variables that are set by pre-commit hooks
for key in ["GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"]:
    if key in os.environ:
        del os.environ[key]


def is_tool(name):
    """
    Check if an executable tool is available in PATH.

    Args:
        name (str): The name or path of the executable.

    Returns:
        bool: True if available, False otherwise.
    """
    return shutil.which(name) is not None


def run_cmd(cmd, cwd=None, env=None, check=True):
    """
    Execute a subprocess command with logging and error handling.

    Args:
        cmd (list[str]): The command and arguments to execute.
        cwd (str, optional): Working directory for the subprocess.
        env (dict, optional): Environment variables mapping.
        check (bool): Whether to exit on non-zero process return code.

    Returns:
        subprocess.CompletedProcess: Result of the executed process.
    """
    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=cwd, env=env, text=True)
    except FileNotFoundError:
        print(f"Command not found: {cmd[0]}")
        if check:
            sys.exit(1)
        else:
            class DummyResult:
                """Stub result object when executable is missing."""
                returncode = 127
            return DummyResult()

    if check and result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}: {' '.join(cmd)}")
        sys.exit(result.returncode)
    return result


def has_native_msvc():
    """
    Check if the native MSVC compiler (cl.exe) is available on Windows.

    Returns:
        bool: True if on Windows and cl.exe is available, False otherwise.
    """
    return os.name == "nt" and is_tool("cl.exe")


def get_msvc_wine_env():
    """
    Detect and prepare the Wine MSVC environment on POSIX platforms.

    Returns:
        tuple[str, dict[str, str]] | None: Tuple of (msvc_path, env) or None if not found.
    """
    if os.name == "nt" or not is_tool("wine"):
        return None

    msvc_path = os.environ.get("MSVC_WINE_PATH") or os.environ.get("MSVC_2026_PATH")
    if not msvc_path:
        candidates = [
            os.path.expanduser("~/my_msvc"),
            os.path.expanduser("~/my_msvc/opt/msvc"),
            os.path.expanduser("~/my_msvc/VC/Tools/MSVC/14.51.36231"),
            "/opt/msvc",
            "/opt/msvc/VC/Tools/MSVC/14.51.36231",
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                msvc_path = candidate
                break

    if not msvc_path or not os.path.exists(msvc_path):
        return None

    # Check for binary path
    bin_x64 = os.path.join(msvc_path, "bin", "x64")
    if not os.path.exists(bin_x64):
        alt_bin = os.path.join(msvc_path, "opt", "msvc", "bin", "x64")
        if os.path.exists(alt_bin):
            msvc_path = os.path.join(msvc_path, "opt", "msvc")
            bin_x64 = alt_bin

    env = os.environ.copy()
    if os.path.exists(bin_x64):
        env["PATH"] = f"{bin_x64}:{env.get('PATH', '')}"

    env["WINEPREFIX"] = os.environ.get("WINEPREFIX", os.path.expanduser("~/.wine_cdd_c"))
    env["WINEDEBUG"] = os.environ.get("WINEDEBUG", "-all")
    env["WINEDLLOVERRIDES"] = os.environ.get("WINEDLLOVERRIDES", "mscoree,mshtml=")
    env["WINE_AUTO_INSTALL"] = "0"
    env["MVK_CONFIG_LOG_LEVEL"] = "0"

    # Start wineserver and initialize wineboot if available
    if is_tool("wineserver"):
        subprocess.run(["wineserver", "-p"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["wine", "wineboot"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return msvc_path, env


def find_cmake_source_dir():
    """
    Locate the root or tests CMake source directory.

    Returns:
        str | None: Directory containing CMakeLists.txt or None if not found.
    """
    if os.path.exists("CMakeLists.txt"):
        return "."
    if os.path.exists(os.path.join("tests", "CMakeLists.txt")):
        return "tests"
    return None


def run_build(toolchain=None):
    """
    Build the project with MSVC (native on Windows, Wine on POSIX).

    Args:
        toolchain (str, optional): Toolchain override name. Defaults to None.

    Returns:
        int: Exit status code (0 for success or graceful skip).
    """
    cmake_src = find_cmake_source_dir()
    if not cmake_src:
        print("No CMakeLists.txt found. Skipping build.")
        return 0

    if os.name == "nt":
        if not has_native_msvc():
            print("Native MSVC (cl.exe) not found on Windows. Skipping build.")
            return 0

        build_dir = "build_msvc"
        os.makedirs(build_dir, exist_ok=True)
        run_cmd([
            "cmake", "-S", cmake_src, "-B", build_dir,
            "-DCMAKE_BUILD_TYPE=Debug",
            "-DBUILD_TESTING=ON"
        ])
        run_cmd(["cmake", "--build", build_dir, "--config", "Debug"])
        return 0

    # Non-Windows POSIX platform: Build via Wine
    wine_info = get_msvc_wine_env()
    if not wine_info:
        print("Wine or MSVC Wine toolchain not found on this platform. Skipping build.")
        return 0

    msvc_path, env = wine_info
    build_dir = "build_msvc_wine"
    os.makedirs(build_dir, exist_ok=True)

    cmake_args = [
        "cmake", "-S", cmake_src, "-B", build_dir,
        "-DCMAKE_BUILD_TYPE=Debug",
        "-DCMAKE_SYSTEM_NAME=Windows",
        "-DCMAKE_C_COMPILER=cl",
        "-DCMAKE_MSVC_DEBUG_INFORMATION_FORMAT=Embedded",
        "-DCMAKE_CROSSCOMPILING_EMULATOR=wine",
        "-DBUILD_TESTING=ON",
        "-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebugDLL"
    ]
    if is_tool("cl"):
        cmake_args.extend(["-DCMAKE_CXX_COMPILER=cl"])

    run_cmd(cmake_args, env=env)
    run_cmd(["cmake", "--build", build_dir, "--config", "Debug"], env=env)
    return 0


def run_test(toolchain=None):
    """
    Execute tests using CTest (native MSVC on Windows, Wine on POSIX).

    Args:
        toolchain (str, optional): Toolchain override name. Defaults to None.

    Returns:
        int: Exit status code (0 for success or graceful skip).
    """
    if os.name == "nt":
        build_dir = "build_msvc"
        if not os.path.exists(build_dir):
            print(f"Build directory {build_dir} not found. Skipping test.")
            return 0

        run_cmd(["ctest", "-C", "Debug", "--output-on-failure"], cwd=build_dir)
        return 0

    # Non-Windows POSIX platform: Test via Wine
    build_dir = "build_msvc_wine"
    if not os.path.exists(build_dir):
        print(f"Build directory {build_dir} not found. Skipping test.")
        return 0

    wine_info = get_msvc_wine_env()
    if not wine_info:
        print("Wine or MSVC Wine toolchain not found on this platform. Skipping test.")
        return 0

    msvc_path, env = wine_info
    winepath_entries = [
        os.path.abspath(build_dir),
        os.path.abspath(os.path.join(build_dir, "tests")),
        os.path.abspath(os.path.join(build_dir, "bin")),
        os.path.abspath(os.path.join(build_dir, "bin", "Debug")),
        os.path.abspath(os.path.join(build_dir, "bin", "Release")),
        f"{msvc_path}/bin/x64",
    ]

    for root, dirs, files in os.walk(msvc_path):
        if "debug_nonredist" in root and "x64" in root:
            winepath_entries.append(root)
        elif "Windows Kits" in root and "x64" in root and "ucrt" in root:
            winepath_entries.append(root)

    env["WINEPATH"] = ";".join(winepath_entries)
    env["_NO_DEBUG_HEAP"] = "1"

    run_cmd(["ctest", "-C", "Debug", "--output-on-failure"], cwd=build_dir, env=env)
    return 0


def main():
    """
    Main CLI entry point for precommit build and test operations.

    Returns:
        int: Exit code of the requested action.
    """
    if len(sys.argv) < 2:
        print("Usage: python scripts/precommit_matrix.py [build|test] [toolchain]")
        sys.exit(1)

    job = sys.argv[1]
    toolchain = sys.argv[2] if len(sys.argv) > 2 else None

    if job == "build":
        sys.exit(run_build(toolchain))
    elif job == "test":
        sys.exit(run_test(toolchain))
    else:
        print(f"Unknown job: {job}. Supported jobs: build, test")
        sys.exit(1)


if __name__ == "__main__":
    main()
