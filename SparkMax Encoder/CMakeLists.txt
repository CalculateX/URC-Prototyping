cmake_minimum_required(VERSION 3.10)
project(spark_bridge)

set(CMAKE_CXX_STANDARD 11)

# Create the shared library
add_library(spark_bridge SHARED spark_bridge.cpp)

# Output to the build directory for the Python script to find
set_target_properties(spark_bridge PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR})
