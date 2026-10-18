#!/bin/bash
set -e

source /opt/conda/etc/profile.d/conda.sh
conda activate paleoproteomics

export PATH=/usr/local/bin:/opt/tools/ThermoRawFileParser:$PATH
export PATH=/opt/tools/maxquant-current:$PATH
export PATH=/opt/tools/openms-development/bin:$PATH

exec "$@"
