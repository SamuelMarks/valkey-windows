cmake_minimum_required(VERSION 3.10)
project(valkey_windows C)

include(CTest)

if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/tests/CMakeLists.txt")
    add_subdirectory(tests)
endif()
