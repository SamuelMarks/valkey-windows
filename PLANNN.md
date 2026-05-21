# Valkey Windows 9.1 Migration & Release Plan

This document outlines the end-to-end plan to upgrade the `valkey-windows` repository to support the newly released Valkey `9.1` tag, ensuring all tests pass natively under MSVC, and culminating in a new public release.

## Phase 1: Synchronization & Dependencies

1. **Update `auto-win-msvc`**:
   - Ensure all recent changes (such as fixing return types for `posix_read`/`posix_write` and any other POSIX mapping additions) in your local `..\auto-win-msvc` repo are committed and pushed to `master`.
   - The `valkey-windows` build scripts pull from the `master` branch of `auto-win-msvc`, so this must be upstreamed first.
2. **Review Native Redis Fixes**:
   - Analyze the `..\redis` repository to identify how the full test suite was fixed for MSVC.
   - Specifically note the `win_kill.c` utility (which prevents `ctest` hangs by replacing the `taskkill` batch scripts) and any new missing source files added to CMake (like `fast_float_strtod.c` or `tre` regex library).

## Phase 2: Codebase Preparation & Patch Migration

1. **Checkout Valkey 9.1**:
   - Inside `valkey-windows`, prepare the codebase for patching:
     ```cmd
     git clone --branch 9.1 https://github.com/valkey-io/valkey.git valkey
     ```
2. **Rebase and Apply Patches**:
   - Attempt to apply the current MSVC build patch:
     ```cmd
     cd valkey
     git apply ..\patches\0001-Windows-native-builds.patch
     git apply ..\patches\0001-Fix-python-execution-for-Windows.patch
     ```
   - Resolve any merge conflicts or patching errors that arise due to structural changes between the previous version and 9.1.
3. **Port Redis CMake Fixes to Valkey**:
   - Modify `valkey\CMakeLists.txt` to include the `win_kill.c` target generation for test teardown.
   - Inject any new compilation units into the `CMakeLists.txt` that were added in Valkey 9.1 but require our MSVC/`auto-win-msvc` scaffolding.
4. **Save Updated Patches**:
   - Once the Valkey tree is successfully patched and configured, generate the updated patch file(s) and overwrite the old ones in the `patches\` directory.
     ```cmd
     git diff > ..\patches\0001-Windows-native-builds.patch
     ```

## Phase 3: Compilation & Native Full Test Suite

1. **Compile Natively**:
   - Generate the MSVC project and compile:
     ```cmd
     cmake -S . -B build_msvc -G "Visual Studio 17 2022" -A x64
     cmake --build build_msvc --config Release
     ```
   - Fix any new C/C++ compilation warnings or POSIX polyfill errors that arise due to new 9.1 code.
2. **Execute Full Test Suite**:
   - Run the full C-level tests (`ctest`) and the TCL/Python test suites directly on Windows.
   - Debug and fix any runtime failures, particularly looking out for socket lifecycle bugs, pathing issues in tests, or test harness hangs. Apply the fixes from `..\redis` where identical patterns occur.

## Phase 4: Local Packaging & E2E Verification

1. **Run Local Build Script**:
   - Execute the `valkey-windows` automated build script in local-only mode to verify the entire pipeline (cloning, patching, configuring CPack, building, E2E testing):
     ```cmd
     .\release.bat 9.1 --local-only
     ```
   - Ensure the basic E2E tests (`PING`, `SET`, `GET`, etc.) pass successfully and that the `.msi` and `.zip` files are correctly generated in the build directory.

## Phase 5: CI/CD & Final Release

1. **Commit `valkey-windows` Changes**:
   - Stage and commit the updated `patches\0001-Windows-native-builds.patch` (and any other modified packaging configs or release scripts) to the `valkey-windows` repository.
   - Push these changes to `master`.
2. **Trigger GitHub Release Workflow**:
   - Navigate to the **Actions** tab of the `valkey-windows` repository.
   - Manually trigger the `Build and Release Valkey Windows` workflow.
   - Provide `9.1` as the `valkey_ref` input.
3. **Verify Release Artifacts**:
   - Confirm that the GitHub Action completes successfully.
   - Verify that the `9.1` tag was created and that the Release page contains the `Valkey-*.msi` and `Valkey-*.zip` native Windows binaries.