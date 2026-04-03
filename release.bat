@echo off
setlocal enabledelayedexpansion

if "%~1"=="" (
    echo Usage: %0 ^<tag_or_branch^> [--local-only]
    exit /b 1
)

set LOCAL_ONLY=0
set VALKEY_REF=

:parse_args
if "%~1"=="" goto validate_args
if "%~1"=="--local-only" (
    set LOCAL_ONLY=1
    shift
    goto parse_args
)
if "!VALKEY_REF!"=="" (
    set VALKEY_REF=%~1
) else (
    echo Usage: %0 ^<tag_or_branch^> [--local-only]
    exit /b 1
)
shift
goto parse_args

:validate_args
if "!VALKEY_REF!"=="" (
    echo Usage: %0 ^<tag_or_branch^> [--local-only]
    exit /b 1
)

set BUILD_DIR=build_msvc2026
set REPO_DIR=%~dp0

echo ==============================================
echo 0. Fetching Valkey at %VALKEY_REF%
echo ==============================================

if exist valkey (
    echo Removing existing valkey directory...
    rmdir /s /q valkey
)

git clone --branch %VALKEY_REF% https://github.com/valkey-io/valkey.git valkey
if errorlevel 1 (
    echo Failed to clone Valkey at %VALKEY_REF%. Trying to fetch if it's not a branch...
    git clone https://github.com/valkey-io/valkey.git valkey
    cd valkey
    git checkout %VALKEY_REF%
    if errorlevel 1 (
        echo Failed to checkout %VALKEY_REF%
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

cd valkey

echo Applying patch...
git apply ..\patches\0001-Windows-native-builds.patch
if errorlevel 1 (
    echo Failed to apply patch
    exit /b 1
)

echo Preparing Windows Service Wrapper...
powershell -Command "Invoke-WebRequest -Uri 'https://github.com/winsw/winsw/releases/download/v3.0.0-alpha.11/WinSW-x64.exe' -OutFile 'valkey-service.exe'"
copy /y "..\packaging\valkey-service.xml" "valkey-service.xml"

echo Configuring CPack...
echo. >> CMakeLists.txt
echo if(WIN32) >> CMakeLists.txt
echo     install(FILES valkey.conf DESTINATION bin COMPONENT valkey) >> CMakeLists.txt
echo     install(PROGRAMS "${CMAKE_CURRENT_SOURCE_DIR}/valkey-service.exe" DESTINATION bin COMPONENT valkey) >> CMakeLists.txt
echo     install(FILES "${CMAKE_CURRENT_SOURCE_DIR}/valkey-service.xml" DESTINATION bin COMPONENT valkey) >> CMakeLists.txt
echo     set(CPACK_GENERATOR "WIX;ZIP;NSIS") >> CMakeLists.txt
echo     set(CPACK_PACKAGE_NAME "Valkey") >> CMakeLists.txt
echo     set(CPACK_PACKAGE_VENDOR "Valkey") >> CMakeLists.txt
echo     set(CPACK_WIX_PATCH_FILE "${CMAKE_CURRENT_SOURCE_DIR}/../packaging/wix_patch.xml") >> CMakeLists.txt
echo     set(CPACK_WIX_UPGRADE_GUID "68097E99-AC62-42B7-B0E3-02FE50FBB6CB") >> CMakeLists.txt
echo     set(CPACK_NSIS_EXTRA_INSTALL_COMMANDS "ExecWait '\"$INSTDIR\bin\valkey-service.exe\" install'\nExecWait '\"$INSTDIR\bin\valkey-service.exe\" start'") >> CMakeLists.txt
echo     set(CPACK_NSIS_EXTRA_UNINSTALL_COMMANDS "ExecWait '\"$INSTDIR\bin\valkey-service.exe\" stop'\nExecWait '\"$INSTDIR\bin\valkey-service.exe\" uninstall'") >> CMakeLists.txt
echo endif() >> CMakeLists.txt

echo Running CMake...
cmake -S . -B %BUILD_DIR% -G "Visual Studio 18 2026"
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
set SERVER_EXE=valkey\%BUILD_DIR%\Release\valkey-server.exe
set CLI_EXE=valkey\%BUILD_DIR%\Release\valkey-cli.exe

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
gh release create %TAG_NAME% valkey\%BUILD_DIR%\Valkey-*.msi valkey\%BUILD_DIR%\Valkey-*.exe valkey\%BUILD_DIR%\Valkey-*.zip valkey\%BUILD_DIR%\Release\*.exe --title "Valkey %VALKEY_REF% for Windows" --notes "Windows builds for Valkey %VALKEY_REF%"
if errorlevel 1 (
    echo Failed to create GitHub release!
    exit /b 1
)

echo Done!