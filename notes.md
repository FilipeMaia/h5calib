# Short notes regarding the calibration plugin

Seems like it can be used both through a filter or through a VOL connector

## When using a filter

We should probably try to store calibration constants in place of the data. We also have to use carefully the chunk size to have an idea of the memory cell we're reading. The only way to get to the calibration constants is probably to store it in another dataset in the same group with a fixed name for example.
