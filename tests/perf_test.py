#!/usr/bin/env python

import h5py
import numpy as np
import random
import h5calib

fname = 'ptest.h5'

def drop_cache():
    import os
    import sys
    if sys.platform.startswith('linux'):
        os.system("sync && sudo echo 3 > /proc/sys/vm/drop_caches")
    elif sys.platform.startswith('darwin'):
        # To avoid filesystem caches on MacOS.
        # From https://stackoverflow.com/questions/28845524/echo-3-proc-sys-vm-drop-caches-on-mac-osx
        os.system("sync && sudo purge")
    

f = h5py.File(fname,'w')

nimages = 400
image_size = 1024
n_cells = 352

print("Generating raw data...", end='\r')

# Example 3, with an (nimages,image_size,image_size) raw data and a calibration
# of size (n_cells, image_size, image_size, 8) using AGIPD_v2.
# That last 8 corresponds to 
data = np.ones((nimages,image_size,image_size),dtype=np.float16)
data[:] = np.linspace(0,image_size**2,image_size**2,endpoint=False).reshape((1,image_size,image_size))
raw_data = np.ones((nimages,image_size,image_size,2),dtype=np.int16)

cal_const = h5calib.AGIPD_gen_calibration_constants((image_size, image_size), n_cells)
for i in range(0,nimages):
    cell = nimages%n_cells
    raw_data[i] = h5calib.AGIPD_encode(data[i], cal_const[cell])
print("Generating raw data...done")
del data

print("Writing raw data and calibration constants...", end='\r')
dset = f.create_dataset("raw_v2", (nimages, image_size, image_size, 2),
                        data=raw_data,
                        chunks=(1, image_size, image_size, 2),dtype=np.int16)

del raw_data
dset = f.create_dataset("calib_v2", (n_cells, image_size, image_size,8), data=cal_const,
                        chunks=(1, image_size, image_size, 8),dtype=np.float32)

del cal_const

print("Writing raw dataset and calibration constants...done")

print("Writing calibrated dataset...", end='\r')
h5calib.create_processed(f, (nimages, image_size, image_size), name="processed_v2", raw="/raw_v2", calib="/calib_v2", calib_alg = 'AGIPD_v2')
f.close()
print("Writing calibrated dataset...done")


f = h5py.File(fname,'r')
import time
#drop_cache()
t = time.time()
raw_data_out = np.array(f['/raw_v2'])
dt = time.time()-t
print("Raw read in %s s", dt)
print("%d MB/s" % (raw_data_out.nbytes/(1024**2 * dt)))
del raw_data_out
#drop_cache()
t = time.time()
data_out = np.array(f['/processed_v2'])
dt = time.time()-t
print("Calibrated read in %s s", dt)
print("%d MB/s" % (data_out.nbytes/(1024**2 * dt)))

