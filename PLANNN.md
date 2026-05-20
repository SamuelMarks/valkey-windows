# Valkey Windows 9.1 Upgrade Plan

This document outlines the steps required to get Valkey 9.1 compiling, passing all tests natively on Windows MSVC, and released via `valkey-windows`.

## 1. Sync Dependency Updates
Recent fixes in our POSIX compatibility layer (`auto-win-msvc`) and our native Redis branch need to be consolidated:
- **`auto-win-msvc` Updates:** Commit and push the staged changes in `..\auto-win-msvc` (which fix the return types of `posix_read` and `posix_write` to `ssize_t`) up to the `master` branch.
- **Port Redis fixes to Valkey CMake:** The recent native Redis tests fix the `ctest` hang issue by replacing `taskkill` batch scripts with a newly authored C program (`win_kill.c`). This fix, along with missing source files (like `fast_float_strtod.c` or any added dependencies like `tre` if Valkey upstreamed them), needs to be ported into Valkey's `CMakeLists.txt`.

## 2. Prepare Valkey 9.1 Worktree
- Run `git clone --branch 9.1 https://github.com/valkey-io/valkey.git valkey` (or fetch and checkout the `9.1` tag if already cloned) to get the clean upstream codebase.

## 3. Update the Build Patch
- Apply our existing patch: `git apply ../patches/0001-Windows-native-builds.patch`
- Resolve any merge conflicts that may have arisen from upstream structural changes between the previous version and Valkey 9.1.
- Introduce the CMake `win_kill.c` generation step for the testing suite.
- Update CMake configuration to include any new files introduced in Valkey 9.1 that require MSVC integration.
- Generate a new patch: `git diff > ../build-repo/patches/0001-Windows-native-builds.patch`.

## 4. Test Locally
- Run `.\release.bat 9.1 --local-only` within the `valkey-windows` repository.
- Ensure that the E2E tests script finishes and that all C-level test runners (like `ctest`) execute cleanly without hanging. The `win_kill` fix and the `auto-win-msvc` signature updates should guarantee this.

## 5. Cut the Release
- Stage and commit the updated `0001-Windows-native-builds.patch` into the `valkey-windows` repository.
- Push the changes to `master`.
- Navigate to the **GitHub Actions** tab for `valkey-windows`.
- Trigger the `Build and Release Valkey Windows` workflow (`workflow_dispatch`) and provide `9.1` as the `valkey_ref` input.
- The CI will build natively against `auto-win-msvc`, bundle the `.msi` and `.zip` distributions, and officially publish the 9.1 tagged release.
