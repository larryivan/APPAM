FROM mambaorg/micromamba:latest

USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    procps \
    wget \
    bzip2 \
    ca-certificates \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

USER mambauser

# Build from repo root:
# docker build -f backend_docker/Dockerfile -t appam-backend .

# Install OpenCode CLI
RUN curl -fsSL https://opencode.ai/install | bash
ENV PATH="/home/mambauser/.opencode/bin:${PATH}"

# Copy environment definitions
COPY --chown=mambauser:mambauser backend_docker/environments /tmp/environments

# Create environments
# We do this one by one to avoid OOM or timeout issues during build and easier debugging
RUN micromamba create -n preprocessing -f /tmp/environments/preprocessing.yml && \
    micromamba clean --all --yes

RUN micromamba create -n mapping_dna -f /tmp/environments/mapping_dna.yml && \
    micromamba clean --all --yes

RUN micromamba create -n ancient_dna -f /tmp/environments/ancient_dna.yml && \
    micromamba clean --all --yes

RUN micromamba create -n taxonomy -f /tmp/environments/taxonomy.yml && \
    micromamba clean --all --yes

RUN micromamba create -n assembly -f /tmp/environments/assembly.yml && \
    micromamba clean --all --yes

RUN micromamba create -n freebayes -f /tmp/environments/freebayes.yml && \
    micromamba clean --all --yes

RUN micromamba create -n bcftools -f /tmp/environments/bcftools.yml && \
    micromamba clean --all --yes

RUN micromamba create -n binning -f /tmp/environments/binning.yml && \
    micromamba clean --all --yes

RUN micromamba create -n checkm -f /tmp/environments/checkm.yml && \
    micromamba clean --all --yes

RUN micromamba create -n metawrap -f /tmp/environments/metawrap.yml && \
    micromamba install -n metawrap --only-deps -c ursky -c bioconda -c conda-forge metawrap-mg=1.3.2 && \
    micromamba clean --all --yes

RUN micromamba create -n prokka -f /tmp/environments/prokka.yml && \
    micromamba clean --all --yes

RUN micromamba create -n rgi -f /tmp/environments/rgi.yml && \
    micromamba clean --all --yes

RUN micromamba create -n abricate -f /tmp/environments/abricate.yml && \
    micromamba clean --all --yes

RUN micromamba create -n gtdbtk -f /tmp/environments/gtdbtk.yml && \
    micromamba clean --all --yes

RUN micromamba create -n antismash -f /tmp/environments/antismash.yml && \
    micromamba clean --all --yes

# Copy backend code
WORKDIR /app
COPY --chown=mambauser:mambauser backend /app/backend
RUN mkdir -p /app/backend/projects

USER root
COPY backend_docker/tool-wrapper.sh /usr/local/bin/appam-tool
RUN chmod +x /usr/local/bin/appam-tool && \
    for name in \
      fastqc multiqc adapterremoval AdapterRemoval bwa bowtie2 samtools bedtools pmdtools pmdtools.py \
      pydamage krakenuniq krona ktImportText ktImportTaxonomy megahit spades spades.py quast quast.py \
      freebayes bcftools metabat2 maxbin2 run_MaxBin.pl concoct gunc checkm metawrap metawrap-mg \
      prokka rgi abricate gtdb-tk gtdbtk antismash; do \
        ln -sf /usr/local/bin/appam-tool /usr/local/bin/$name; \
    done
RUN mkdir -p /databases && chown -R mambauser:mambauser /databases
USER mambauser

# Install backend dependencies
RUN micromamba create -n backend -y python=3.12 pip && \
    micromamba run -n backend pip install --no-cache-dir -r /app/backend/requirements.txt && \
    micromamba clean --all --yes

# Set default shell to bash
SHELL ["/bin/bash", "-c"]

# Runtime settings
WORKDIR /app/backend
ENV PYTHONUNBUFFERED=1
ENV FLASK_PORT=8666
VOLUME ["/app/backend/projects", "/databases"]
EXPOSE 8666

# Start backend service
CMD ["micromamba", "run", "-n", "backend", "python", "run.py"]
