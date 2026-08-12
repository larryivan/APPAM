import assert from 'node:assert/strict'
import test from 'node:test'

import {
  WORKFLOW_OPTIONS,
  describeWorkflowError,
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

test('reproducibility rejections become short actionable messages', () => {
  const changedInputs = describeWorkflowError(new Error(
    'Frozen workflow inputs changed after the source run. Submit a new run instead of retry/resume: '
    + '/projects/p1/raw/sample1_R1.fastq.gz: changed size_bytes, mtime_ns',
  ))
  assert.equal(changedInputs.message, 'The input files changed since that run.')
  assert.match(changedInputs.hint, /Start a new analysis/)
  assert.match(changedInputs.details, /changed size_bytes/)

  const changedRuntime = describeWorkflowError(new Error(
    'Workflow runtime or database resources changed after the source run. Submit a new run, or explicitly '
    + 'set APPAM_ALLOW_RUNTIME_DRIFT_ON_RETRY=true and document the deviation.',
  ))
  assert.equal(changedRuntime.message, 'The server software or databases changed since that run.')
  assert.doesNotMatch(changedRuntime.hint, /APPAM_ALLOW_RUNTIME_DRIFT_ON_RETRY/)
  assert.match(changedRuntime.details, /APPAM_ALLOW_RUNTIME_DRIFT_ON_RETRY/)
})

test('unrecognised short errors are shown verbatim without a hint', () => {
  const described = describeWorkflowError(new Error('Workflow run not found'))
  assert.deepEqual(described, { message: 'Workflow run not found', hint: '', details: '' })
  assert.equal(describeWorkflowError(new Error('x'.repeat(400))).message, 'The analysis could not be started.')
})
