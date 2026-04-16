import re


RULE_PATTERNS = (
    re.compile(r'(?:^|\n)(?:local)?rule\s+([A-Za-z0-9_:-]+):'),
    re.compile(r'(?:^|\n)checkpoint\s+([A-Za-z0-9_:-]+):'),
)


WORKFLOW_RUNTIME_DEFINITIONS = {
    'appam-smk': {
        'id': 'appam-smk',
        'title': 'APPAM-SMK Workflow',
        'stages': [
            {
                'id': 'qc-trim',
                'title': 'Adapter / QC',
                'optional': False,
                'rules': ['fastp_preprocess', 'fastqc', 'adapter_removal', 'collapse_to_single_end'],
            },
            {
                'id': 'assembly',
                'title': 'Assembly',
                'optional': False,
                'rules': ['megahit'],
            },
            {
                'id': 'alignment-validation',
                'title': 'Alignment & aDNA Validation',
                'optional': False,
                'rules': ['bowtie2_index', 'bowtie2_align', 'index_bam', 'freebayes', 'bcftools', 'pydamage'],
            },
            {
                'id': 'filter-contigs',
                'title': 'Filter Contigs',
                'optional': False,
                'rules': ['split_contigs_by_pydamage'],
            },
            {
                'id': 'binning',
                'title': 'Binning / Refinement / Evaluation',
                'optional': False,
                'rules': ['metawrap_binning', 'metawrap_bin_refinement', 'checkm', 'gunc'],
            },
            {
                'id': 'taxonomy-annotation',
                'title': 'Species / Genome Annotation',
                'optional': False,
                'rules': ['gtdbtk_classify'],
            },
        ],
    },
    'appam-paleoproteomics': {
        'id': 'appam-paleoproteomics',
        'title': 'APPAM Paleoproteomics Workflow',
        'stages': [
            {
                'id': 'thermo-convert',
                'title': 'Thermo Conversion',
                'optional': False,
                'rules': ['thermo_raw_to_mzml'],
            },
            {
                'id': 'bruker-convert',
                'title': 'Bruker Conversion',
                'optional': False,
                'rules': ['bruker_d_to_mzml'],
            },
            {
                'id': 'mzml-standardize',
                'title': 'mzML Standardization',
                'optional': False,
                'rules': ['finalize_raw_mzml', 'finalize_bruker_mzml'],
            },
            {
                'id': 'mqpar',
                'title': 'mqpar Generation',
                'optional': False,
                'rules': ['render_mqpar'],
            },
            {
                'id': 'maxquant',
                'title': 'MaxQuant Search',
                'optional': False,
                'rules': ['run_maxquant'],
            },
        ],
    },
}


def get_workflow_runtime_definition(workflow_id: str):
    if not workflow_id:
        return None
    return WORKFLOW_RUNTIME_DEFINITIONS.get(str(workflow_id).strip())


def get_workflow_stage_definitions(workflow_id: str):
    definition = get_workflow_runtime_definition(workflow_id)
    if not definition:
        return []
    stages = []
    for index, stage in enumerate(definition.get('stages', [])):
        stages.append({
            'id': stage['id'],
            'title': stage['title'],
            'optional': bool(stage.get('optional', False)),
            'rules': list(stage.get('rules', [])),
            'order': index,
        })
    return stages


def get_rule_to_stage_map(workflow_id: str):
    mapping = {}
    for stage in get_workflow_stage_definitions(workflow_id):
        for rule_name in stage.get('rules', []):
            mapping[rule_name] = stage
    return mapping


def detect_rule_name(line: str):
    text = line or ''
    for pattern in RULE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None

