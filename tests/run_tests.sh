#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

export HDF5_PLUGIN_PATH=${DIR}/../build/src
python comp.py
