FROM condaforge/mambaforge:24.9.2-0

LABEL maintainer="XREAL1TY"
LABEL description="Runtime image for APPAM paleoproteomics with ThermoRawFileParser, timsconvert, MaxQuant, OpenMS, and Snakemake"

SHELL ["/bin/bash", "-c"]

WORKDIR /opt

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt-get update && apt-get install -y \
    bash \
    bzip2 \
    curl \
    git \
    tzdata \
    libgomp1 \
    libglib2.0-0 \
    libxml2 \
    zlib1g \
    libxrender1 \
    libxtst6 \
    libxi6 \
    libgl1 \
    libegl1 \
    libfontconfig1 \
    libfreetype6 \
    libxkbcommon0 \
    libxkbcommon-x11-0 \
    libdbus-1-3 \
    ca-certificates \
    patchelf \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

COPY environment.yml /opt/environment.yml
COPY requirements-pypi.txt /opt/requirements-pypi.txt
COPY patch_pytdfsdk.py /opt/patch_pytdfsdk.py

RUN mamba env create -f /opt/environment.yml && \
    mamba create -y -n timsconvert python=3.11 pip && \
    /opt/conda/envs/timsconvert/bin/pip install --no-cache-dir -r /opt/requirements-pypi.txt && \
    /opt/conda/envs/timsconvert/bin/pip install --no-cache-dir --no-deps \
        'git+https://github.com/gtluu/pyimzML.git@fe24388984aa96a18ef2ed54927ec05d6701cc04' \
        'git+https://github.com/gtluu/pyTDFSDK.git@4808da81d3e37f82da96f392dbb446c3733edacb' \
        'git+https://github.com/gtluu/pyBaf2Sql.git@06bb37fa3168b113c73b22d1d85fb4203bb83fb9' \
        'git+https://github.com/gtluu/timsconvert.git@c8bbfd98251e07e24522220fd4309e37eea4d7a9' && \
    /opt/conda/envs/timsconvert/bin/python /opt/patch_pytdfsdk.py && \
    mamba clean -a -y

RUN printf '%s\n' \
    '#!/bin/bash' \
    'set -euo pipefail' \
    'unset LD_LIBRARY_PATH' \
    'unset QT_PLUGIN_PATH' \
    'unset QML2_IMPORT_PATH' \
    'export PYTHONNOUSERSITE=1' \
    'exec /opt/conda/envs/timsconvert/bin/timsconvert "$@"' \
    > /usr/local/bin/timsconvert && \
    chmod 0755 /usr/local/bin/timsconvert && \
    env -u LD_LIBRARY_PATH -u QT_PLUGIN_PATH -u QML2_IMPORT_PATH \
      /opt/conda/envs/timsconvert/bin/python -c \
      "import PySide6; from PySide6.QtCore import qVersion; from PySide6.QtGui import QGuiApplication; assert PySide6.__version__ == '6.7.2'; assert qVersion().startswith('6.7.')" && \
    /usr/local/bin/timsconvert --help >/dev/null

# Vendor tool directories are expected in the Docker build context.
COPY tools/ThermoRawFileParser /opt/tools/ThermoRawFileParser
COPY tools/MaxQuant /opt/tools/maxquant-current
COPY tools/openms-development/bin /opt/tools/openms-development/bin
COPY tools/openms-development/lib /opt/tools/openms-development/lib
COPY tools/openms-development/OpenMS/share /opt/tools/openms-development/share

RUN patchelf --set-rpath /opt/conda/envs/paleoproteomics/lib:/opt/tools/openms-development/lib /opt/tools/openms-development/bin/FileConverter && \
    patchelf --set-rpath /opt/conda/envs/paleoproteomics/lib:/opt/tools/openms-development/lib /opt/tools/openms-development/lib/libOpenMS.so && \
    patchelf --set-rpath /opt/conda/envs/paleoproteomics/lib:/opt/tools/openms-development/lib /opt/tools/openms-development/lib/libOpenSwathAlgo.so

ENV CONDA_ENV_NAME=paleoproteomics
ENV PATH=/usr/local/bin:/opt/conda/envs/paleoproteomics/bin:/opt/tools/ThermoRawFileParser:/opt/tools/maxquant-current:/opt/tools/openms-development/bin:$PATH
ENV THERMO_RAW_FILE_PARSER=/opt/tools/ThermoRawFileParser
ENV MAXQUANT_DIR=/opt/tools/maxquant-current
ENV OPENMS_DIR=/opt/tools/openms-development
ENV TIMSCONVERT_DIR=/opt/conda/envs/timsconvert

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/bin/bash"]
