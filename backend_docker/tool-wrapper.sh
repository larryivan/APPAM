#!/usr/bin/env bash
set -euo pipefail

cmd="$(basename "$0")"
env=""
target="$cmd"

case "$cmd" in
  fastqc|multiqc|adapterremoval|AdapterRemoval)
    env="preprocessing"
    ;;
  bwa|bowtie2|samtools|bedtools)
    env="mapping_dna"
    ;;
  pmdtools|pmdtools.py|pydamage)
    env="ancient_dna"
    ;;
  krakenuniq|krona|ktImportText|ktImportTaxonomy)
    env="taxonomy"
    ;;
  megahit|spades|spades.py|quast|quast.py)
    env="assembly"
    ;;
  freebayes)
    env="freebayes"
    ;;
  bcftools)
    env="bcftools"
    ;;
  metabat2|maxbin2|run_MaxBin.pl|concoct|gunc)
    env="binning"
    ;;
  checkm)
    env="checkm"
    ;;
  metawrap|metawrap-mg)
    env="metawrap"
    ;;
  prokka)
    env="prokka"
    ;;
  rgi)
    env="rgi"
    ;;
  abricate)
    env="abricate"
    ;;
  gtdb-tk|gtdbtk)
    env="gtdbtk"
    ;;
  antismash)
    env="antismash"
    ;;
  *)
    echo "Unknown tool: ${cmd}" >&2
    exit 127
    ;;
esac

case "$cmd" in
  adapterremoval) target="AdapterRemoval" ;;
  pmdtools) target="pmdtools.py" ;;
  spades) target="spades.py" ;;
  quast) target="quast.py" ;;
  krona) target="ktImportText" ;;
  maxbin2) target="run_MaxBin.pl" ;;
  gtdb-tk) target="gtdbtk" ;;
  *) target="$cmd" ;;
esac

exec micromamba run -n "$env" "$target" "$@"
