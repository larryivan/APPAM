import { parameterLabel } from './workflowUi.js'

export const TOOL_SECTION_OPTIONS = Object.freeze([
  { id: 'reads-qc', label: 'Reads & QC' },
  { id: 'read-taxonomy', label: 'Read taxonomy' },
  { id: 'assembly-authentication', label: 'Assembly & aDNA' },
  { id: 'binning-mags', label: 'Binning & MAGs' },
  { id: 'functional-annotation', label: 'Genome annotation' },
  { id: 'paleoproteomics', label: 'Paleoproteomics' },
])

const TOOL_SECTION_IDS = new Set(TOOL_SECTION_OPTIONS.map((section) => section.id))

export function normalizeToolSection(sectionId) {
  const normalized = String(sectionId || '')
  return TOOL_SECTION_IDS.has(normalized) ? normalized : ''
}

const TOOL_PARAMETER_ALIASES = Object.freeze({
  '-1': 'Forward reads',
  '-2': 'Reverse reads',
  '-r': 'Single reads',
  '-t': 'Threads',
  '-@': 'Threads',
  '--threads': 'Threads',
  '--cpus': 'Threads',
  '--num_threads': 'Threads',
  '--db': 'Database',
  '--database_path': 'Database',
})

export function toolParameterLabel(parameter = {}) {
  const name = String(parameter.name || '')
  const explicitLabel = String(parameter.label || parameter.ui_label || '').trim()
  if (parameter.path_role === 'output') {
    if (parameter.path_kind === 'prefix') return 'Output name'
    if (parameter.type === 'directory' || parameter.path_kind === 'directory') return 'Output folder'
    return 'Output file'
  }
  if (parameter.path_scope === 'shared' && parameter.path_role === 'input') return 'Database'
  if (explicitLabel) return explicitLabel
  if (TOOL_PARAMETER_ALIASES[name]) return TOOL_PARAMETER_ALIASES[name]

  const normalizedName = name.replace(/^-+/, '')
  const description = String(parameter.description || '').trim().replace(/[.:;]+$/, '')
  if (/^[a-z0-9@]$/i.test(normalizedName) && description && description.length <= 48) {
    return description
  }
  return parameterLabel(name)
}

export function primaryToolParameters(tool = {}) {
  const parameters = tool.parameters || []
  const contractNames = new Set([
    ...(tool.required_any || []),
    ...((tool.paired_parameters || []).flat()),
  ])
  const primary = parameters.filter((parameter) => (
    parameter.required
    || parameter.positional
    || parameter.path_role === 'output'
    || contractNames.has(parameter.name)
  ))
  return primary.length ? primary : parameters.slice(0, 4)
}

export function filterToolSections(sections = [], { query = '', sectionId = '' } = {}) {
  const normalizedQuery = String(query).trim().toLowerCase()
  return sections
    .filter((section) => section.id !== 'workflow-automation')
    .filter((section) => !sectionId || section.id === sectionId)
    .map((section) => ({
      ...section,
      tools: (section.tools || []).filter((tool) => {
        if (!normalizedQuery) return true
        return `${tool.tool_name || ''} ${tool.description || ''}`.toLowerCase().includes(normalizedQuery)
      }),
    }))
    .filter((section) => section.tools.length)
}
