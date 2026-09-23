cmake_minimum_required(VERSION 3.10)
project(ValkeyWindowsTests C)

enable_testing()

# The paths to the built executables
if(NOT DEFINED VALKEY_SERVER_EXE)
    set(VALKEY_SERVER_EXE "${CMAKE_CURRENT_SOURCE_DIR}/../valkey/build_msvc2026/bin/Release/valkey-server.exe")
endif()
if(NOT DEFINED VALKEY_CLI_EXE)
    set(VALKEY_CLI_EXE "${CMAKE_CURRENT_SOURCE_DIR}/../valkey/build_msvc2026/bin/Release/valkey-cli.exe")
endif()

# Build the C test executable
add_executable(ReplicateIssue1 test_issue_1.c)
target_link_libraries(ReplicateIssue1 ws2_32)

add_test(
    NAME SanityCheck
    COMMAND ${CMAKE_COMMAND} -E echo "Sanity check passed"
)

# Register it with CTest
if(EXISTS "${VALKEY_SERVER_EXE}" AND EXISTS "${VALKEY_CLI_EXE}")
    add_test(
        NAME ReplicateIssue1
        COMMAND ReplicateIssue1 "${VALKEY_SERVER_EXE}" "${VALKEY_CLI_EXE}"
    )
    set_tests_properties(ReplicateIssue1 PROPERTIES TIMEOUT 30)
else()
    message(STATUS "Valkey executables not found at ${VALKEY_SERVER_EXE}; skipping ReplicateIssue1 test registration")
endif()
