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


file(READ "valkey/deps/libvalkey/src/net.c" CONTENT)
string(REPLACE "if (ioctl(c->fd, FIONBIO, &mode) == -1) {" "if (posix_ioctl(c->fd, FIONBIO, &mode) == -1) {" CONTENT "${CONTENT}")
string(REPLACE "#include \"fmacros.h\"" "#include \"fmacros.h\"\n#undef ioctl\n#define ioctl posix_ioctl\n#undef socket\n#define socket posix_socket\n#undef poll\n#define poll posix_poll\n#undef getsockopt\n#define getsockopt posix_getsockopt\n#undef setsockopt\n#define setsockopt posix_setsockopt\n#undef bind\n#define bind posix_bind\n#undef listen\n#define listen posix_listen\n#undef accept\n#define accept posix_accept\n#undef recv\n#define recv posix_recv\n#undef send\n#define send posix_send\n#undef freeaddrinfo\n#define freeaddrinfo posix_freeaddrinfo\n#undef getaddrinfo\n#define getaddrinfo posix_getaddrinfo\n#undef gai_strerror\n#define gai_strerror posix_gai_strerror\n" CONTENT "${CONTENT}")
file(WRITE "valkey/deps/libvalkey/src/net.c" "${CONTENT}")

file(READ "valkey/deps/libvalkey/src/net.c" CONTENT)
string(REPLACE "if (ioctl(c->fd, FIONBIO, &mode) == -1) {" "if (posix_ioctl(c->fd, FIONBIO, &mode) == -1) {" CONTENT "${CONTENT}")
string(REPLACE "#include \"valkey_private.h\"" "#include \"valkey_private.h\"\n#undef ioctl\n#define ioctl posix_ioctl\n#undef socket\n#define socket posix_socket\n#undef poll\n#define poll posix_poll\n#undef getsockopt\n#define getsockopt posix_getsockopt\n#undef setsockopt\n#define setsockopt posix_setsockopt\n#undef bind\n#define bind posix_bind\n#undef listen\n#define listen posix_listen\n#undef accept\n#define accept posix_accept\n#undef recv\n#define recv posix_recv\n#undef send\n#define send posix_send\n#undef freeaddrinfo\n#define freeaddrinfo posix_freeaddrinfo\n#undef getaddrinfo\n#define getaddrinfo posix_getaddrinfo\n#undef gai_strerror\n#define gai_strerror posix_gai_strerror\n#undef connect\n#define connect posix_connect\n#undef close\n#define close posix_close\n" CONTENT "${CONTENT}")
file(WRITE "valkey/deps/libvalkey/src/net.c" "${CONTENT}")
