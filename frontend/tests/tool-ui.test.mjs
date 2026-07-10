import assert from 'node:assert/strict'
import test from 'node:test'

import { filterToolSections, primaryToolParameters, toolParameterLabel } from '../src/lib/toolUi.js'

test('tool setup shows input contracts and outputs before optional CLI parameters', () => {
  const tool = {
    required_any: ['reads_1', 'single_reads'],
    paired_parameters: [['reads_1', 'reads_2']],
    parameters: [
      { name: 'reads_1', type: 'file' },
      { name: 'reads_2', type: 'file' },
      { name: 'single_reads', type: 'file' },
      { name: 'output', type: 'directory', path_role: 'output' },
      { name: 'threads', type: 'integer', default: 4 },
    ],
  }

  assert.deepEqual(primaryToolParameters(tool).map((parameter) => parameter.name), [
    'reads_1',
    'reads_2',
    'single_reads',
    'output',
  ])
})

test('tool catalog excludes workflow launchers and supports search', () => {
  const sections = [
    { id: 'reads-qc', tools: [{ tool_name: 'FastQC', description: 'Read quality' }] },
    { id: 'assembly', tools: [{ tool_name: 'MEGAHIT', description: 'Assembly' }] },
    { id: 'workflow-automation', tools: [{ tool_name: 'APPAM-SMK Workflow' }] },
  ]

  const filtered = filterToolSections(sections, { query: 'quality' })
  assert.deepEqual(filtered.map((section) => section.id), ['reads-qc'])
  assert.equal(filtered[0].tools[0].tool_name, 'FastQC')
})

test('tool parameters use task-oriented labels instead of CLI flags', () => {
  assert.equal(toolParameterLabel({ name: '-o', type: 'directory', path_role: 'output' }), 'Output folder')
  assert.equal(toolParameterLabel({ name: '--threads', type: 'integer' }), 'Threads')
  assert.equal(toolParameterLabel({ name: '--db', path_role: 'input', path_scope: 'shared' }), 'Database')
})
