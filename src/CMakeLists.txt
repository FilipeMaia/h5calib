add_library(h5calib_filter SHARED h5calib_filter.c)
set_property(TARGET h5calib_filter PROPERTY C_STANDARD 99)
include_directories(${CMAKE_CURRENT_SOURCE_DIR} ${HDF5_INCLUDE_DIRS})
target_link_libraries(h5calib_filter ${HDF5_LIBRARIES})