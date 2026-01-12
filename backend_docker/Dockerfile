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

# Copy environment definitions
COPY --chown=mambauser:mambauser environments /tmp/environments

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

# Set default shell to bash
SHELL ["/bin/bash", "-c"]

# Instructions for the user or default command
CMD ["/bin/bash"]
