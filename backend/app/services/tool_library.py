import copy
import json
import os
import re
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
    'caln50': 'assembly-authentication',
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
    'calN50': 'calN50.pl',
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

ADDITIONAL_TOOLS = [
    {
        'tool_name': 'FreeBayes',
        'description': 'Bayesian haplotype-based polymorphism discovery for aligned reads.',
        'parameters': [
            {'name': '-f', 'description': 'Reference FASTA file', 'type': 'file', 'extensions': ['.fasta', '.fa', '.fna']},
            {'name': 'alignment_bam', 'description': 'Aligned BAM file', 'type': 'file', 'extensions': ['.bam']},
            {'name': '-v', 'description': 'Output VCF file', 'type': 'string', 'default': 'variants.vcf'},
            {'name': '--min-alternate-fraction', 'description': 'Minimum alternate allele fraction', 'type': 'float', 'default': 0.33},
            {'name': '--min-base-quality', 'description': 'Minimum base quality', 'type': 'integer', 'default': 20},
            {'name': '--ploidy', 'description': 'Ploidy', 'type': 'integer', 'default': 1},
        ],
    },
    {
        'tool_name': 'BCFtools',
        'description': 'Utilities for variant calling and manipulating VCF/BCF files.',
        'parameters': [
            {'name': 'subcommand', 'description': 'BCFtools subcommand', 'type': 'string', 'options': ['view', 'filter', 'stats', 'index', 'sort', 'consensus'], 'default': 'view'},
            {'name': 'input_file', 'description': 'Input VCF/BCF file', 'type': 'file', 'extensions': ['.vcf', '.vcf.gz', '.bcf']},
            {'name': '-o', 'description': 'Output file', 'type': 'string', 'default': 'bcftools_output.vcf.gz'},
            {'name': '-O', 'description': 'Output type', 'type': 'string', 'options': ['u', 'b', 'v', 'z'], 'default': 'z'},
            {'name': '--threads', 'description': 'Number of threads', 'type': 'integer', 'default': 4},
        ],
    },
    {
        'tool_name': 'SeqKit',
        'description': 'A fast and cross-platform toolkit for FASTA/Q file manipulation.',
        'parameters': [
            {'name': 'subcommand', 'description': 'SeqKit subcommand', 'type': 'string', 'options': ['stats', 'seq', 'fx2tab', 'sample', 'grep'], 'default': 'stats'},
            {'name': 'input_file', 'description': 'Input FASTA/FASTQ file', 'type': 'file', 'extensions': ['.fasta', '.fa', '.fna', '.fastq', '.fq', '.fastq.gz', '.fq.gz']},
            {'name': '-o', 'description': 'Output file', 'type': 'string', 'default': 'seqkit_output.txt'},
            {'name': '-j', 'description': 'Number of threads', 'type': 'integer', 'default': 4},
        ],
    },
    {
        'tool_name': 'calN50',
        'description': 'Calculate assembly N50 and related continuity statistics from FASTA assemblies.',
        'parameters': [
            {'name': 'input_fasta', 'description': 'Input assembly FASTA file', 'type': 'file', 'extensions': ['.fasta', '.fa', '.fna']},
            {'name': '--output', 'description': 'Optional output file', 'type': 'string', 'default': 'caln50.txt'},
        ],
    },
    {
        'tool_name': 'CONCOCT',
        'description': 'Metagenomic binning using coverage and composition.',
        'parameters': [
            {'name': '--composition_file', 'description': 'Composition FASTA file', 'type': 'file', 'extensions': ['.fasta', '.fa', '.fna']},
            {'name': '--coverage_file', 'description': 'Coverage table TSV file', 'type': 'file', 'extensions': ['.tsv', '.txt']},
            {'name': '-b', 'description': 'Output directory prefix', 'type': 'directory', 'default': './concoct_output'},
            {'name': '-c', 'description': 'Number of clusters (optional)', 'type': 'integer'},
            {'name': '--threads', 'description': 'Number of threads', 'type': 'integer', 'default': 4},
        ],
    },
    {
        'tool_name': 'metaWRAP',
        'description': 'Wrapper utilities for metagenomic binning refinement and MAG improvement.',
        'parameters': [
            {'name': 'subcommand', 'description': 'metaWRAP subcommand', 'type': 'string', 'options': ['bin_refinement'], 'default': 'bin_refinement'},
            {'name': '-o', 'description': 'Output directory', 'type': 'directory', 'default': './metawrap_output'},
            {'name': '-A', 'description': 'Binning result set A', 'type': 'directory'},
            {'name': '-B', 'description': 'Binning result set B', 'type': 'directory'},
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
            {'name': 'input_genomes', 'description': 'Genome directory or FASTA file', 'type': 'directory'},
            {'name': '--out_dir', 'description': 'Output directory', 'type': 'directory', 'default': './gunc_output'},
            {'name': '--db_file', 'description': 'GUNC database file or directory', 'type': 'string'},
            {'name': '--threads', 'description': 'Number of threads', 'type': 'integer', 'default': 4},
        ],
    },
    {
        'tool_name': 'ABRicate',
        'description': 'Mass screening of contigs for antimicrobial resistance and virulence gene databases.',
        'parameters': [
            {'name': '--db', 'description': 'Database name', 'type': 'string', 'options': ['ncbi', 'card', 'vfdb', 'plasmidfinder', 'resfinder'], 'default': 'vfdb'},
            {'name': 'input_file', 'description': 'Input FASTA file', 'type': 'file', 'extensions': ['.fasta', '.fa', '.fna']},
            {'name': '--minid', 'description': 'Minimum percent identity', 'type': 'integer', 'default': 80},
            {'name': '--mincov', 'description': 'Minimum percent coverage', 'type': 'integer', 'default': 80},
        ],
    },
    {
        'tool_name': 'eggNOG-mapper',
        'description': 'Fast functional annotation using orthology assignments and KEGG/eggNOG databases.',
        'parameters': [
            {'name': '-i', 'description': 'Input protein FASTA file', 'type': 'file', 'extensions': ['.faa', '.fasta', '.fa']},
            {'name': '-o', 'description': 'Output prefix', 'type': 'string', 'default': 'eggnog_mapper'},
            {'name': '--cpu', 'description': 'Number of CPUs', 'type': 'integer', 'default': 4},
            {'name': '--itype', 'description': 'Input type', 'type': 'string', 'options': ['proteins', 'CDS'], 'default': 'proteins'},
        ],
    },
    {
        'tool_name': 'ThermoRawFileParser',
        'description': 'Convert Thermo RAW files to mzML for downstream paleoproteomics processing.',
        'parameters': [
            {'name': '--input', 'description': 'Input Thermo RAW file', 'type': 'file', 'extensions': ['.RAW']},
            {'name': '--output_file', 'description': 'Output mzML file', 'type': 'string', 'default': 'thermo_output.mzML'},
            {'name': '--format', 'description': 'Output format', 'type': 'string', 'options': ['0', '1', '2'], 'default': '1'},
            {'name': '--gzip', 'description': 'Compress output', 'type': 'flag', 'default': False},
        ],
    },
    {
        'tool_name': 'timsconvert',
        'description': 'Convert Bruker timsTOF .d datasets into mzML.',
        'parameters': [
            {'name': '--input', 'description': 'Input Bruker .d directory', 'type': 'directory'},
            {'name': '--outdir', 'description': 'Output directory', 'type': 'directory', 'default': './timsconvert_output'},
            {'name': '--outfile', 'description': 'Output filename prefix', 'type': 'string', 'default': 'bruker_output'},
            {'name': '--mode', 'description': 'Conversion mode', 'type': 'string', 'options': ['centroid', 'profile'], 'default': 'centroid'},
        ],
    },
    {
        'tool_name': 'OpenMS FileConverter',
        'description': 'Normalize or convert spectra files using OpenMS FileConverter.',
        'parameters': [
            {'name': '-in', 'description': 'Input spectra file', 'type': 'file', 'extensions': ['.mzML', '.mzXML', '.mgf']},
            {'name': '-out', 'description': 'Output spectra file', 'type': 'string', 'default': 'converted.mzML'},
            {'name': '-threads', 'description': 'Number of threads', 'type': 'integer', 'default': 4},
        ],
    },
    {
        'tool_name': 'MaxQuant',
        'description': 'Run MaxQuant in batch mode from an mqpar.xml configuration file.',
        'parameters': [
            {'name': 'maxquant_cmd_dll', 'description': 'Absolute path to MaxQuantCmd.dll', 'type': 'string', 'default': '/opt/tools/MaxQuant_v2.7.5.0/bin/MaxQuantCmd.dll', 'position': 0},
            {'name': 'mqpar_xml', 'description': 'mqpar.xml file', 'type': 'file', 'extensions': ['.xml'], 'position': 1},
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
            {'name': 'min_contig_len', 'description': 'Minimum contig length', 'type': 'integer', 'default': 500},
            {'name': 'use_ancient_contigs', 'description': 'Enable ancient-contig-only binning', 'type': 'flag', 'default': True},
            {'name': 'enable_checkm2', 'description': 'Run CheckM2 MAG quality assessment', 'type': 'flag', 'default': True},
            {'name': 'enable_gunc', 'description': 'Run GUNC contamination assessment', 'type': 'flag', 'default': True},
            {'name': 'enable_prokka', 'description': 'Run Prokka gene annotation', 'type': 'flag', 'default': True},
            {'name': 'enable_eggnog', 'description': 'Run eggNOG-mapper functional annotation', 'type': 'flag', 'default': True},
            {'name': 'enable_abricate', 'description': 'Run ABRicate screening', 'type': 'flag', 'default': True},
            {'name': 'enable_rgi', 'description': 'Run RGI resistome screening', 'type': 'flag', 'default': False},
            {'name': 'enable_antismash', 'description': 'Run antiSMASH BGC annotation', 'type': 'flag', 'default': True},
            {'name': 'annotation_threads', 'description': 'Threads for per-sample annotation modules', 'type': 'integer', 'default': 8},
            {'name': 'abricate_db', 'description': 'ABRicate database name', 'type': 'string', 'options': ['ncbi', 'card', 'vfdb', 'plasmidfinder', 'resfinder'], 'default': 'vfdb'},
            {'name': 'target_rule', 'description': 'Optional rule or file target', 'type': 'string'},
            {'name': 'dry_run', 'description': 'Only build the DAG without executing rules', 'type': 'flag', 'default': False},
            {'name': 'metawrap_env', 'description': 'Override MetaWRAP conda environment path (optional)', 'type': 'string'},
            {'name': 'pydamage_env', 'description': 'Override PyDamage environment path (optional)', 'type': 'string'},
            {'name': 'checkm_db', 'description': 'Override legacy CheckM1 database path (optional)', 'type': 'string'},
            {'name': 'checkm1_db', 'description': 'Override CheckM1 database path for MetaWRAP refinement (optional)', 'type': 'string'},
            {'name': 'checkm2_env', 'description': 'Override CheckM2 conda environment path (optional)', 'type': 'string'},
            {'name': 'checkm2_db', 'description': 'Override CheckM2 database path (optional)', 'type': 'string'},
            {'name': 'gunc_env', 'description': 'Override GUNC conda environment path (optional)', 'type': 'string'},
            {'name': 'gunc_db', 'description': 'Override GUNC database path (optional)', 'type': 'string'},
            {'name': 'prokka_env', 'description': 'Override Prokka conda environment path (optional)', 'type': 'string'},
            {'name': 'eggnog_env', 'description': 'Override eggNOG-mapper conda environment path (optional)', 'type': 'string'},
            {'name': 'eggnog_db', 'description': 'Override eggNOG database path (optional)', 'type': 'string'},
            {'name': 'abricate_env', 'description': 'Override ABRicate conda environment path (optional)', 'type': 'string'},
            {'name': 'rgi_env', 'description': 'Override RGI conda environment path (optional)', 'type': 'string'},
            {'name': 'rgi_db_mode', 'description': 'RGI database mode', 'type': 'string', 'options': ['online', 'local'], 'default': 'online'},
            {'name': 'rgi_db', 'description': 'Override local RGI database path when using local mode (optional)', 'type': 'string'},
            {'name': 'antismash_env', 'description': 'Override antiSMASH conda environment path (optional)', 'type': 'string'},
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
            {'name': 'fasta_path', 'description': 'Reference FASTA path (project-relative or absolute)', 'type': 'string', 'required': True},
            {'name': 'cores', 'description': 'Snakemake cores', 'type': 'integer', 'default': 4},
            {'name': 'match_between_runs', 'description': 'Enable MaxQuant match between runs', 'type': 'flag', 'default': False},
            {'name': 'include_contaminants', 'description': 'Include contaminants database', 'type': 'flag', 'default': True},
            {'name': 'min_peptide_length', 'description': 'Minimum peptide length', 'type': 'integer', 'default': 7},
            {'name': 'first_search_tol', 'description': 'First search tolerance (ppm)', 'type': 'float', 'default': 20},
            {'name': 'main_search_tol', 'description': 'Main search tolerance (ppm)', 'type': 'float', 'default': 4.5},
            {'name': 'target_rule', 'description': 'Optional rule or file target', 'type': 'string'},
            {'name': 'dry_run', 'description': 'Only build the DAG without executing rules', 'type': 'flag', 'default': False},
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
        execution.setdefault('command', COMMAND_OVERRIDES.get(tool['tool_name'], tool['tool_name'].lower()))
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
