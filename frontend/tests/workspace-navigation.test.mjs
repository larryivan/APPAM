import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'


const workspaceSource = await readFile(
  new URL('../src/views/Workspace.vue', import.meta.url),
  'utf8',
)

test('workspace navigation retains rail and nested collapse controls', () => {
  assert.match(workspaceSource, /nav-collapsed/)
  assert.match(workspaceSource, /analysis-submenu/)
  assert.match(workspaceSource, /plots-submenu/)
  assert.match(workspaceSource, /<span>Reports<\/span>/)
  assert.match(workspaceSource, /tools-submenu/)
  assert.match(workspaceSource, /panel-left-open/)
})

test('project navigation aborts stale requests before loading another project', () => {
  assert.match(workspaceSource, /projectLoadController\?\.abort\(\)/)
  assert.match(workspaceSource, /requestedProjectId === projectId\.value/)
})

test('submenu selections are scoped to their own workspace route', () => {
  assert.match(workspaceSource, /if \(route\.name !== 'PlotStudio'\) return ''/)
  assert.match(workspaceSource, /\['ToolLibrary', 'PipelineTool'\]\.includes/)
})
