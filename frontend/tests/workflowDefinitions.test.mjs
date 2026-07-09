import assert from 'node:assert/strict'
import test from 'node:test'

import { getWorkflowDefinition } from '../src/lib/workflowDefinitions.js'


test('core workflow definitions expose stable IDs and tools', () => {
  const workflows = ['appam-smk', 'appam-paleoproteomics'].map(getWorkflowDefinition)
  assert.equal(new Set(workflows.map((item) => item.id)).size, workflows.length)
  assert.equal(new Set(workflows.map((item) => item.toolId)).size, workflows.length)
  for (const workflow of workflows) {
    assert.ok(workflow.id)
    assert.ok(workflow.toolId)
    assert.ok(workflow.title)
  }
})
