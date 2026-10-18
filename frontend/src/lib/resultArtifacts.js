const REPORT_EXTENSIONS = new Set(['.html', '.htm'])
const PLOT_TABLE_EXTENSIONS = new Set(['.csv', '.tsv', '.tab', '.txt'])
const PREVIEW_FIGURE_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.webp', '.gif'])

function extension(path) {
  const match = String(path || '').toLowerCase().match(/\.[^.\/]+$/)
  return match?.[0] || ''
}

export function artifactProjectPath(artifact) {
  return String(artifact?.project_path || '')
}

export function isReportArtifact(artifact) {
  const path = artifactProjectPath(artifact)
  return artifact?.kind === 'report' && REPORT_EXTENSIONS.has(extension(path))
}

export function isPlotTableArtifact(artifact) {
  return PLOT_TABLE_EXTENSIONS.has(extension(artifactProjectPath(artifact)))
}

export function isPreviewFigureArtifact(artifact) {
  return artifact?.kind === 'visualization'
    && PREVIEW_FIGURE_EXTENSIONS.has(extension(artifactProjectPath(artifact)))
}

export function collectWorkflowReports(runs) {
  const reports = []
  for (const run of runs || []) {
    for (const artifact of run.artifacts || []) {
      if (!isReportArtifact(artifact)) continue
      const path = artifactProjectPath(artifact)
      reports.push({
        id: `${run.id}:${path}`,
        title: artifact.label || path.split('/').pop() || 'Analysis report',
        path,
        workflowId: String(run.workflow_id || ''),
        runId: String(run.id || ''),
        createdAt: run.finished_at || run.completed_at || run.created_at || '',
        status: String(run.status || ''),
        size: Number(artifact.size_bytes || 0),
        sha256: String(artifact.sha256 || ''),
      })
    }
  }
  return reports.sort((left, right) => (
    new Date(String(right.createdAt).replace(' ', 'T') || 0).getTime()
    - new Date(String(left.createdAt).replace(' ', 'T') || 0).getTime()
  ))
}
