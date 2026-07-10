const WORKFLOWS = Object.freeze({
  'appam-smk': Object.freeze({
    id: 'appam-smk',
    toolId: 'workflow-appam-smk',
    title: 'Ancient metagenomics',
    description: 'Paired FASTQ reads to authenticated MAGs, taxonomy and annotation.',
  }),
  'appam-paleoproteomics': Object.freeze({
    id: 'appam-paleoproteomics',
    toolId: 'workflow-appam-paleoproteomics',
    title: 'Paleoproteomics',
    description: 'RAW or Bruker .d data to MaxQuant results and quality summaries.',
  }),
})

export function getWorkflowDefinition(workflowId) {
  return WORKFLOWS[String(workflowId || '')] || null
}

export function getWorkflowDefinitionByToolId(toolId) {
  return Object.values(WORKFLOWS).find((workflow) => workflow.toolId === toolId) || null
}

export function initWorkflowFormValues(parameters = []) {
  const initialValues = {}
  parameters.forEach((param) => {
    if (param.type === 'file' || param.type === 'directory') {
      initialValues[param.name] = param.multiple ? [] : ''
      return
    }
    if (param.type === 'flag') {
      initialValues[param.name] = Boolean(param.default)
      return
    }
    if (param.options?.length) {
      initialValues[param.name] = param.default && param.options.includes(param.default)
        ? param.default
        : param.options[0]
      return
    }
    initialValues[param.name] = param.default ?? ''
  })
  return initialValues
}
