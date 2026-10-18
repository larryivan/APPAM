import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import {
  buildPlotOption,
  collectWorkflowFigures,
  parsePlotTable,
} from '../src/lib/plotStudio.js'

const source = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('workspace exposes a dedicated collapsible plot route', async () => {
  const [router, workspace] = await Promise.all([
    source('router.js'),
    source('views/Workspace.vue'),
  ])

  assert.match(router, /path:\s*'plots'[\s\S]*?name:\s*'PlotStudio'[\s\S]*?component:\s*PlotStudioView/)
  assert.match(workspace, /<span>Plots<\/span>/)
  assert.match(workspace, /plots-submenu/)
  assert.match(workspace, /Analysis figures/)
  assert.match(workspace, /Create your own/)
})

test('plot studio guides users from a project table to a saved figure', async () => {
  const view = await source('views/PlotStudioView.vue')

  assert.match(view, /Choose data/)
  assert.match(view, /Choose the question/)
  assert.match(view, /Map columns/)
  assert.match(view, /Save to project/)
  assert.match(view, /View-only project/)
  assert.match(view, /\['editor', 'owner', 'admin'\]/)
  assert.match(view, /Analysis figures/)
  assert.match(view, /Create your own/)
  assert.match(view, /Example output/)
  assert.match(view, /ref="exampleCanvas"/)
  assert.match(view, /figureSections/)
  assert.match(view, /plot-table/)
  assert.match(view, /upload-chunk/)
  assert.doesNotMatch(view, /linear-gradient|radial-gradient/)
})

test('table parsing detects numeric columns in TSV data', () => {
  const parsed = parsePlotTable(
    'sample\tgroup\tvalue\nA\tcontrol\t1.5\nB\ttreated\t2.25\n',
    '/results/summary.tsv',
  )

  assert.deepEqual(parsed.fields, ['sample', 'group', 'value'])
  assert.deepEqual(parsed.numericColumns, ['value'])
  assert.equal(parsed.rows.length, 2)
})

test('grouped bar charts average repeated observations', () => {
  const option = buildPlotOption({
    type: 'bar',
    title: 'Abundance',
    xColumn: 'sample',
    yColumn: 'value',
    groupColumn: 'group',
  }, [
    { sample: 'A', group: 'control', value: '1' },
    { sample: 'A', group: 'control', value: '3' },
    { sample: 'B', group: 'control', value: '2' },
    { sample: 'A', group: 'treated', value: '4' },
  ])

  assert.deepEqual(option.xAxis.data, ['A', 'B'])
  assert.deepEqual(option.series[0].data, [2, 2])
  assert.deepEqual(option.series[1].data, [4, null])
})

test('workflow PNG and PDF artifacts become one categorized analysis figure', () => {
  const figures = collectWorkflowFigures([{
    id: 'run-1',
    workflow_id: 'appam-smk',
    finished_at: '2026-08-12 20:00:00',
    artifacts: [
      { kind: 'visualization', label: 'Visualization plot', project_path: 'workflow/visualization/sample-a/checkm2/checkm2_scatter.png', size_bytes: 1200 },
      { kind: 'visualization', label: 'Visualization plot', project_path: 'workflow/visualization/sample-a/checkm2/checkm2_scatter.pdf', size_bytes: 2400 },
    ],
  }])

  assert.equal(figures.length, 1)
  assert.equal(figures[0].previewPath, 'workflow/visualization/sample-a/checkm2/checkm2_scatter.png')
  assert.equal(figures[0].files.length, 2)
  assert.equal(figures[0].title, 'CheckM2 completeness and contamination')
  assert.equal(figures[0].category, 'mag-quality')
  assert.equal(figures[0].categoryLabel, 'MAG quality')
  assert.equal(figures[0].sampleId, 'sample-a')
})
