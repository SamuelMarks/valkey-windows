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
