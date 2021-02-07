#!/usr/bin/env python

import h5py
import numpy as np


def create_processed(parent, shape, name="processed", raw='/raw', calib='/calib', calib_alg = 'AGIPD', n_cells=2, dtype=np.float32):
    dset = parent.create_dataset(name, shape, compression=57836,
                                 chunks=(1, shape[1], shape[2]),dtype=dtype)
    nimages = shape[0]
    for image_id in range(nimages):
        cell_id = image_id%n_cells
        proc_data = [ord(l) for l in list(raw)] + [-1] + [ord(l) for l in list(calib)] + [-1] + [cell_id, image_id, n_cells, shape[1], shape[2], -1]
        #proc_data = np.array(proc_data,dtype=np.float32)
        #print(proc_data.dtype)
        #print(proc_data.view(dtype=dset.dtype))
        dset[image_id,0,:len(proc_data)] = proc_data
    
# plist = h5py.h5p.create(h5py.h5p.FILE_ACCESS)
# plist.set_cache(0, 10007, 2*4*1024*1024*10, 0.5)
# fid = h5py.h5f.create('comp.h5', fapl=plist)
# f = h5py.File(fid)
f = h5py.File('comp.h5','w',libver='latest')
#f = h5py.File('/Users/filipe/src/vol-external-passthrough/sample.h5')

nimages = 10
image_size = 20
data = np.ones((nimages,image_size,image_size),dtype=np.float32)
data[:] = np.linspace(0,nimages,nimages,endpoint=False).reshape((nimages,1,1))
dset = f.create_dataset("raw", (nimages, image_size, image_size), data=data,
                        chunks=(1, image_size, image_size),dtype=np.int16)
n_cells = 2
calib_data = np.ones((n_cells, image_size,image_size),dtype=np.float32)
calib_data[:] = np.linspace(0,n_cells,n_cells,endpoint=False).reshape((n_cells,1,1))
dset = f.create_dataset("calib", (n_cells, image_size, image_size), data=calib_data,
                        chunks=(1, image_size, image_size),dtype=np.float32)

#dset = f.create_dataset("processed", (nimages, image_size, image_size), compression=57836,
#                        chunks=(1, image_size, image_size),dtype=np.float32)
#dset = f.create_dataset("processed", (10, image_size, image_size),data=data,
#                        chunks=(1, image_size, image_size), dtype=np.int64)
#dset.attrs['calib_dataset'] = '/calib'
#dset.attrs['calib_type'] = 'AGIPD'
#dset.attrs['calib_version'] = 0
#print(dset[0,0,0])
create_processed(f, (nimages, image_size, image_size), "processed")

#f.close()
#f = h5py.File('comp.h5','r')
data_out = f['/processed'][5]
print(data_out)
data_out = f['/processed'][6]
print(data_out)
data_out = f['/processed'][7]
print(data_out)

f.close()
