cmake_minimum_required(VERSION 3.10)
project(ValkeyWindowsTests C)

enable_testing()

# The paths to the built executables
set(VALKEY_SERVER_EXE "${CMAKE_CURRENT_SOURCE_DIR}/../valkey/build_msvc2026/bin/Release/valkey-server.exe")
set(VALKEY_CLI_EXE "${CMAKE_CURRENT_SOURCE_DIR}/../valkey/build_msvc2026/bin/Release/valkey-cli.exe")

# Build the C test executable
add_executable(ReplicateIssue1 test_issue_1.c)
target_link_libraries(ReplicateIssue1 ws2_32)

# Register it with CTest
add_test(
    NAME ReplicateIssue1
    COMMAND ReplicateIssue1 "${VALKEY_SERVER_EXE}" "${VALKEY_CLI_EXE}"
)

# Test should pass if it successfully replicates the bugs (returns 0)
set_tests_properties(ReplicateIssue1 PROPERTIES TIMEOUT 30)
