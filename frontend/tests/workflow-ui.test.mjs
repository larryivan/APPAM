import assert from 'node:assert/strict'
import test from 'node:test'

import {
  WORKFLOW_OPTIONS,
  getWorkflowOption,
  parameterLabel,
  runStatusLabel,
} from '../src/lib/workflowUi.js'

test('workflow UI catalog exposes the two guided analyses', () => {
  assert.deepEqual(WORKFLOW_OPTIONS.map((workflow) => workflow.id), [
    'appam-smk',
    'appam-paleoproteomics',
  ])
  assert.equal(getWorkflowOption('appam-smk').inputHint, 'Paired FASTQ files')
})

test('technical parameter and status identifiers have user-facing labels', () => {
  assert.equal(parameterLabel('enable_checkm2'), 'MAG quality assessment')
  assert.equal(parameterLabel('max_missed_cleavages'), 'Max Missed Cleavages')
  assert.equal(runStatusLabel('failed'), 'Needs attention')
})
