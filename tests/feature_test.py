#!/usr/bin/env python

import h5py
import numpy as np
import random
import h5calib

fname = 'ftest.h5'

f = h5py.File(fname,'w')

nimages = 3
image_size = 6

# Example 1, with an (nimages,image_size,image_size) raw data and a calibration
# of size (n_cells, image_size, image_size)
pedestal_data = np.random.randint(low=0, high=100, size=(1,image_size,image_size)).astype(np.uint16)
dset = f.create_dataset("pedestal", (1, image_size, image_size), data=pedestal_data,
                        chunks=(1, image_size, image_size),dtype=np.int16)

dset = f.create_dataset("raw1", (nimages, image_size, image_size),
                        data=pedestal_data+np.ones((nimages,image_size,image_size))*7.0,
                        chunks=(1, image_size, image_size),dtype=np.int16)


h5calib.create_processed(f, (nimages, image_size, image_size), "proc_pedestal", raw="/raw1", calib="/pedestal", calib_alg="pedestal_v1")

f.close()
f = h5py.File(fname,'r')
print(f['/proc_pedestal'][0])

f.close()
f = h5py.File(fname,'r+')

# Example 2, with an (nimages,image_size,image_size) raw data and a calibration
# of size (n_cells, image_size, image_size)
data = np.ones((nimages,image_size,image_size),dtype=np.float32)
data[:] = np.linspace(0,nimages,nimages,endpoint=False).reshape((nimages,1,1))
dset = f.create_dataset("raw_v1", (nimages, image_size, image_size), data=data,
                        chunks=(1, image_size, image_size),dtype=np.int16)
n_cells = 2
calib_data = np.ones((n_cells, image_size,image_size),dtype=np.float32)
calib_data[:] = np.linspace(0,n_cells,n_cells,endpoint=False).reshape((n_cells,1,1))
dset = f.create_dataset("calib", (n_cells, image_size, image_size), data=calib_data,
                        chunks=(1, image_size, image_size),dtype=np.float32)

h5calib.create_processed(f, (nimages, image_size, image_size), "processed", raw="/raw_v1")

f.close()
f = h5py.File(fname,'r')
data_out = f['/processed'][2]
print(data_out)

f.close()
f = h5py.File(fname,'r')
data_out = f['/processed'][2]
print(data_out)
import sys

f.close()
f = h5py.File(fname,'r+')

# Example 3, with an (nimages,image_size,image_size) raw data and a calibration
# of size (n_cells, image_size, image_size, 8) using AGIPD_v2.
# That last 8 corresponds to 
data = np.ones((nimages,image_size,image_size),dtype=np.float32)
data[:] = np.linspace(0,image_size**2,image_size**2,endpoint=False).reshape((1,image_size,image_size))
raw_data = np.ones((nimages,image_size,image_size,2),dtype=np.int16)

cal_const = h5calib.AGIPD_gen_calibration_constants((image_size, image_size), n_cells)
for i in range(0,nimages):
    cell = nimages%n_cells
    raw_data[i] = h5calib.AGIPD_encode(data[i], cal_const[cell])

dset = f.create_dataset("raw_v2", (nimages, image_size, image_size, 2),
                        data=raw_data,
                        chunks=(1, image_size, image_size, 2),dtype=np.int16)
n_cells = 2
calib_data = np.ones((n_cells, image_size,image_size),dtype=np.float32)
calib_data[:] = np.linspace(0,n_cells,n_cells,endpoint=False).reshape((n_cells,1,1))
dset = f.create_dataset("calib_v2", (n_cells, image_size, image_size,8), data=cal_const,
                        chunks=(1, image_size, image_size, 8),dtype=np.float32)

h5calib.create_processed(f, (nimages, image_size, image_size), name="processed_v2", raw="/raw_v2", calib="/calib_v2", calib_alg = 'AGIPD_v2')

f.close()
f = h5py.File(fname,'r')
data_out = f['/processed_v2'][0]
print(data_out)


# Trying to write to one of the "filter compressed" datasets.
# This will result in the warning from the filter as the datasets are read-only
f.close()
f = h5py.File(fname,'r+')
f['/processed'][2] = 0
