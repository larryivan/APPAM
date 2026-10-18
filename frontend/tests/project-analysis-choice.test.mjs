import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'


const readView = (name) => readFile(new URL(`../src/views/${name}`, import.meta.url), 'utf8')

const [projectListSource, overviewSource, workspaceSource, reportsSource, plotsSource] = await Promise.all([
  readView('ProjectList.vue'),
  readView('Overview.vue'),
  readView('Workspace.vue'),
  readView('ReportCenterView.vue'),
  readView('PlotStudioView.vue'),
])

test('projects are not bound to a default analysis in the frontend', () => {
  const projectSurfaces = [
    projectListSource,
    overviewSource,
    workspaceSource,
    reportsSource,
    plotsSource,
  ].join('\n')

  assert.doesNotMatch(projectSurfaces, /analysis_workflow/)
  assert.doesNotMatch(projectSurfaces, /Default analysis|Project default|No default analysis/)
  assert.doesNotMatch(projectListSource, /What do you want to analyze\?/)
  assert.match(projectListSource, /router\.push\(\{ name: 'Overview'/)
})

test('every workflow remains directly selectable from overview and navigation', () => {
  assert.match(overviewSource, /id="analysis-workflows"/)
  assert.match(overviewSource, /v-for="workflow in workflowOptions"/)
  assert.doesNotMatch(overviewSource, /v-if="!project\.analysis_workflow"/)
  assert.match(workspaceSource, /v-for="workflow in workflowOptions"/)
  assert.match(workspaceSource, /hash: '#analysis-workflows'/)
})

test('reports and plots never fall back to an arbitrary workflow', () => {
  assert.doesNotMatch(reportsSource, /\|\| 'appam-smk'/)
  assert.doesNotMatch(plotsSource, /\|\| 'appam-smk'/)
  assert.match(reportsSource, /if \(!report\?\.workflowId\) return analysisHubRoute\.value/)
  assert.match(plotsSource, /if \(!contextWorkflowId\.value\)/)
})
