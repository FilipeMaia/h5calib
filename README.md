# h5calib
HDF5 filter for generating calibrated data on the fly from raw data

## To compile the filter

Create a `build` directory and from within it run:

	ccmake ..

If necessary give the location of the HDF5 library to build against. This must be exactly the same library as the `h5py` package you will be using. Run make to actually build it.

	$ make
	[ 50%] Building C object src/CMakeFiles/h5calib_filter.dir/h5calib_filter.c.o
	[100%] Linking C shared library libh5calib_filter.dylib
	[100%] Built target h5calib_filter

## Testing the filter

Within the `tests` directory there is a `run_tests.sh` which will set `HDF5_PLUGIN_PATH` environment variable to point to the freshly built filter. It will then run `comp.py` using the `python` in your path. It's important that the `h5py` from that `python` is using the same HDF5 library that you built against.

The `comp.py` filter does most of the work, in particular the `create_processed` function. It create a file with 4 regular datasets:

- A `raw1` dataset, which contains the uncalibrated data that will be used together with the pedestal_v1 algorithm example.
- A `pedestal` dataset, which contains a dark like background, which is the same for all images.
- A `raw2` dataset, which contains the uncalibrated data, with no filter.
- A `calib` dataset, which contains the calibration constants, per detector cell.

The first two datasets are combined to create a `proc_pedestal` dataset, using the `pedestal_v1` algorithm

The last two datasets are combined to create a `processed` dataset, with a cell and pixel dependent "dark" correction using the simply named `AGIPD_v1` algorithm.


## Notes and limitations

Creating the processed datasets is complex, but accessing them is transparent. Check the documentation of `create_processed` in `comp.py` for details on how the dataset is created.

There is some skeleton code for an `AGIPD_v2` algorithm, taking into account, gain levels, but it's not yet finished.

Currently there is a minimum image size as all the metadata for the compressed dataset is stored in the space corresponding to the first row of the image. If the row is very small the metadata might not fit.


	
