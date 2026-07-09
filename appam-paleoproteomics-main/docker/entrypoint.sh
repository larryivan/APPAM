#!/bin/bash
set -e

source /opt/conda/etc/profile.d/conda.sh
conda activate paleoproteomics

export PATH=/opt/tools/ThermoRawFileParser:$PATH
export PATH=/opt/tools/maxquant-current:$PATH
export PATH=/opt/tools/openms-development/bin:$PATH
export LD_LIBRARY_PATH=/opt/tools/openms-development/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}

exec "$@"
