#!/usr/bin/env python

import h5py
import numpy as np
import random


def create_processed(parent, shape, name="processed", raw='/raw', calib='/calib', calib_alg = 'AGIPD_v1', n_cells=2, dtype=np.float32):
    """Create a read-only dataset of processed data from the given raw and calibraton data.

    The dataset is defined by a path to the raw data, a path to the calibration constants and the name of a calibration algorithm, as well
    as parameters specific to certain calibration algorithms, like the number of cells. The calibration is only done when the data is read
    using a repurposed decompression hdf5 filter.

    Notes
    -----
    Writes a header to each chunk of the dataset that includes all the necessary metadata to return calibrated data at read-time.
    The header is composed of 3 32-bit unsigned ints: (1) magic number identifying an h5calib header, (2) random number identifying
    the file, (3) calibration algorithm identifier. These will be followed by algorithm specific header components.

    The AGIPD_v1 algorithm requires 5 extra 32-bit unsigned ints: (1) cell id of the chunk, (2) image index, (3) total number of
    cells, (4) dataset shape[1], (5) dataset shape[2]. This is followed by two null terminated strings (C-style) with the path
    to the raw dataset and the calibration dataset.

    A 'h5calib_file_magic' attribute is written to the root of the file, if it does not already exist, to uniquely identify the file.
    This is a hack around the limited capabilities of the HDF5 filter API, to allow us to figure out which file has the dataset
    we are working on.

    """
    h5calib_magic = np.uint32(0x6290D662)
    pedestal_v1_magic = np.uint32(0x00010001)
    AGIPD_v1_magic = np.uint32(0x00020001)
    AGIPD_v2_magic = np.uint32(0x00020002)

    if('h5calib_file_magic' in parent.file.attrs):
        file_magic = np.uint32(parent.file.attrs['h5calib_file_magic'])
    else:
        file_magic = np.uint32(random.getrandbits(32))
        parent.file.attrs['h5calib_file_magic'] = file_magic


    header_base = [h5calib_magic,file_magic]

    dset = parent.create_dataset(name, shape, compression=57836,
                                 chunks=(1, shape[1], shape[2]),dtype=dtype)
    nimages = shape[0]
    for image_id in range(nimages):
        if(calib_alg == 'pedestal_v1'):
            # Simple static pedestal correction
            chunk_header = header_base + [pedestal_v1_magic, image_id, shape[1], shape[2]]
            bytes_string = np.array(chunk_header,dtype=np.uint32).tobytes()+raw.encode()+b'\x00'+calib.encode()+b'\x00'
            bytes_string = bytes_string + b'\x00'*(len(bytes_string)%np.dtype(dtype).itemsize)
            chunk_header = np.frombuffer(bytes_string, dtype)
        elif(calib_alg == 'AGIPD_v1'):
            # Very basic AGIPD like calibration with only memory cell based pedestal
            cell_id = image_id%n_cells
            chunk_header = header_base + [AGIPD_v1_magic, cell_id, image_id, n_cells, shape[1], shape[2]]
            bytes_string = np.array(chunk_header,dtype=np.uint32).tobytes()+raw.encode()+b'\x00'+calib.encode()+b'\x00'
            bytes_string = bytes_string + b'\x00'*(len(bytes_string)%np.dtype(dtype).itemsize)
            chunk_header = np.frombuffer(bytes_string, dtype)
        elif(calib_alg == 'AGIPD_v2'):
            # More realistic AGIPD calibration. The raw data now has a final dimension of 2, the signal and the gain.
            # The calibration has a leading dimension equal to the number of cells and a final dimension of 8:
            # The high/medium gain threshold, the medium/low threshold, the high pedestal, the high gain, the medium pedestal,
            # the medium gain, the low pedestal and the low gain.
            cell_id = image_id%n_cells
            chunk_header = header_base + [AGIPD_v2_magic, cell_id, image_id, n_cells, shape[1], shape[2]]
            bytes_string = np.array(chunk_header,dtype=np.uint32).tobytes()+raw.encode()+b'\x00'+calib.encode()+b'\x00'
            bytes_string = bytes_string + b'\x00'*(len(bytes_string)%np.dtype(dtype).itemsize)
            chunk_header = np.frombuffer(bytes_string, dtype)
        else:
            raise ValueError('%s is not a valid calib_alg' % (calib_alg))

        dset[image_id, 0, :len(chunk_header)] = chunk_header


f = h5py.File('comp.h5','w',libver='latest')

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

pedestal_data = np.random.random((1,image_size,image_size)).astype(np.float32)
dset = f.create_dataset("pedestal", (1, image_size, image_size), data=pedestal_data,
                        chunks=(1, image_size, image_size),dtype=np.float32)

dset = f.create_dataset("raw_pedestal", (nimages, image_size, image_size), data=pedestal_data+np.ones((nimages,image_size,image_size))*7.0,
                        chunks=(1, image_size, image_size),dtype=np.float32)

create_processed(f, (nimages, image_size, image_size), "processed")

create_processed(f, (nimages, image_size, image_size), "proc_pedestal", raw="/raw_pedestal", calib="/pedestal", calib_alg="pedestal_v1")

#f.close()
#f = h5py.File('comp.h5','r')
data_out = f['/processed'][5]
print(data_out)
data_out = f['/processed'][6]
print(data_out)
data_out = f['/processed'][7]
print(data_out)

f['/processed'][7] = 0

print(f['/raw_pedestal'][7])
print(f['/proc_pedestal'][7])
f.close()
