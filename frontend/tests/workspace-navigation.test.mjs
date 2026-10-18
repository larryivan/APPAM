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

test('routed workspace views scroll inside the clipped content region', async () => {
  // .workspace-content clips overflow, so each view root must have a fixed
  // height to become the scroll container. min-height lets it grow with its
  // content instead and everything below the fold becomes unreachable.
  assert.match(workspaceSource, /\.workspace-content \{[^}]*overflow: hidden/)
  const roots = {
    'views/Overview.vue': 'project-home',
    'views/WorkflowView.vue': 'workflow-view',
    'views/ToolLibraryView.vue': 'tool-library',
    'views/PlotStudioView.vue': 'plot-studio',
    'components/PipelineTool.vue': 'tool-interface-container',
  }
  for (const [path, root] of Object.entries(roots)) {
    const view = await readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')
    const rule = view.match(new RegExp(`\\n\\.${root} \\{([^}]*)\\}`))?.[1] ?? ''
    assert.match(rule, /\n\s*height: 100%;/, `${path} root needs a fixed height`)
    assert.match(rule, /overflow-y: auto;/, `${path} root must scroll`)
  }
})

test('the assistant is offered whenever the OpenCode CLI is installed', () => {
  // The panel runs the CLI in a terminal; the API server only backs parameter filling.
  assert.match(workspaceSource, /fetch\('\/api\/terminal\/assistant'\)/)
  assert.doesNotMatch(workspaceSource, /parameter-fill\/health/)
})
