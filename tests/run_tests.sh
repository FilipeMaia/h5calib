#!/bin/bash

export HDF5_PLUGIN_PATH=/Users/filipe/src/h5calib/build/src
#export HDF5_VOL_CONNECTOR="pass_through_ext under_vol=0;under_info={};"
#export DYLD_LIBRARY_PATH=${DYLD_LIBRARY_PATH}:${HDF5_PLUGIN_PATH}
#h5ls /Users/filipe/src/vol-external-passthrough/sample.h5
#h5repack /Users/filipe/src/vol-external-passthrough/sample.h5 /Users/filipe/src/vol-external-passthrough/sample_out.h5
python comp.py
