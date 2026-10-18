import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import {
  collectWorkflowReports,
  isPlotTableArtifact,
  isPreviewFigureArtifact,
  isReportArtifact,
} from '../src/lib/resultArtifacts.js'

const source = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('workflow report artifacts retain their run context', () => {
  const reports = collectWorkflowReports([{
    id: 'run-2026',
    workflow_id: 'appam-smk',
    finished_at: '2026-08-12 20:00:00',
    artifacts: [
      {
        label: 'Visualization report',
        kind: 'report',
        project_path: 'results/visualization/report.html',
        size_bytes: 2048,
        sha256: 'abc123',
      },
      { kind: 'summary', project_path: 'results/summary.tsv' },
    ],
  }])

  assert.equal(reports.length, 1)
  assert.equal(reports[0].runId, 'run-2026')
  assert.equal(reports[0].workflowId, 'appam-smk')
  assert.equal(reports[0].path, 'results/visualization/report.html')
})

test('result artifact actions distinguish reports, figures and plottable tables', () => {
  assert.equal(isReportArtifact({ kind: 'report', project_path: 'report.html' }), true)
  assert.equal(isPreviewFigureArtifact({ kind: 'visualization', project_path: 'figure.png' }), true)
  assert.equal(isPlotTableArtifact({ kind: 'summary', project_path: 'summary.tsv' }), true)
  assert.equal(isPlotTableArtifact({ kind: 'report', project_path: 'report.html' }), false)
})

test('reports are a native workspace route with an isolated interactive viewer', async () => {
  const [router, workspace, reportView] = await Promise.all([
    source('router.js'),
    source('views/Workspace.vue'),
    source('views/ReportCenterView.vue'),
  ])

  assert.match(router, /path:\s*'reports'[\s\S]*?name:\s*'ReportCenter'[\s\S]*?component:\s*ReportCenterView/)
  assert.match(workspace, /<span>Reports<\/span>/)
  assert.match(reportView, /sandbox="allow-scripts"/)
  assert.doesNotMatch(reportView, /allow-same-origin/)
  assert.match(reportView, /\/report\?path=/)
  assert.match(reportView, /Back to results|Source analysis|Open source analysis/)
})

test('workflow results link reports, figures and tables into native views', async () => {
  const workflowView = await source('views/WorkflowView.vue')

  assert.match(workflowView, /Explore this run/)
  assert.match(workflowView, /Open report/)
  assert.match(workflowView, /Create a plot from this table/)
  assert.match(workflowView, /source:\s*artifact\.project_path/)
  assert.match(workflowView, /figure:\s*artifact\.project_path/)
})

test('analysis figures use deep links and an in-app figure viewer', async () => {
  const plotView = await source('views/PlotStudioView.vue')

  assert.match(plotView, /route\.query\.source/)
  assert.match(plotView, /route\.query\.figure/)
  assert.match(plotView, /figure-viewer__dialog/)
  assert.match(plotView, /Source results/)
  assert.match(plotView, /No figures for this run/)
  assert.doesNotMatch(plotView, /target="_blank"/)
})
