FROM condaforge/mambaforge:24.9.2-0

LABEL maintainer="XREAL1TY"
LABEL description="Runtime image for APPAM paleoproteomics with ThermoRawFileParser, timsconvert, MaxQuant, OpenMS, and Snakemake"

SHELL ["/bin/bash", "-c"]

WORKDIR /opt

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

RUN apt-get update && apt-get install -y \
    tzdata \
    libgomp1 \
    libglib2.0-0 \
    libxml2 \
    zlib1g \
    libxrender1 \
    libxtst6 \
    libxi6 \
    ca-certificates \
    patchelf \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

COPY environment.yml /opt/environment.yml
COPY requirements-pypi.txt /opt/requirements-pypi.txt
COPY vendor/wheels /opt/vendor/wheels

RUN mamba env create -f /opt/environment.yml && \
    /opt/conda/envs/paleoproteomics/bin/pip install -r /opt/requirements-pypi.txt && \
    install_local_or_remote() { \
        package_name="$1"; \
        wheel_glob="$2"; \
        source_url="$3"; \
        local_wheel="$(find /opt/vendor/wheels -maxdepth 1 -type f -iname "${wheel_glob}" -print -quit)"; \
        if [ -n "${local_wheel}" ]; then \
            echo "Installing ${package_name} from local wheel: ${local_wheel}"; \
            /opt/conda/envs/paleoproteomics/bin/pip install --no-deps "${local_wheel}"; \
        else \
            echo "Installing ${package_name} from source URL: ${source_url}"; \
            /opt/conda/envs/paleoproteomics/bin/pip install --no-deps "${source_url}"; \
        fi; \
    } && \
    install_local_or_remote "pyimzML" "pyimzml-*.whl" "git+https://github.com/gtluu/pyimzML.git@fe24388984aa96a18ef2ed54927ec05d6701cc04" && \
    install_local_or_remote "pyTDFSDK" "pytdfsdk-*.whl" "git+https://github.com/gtluu/pyTDFSDK.git@4808da81d3e37f82da96f392dbb446c3733edacb" && \
    install_local_or_remote "pyBaf2Sql" "pybaf2sql-*.whl" "git+https://github.com/gtluu/pyBaf2Sql.git@06bb37fa3168b113c73b22d1d85fb4203bb83fb9" && \
    install_local_or_remote "timsconvert" "timsconvert-*.whl" "git+https://github.com/gtluu/timsconvert.git" && \
    # Patch pyTDFSDK/tims.py extract_2d_tdf_spectrum() to normalize raw scan offsets for ddaPASEF precursor extraction. \
    /opt/conda/envs/paleoproteomics/bin/python -c "from importlib.util import find_spec; from pathlib import Path; module_spec = find_spec('pyTDFSDK.tims'); assert module_spec is not None and module_spec.origin is not None, 'Could not locate pyTDFSDK.tims for patching'; tims_path = Path(module_spec.origin); source = tims_path.read_text(encoding='utf-8'); old = '''        list_of_scans = tims_read_scans_v2(tdf_data.api, tdf_data.handle, frame, scan_begin, scan_end)\n        frame_mz_arrays = []\n        frame_intensity_arrays = []\n        for scan_num in range(scan_begin, scan_end):\n'''; new = '''        list_of_scans = tims_read_scans_v2(tdf_data.api, tdf_data.handle, frame, scan_begin, scan_end)\n        frame_mz_arrays = []\n        frame_intensity_arrays = []\n        if scan_begin != 0:\n            scan_end = scan_end - scan_begin\n            scan_begin = 0\n        for scan_num in range(scan_begin, scan_end):\n'''; assert old in source, 'Could not find expected pyTDFSDK raw scan block to patch'; tims_path.write_text(source.replace(old, new, 1), encoding='utf-8')" && \
    mamba clean -a -y

# Vendor tool directories are expected in the Docker build context.
COPY tools/ThermoRawFileParser /opt/tools/ThermoRawFileParser
COPY tools/MaxQuant_v2.7.5.0 /opt/tools/MaxQuant_v2.7.5.0
COPY tools/openms-development/bin /opt/tools/openms-development/bin
COPY tools/openms-development/lib /opt/tools/openms-development/lib
COPY tools/openms-development/OpenMS/share /opt/tools/openms-development/share

RUN patchelf --set-rpath /opt/conda/envs/paleoproteomics/lib:/opt/tools/openms-development/lib /opt/tools/openms-development/bin/FileConverter && \
    patchelf --set-rpath /opt/conda/envs/paleoproteomics/lib:/opt/tools/openms-development/lib /opt/tools/openms-development/lib/libOpenMS.so && \
    patchelf --set-rpath /opt/conda/envs/paleoproteomics/lib:/opt/tools/openms-development/lib /opt/tools/openms-development/lib/libOpenSwathAlgo.so

RUN mv /opt/conda/envs/paleoproteomics/bin/timsconvert /opt/conda/envs/paleoproteomics/bin/timsconvert.real && \
    printf '%s\n' \
    '#!/bin/bash' \
    'set -e' \
    'PYSIDE6_QT_LIB=/opt/conda/envs/paleoproteomics/lib/python3.11/site-packages/PySide6/Qt/lib' \
    'export LD_LIBRARY_PATH=${PYSIDE6_QT_LIB}:/opt/conda/envs/paleoproteomics/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}' \
    'exec /opt/conda/envs/paleoproteomics/bin/timsconvert.real "$@"' \
    > /opt/conda/envs/paleoproteomics/bin/timsconvert && \
    chmod +x /opt/conda/envs/paleoproteomics/bin/timsconvert

ENV CONDA_ENV_NAME=paleoproteomics
ENV PATH=/opt/conda/envs/paleoproteomics/bin:/opt/tools/ThermoRawFileParser:/opt/tools/MaxQuant_v2.7.5.0:/opt/tools/openms-development/bin:$PATH
ENV LD_LIBRARY_PATH=/opt/tools/openms-development/lib
ENV THERMO_RAW_FILE_PARSER=/opt/tools/ThermoRawFileParser
ENV MAXQUANT_DIR=/opt/tools/MaxQuant_v2.7.5.0
ENV OPENMS_DIR=/opt/tools/openms-development

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["/bin/bash"]
