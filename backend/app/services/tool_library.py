import copy
import json
import os
import re
import shutil
from pathlib import Path
from functools import lru_cache
from ..paths import BACKEND_ROOT


TOOL_LIBRARY_PATH = str(BACKEND_ROOT / 'tool_library.json')


SECTION_DEFINITIONS = [
    {
        'id': 'reads-qc',
        'title': 'Reads & QC',
        'description': 'Quality control and read preprocessing for ancient sequencing libraries.',
        'icon': 'reads',
        'order': 10,
    },
    {
        'id': 'read-taxonomy',
        'title': 'Read Taxonomy',
        'description': 'Read-level authentication and taxonomic profiling utilities.',
        'icon': 'taxonomy',
        'order': 20,
    },
    {
        'id': 'assembly-authentication',
        'title': 'Assembly & Authentication',
        'description': 'Assembly, alignment, variant calling, and aDNA authenticity analysis.',
        'icon': 'assembly',
        'order': 30,
    },
    {
        'id': 'binning-mags',
        'title': 'Binning & MAG Recovery',
        'description': 'MAG binning, refinement, quality assessment, and classification.',
        'icon': 'binning',
        'order': 40,
    },
    {
        'id': 'functional-annotation',
        'title': 'Genome Annotation',
        'description': 'Functional annotation, ARG/VF screening, and biosynthetic cluster analysis.',
        'icon': 'annotation',
        'order': 50,
    },
    {
        'id': 'paleoproteomics',
        'title': 'Paleoproteomics',
        'description': 'Raw conversion, mzML standardization, and MaxQuant-oriented proteomics tools.',
        'icon': 'proteomics',
        'order': 60,
    },
    {
        'id': 'workflow-automation',
        'title': 'Workflow Automation',
        'description': 'One-click Snakemake entry points for APPAM metagenomics and paleoproteomics workflows.',
        'icon': 'workflow',
        'order': 70,
    },
]

SECTION_BY_ID = {section['id']: section for section in SECTION_DEFINITIONS}

TOOL_SECTION_OVERRIDES = {
    'fastqc': 'reads-qc',
    'multiqc': 'reads-qc',
    'adapterremoval': 'reads-qc',
    'bwa': 'read-taxonomy',
    'pmdtools': 'read-taxonomy',
    'bedtools': 'read-taxonomy',
    'krakenuniq': 'read-taxonomy',
    'krona': 'read-taxonomy',
    'megahit': 'assembly-authentication',
    'spades': 'assembly-authentication',
    'quast': 'assembly-authentication',
    'bowtie2': 'assembly-authentication',
    'samtools': 'assembly-authentication',
    'freebayes': 'assembly-authentication',
    'bcftools': 'assembly-authentication',
    'pydamage': 'assembly-authentication',
    'seqkit': 'assembly-authentication',
    'metabat2': 'binning-mags',
    'maxbin2': 'binning-mags',
    'concoct': 'binning-mags',
    'metawrap': 'binning-mags',
    'checkm': 'binning-mags',
    'gunc': 'binning-mags',
    'gtdbtk': 'binning-mags',
    'gtdb-tk': 'binning-mags',
    'prokka': 'functional-annotation',
    'eggnog-mapper': 'functional-annotation',
    'rgi': 'functional-annotation',
    'abricate': 'functional-annotation',
    'antismash': 'functional-annotation',
    'thermorawfileparser': 'paleoproteomics',
    'timsconvert': 'paleoproteomics',
    'openms-fileconverter': 'paleoproteomics',
    'maxquant': 'paleoproteomics',
    'workflow-appam-smk': 'workflow-automation',
    'workflow-appam-paleoproteomics': 'workflow-automation',
}

COMMAND_OVERRIDES = {
    'FastQC': 'fastqc',
    'MultiQC': 'multiqc',
    'AdapterRemoval': 'AdapterRemoval',
    'bwa': 'bwa',
    'PMDtools': 'pmdtools.py',
    'bedtools': 'bedtools',
    'KrakenUniq': 'krakenuniq',
    'Krona': 'ktImportTaxonomy',
    'MEGAHIT': 'megahit',
    'SPAdes': 'spades.py',
    'QUAST': 'quast.py',
    'Bowtie2': 'bowtie2',
    'Samtools': 'samtools',
    'PyDamage': 'pydamage',
    'MetaBAT2': 'metabat2',
    'MaxBin2': 'run_MaxBin.pl',
    'CheckM': 'checkm2',
    'GTDB-Tk': 'gtdbtk',
    'PROKKA': 'prokka',
    'RGI': 'rgi',
    'antiSMASH': 'antismash',
    'FreeBayes': 'freebayes',
    'BCFtools': 'bcftools',
    'SeqKit': 'seqkit',
    'CONCOCT': 'concoct',
    'metaWRAP': 'metawrap',
    'GUNC': 'gunc',
    'ABRicate': 'abricate',
    'eggNOG-mapper': 'emapper.py',
    'ThermoRawFileParser': 'ThermoRawFileParser',
    'timsconvert': 'timsconvert',
    'OpenMS FileConverter': 'FileConverter',
    'MaxQuant': 'dotnet',
}

COMMAND_ENV_OVERRIDES = {
    'ThermoRawFileParser': 'APPAM_PALEO_THERMO_RAW_FILE_PARSER',
    'timsconvert': 'APPAM_PALEO_TIMSCONVERT_BIN',
    'OpenMS FileConverter': 'APPAM_PALEO_OPENMS_FILECONVERTER',
    'MaxQuant': 'APPAM_PALEO_DOTNET_BIN',
}

PREFIX_ARG_ENV_OVERRIDES = {
    'MaxQuant': ('APPAM_PALEO_MAXQUANT_CMD', '/opt/tools/maxquant-current/bin/MaxQuantCmd.dll'),
}

THREAD_PARAMETER_NAMES = {
    '--threads', '--cpus', '--cpu', '--num_threads',
    '-t', '-@', '-p', '-j', '-thread', '-threads',
}

ADMIN_ONLY_WORKFLOW_PARAMETERS = {
    'metawrap_env', 'pydamage_env', 'checkm_env', 'checkm1_env', 'checkm2_env',
    'gunc_env', 'gtdbtk_env', 'prokka_env', 'eggnog_env', 'abricate_env',
    'rgi_env', 'antismash_env', 'freebayes_env', 'bcftools_env', 'reporting_env',
    'checkm_db', 'checkm1_db', 'checkm2_db',
    'gunc_db', 'gtdbtk_db', 'eggnog_db', 'rgi_db', 'runtime_env', 'dotnet_bin',
    'maxquant_cmd_dll', 'thermo_raw_file_parser', 'timsconvert_bin',
    'openms_fileconverter',
}

TOOL_RUNTIME_REQUIREMENTS = {
    'KrakenUniq': {
        'required_paths': [
            ('APPAM_KRAKENUNIQ_KDB', '/databases/krakenuniq_refseq_bav/database.kdb', 'file', 'KrakenUniq database.kdb'),
            ('APPAM_KRAKENUNIQ_IDX', '/databases/krakenuniq_refseq_bav/database.idx', 'file', 'KrakenUniq database.idx'),
            ('APPAM_KRAKENUNIQ_TAXDB', '/databases/krakenuniq_refseq_bav/taxDB', 'file', 'KrakenUniq taxDB'),
        ],
    },
    'GTDB-Tk': {
        'environment': {
            'GTDBTK_DATA_PATH': ('APPAM_SMK_GTDBTK_DB', '/databases/gtdbtk_r226'),
        },
        'required_paths': [
            ('APPAM_SMK_GTDBTK_DB', '/databases/gtdbtk_r226', 'directory', 'GTDB-Tk database'),
        ],
    },
    'MaxQuant': {
        'required_paths': [
            ('APPAM_PALEO_MAXQUANT_CMD', '/opt/tools/maxquant-current/bin/MaxQuantCmd.dll', 'file', 'MaxQuantCmd.dll'),
        ],
    },
}

ADDITIONAL_TOOLS = [
    {
        'tool_name': 'FreeBayes',
        'description': 'Bayesian haplotype-based polymorphism discovery for aligned reads.',
        'parameters': [
            {'name': '-f', 'description': 'Reference FASTA file', 'type': 'file', 'extensions': ['.fasta', '.fa', '.fna'], 'required': True},
            {'name': 'alignment_bam', 'description': 'Aligned BAM file', 'type': 'file', 'extensions': ['.bam'], 'positional': True, 'order': 100, 'required': True},
            {'name': '-v', 'description': 'Output VCF file', 'type': 'string', 'default': 'results/freebayes/variants.vcf', 'path_role': 'output', 'path_kind': 'file'},
            {'name': '--min-alternate-fraction', 'description': 'Minimum alternate allele fraction', 'type': 'float', 'default': 0.33},
            {'name': '--min-base-quality', 'description': 'Minimum base quality', 'type': 'integer', 'default': 20},
            {'name': '--ploidy', 'description': 'Ploidy', 'type': 'integer', 'default': 1},
        ],
    },
    {
        'tool_name': 'BCFtools',
        'description': 'Utilities for variant calling and manipulating VCF/BCF files.',
        'parameters': [
            {'name': 'subcommand', 'description': 'BCFtools subcommand', 'type': 'string', 'options': ['view'], 'default': 'view', 'positional': True, 'order': 0, 'required': True},
            {'name': 'input_file', 'description': 'Input VCF/BCF file', 'type': 'file', 'extensions': ['.vcf', '.vcf.gz', '.bcf'], 'positional': True, 'order': 100, 'required': True},
            {'name': '-o', 'description': 'Output file', 'type': 'string', 'default': 'results/bcftools/output.vcf.gz', 'path_role': 'output', 'path_kind': 'file'},
            {'name': '-O', 'description': 'Output type', 'type': 'string', 'options': ['u', 'b', 'v', 'z'], 'default': 'z'},
            {'name': '--threads', 'description': 'Number of threads', 'type': 'integer', 'default': 4},
        ],
    },
    {
        'tool_name': 'SeqKit',
        'description': 'A fast and cross-platform toolkit for FASTA/Q file manipulation.',
        'parameters': [
            {'name': 'subcommand', 'description': 'SeqKit subcommand', 'type': 'string', 'options': ['stats'], 'default': 'stats', 'positional': True, 'order': 0, 'required': True},
            {'name': 'input_file', 'description': 'Input FASTA/FASTQ file', 'type': 'file', 'extensions': ['.fasta', '.fa', '.fna', '.fastq', '.fq', '.fastq.gz', '.fq.gz'], 'positional': True, 'order': 100, 'required': True},
            {'name': '-o', 'description': 'Output file', 'type': 'string', 'default': 'results/seqkit/stats.tsv', 'path_role': 'output', 'path_kind': 'file'},
            {'name': '-j', 'description': 'Number of threads', 'type': 'integer', 'default': 4},
        ],
    },
    {
        'tool_name': 'CONCOCT',
        'description': 'Metagenomic binning using coverage and composition.',
        'parameters': [
            {'name': '--composition_file', 'description': 'Composition FASTA file', 'type': 'file', 'extensions': ['.fasta', '.fa', '.fna']},
            {'name': '--coverage_file', 'description': 'Coverage table TSV file', 'type': 'file', 'extensions': ['.tsv', '.txt']},
            {'name': '-b', 'description': 'Output directory prefix', 'type': 'directory', 'default': 'results/concoct', 'path_role': 'output', 'create_output_directory': True},
            {'name': '-c', 'description': 'Number of clusters (optional)', 'type': 'integer'},
            {'name': '--threads', 'description': 'Number of threads', 'type': 'integer', 'default': 4},
        ],
    },
    {
        'tool_name': 'metaWRAP',
        'description': 'Wrapper utilities for metagenomic binning refinement and MAG improvement.',
        'parameters': [
            {'name': 'subcommand', 'description': 'metaWRAP subcommand', 'type': 'string', 'options': ['bin_refinement'], 'default': 'bin_refinement', 'positional': True, 'order': 0, 'required': True},
            {'name': '-o', 'description': 'Output directory', 'type': 'directory', 'default': 'results/metawrap', 'path_role': 'output', 'create_output_directory': True},
            {'name': '-A', 'description': 'Binning result set A', 'type': 'directory', 'required': True},
            {'name': '-B', 'description': 'Binning result set B', 'type': 'directory', 'required': True},
            {'name': '-C', 'description': 'Binning result set C', 'type': 'directory'},
            {'name': '-t', 'description': 'Number of threads', 'type': 'integer', 'default': 8},
            {'name': '-c', 'description': 'Minimum completeness threshold', 'type': 'integer', 'default': 50},
            {'name': '-x', 'description': 'Maximum contamination threshold', 'type': 'integer', 'default': 10},
        ],
    },
    {
        'tool_name': 'GUNC',
        'description': 'Genome UNClutterer for chimerism and contamination detection in genomes.',
        'parameters': [
            {'name': 'command', 'description': 'GUNC operation', 'type': 'string', 'options': ['run'], 'default': 'run', 'positional': True, 'order': 0, 'required': True},
            {'name': '--input_dir', 'description': 'Directory containing genome FASTA files', 'type': 'directory', 'required': True},
            {'name': '--out_dir', 'description': 'Output directory', 'type': 'directory', 'default': 'results/gunc', 'path_role': 'output', 'create_output_directory': True},
            {'name': '--db_file', 'description': 'GUNC database under APPAM_DATABASES_ROOT', 'type': 'string', 'default': 'gunc', 'default_env': 'APPAM_SMK_GUNC_DB', 'path_role': 'input', 'path_scope': 'shared', 'path_kind': 'file', 'path_select': '*.dmnd', 'required': True},
            {'name': '--threads', 'description': 'Number of threads', 'type': 'integer', 'default': 4},
        ],
    },
    {
        'tool_name': 'ABRicate',
        'description': 'Mass screening of contigs for antimicrobial resistance and virulence gene databases.',
        'parameters': [
            {'name': '--db', 'description': 'Database name', 'type': 'string', 'options': ['ncbi', 'card', 'vfdb', 'plasmidfinder', 'resfinder'], 'default': 'vfdb'},
            {'name': 'input_file', 'description': 'Input FASTA file', 'type': 'file', 'extensions': ['.fasta', '.fa', '.fna'], 'positional': True, 'order': 100, 'required': True},
            {'name': '--minid', 'description': 'Minimum percent identity', 'type': 'integer', 'default': 80},
            {'name': '--mincov', 'description': 'Minimum percent coverage', 'type': 'integer', 'default': 80},
            {'name': 'output_file', 'description': 'Screening result table', 'type': 'string', 'default': 'results/abricate/results.tsv', 'path_role': 'output', 'path_kind': 'file', 'stream': 'stdout', 'required': True},
        ],
    },
    {
        'tool_name': 'eggNOG-mapper',
        'description': 'Fast functional annotation using orthology assignments and KEGG/eggNOG databases.',
        'parameters': [
            {'name': '-i', 'description': 'Input protein FASTA file', 'type': 'file', 'extensions': ['.faa', '.fasta', '.fa'], 'required': True},
            {'name': '-o', 'description': 'Output prefix', 'type': 'string', 'default': 'results/eggnog/annotation', 'path_role': 'output', 'path_kind': 'prefix'},
            {'name': '--data_dir', 'description': 'eggNOG database under APPAM_DATABASES_ROOT', 'type': 'string', 'default': 'eggnog', 'default_env': 'APPAM_SMK_EGGNOG_DB', 'path_role': 'input', 'path_scope': 'shared', 'path_kind': 'directory'},
            {'name': '--cpu', 'description': 'Number of CPUs', 'type': 'integer', 'default': 4},
            {'name': '--itype', 'description': 'Input type', 'type': 'string', 'options': ['proteins', 'CDS'], 'default': 'proteins'},
        ],
    },
    {
        'tool_name': 'ThermoRawFileParser',
        'description': 'Convert Thermo RAW files to mzML for downstream paleoproteomics processing.',
        'parameters': [
            {'name': '-i', 'description': 'Input Thermo RAW file', 'type': 'file', 'extensions': ['.RAW', '.raw'], 'required': True, 'separator': '='},
            {'name': '-b', 'description': 'Output mzML file', 'type': 'string', 'default': 'results/paleoproteomics/thermo_output.mzML', 'path_role': 'output', 'path_kind': 'file', 'separator': '='},
            {'name': '-f', 'description': 'Output format', 'type': 'string', 'options': ['2'], 'default': '2', 'separator': '='},
            {'name': '-m', 'description': 'Metadata output mode', 'type': 'string', 'options': ['2', '0', '1'], 'default': '2', 'separator': '='},
        ],
    },
    {
        'tool_name': 'timsconvert',
        'description': 'Convert Bruker timsTOF .d datasets into mzML.',
        'parameters': [
            {'name': '--input', 'description': 'Input Bruker .d directory', 'type': 'directory', 'required': True},
            {'name': '--outdir', 'description': 'Output directory', 'type': 'directory', 'default': 'results/paleoproteomics/timsconvert', 'path_role': 'output', 'create_output_directory': True},
            {'name': '--mode', 'description': 'Conversion mode', 'type': 'string', 'options': ['raw'], 'default': 'raw'},
        ],
    },
    {
        'tool_name': 'OpenMS FileConverter',
        'description': 'Normalize or convert spectra files using OpenMS FileConverter.',
        'parameters': [
            {'name': '-in', 'description': 'Input spectra file', 'type': 'file', 'extensions': ['.mzML', '.mzXML', '.mgf'], 'required': True},
            {'name': '-out', 'description': 'Output spectra file', 'type': 'string', 'default': 'results/paleoproteomics/converted.mzML', 'path_role': 'output', 'path_kind': 'file'},
            {'name': '-threads', 'description': 'Number of threads', 'type': 'integer', 'default': 4},
        ],
    },
    {
        'tool_name': 'MaxQuant',
        'admin_only': True,
        'description': 'Run MaxQuant in batch mode from an mqpar.xml configuration file.',
        'parameters': [
            {'name': 'mqpar_xml', 'description': 'mqpar.xml file', 'type': 'file', 'extensions': ['.xml'], 'position': 0, 'required': True},
        ],
    },
    {
        'id': 'workflow-appam-smk',
        'tool_name': 'APPAM-SMK Workflow',
        'kind': 'workflow',
        'description': 'One-click Snakemake launch for the APPAM-SMK ancient metagenomics workflow.',
        'run_label': 'Run Workflow',
        'notes': [
            'Generates a project-local config file and runs APPAM-SMK with Snakemake.',
            'Requires Snakemake on PATH plus configured Docker/runtime resources and mounted workflow databases.',
            'Outputs are written under workflow_runs/appam-smk within the current project.',
        ],
        'execution': {
            'mode': 'snakemake',
            'workflow_id': 'appam-smk',
        },
        'parameters': [
            {'name': 'sample_manifest', 'description': 'Project-relative samples.tsv file for APPAM-SMK', 'type': 'file', 'extensions': ['.tsv'], 'required': True},
            {'name': 'raw_data_dir', 'description': 'Project-relative directory containing raw FASTQ files', 'type': 'directory', 'required': True},
            {'name': 'profile', 'description': 'Snakemake execution profile', 'type': 'string', 'options': ['local', 'slurm'], 'default': 'local'},
            {'name': 'cores', 'description': 'Local cores or maximum queued jobs', 'type': 'integer', 'default': 4},
            {'name': 'preprocess_method', 'description': 'Preprocessing backend', 'type': 'string', 'options': ['adapter_removal', 'fastp'], 'default': 'fastp'},
            {'name': 'min_contig_len', 'description': 'Minimum contig length', 'type': 'integer', 'default': 500, 'minimum': 1},
            {'name': 'use_ancient_contigs', 'description': 'Experimental: restrict binning to PyDamage-positive contigs', 'type': 'flag', 'default': False},
            {'name': 'enable_bin_refinement', 'description': 'Refine MetaBAT2/MaxBin2/CONCOCT bins with MetaWRAP and CheckM1', 'type': 'flag', 'default': False},
            {'name': 'unrefined_binner', 'description': 'Bin set used when refinement is disabled', 'type': 'string', 'options': ['metabat2', 'maxbin2', 'concoct'], 'default': 'metabat2'},
            {'name': 'enable_checkm1', 'description': 'Run the standalone CheckM1 quality report', 'type': 'flag', 'default': False},
            {'name': 'enable_checkm2', 'description': 'Run CheckM2 MAG quality assessment', 'type': 'flag', 'default': True},
            {'name': 'enable_gunc', 'description': 'Run GUNC contamination assessment', 'type': 'flag', 'default': True},
            {'name': 'enable_gtdbtk', 'description': 'Run GTDB-Tk taxonomic classification', 'type': 'flag', 'default': True},
            {'name': 'enable_prokka', 'description': 'Run Prokka gene annotation', 'type': 'flag', 'default': True},
            {'name': 'enable_eggnog', 'description': 'Run eggNOG-mapper functional annotation', 'type': 'flag', 'default': False},
            {'name': 'enable_abricate', 'description': 'Run ABRicate screening', 'type': 'flag', 'default': False},
            {'name': 'enable_rgi', 'description': 'Run RGI resistome screening', 'type': 'flag', 'default': False},
            {'name': 'enable_antismash', 'description': 'Run antiSMASH BGC annotation', 'type': 'flag', 'default': False},
            {'name': 'enable_variants', 'description': 'Run haploid FreeBayes variant calling and build a consensus sequence', 'type': 'flag', 'default': False},
            {'name': 'enable_visualization', 'description': 'Generate publication-ready plots and a self-contained report', 'type': 'flag', 'default': True},
            {'name': 'annotation_threads', 'description': 'Threads for per-sample annotation modules', 'type': 'integer', 'default': 8},
            {'name': 'abricate_db', 'description': 'ABRicate database name', 'type': 'string', 'options': ['ncbi', 'card', 'vfdb', 'plasmidfinder', 'resfinder'], 'default': 'vfdb'},
            {'name': 'target_rule', 'description': 'Optional rule or file target', 'type': 'string'},
            {'name': 'dry_run', 'description': 'Only build the DAG without executing rules', 'type': 'flag', 'default': False},
            {'name': 'input_hash_mode', 'description': 'Input provenance fingerprint mode', 'type': 'string', 'options': ['metadata', 'sha256'], 'default': 'metadata'},
            {'name': 'require_database_manifest', 'description': 'Require a versioned appam-db-manifest.json before execution', 'type': 'flag', 'default': False},
            {'name': 'metawrap_env', 'description': 'Override MetaWRAP conda environment path (optional)', 'type': 'string'},
            {'name': 'pydamage_env', 'description': 'Override PyDamage environment path (optional)', 'type': 'string'},
            {'name': 'checkm1_env', 'description': 'Override CheckM1 conda environment path (optional)', 'type': 'string'},
            {'name': 'checkm_db', 'description': 'Override legacy CheckM1 database path (optional)', 'type': 'string'},
            {'name': 'checkm1_db', 'description': 'Override CheckM1 database path for MetaWRAP refinement (optional)', 'type': 'string'},
            {'name': 'checkm2_env', 'description': 'Override CheckM2 conda environment path (optional)', 'type': 'string'},
            {'name': 'checkm2_db', 'description': 'Override CheckM2 database path (optional)', 'type': 'string'},
            {'name': 'gunc_env', 'description': 'Override GUNC conda environment path (optional)', 'type': 'string'},
            {'name': 'gunc_db', 'description': 'Override GUNC database path (optional)', 'type': 'string'},
            {'name': 'gtdbtk_env', 'description': 'Override GTDB-Tk conda environment path (optional)', 'type': 'string'},
            {'name': 'gtdbtk_db', 'description': 'Override GTDB-Tk reference data path (optional)', 'type': 'string'},
            {'name': 'prokka_env', 'description': 'Override Prokka conda environment path (optional)', 'type': 'string'},
            {'name': 'eggnog_env', 'description': 'Override eggNOG-mapper conda environment path (optional)', 'type': 'string'},
            {'name': 'eggnog_db', 'description': 'Override eggNOG database path (optional)', 'type': 'string'},
            {'name': 'abricate_env', 'description': 'Override ABRicate conda environment path (optional)', 'type': 'string'},
            {'name': 'rgi_env', 'description': 'Override RGI conda environment path (optional)', 'type': 'string'},
            {'name': 'rgi_db_mode', 'description': 'RGI database mode', 'type': 'string', 'options': ['global', 'local'], 'default': 'global'},
            {'name': 'rgi_db', 'description': 'Override local RGI database path when using local mode (optional)', 'type': 'string'},
            {'name': 'antismash_env', 'description': 'Override antiSMASH conda environment path (optional)', 'type': 'string'},
            {'name': 'freebayes_env', 'description': 'Override FreeBayes conda environment path (optional)', 'type': 'string'},
            {'name': 'bcftools_env', 'description': 'Override BCFtools conda environment path (optional)', 'type': 'string'},
            {'name': 'reporting_env', 'description': 'Override reporting conda environment path (optional)', 'type': 'string'},
        ],
    },
    {
        'id': 'workflow-appam-paleoproteomics',
        'tool_name': 'APPAM Paleoproteomics Workflow',
        'kind': 'workflow',
        'description': 'One-click Snakemake launch for the APPAM paleoproteomics workflow.',
        'run_label': 'Run Workflow',
        'notes': [
            'Generates a project-local config file and runs the paleoproteomics workflow with Snakemake.',
            'Requires host or container access to ThermoRawFileParser, timsconvert, OpenMS FileConverter, dotnet, and MaxQuant.',
            'Outputs are written under workflow_runs/appam-paleoproteomics within the current project.',
        ],
        'execution': {
            'mode': 'snakemake',
            'workflow_id': 'appam-paleoproteomics',
        },
        'parameters': [
            {'name': 'sample_table', 'description': 'Project-relative samples.tsv file for paleoproteomics', 'type': 'file', 'extensions': ['.tsv'], 'required': True},
            {'name': 'fasta_path', 'description': 'Reference FASTA in this project or APPAM_DATABASES_ROOT', 'type': 'string', 'required': True},
            {'name': 'cores', 'description': 'Snakemake cores', 'type': 'integer', 'default': 4},
            {'name': 'maxquant_mode', 'description': 'Run one joint MaxQuant search or one search per sample ID', 'type': 'string', 'options': ['batch', 'per_sample_id'], 'default': 'batch'},
            {'name': 'match_between_runs', 'description': 'Enable MaxQuant match between runs', 'type': 'flag', 'default': False},
            {'name': 'enzymes', 'description': 'Comma-separated MaxQuant enzymes', 'type': 'string', 'default': 'Trypsin/P'},
            {'name': 'enzyme_mode', 'description': 'MaxQuant enzyme mode', 'type': 'integer', 'default': 4, 'minimum': 0, 'maximum': 5},
            {'name': 'max_missed_cleavages', 'description': 'Maximum missed cleavages', 'type': 'integer', 'default': 0, 'minimum': 0, 'maximum': 10},
            {'name': 'max_missed_cleavages_dia', 'description': 'Maximum missed cleavages for DIA searches', 'type': 'integer', 'default': 0, 'minimum': 0, 'maximum': 10},
            {'name': 'fixed_modifications', 'description': 'Comma-separated fixed modifications', 'type': 'string', 'default': 'Carbamidomethyl (C)'},
            {'name': 'variable_modifications', 'description': 'Comma-separated variable modifications', 'type': 'string', 'default': 'Deamidation (NQ),Oxidation (MP),Gln->pyro-Glu,Glu->pyro-Glu,Phospho (ST)'},
            {'name': 'peptide_fdr', 'description': 'Peptide-level FDR', 'type': 'float', 'default': 0.01, 'minimum': 0, 'maximum': 1},
            {'name': 'protein_fdr', 'description': 'Protein-level FDR', 'type': 'float', 'default': 0.01, 'minimum': 0, 'maximum': 1},
            {'name': 'site_fdr', 'description': 'Modification-site FDR', 'type': 'float', 'default': 0.01, 'minimum': 0, 'maximum': 1},
            {'name': 'include_contaminants', 'description': 'Include contaminants database', 'type': 'flag', 'default': True},
            {'name': 'min_peptide_length', 'description': 'Minimum peptide length', 'type': 'integer', 'default': 7, 'minimum': 1},
            {'name': 'first_search_tol', 'description': 'First search tolerance (ppm)', 'type': 'float', 'default': 20, 'minimum': 0.01},
            {'name': 'main_search_tol', 'description': 'Main search tolerance (ppm)', 'type': 'float', 'default': 4.5, 'minimum': 0.01},
            {'name': 'target_rule', 'description': 'Optional rule or file target', 'type': 'string'},
            {'name': 'dry_run', 'description': 'Only build the DAG without executing rules', 'type': 'flag', 'default': False},
            {'name': 'input_hash_mode', 'description': 'Input provenance fingerprint mode', 'type': 'string', 'options': ['metadata', 'sha256'], 'default': 'metadata'},
            {'name': 'dotnet_bin', 'description': 'Override dotnet binary (optional)', 'type': 'string'},
            {'name': 'maxquant_cmd_dll', 'description': 'Override MaxQuantCmd.dll path (optional)', 'type': 'string'},
            {'name': 'thermo_raw_file_parser', 'description': 'Override ThermoRawFileParser binary (optional)', 'type': 'string'},
            {'name': 'timsconvert_bin', 'description': 'Override timsconvert binary (optional)', 'type': 'string'},
            {'name': 'openms_fileconverter', 'description': 'Override OpenMS FileConverter binary (optional)', 'type': 'string'},
        ],
    },
]


def _slugify(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', str(value).strip().lower()).strip('-')


def _load_base_tools():
    with open(TOOL_LIBRARY_PATH, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def _infer_section_id(tool: dict) -> str:
    explicit = tool.get('section')
    if explicit in SECTION_BY_ID:
        return explicit

    tool_id = tool.get('id') or _slugify(tool.get('tool_name', 'tool'))
    if tool_id in TOOL_SECTION_OVERRIDES:
        return TOOL_SECTION_OVERRIDES[tool_id]

    normalized_name = _slugify(tool.get('tool_name', 'tool'))
    if normalized_name in TOOL_SECTION_OVERRIDES:
        return TOOL_SECTION_OVERRIDES[normalized_name]

    description = str(tool.get('description', '')).lower()
    if 'proteomics' in description or 'mzml' in description or 'maxquant' in description:
        return 'paleoproteomics'
    if 'annotation' in description or 'resistance' in description or 'biosynthetic' in description:
        return 'functional-annotation'
    if 'bin' in description or 'mag' in description or 'genome' in description:
        return 'binning-mags'
    if 'assembly' in description or 'align' in description or 'damage' in description or 'variant' in description:
        return 'assembly-authentication'
    if 'taxonomy' in description or 'classification' in description:
        return 'read-taxonomy'
    return 'reads-qc'


def _normalize_tool(raw_tool: dict) -> dict:
    tool = copy.deepcopy(raw_tool)
    tool_id = tool.get('id') or _slugify(tool.get('tool_name', 'tool'))
    tool['id'] = tool_id
    tool['kind'] = tool.get('kind', 'tool')
    tool['parameters'] = tool.get('parameters', [])
    max_tool_threads = max(1, int(os.getenv('APPAM_MAX_TOOL_THREADS', str(os.cpu_count() or 1))))
    max_workflow_cores = max(1, int(os.getenv('APPAM_MAX_WORKFLOW_CORES', str(max(64, os.cpu_count() or 1)))))
    for parameter in tool['parameters']:
        default_env = parameter.get('default_env')
        if default_env and os.getenv(default_env):
            parameter['default'] = os.getenv(default_env)
        if tool.get('kind', 'tool') != 'workflow' and parameter.get('type') == 'integer' and parameter.get('name') in THREAD_PARAMETER_NAMES:
            parameter.setdefault('minimum', 1)
            parameter.setdefault('maximum', max_tool_threads)
            if parameter.get('default') is not None:
                parameter['default'] = min(max_tool_threads, max(1, int(parameter['default'])))
        if tool.get('kind', 'tool') == 'workflow' and parameter.get('name') in ADMIN_ONLY_WORKFLOW_PARAMETERS:
            parameter['admin_only'] = True
        if tool.get('kind', 'tool') == 'workflow' and parameter.get('type') == 'integer' and parameter.get('name') in {'cores', 'annotation_threads'}:
            parameter.setdefault('minimum', 1)
            parameter.setdefault('maximum', max_workflow_cores)
            if parameter.get('default') is not None:
                parameter['default'] = min(max_workflow_cores, max(1, int(parameter['default'])))
    tool['notes'] = tool.get('notes', [])
    tool['run_label'] = tool.get('run_label') or ('Run Workflow' if tool['kind'] == 'workflow' else 'Run Tool')

    section_id = _infer_section_id(tool)
    section = SECTION_BY_ID[section_id]
    tool['section'] = section_id
    tool['section_title'] = section['title']
    tool['section_description'] = section['description']
    tool['section_icon'] = section['icon']
    tool['section_order'] = section['order']

    execution = copy.deepcopy(tool.get('execution') or {})
    if tool['kind'] == 'workflow':
        execution.setdefault('mode', 'snakemake')
    else:
        execution.setdefault('mode', 'command')
        command_env = COMMAND_ENV_OVERRIDES.get(tool['tool_name'])
        configured_command = os.getenv(command_env) if command_env else None
        execution.setdefault('command', configured_command or COMMAND_OVERRIDES.get(tool['tool_name'], tool['tool_name'].lower()))
        prefix_arg_env = PREFIX_ARG_ENV_OVERRIDES.get(tool['tool_name'])
        if prefix_arg_env:
            environment_name, fallback = prefix_arg_env
            execution.setdefault('prefix_args', [os.getenv(environment_name, fallback)])
        runtime_requirements = TOOL_RUNTIME_REQUIREMENTS.get(tool['tool_name']) or {}
        runtime_environment = {
            name: os.getenv(environment_name, fallback)
            for name, (environment_name, fallback) in (runtime_requirements.get('environment') or {}).items()
        }
        if runtime_environment:
            execution.setdefault('env', runtime_environment)
        required_paths = [
            {
                'path': os.getenv(environment_name, fallback),
                'kind': kind,
                'label': label,
            }
            for environment_name, fallback, kind, label in runtime_requirements.get('required_paths') or []
        ]
        if required_paths:
            execution.setdefault('required_paths', required_paths)
    tool['execution'] = execution
    return tool


@lru_cache(maxsize=1)
def get_tool_library():
    tools = [_normalize_tool(tool) for tool in _load_base_tools()]
    tools.extend(_normalize_tool(tool) for tool in ADDITIONAL_TOOLS)
    tools.sort(key=lambda item: (item['section_order'], item['tool_name'].lower()))
    return tools


def get_tool_library_map():
    mapping = {}
    for tool in get_tool_library():
        mapping[tool['id']] = tool
        mapping[_slugify(tool['tool_name'])] = tool
        mapping[tool['tool_name'].lower()] = tool
    return mapping


def get_tool_definition(tool_key: str):
    if not tool_key:
        return None
    return get_tool_library_map().get(tool_key.lower())


def get_tool_sections():
    section_items = {section['id']: [] for section in SECTION_DEFINITIONS}
    for tool in get_tool_library():
        section_items.setdefault(tool['section'], []).append(tool)

    sections = []
    for section in SECTION_DEFINITIONS:
        items = section_items.get(section['id'], [])
        if not items:
            continue
        sections.append({
            **section,
            'tools': items,
        })
    return sections


def get_tool_runtime_status(tool: dict) -> dict:
    execution = tool.get('execution') or {}
    if tool.get('kind') == 'workflow':
        command = os.getenv('APPAM_SNAKEMAKE_BIN', 'snakemake')
    else:
        command = execution.get('command')

    if not command:
        return {'available': False, 'availability_message': 'No executable configured'}
    command_path = Path(str(command)).expanduser()
    executable = (
        str(command_path.resolve())
        if command_path.is_absolute() and command_path.is_file() and os.access(command_path, os.X_OK)
        else shutil.which(str(command))
    )
    if not executable:
        return {'available': False, 'availability_message': f'Executable not found: {command}'}

    for requirement in execution.get('required_paths') or []:
        path = Path(str(requirement.get('path') or '')).expanduser()
        kind = requirement.get('kind', 'any')
        exists = path.is_file() if kind == 'file' else path.is_dir() if kind == 'directory' else path.exists()
        if not exists:
            return {
                'available': False,
                'availability_message': f'{requirement.get("label") or "Runtime resource"} not found',
            }
    shared_root = Path(os.getenv('APPAM_DATABASES_ROOT', '/databases')).expanduser().resolve()
    for parameter in tool.get('parameters') or []:
        if parameter.get('path_role') != 'input' or parameter.get('path_scope') != 'shared':
            continue
        value = parameter.get('default')
        if not value:
            continue
        path = Path(str(value)).expanduser()
        if not path.is_absolute():
            path = shared_root / path
        path = path.resolve()
        if path != shared_root and shared_root not in path.parents:
            return {'available': False, 'availability_message': f'{parameter["name"]} is outside APPAM_DATABASES_ROOT'}
        selector = parameter.get('path_select')
        if selector and path.is_dir():
            exists = any(candidate.is_file() for candidate in path.rglob(str(selector)))
        else:
            kind = parameter.get('path_kind', 'any')
            exists = path.is_file() if kind == 'file' else path.is_dir() if kind == 'directory' else path.exists()
        if not exists:
            return {
                'available': False,
                'availability_message': f'{parameter.get("description") or parameter["name"]} not found',
            }
    return {'available': True, 'availability_message': 'Ready'}


def get_tool_catalog():
    tools = []
    by_id = {}
    for source in get_tool_library():
        tool = copy.deepcopy(source)
        tool.update(get_tool_runtime_status(tool))
        tools.append(tool)
        by_id[tool['id']] = tool

    tools_by_key = {
        key: by_id[source['id']]
        for key, source in get_tool_library_map().items()
    }
    sections = []
    for source_section in get_tool_sections():
        section = copy.deepcopy(source_section)
        section['tools'] = [by_id[tool['id']] for tool in source_section['tools']]
        sections.append(section)
    return tools, tools_by_key, sections
