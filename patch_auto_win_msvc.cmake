file(READ "auto-win-msvc/posix-sys-resource/src/posix-sys-resource.c" CONTENT)
string(REPLACE "errno = EINVAL;\n      return -1;" "_setmaxstdio(8192);\n      return 0;" CONTENT "${CONTENT}")
file(WRITE "auto-win-msvc/posix-sys-resource/src/posix-sys-resource.c" "${CONTENT}")

file(READ "auto-win-msvc/posix-sockets/src/posix-sockets.c" CONTENT)
string(REPLACE "errno = EAGAIN;" "errno = EWOULDBLOCK;" CONTENT "${CONTENT}")
file(WRITE "auto-win-msvc/posix-sockets/src/posix-sockets.c" "${CONTENT}")

file(READ "auto-win-msvc/posix-core/src/posix_read_write.c" CONTENT)
string(REPLACE "errno = EAGAIN;" "errno = EWOULDBLOCK;" CONTENT "${CONTENT}")
string(REPLACE "if (pathname[0] != '/' && pathname[0] != '\\\\' && pathname[1] != ':' &&\n      g_cloned_cwd[0] != 0) {" "if (pathname[0] != '/' && pathname[0] != '\\\\' && pathname[1] != ':') {\n    char cwd[1024];\n    GetCurrentDirectoryA(1024, cwd);\n#undef g_cloned_cwd\n#define g_cloned_cwd cwd" CONTENT "${CONTENT}")
file(WRITE "auto-win-msvc/posix-core/src/posix_read_write.c" "${CONTENT}")





# Dynamically fix patch for latest valkey
file(READ "patches/0001-Windows-native-builds.patch" PATCH_CONTENT)

# 1. deps/libvalkey/CMakeLists.txt hunk
string(REPLACE "@@ -47,7 +47,7 @@ set(valkey_sources\n     src/conn.c\n     src/crc16.c\n     src/dict.c\n-    src/net.c\n+    \${CMAKE_BINARY_DIR}/patched/deps/libvalkey/src/net.c\n     src/read.c\n     src/sockcompat.c\n     src/valkey.c" "@@ -46,7 +46,7 @@ set(valkey_sources\n     src/command.c\n     src/conn.c\n     src/crc16.c\n-    src/net.c\n+    \${CMAKE_BINARY_DIR}/patched/deps/libvalkey/src/net.c\n     src/read.c\n     src/sockcompat.c\n     src/valkey.c" PATCH_CONTENT "${PATCH_CONTENT}")

# 2. src/CMakeLists.txt hunk 76
set(HUNK76_OLD "@@ -76,16 +81,6 @@ add_dependencies(valkey-cli generate_commands_def)\n add_dependencies(valkey-cli generate_fmtargs_h)\n add_dependencies(valkey-cli release_header)\n \n-# Target: valkey-benchmark\n-list(APPEND BENCH_LIBS \"fpconv\")\n-list(APPEND BENCH_LIBS \"hdr_histogram\")\n-list(APPEND BENCH_LIBS \"ffc\")\n-valkey_build_and_install_bin(valkey-benchmark \"\${VALKEY_BENCHMARK_SRCS}\" \"\${VALKEY_SERVER_LDFLAGS}\" \"\${BENCH_LIBS}\"\n-                             \"redis-benchmark\")\n-add_dependencies(valkey-benchmark generate_commands_def)\n-add_dependencies(valkey-benchmark generate_fmtargs_h)\n-add_dependencies(valkey-benchmark release_header)\n-\n # Targets: valkey-sentinel, valkey-check-aof and valkey-check-rdb are just symbolic links\n valkey_create_symlink(\"valkey-server\" \"valkey-sentinel\")")
set(HUNK76_NEW "@@ -75,15 +80,5 @@ valkey_build_and_install_bin(valkey-cli \"\${VALKEY_CLI_SRCS}\" \"\${VALKEY_SERVER_LD\n add_dependencies(valkey-cli generate_commands_def)\n add_dependencies(valkey-cli generate_fmtargs_h)\n \n-# Target: valkey-benchmark\n-list(APPEND BENCH_LIBS \"fpconv\")\n-list(APPEND BENCH_LIBS \"hdr_histogram\")\n-list(APPEND BENCH_LIBS \"ffc\")\n-valkey_build_and_install_bin(valkey-benchmark \"\${VALKEY_BENCHMARK_SRCS}\" \"\${VALKEY_SERVER_LDFLAGS}\" \"\${BENCH_LIBS}\"\n-                             \"redis-benchmark\")\n-add_dependencies(valkey-benchmark generate_commands_def)\n-add_dependencies(valkey-benchmark generate_fmtargs_h)\n-\n # Targets: valkey-sentinel, valkey-check-aof and valkey-check-rdb are just symbolic links\n valkey_create_symlink(\"valkey-server\" \"valkey-sentinel\")")
string(REPLACE "${HUNK76_OLD}" "${HUNK76_NEW}" PATCH_CONTENT "${PATCH_CONTENT}")

# 3. Remove queues.c completely using REGEX
string(REGEX REPLACE "diff --git a/src/queues\\.c b/src/queues\\.c.*diff --git a/src/unit/CMakeLists\\.txt" "diff --git a/src/unit/CMakeLists.txt" PATCH_CONTENT "${PATCH_CONTENT}")

# 4. Remove src/unit/CMakeLists.txt completely using REGEX
string(REGEX REPLACE "diff --git a/src/unit/CMakeLists\\.txt b/src/unit/CMakeLists\\.txt.*" "" PATCH_CONTENT "${PATCH_CONTENT}")

file(WRITE "patches/0001-Windows-native-builds.patch" "${PATCH_CONTENT}")

# 5. Modify src/unit/CMakeLists.txt natively
file(READ "valkey/src/unit/CMakeLists.txt" UNIT_CONTENT)
string(REPLACE "target_compile_options(valkeylib-gtest PRIVATE -Og -g -fno-lto)" "if(NOT MSVC)\n  target_compile_options(valkeylib-gtest PRIVATE -Og -g -fno-lto)\nendif()" UNIT_CONTENT "${UNIT_CONTENT}")
file(WRITE "valkey/src/unit/CMakeLists.txt" "${UNIT_CONTENT}")

# 6. Modify src/queues.c natively to remove inline
file(READ "valkey/src/queues.c" QUEUES_CONTENT)
string(REPLACE "inline void mpscInit" "void mpscInit" QUEUES_CONTENT "${QUEUES_CONTENT}")
string(REPLACE "inline void spmcInit" "void spmcInit" QUEUES_CONTENT "${QUEUES_CONTENT}")
string(REPLACE "inline void spscInit" "void spscInit" QUEUES_CONTENT "${QUEUES_CONTENT}")
file(WRITE "valkey/src/queues.c" "${QUEUES_CONTENT}")
