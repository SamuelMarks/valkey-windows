# Valkey Windows Native Builds

This repository serves the mission of providing **native, performant Windows builds** of [Valkey](https://github.com/valkey-io/valkey) using the Microsoft Visual C++ (MSVC) toolchain.

Valkey is a high-performance, open-source key-value store. Historically, running software in this ecosystem on Windows required virtualization (like WSL2), heavy emulation layers (like Cygwin/MSYS2), or maintaining massive, deeply invasive forks. Following the rejection of native Windows support in upstream Valkey ([PR #3427](https://github.com/valkey-io/valkey/pull/3427)), our mission is to provide true native Windows binaries without compromising the maintainability of the upstream codebase.

## The Magic: `auto-win-msvc`

To achieve minimal friction and high compatibility, `valkey-windows` makes extensive use of **[auto-win-msvc](https://github.com/SamuelMarks/auto-win-msvc)**.

`auto-win-msvc` is a modular, lightweight POSIX compatibility layer for Windows. Instead of rewriting Valkey's deeply-integrated Linux/POSIX networking and system calls, our custom CMake patches instruct the MSVC compiler to map standard POSIX headers (like `<sys/socket.h>` or `<pthread.h>`) directly to Windows-native implementations provided by `auto-win-msvc`.

By decoupling the Windows compatibility layer from the Valkey codebase itself, we ensure:
- **Maintainability:** We avoid touching upstream `.c` or `.h` files. Our patch strictly modifies the `CMakeLists.txt` build scripts to inject `auto-win-msvc`.
- **Performance:** No heavy emulation overhead or `<windows.h>` namespace pollution.
- **Sustainability:** Future Valkey updates can be merged and built effortlessly with minimal breakage.

## Releases

Automatically compiled versions are available in the [Releases](../../releases) tab.

### Included Packages:
- **ZIP Archive:** Portable binaries (`valkey-server.exe`, `valkey-cli.exe`) ready to run standalone.
- **MSI Installer:** A fully-featured Windows installer that not only installs Valkey but automatically registers it as a background Windows Service (via [WinSW](https://github.com/winsw/winsw)). This ensures Valkey starts automatically on boot and runs cleanly in the background.

## How It Works

Our fully automated CI/CD pipeline runs every week to check for new upstream Valkey releases. When a new version drops, GitHub Actions springs into action:

1. **Source Synchronization:** Clones the targeted source branch from the official `valkey-io/valkey` repository.
2. **POSIX Polyfilling:** Pulls down the `auto-win-msvc` POSIX compatibility layer.
3. **Patch Application:** Applies our native Windows patch (`patches/0001-Windows-native-builds.patch`). Crucially, this patch purely targets CMake files to configure MSVC and integrate the compatibility layer.
4. **Compilation:** Compiles all Valkey components natively via MSVC.
5. **Packaging:** Packages the compiled artifacts using CPack with the WiX Generator (for the `.msi` installer) and ZIP (for the portable archive).

## Building Locally

If you want to build Valkey for Windows from source yourself, ensure you have **Visual Studio** (with C++ CMake tools for Windows) installed.

1. Clone Valkey, `auto-win-msvc`, and this build repository side-by-side:
   ```cmd
   git clone https://github.com/valkey-io/valkey.git
   git clone https://github.com/SamuelMarks/auto-win-msvc.git
   git clone https://github.com/valkey-windows/valkey-windows.git build-repo
   ```
2. Navigate into `valkey` and apply the build patch:
   ```cmd
   cd valkey
   git apply ../build-repo/patches/0001-Windows-native-builds.patch
   ```
3. Generate the MSVC project using CMake:
   ```cmd
   cmake -S . -B build -G "Visual Studio 18 2026" -A x64
   ```
4. Build the Release binaries:
   ```cmd
   cmake --build build --config Release
   ```

Your freshly built binaries will be located inside the `build/Release` folder!

### Using the Automated Release Script

For convenience, we provide a complete, automated build and test script (`release.bat`). This script fetches a specific Valkey version, configures the Windows build, compiles it, runs End-to-End (E2E) tests, and optionally tags and publishes the release to GitHub.

**Prerequisites:**
- Visual Studio (with C++ CMake tools for Windows)
- `git` available in your PATH
- [GitHub CLI (`gh`)](https://cli.github.com/) (required only if pushing a release)

**Usage:**

To build, test, and completely release a specific version to GitHub (e.g., version `9.0.3`):
```cmd
.\release.bat 9.0.3
```

To build and test locally without creating any Git tags or uploading artifacts to GitHub, append the `--local-only` flag:
```cmd
.\release.bat 9.0.3 --local-only
```
This is highly recommended for local testing and development.
