#SET(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -Wall -std=c99")
cmake_minimum_required(VERSION 3.1)

project (h5hcalib)
find_package(HDF5 REQUIRED)

ADD_SUBDIRECTORY(src)
