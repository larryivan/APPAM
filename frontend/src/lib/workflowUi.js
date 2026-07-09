export const WORKFLOW_OPTIONS = Object.freeze([
  {
    id: 'appam-smk',
    label: 'Ancient metagenomics',
    shortLabel: 'Metagenomics',
    description: 'Paired FASTQ reads to authenticated MAGs, taxonomy and annotation.',
    inputHint: 'Paired FASTQ files',
  },
  {
    id: 'appam-paleoproteomics',
    label: 'Paleoproteomics',
    shortLabel: 'Paleoproteomics',
    description: 'Thermo RAW or Bruker .d data to MaxQuant results and quality summaries.',
    inputHint: 'RAW or Bruker .d files plus a reference FASTA',
  },
])

const WORKFLOW_BY_ID = new Map(WORKFLOW_OPTIONS.map((workflow) => [workflow.id, workflow]))

const PARAMETER_LABELS = Object.freeze({
  profile: 'Execution environment',
  cores: 'Maximum parallel jobs',
  preprocess_method: 'Read preprocessing',
  use_ancient_contigs: 'Use damage-supported contigs only',
  enable_bin_refinement: 'Refine recovered MAGs',
  enable_checkm1: 'Legacy CheckM quality report',
  enable_checkm2: 'MAG quality assessment',
  enable_gunc: 'Contamination assessment',
  enable_gtdbtk: 'Taxonomic classification',
  enable_prokka: 'Gene annotation',
  enable_eggnog: 'Functional annotation',
  enable_abricate: 'Resistance and virulence screening',
  enable_rgi: 'Resistome screening',
  enable_antismash: 'Biosynthetic cluster analysis',
  fasta_path: 'Reference protein database',
  match_between_runs: 'Match features between runs',
  include_contaminants: 'Include contaminant sequences',
})

export function getWorkflowOption(workflowId) {
  return WORKFLOW_BY_ID.get(String(workflowId || '')) || null
}

export function workflowLabel(workflowId, fallback = 'Analysis') {
  return getWorkflowOption(workflowId)?.label || fallback
}

export function parameterLabel(parameterName) {
  const name = String(parameterName || '')
  if (PARAMETER_LABELS[name]) return PARAMETER_LABELS[name]
  return name
    .replace(/^--?/, '')
    .replace(/[_-]+/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase())
}

export function runStatusLabel(status) {
  return {
    queued: 'Waiting in queue',
    starting: 'Starting',
    running: 'Running',
    completed: 'Completed',
    failed: 'Needs attention',
    canceled: 'Canceled',
  }[status] || 'Not started'
}
