#!/usr/bin/env python

import h5py
import numpy as np
import random


def AGIPD_encode(image, cal_const):
    """A pseudo signal->raw AGIPD data converter"""

    # default to high gain
    gain_level = np.zeros_like(image,dtype=int)
    # Arbitrary signal threshold to medium gain
    gain_level[image > 100] = 1
    # Arbitrary signal threshold to low gain
    gain_level[image > 500] = 2
    
    raw = np.zeros(image.shape+(2,),dtype=np.float32)
    # We'll take 0 to be signal and 1 to be gain. Don't remember if that's how
    # the real data is laid out.]
    pixel_gain = np.take_along_axis(cal_const,3+gain_level[...,np.newaxis]*2,axis=2)
    # Remove trailing dimension size 1
    pixel_gain = pixel_gain.reshape(image.shape)
    
    pixel_pedestal = np.take_along_axis(cal_const,2+gain_level[...,np.newaxis]*2,axis=2)
    # Remove trailing dimension size 1
    pixel_pedestal = pixel_pedestal.reshape(image.shape)

    raw[:,:,0] = image*pixel_gain + pixel_pedestal

    pixel_threshold = np.take_along_axis(cal_const,gain_level[...,np.newaxis],axis=2)
    # Remove trailing dimension size 1
    pixel_threshold = pixel_threshold.reshape(image.shape)
    # For simplicity for the gain value I'll only take 1 value below the threshold
    raw[:,:,1] = pixel_threshold-1
    # We need to treat low gain specially, in this case 1 above the threshold
    raw[gain_level == 2,1] = cal_const[gain_level == 2, 1] + 1

    return raw

def AGIPD_gen_calibration_constants(img_shape, n_cells):
    """Generate some fake AGIPD calibration constants"""
    
    cal_const = np.zeros(((n_cells,)+img_shape+(8,)),dtype=np.float16)
    # For simplicity we'll start with the same constants for all pixels and cells

    # High/Med gain threshold
    cal_const[...,0] = 1000

    # Med/Low gain threshold
    cal_const[...,1] = 3000

    # High pedestals
    cal_const[...,2] = 4231

    # High gain
    cal_const[...,3] = 20

    # Medium pedestals
    cal_const[...,4] = 3232

    # Medium gain
    cal_const[...,5] = 6

    # Low pedestals
    cal_const[...,6] = 2512

    # Low gain
    cal_const[...,7] = 2

    return cal_const

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

    The AGIPD_v2 algorithm requires exactly the same arguments as AGIPD_v1. The only different is that the dimensions of the calibration dataset, instead of of having 3 dimensions (cell, dataset shape[1], dataset shape[2]) it has an extra of size 8 to fit the 8 calibration constants per cell: the high/medium gain threshold, the medium/low threshold, the high pedestal, the high gain, the medium pedestal, the medium gain, the low pedestal and the low gain. They should be in this exact order.

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
            # Pad with zeros to match dtype length
            while(len(bytes_string)%np.dtype(dtype).itemsize):
                bytes_string += b'\x00'
            chunk_header = np.frombuffer(bytes_string, dtype)

        elif(calib_alg == 'AGIPD_v1'):
            # Very basic AGIPD like calibration with only memory cell based pedestal
            cell_id = image_id%n_cells
            chunk_header = header_base + [AGIPD_v1_magic, cell_id, image_id, n_cells, shape[1], shape[2]]
            bytes_string = np.array(chunk_header,dtype=np.uint32).tobytes()+raw.encode()+b'\x00'+calib.encode()+b'\x00'
            # Pad with zeros to match dtype length
            while(len(bytes_string)%np.dtype(dtype).itemsize):
                bytes_string += b'\x00'
            chunk_header = np.frombuffer(bytes_string, dtype)

        elif(calib_alg == 'AGIPD_v2'):
            # More realistic AGIPD calibration. The raw data now has a final dimension of 2, the signal and the gain.
            # The calibration has a leading dimension equal to the number of cells and a final dimension of 8:
            # The high/medium gain threshold, the medium/low threshold, the high pedestal, the high gain, the medium pedestal,
            # the medium gain, the low pedestal and the low gain.
            cell_id = image_id%n_cells
            chunk_header = header_base + [AGIPD_v2_magic, cell_id, image_id, n_cells, shape[1], shape[2]]
            bytes_string = np.array(chunk_header,dtype=np.uint32).tobytes()+raw.encode()+b'\x00'+calib.encode()+b'\x00'
            # Pad with zeros to match dtype length
            while(len(bytes_string)%np.dtype(dtype).itemsize):
                bytes_string += b'\x00'
            chunk_header = np.frombuffer(bytes_string, dtype)
        else:
            raise ValueError('%s is not a valid calib_alg' % (calib_alg))

        buf = np.zeros((dset.shape[1],dset.shape[2]),dtype=dset.dtype)
        buf.flat[:len(chunk_header)] = chunk_header
        #dset[image_id, 0, :len(chunk_header)] = chunk_header
        dset[image_id, :, :] = buf
