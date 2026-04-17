FROM mambaorg/micromamba:latest

USER root

ARG DEBIAN_FRONTEND=noninteractive
ARG THERMO_RAW_FILE_PARSER_URL=https://github.com/CompOmics/ThermoRawFileParser/releases/download/v.2.0.0-dev/ThermoRawFileParser-v.2.0.0-dev-linux.zip
ARG METAWRAP_REPO=https://github.com/bxlab/metaWRAP.git
ARG METAWRAP_REF=c4a23f0fff872abe3cafb63767dc592a8361331b
ARG APPAM_BUILD_RETRY_ATTEMPTS=5
ARG APPAM_BUILD_RETRY_INITIAL_DELAY=10

RUN apt-get update && apt-get install -y \
    bash \
    bzip2 \
    ca-certificates \
    curl \
    git \
    procps \
    unzip \
    wget \
    tzdata \
    libgomp1 \
    libglib2.0-0 \
    libxml2 \
    zlib1g \
    libxrender1 \
    libxtst6 \
    libxi6 \
    patchelf \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/appam

COPY backend /opt/appam/backend
COPY APPAM-SMK-main /opt/appam/APPAM-SMK-main
COPY appam-paleoproteomics-main /opt/appam/appam-paleoproteomics-main
COPY vendor/maxquant /opt/tools
COPY docker/tools/environments /opt/appam/docker/tools/environments
COPY docker/tools/tool-wrapper.sh /opt/appam/docker/tools/tool-wrapper.sh
COPY docker/tools/retry-bash.sh /usr/local/bin/retry-bash
COPY docker/tools/start-tools.sh /usr/local/bin/start-appam-tools

RUN chmod +x /usr/local/bin/start-appam-tools /usr/local/bin/retry-bash

USER mambauser

RUN mkdir -p /home/mambauser/.conda && \
    cat > /home/mambauser/.condarc <<'EOF'
channel_priority: flexible
remote_max_retries: 10
remote_connect_timeout_secs: 30
remote_read_timeout_secs: 120
EOF

RUN retry-bash "curl --retry 8 --retry-delay 5 --retry-all-errors -fsSL https://opencode.ai/install | bash"
ENV PATH="/home/mambauser/.opencode/bin:${PATH}"

USER root

RUN mkdir -p /opt/vendor && \
    retry-bash "git clone ${METAWRAP_REPO} /opt/vendor/metaWRAP" && \
    git -C /opt/vendor/metaWRAP checkout --detach "${METAWRAP_REF}" && \
    printf '%s\n' \
      'SOFT=/opt/vendor/metaWRAP/bin/metawrap-scripts' \
      'PIPES=/opt/vendor/metaWRAP/bin/metawrap-modules' \
      'KRAKEN_DB=${APPAM_METAWRAP_KRAKEN_DB:-/databases/kraken}' \
      'KRAKEN2_DB=${APPAM_METAWRAP_KRAKEN2_DB:-/databases/kraken2}' \
      'BMTAGGER_DB=${APPAM_METAWRAP_BMTAGGER_DB:-/databases/bmtagger}' \
      'BLASTDB=${APPAM_METAWRAP_BLASTDB:-/databases/blastdb}' \
      'TAXDUMP=${APPAM_METAWRAP_TAXDUMP:-/databases/taxdump}' \
      > /opt/vendor/metaWRAP/bin/config-metawrap

USER mambauser

RUN retry-bash "micromamba create -y -n preprocessing -f /opt/appam/docker/tools/environments/preprocessing.yml && micromamba clean --all --yes"
RUN retry-bash "micromamba create -y -n mapping_dna -f /opt/appam/docker/tools/environments/mapping_dna.yml && micromamba clean --all --yes"
RUN retry-bash "micromamba create -y -n ancient_dna -f /opt/appam/docker/tools/environments/ancient_dna.yml && micromamba clean --all --yes"
RUN retry-bash "micromamba create -y -n taxonomy -f /opt/appam/docker/tools/environments/taxonomy.yml && micromamba clean --all --yes"
RUN retry-bash "micromamba create -y -n assembly -f /opt/appam/docker/tools/environments/assembly.yml && micromamba install -y -n assembly -c bioconda -c conda-forge seqkit && micromamba clean --all --yes"
RUN retry-bash "micromamba create -y -n freebayes -f /opt/appam/docker/tools/environments/freebayes.yml && micromamba clean --all --yes"
RUN retry-bash "micromamba create -y -n bcftools -f /opt/appam/docker/tools/environments/bcftools.yml && micromamba clean --all --yes"
RUN retry-bash "micromamba create -y -n binning -f /opt/appam/docker/tools/environments/binning.yml && micromamba clean --all --yes"
RUN retry-bash "micromamba create -y -n checkm -f /opt/appam/docker/tools/environments/checkm.yml && micromamba clean --all --yes"
RUN retry-bash "micromamba create -y -n metawrap -f /opt/appam/docker/tools/environments/metawrap.yml && micromamba clean --all --yes"
RUN retry-bash "micromamba create -y -n prokka -f /opt/appam/docker/tools/environments/prokka.yml && micromamba clean --all --yes"
RUN retry-bash "micromamba create -y -n rgi -f /opt/appam/docker/tools/environments/rgi.yml && micromamba clean --all --yes"
RUN retry-bash "micromamba create -y -n abricate -f /opt/appam/docker/tools/environments/abricate.yml && micromamba clean --all --yes"
RUN retry-bash "micromamba create -y -n gtdbtk -f /opt/appam/docker/tools/environments/gtdbtk.yml && micromamba clean --all --yes"
RUN retry-bash "micromamba create -y -n antismash -f /opt/appam/docker/tools/environments/antismash.yml && micromamba clean --all --yes"

RUN retry-bash "micromamba create -y -n paleoproteomics -f /opt/appam/appam-paleoproteomics-main/docker/environment.yml && micromamba run -n paleoproteomics pip install -r /opt/appam/appam-paleoproteomics-main/docker/requirements-pypi.txt && micromamba install -y -n paleoproteomics -c bioconda -c conda-forge openms && micromamba run -n paleoproteomics pip install --no-deps git+https://github.com/gtluu/pyimzML.git@fe24388984aa96a18ef2ed54927ec05d6701cc04 git+https://github.com/gtluu/pyTDFSDK.git@4808da81d3e37f82da96f392dbb446c3733edacb git+https://github.com/gtluu/pyBaf2Sql.git@06bb37fa3168b113c73b22d1d85fb4203bb83fb9 git+https://github.com/gtluu/timsconvert.git && micromamba clean --all --yes"

RUN retry-bash "micromamba create -y -n backend python=3.12 pip && micromamba run -n backend pip install --no-cache-dir -r /opt/appam/backend/requirements.txt && micromamba run -n backend pip install --no-cache-dir snakemake==9.16.0 && micromamba clean --all --yes"

USER root

RUN mkdir -p /opt/vendor/ThermoRawFileParser /opt/tools /data /workspaces/projects /databases && \
    curl --retry 8 --retry-delay 5 --retry-all-errors -L "${THERMO_RAW_FILE_PARSER_URL}" -o /tmp/ThermoRawFileParser.zip && \
    unzip -q /tmp/ThermoRawFileParser.zip -d /opt/vendor/ThermoRawFileParser && \
    rm -f /tmp/ThermoRawFileParser.zip && \
    THERMO_BIN="$(find /opt/vendor/ThermoRawFileParser -type f -name 'ThermoRawFileParser*' -perm -u+x | head -n 1)" && \
    if [ -n "${THERMO_BIN}" ]; then ln -sf "${THERMO_BIN}" /usr/local/bin/ThermoRawFileParser; fi && \
    cp /opt/appam/docker/tools/tool-wrapper.sh /usr/local/bin/appam-tool && \
    ln -sf /opt/vendor/metaWRAP/bin/config-metawrap /usr/local/bin/config-metawrap && \
    chmod +x /usr/local/bin/appam-tool /usr/local/bin/start-appam-tools && \
    for name in \
      fastqc multiqc adapterremoval AdapterRemoval bwa bowtie2 samtools bedtools pmdtools pmdtools.py \
      pydamage krakenuniq krona ktImportText ktImportTaxonomy megahit spades spades.py quast quast.py \
      freebayes bcftools metabat2 maxbin2 run_MaxBin.pl concoct gunc checkm checkm2 metawrap metawrap-mg \
      jgi_summarize_bam_contig_depths cut_up_fasta.py concoct_coverage_table.py merge_cutup_clustering.py \
      prokka rgi abricate gtdb-tk gtdbtk antismash seqkit; do \
      ln -sf /usr/local/bin/appam-tool /usr/local/bin/$name; \
    done && \
    chown -R mambauser:mambauser /opt/appam /opt/vendor /opt/tools /data /workspaces/projects /databases

USER mambauser

ENV PYTHONUNBUFFERED=1
ENV APPAM_BUILD_RETRY_ATTEMPTS=${APPAM_BUILD_RETRY_ATTEMPTS}
ENV APPAM_BUILD_RETRY_INITIAL_DELAY=${APPAM_BUILD_RETRY_INITIAL_DELAY}
ENV FLASK_PORT=19454
ENV OPENCODE_PORT=19455
ENV OPENCODE_BASE_URL=http://127.0.0.1:19455
ENV SOCKETIO_ASYNC_MODE=threading
ENV APPAM_REPO_ROOT=/opt/appam
ENV APPAM_BACKEND_ROOT=/opt/appam/backend
ENV APPAM_PROJECTS_ROOT=/workspaces/projects
ENV APPAM_DATABASES_ROOT=/databases
ENV APPAM_DB_PATH=/data/app_database.db
ENV APPAM_SMK_ROOT=/opt/appam/APPAM-SMK-main
ENV APPAM_PALEOPROTEOMICS_ROOT=/opt/appam/appam-paleoproteomics-main
ENV APPAM_SNAKEMAKE_BIN=snakemake
ENV APPAM_PALEO_DOTNET_BIN=dotnet
ENV APPAM_PALEO_MAXQUANT_CMD=/opt/tools/MaxQuant_v2.7.5.0/bin/MaxQuantCmd.dll
ENV APPAM_PALEO_THERMO_RAW_FILE_PARSER=ThermoRawFileParser
ENV APPAM_PALEO_TIMSCONVERT_BIN=timsconvert
ENV APPAM_PALEO_OPENMS_FILECONVERTER=FileConverter
ENV OPENCODE_CLI_COMMAND=opencode
ENV OPENCODE_CLI_AGENTS_PATH=/opt/appam/backend/opencode/AGENTS.md
ENV OPENCODE_CLI_SYSTEM_PROMPT_PATH=/opt/appam/backend/opencode/system_prompt.txt
ENV PATH="/opt/conda/envs/paleoproteomics/bin:/opt/vendor/ThermoRawFileParser:/opt/tools/MaxQuant_v2.7.5.0:/opt/tools/MaxQuant_v2.7.5.0/bin:${PATH}"

VOLUME ["/data", "/workspaces/projects", "/databases"]
EXPOSE 19454 19455

CMD ["/usr/local/bin/start-appam-tools"]
