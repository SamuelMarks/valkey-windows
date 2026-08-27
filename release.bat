@echo off
setlocal enabledelayedexpansion

if "%~1"=="" (
    echo Usage: %0 ^<tag_or_branch^> [--local-only] [--hash ^<git_hash^>]
    exit /b 1
)

set LOCAL_ONLY=0
set VALKEY_REF=
set VALKEY_HASH=

:parse_args
if "%~1"=="" goto validate_args
if "%~1"=="--local-only" (
    set LOCAL_ONLY=1
    shift
    goto parse_args
)
if "%~1"=="--hash" (
    set VALKEY_HASH=%~2
    shift
    shift
    goto parse_args
)
if "!VALKEY_REF!"=="" (
    set VALKEY_REF=%~1
) else (
    echo Usage: %0 ^<tag_or_branch^> [--local-only] [--hash ^<git_hash^>]
    exit /b 1
)
shift
goto parse_args

:validate_args
if "!VALKEY_REF!"=="" (
    echo Usage: %0 ^<tag_or_branch^> [--local-only] [--hash ^<git_hash^>]
    exit /b 1
)

set BUILD_DIR=build_msvc2026
set REPO_DIR=%~dp0

if "!VALKEY_HASH!"=="" (
    set CLONE_REF=!VALKEY_REF!
) else (
    set CLONE_REF=!VALKEY_HASH!
)

echo ==============================================
echo 0. Fetching Valkey at !CLONE_REF!
echo ==============================================

if exist valkey (
    echo Removing existing valkey directory...
    rmdir /s /q valkey
)

git clone --branch !CLONE_REF! https://github.com/valkey-io/valkey.git valkey
if errorlevel 1 (
    echo Failed to clone Valkey at !CLONE_REF!. Trying to fetch if it's not a branch...
    git clone https://github.com/valkey-io/valkey.git valkey
    cd valkey
    git checkout !CLONE_REF!
    if errorlevel 1 (
        echo Failed to checkout !CLONE_REF!
        exit /b 1
    )
    cd ..
)

echo ==============================================
echo 1. Configuring and Building with MSVC 2026
echo ==============================================

if not exist auto-win-msvc (
    git clone https://github.com/SamuelMarks/auto-win-msvc.git auto-win-msvc
)

echo Fixing auto-win-msvc compatibility issues...
cmake -P patch_auto_win_msvc.cmake


cd valkey

if "!VALKEY_REF!"=="unstable" (
    echo Updating version for unstable...
    powershell -Command "(Get-Content src\version.h) -replace '255.255.255', '0.0.0' | Set-Content src\version.h"
)

echo Applying patch...
git apply --ignore-whitespace --recount ..\patches\0001-Windows-native-builds.patch
if errorlevel 1 (
    echo Failed to apply patch
    exit /b 1
)

echo Preparing Windows Service Wrapper...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/winsw/winsw/releases/download/v3.0.0-alpha.11/WinSW-x64.exe' -OutFile 'valkey-service.exe'"
copy /y "..\packaging\valkey-service.xml" "valkey-service.xml"

echo Configuring CPack...
copy /y COPYING COPYING.txt
echo. >> CMakeLists.txt
echo if(WIN32) >> CMakeLists.txt
echo     install(FILES valkey.conf DESTINATION bin COMPONENT valkey) >> CMakeLists.txt
echo     install(PROGRAMS "${CMAKE_CURRENT_SOURCE_DIR}/valkey-service.exe" DESTINATION bin COMPONENT valkey) >> CMakeLists.txt
echo     install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/valkey-service.xml" DESTINATION bin COMPONENT valkey) >> CMakeLists.txt
echo endif() >> CMakeLists.txt
echo file(WRITE "${CMAKE_BINARY_DIR}/posix_stubs/sys/epoll.h" "#include <linux-epoll.h>\n") >> CMakeLists.txt

echo $cpack = @' > patch_cpack.ps1
echo if(WIN32) >> patch_cpack.ps1
echo     set(CPACK_GENERATOR "WIX;ZIP;NSIS") >> patch_cpack.ps1
echo     set(CPACK_PACKAGE_NAME "Valkey") >> patch_cpack.ps1
echo     set(CPACK_PACKAGE_VENDOR "Valkey") >> patch_cpack.ps1
echo     set(CPACK_WIX_PATCH_FILE "${CMAKE_CURRENT_SOURCE_DIR}/../packaging/wix_patch.xml") >> patch_cpack.ps1
echo     set(CPACK_WIX_UPGRADE_GUID "68097E99-AC62-42B7-B0E3-02FE50FBB6CB") >> patch_cpack.ps1
echo     set(CPACK_NSIS_EXTRA_INSTALL_COMMANDS "ExecWait '$\\\"$INSTDIR\\\\bin\\\\valkey-service.exe$\\\" install'\nExecWait '$\\\"$INSTDIR\\\\bin\\\\valkey-service.exe$\\\" start'") >> patch_cpack.ps1
echo     set(CPACK_NSIS_EXTRA_UNINSTALL_COMMANDS "ExecWait '$\\\"$INSTDIR\\\\bin\\\\valkey-service.exe$\\\" stop'\nExecWait '$\\\"$INSTDIR\\\\bin\\\\valkey-service.exe$\\\" uninstall'") >> patch_cpack.ps1
echo     set(CPACK_RESOURCE_FILE_LICENSE "${CMAKE_SOURCE_DIR}/COPYING.txt") >> patch_cpack.ps1
echo endif() >> patch_cpack.ps1
echo include(CPack) >> patch_cpack.ps1
echo '@ >> patch_cpack.ps1
echo $txt = Get-Content cmake\Modules\Packaging.cmake -Raw >> patch_cpack.ps1
echo $old = [regex]::Match($txt, 'include\(CPack\)').Value >> patch_cpack.ps1
echo $txt = $txt.Replace($old, $cpack) >> patch_cpack.ps1
echo $txt ^| Set-Content cmake\Modules\Packaging.cmake >> patch_cpack.ps1

powershell -ExecutionPolicy Bypass -File patch_cpack.ps1

echo Running CMake...
cmake -S . -B %BUILD_DIR% -G "Visual Studio 17 2022"
if errorlevel 1 (
    echo CMake configuration failed
    exit /b 1
)

echo Building Valkey...
cmake --build %BUILD_DIR% --config Release
if errorlevel 1 (
    echo Build failed
    exit /b 1
)

echo Packaging with CPack...
cd %BUILD_DIR%
cpack -C Release
if errorlevel 1 (
    echo Packaging failed
    exit /b 1
)

cd ..\..

echo ==============================================
echo 2. E2E Testing
echo ==============================================
set SERVER_EXE=valkey\%BUILD_DIR%\bin\Release\valkey-server.exe
set CLI_EXE=valkey\%BUILD_DIR%\bin\Release\valkey-cli.exe

if not exist "%SERVER_EXE%" (
    echo Server executable not found!
    exit /b 1
)
if not exist "%CLI_EXE%" (
    echo CLI executable not found!
    exit /b 1
)

echo Starting Valkey Server...
start "Valkey Server" "%SERVER_EXE%"
:: Wait for server to start
timeout /t 3 /nobreak > nul

echo Running tests...
"%CLI_EXE%" PING > test_output.txt
findstr "PONG" test_output.txt > nul
if errorlevel 1 (
    echo PING failed!
    type test_output.txt
    taskkill /f /im valkey-server.exe
    exit /b 1
)

"%CLI_EXE%" SET mykey "Hello Windows" > test_output.txt
findstr "OK" test_output.txt > nul
if errorlevel 1 (
    echo SET failed!
    type test_output.txt
    taskkill /f /im valkey-server.exe
    exit /b 1
)

"%CLI_EXE%" GET mykey > test_output.txt
findstr "Hello Windows" test_output.txt > nul
if errorlevel 1 (
    echo GET failed!
    type test_output.txt
    taskkill /f /im valkey-server.exe
    exit /b 1
)

"%CLI_EXE%" KEYS * > test_output.txt
findstr "mykey" test_output.txt > nul
if errorlevel 1 (
    echo KEYS * failed
    type test_output.txt
    taskkill /f /im valkey-server.exe
    exit /b 1
)

"%CLI_EXE%" FLUSHDB > test_output.txt
findstr "OK" test_output.txt > nul
if errorlevel 1 (
    echo FLUSHDB failed!
    type test_output.txt
    taskkill /f /im valkey-server.exe
    exit /b 1
)

echo Tests passed!
taskkill /f /im valkey-server.exe

if "!LOCAL_ONLY!"=="1" (
    echo.
    echo ==============================================
    echo Skipping Git Tag and GitHub Release [--local-only]
    echo ==============================================
    echo Done!
    exit /b 0
)

echo ==============================================
echo 3. Pushing Git Tag
echo ==============================================
set TAG_NAME=%VALKEY_REF%

echo Deleting old tag if exists...
git tag -d %TAG_NAME% 2>nul
git push origin :refs/tags/%TAG_NAME% 2>nul
gh release delete %TAG_NAME% -y --cleanup-tag 2>nul

echo Creating new tag %TAG_NAME%...
git tag %TAG_NAME%
git push origin %TAG_NAME%

echo ==============================================
echo 4. Creating GitHub Release
echo ==============================================
echo Uploading artifacts...
gh release create %TAG_NAME% valkey\%BUILD_DIR%\Valkey-*.msi valkey\%BUILD_DIR%\Valkey-*.exe valkey\%BUILD_DIR%\Valkey-*.zip valkey\%BUILD_DIR%\bin\Release\*.exe --title "Valkey %VALKEY_REF% for Windows" --notes "Windows builds for Valkey %VALKEY_REF%"
if errorlevel 1 (
    echo Failed to create GitHub release!
    exit /b 1
)

echo Done!