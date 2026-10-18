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
  enable_variants: 'Variant calling and consensus',
  enable_visualization: 'Generate figures and report',
  fasta_path: 'Reference protein database',
  maxquant_mode: 'MaxQuant run mode',
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

// Server messages are precise but technical. Each rule keeps the banner short and
// actionable; the original text stays available under "Technical details".
const WORKFLOW_ERROR_RULES = Object.freeze([
  {
    match: (raw) => raw.startsWith('Missing APPAM-SMK runtime resources:')
      || raw.startsWith('Missing paleoproteomics runtime resources:'),
    message: 'This analysis is not available yet.',
    hint: 'The server setup is incomplete. Ask an administrator to finish System Setup.',
  },
  {
    match: (raw) => raw.includes('No complete FASTQ pairs'),
    message: 'No complete FASTQ pairs were found.',
    hint: 'Upload matching R1 and R2 files, then rescan the input folder.',
  },
  {
    match: (raw) => raw.includes('No RAW/.d files'),
    message: 'No mass spectrometry inputs were found.',
    hint: 'Upload Thermo RAW files or add a Bruker .d dataset, then rescan.',
  },
  {
    match: (raw) => raw.includes('Frozen workflow inputs changed'),
    message: 'The input files changed since that run.',
    hint: 'Retry and resume reuse the original inputs. Start a new analysis instead.',
  },
  {
    match: (raw) => raw.includes('runtime or database resources changed'),
    message: 'The server software or databases changed since that run.',
    hint: 'Retry and resume reuse the original runtime. Start a new analysis instead.',
  },
  {
    match: (raw) => raw.includes('Publication database manifest is incomplete'),
    message: 'The database version record is incomplete.',
    hint: 'Ask an administrator to complete the database manifest, or run without the publication preset.',
  },
  {
    match: (raw) => raw.toLowerCase().includes('queue limit'),
    message: 'The analysis queue is currently full.',
    hint: 'Try again after one of the queued jobs has started or finished.',
  },
])

export function describeWorkflowError(error) {
  const raw = error instanceof Error ? error.message : String(error ?? '')
  const rule = WORKFLOW_ERROR_RULES.find((candidate) => candidate.match(raw))
  if (rule) {
    return { message: rule.message, hint: rule.hint, details: raw }
  }
  if (raw.length > 240) {
    return {
      message: 'The analysis could not be started.',
      hint: 'Review the technical details or ask an administrator for help.',
      details: raw,
    }
  }
  return { message: raw, hint: '', details: '' }
}
