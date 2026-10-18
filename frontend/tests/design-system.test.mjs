import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('global design tokens keep controls compact and surfaces restrained', async () => {
  const app = await source('App.vue')

  assert.match(app, /--control-height:\s*36px/)
  assert.match(app, /--radius-md:\s*0\.5rem/)
  assert.match(app, /--radius-lg:\s*0\.5rem/)
  assert.doesNotMatch(app, /fonts\.googleapis|@import\s+url/)
  assert.doesNotMatch(app, /linear-gradient|radial-gradient/)
})

test('topbar keeps a spacious hierarchy across navigation and account controls', async () => {
  const [app, topbar] = await Promise.all([
    source('App.vue'),
    source('components/Topbar.vue'),
  ])

  assert.match(app, /--header-height:\s*68px/)
  assert.match(topbar, /class="brand-mark"/)
  assert.match(topbar, /class="account-avatar"/)
  assert.match(topbar, /class="account-copy"/)
  assert.match(topbar, /projectsActive/)
  assert.match(topbar, /document\.addEventListener\('pointerdown'/)
  assert.match(topbar, /document\.addEventListener\('keydown'/)
  assert.match(topbar, /\.primary-nav a::after/)
  assert.match(topbar, /\.mobile-identity/)
  assert.doesNotMatch(topbar, /linear-gradient|radial-gradient/)
})

test('core work surfaces use the shared icon system', async () => {
  const paths = [
    'components/DownloadManager.vue',
    'components/FileManagerOptimized.vue',
    'components/FilePicker.vue',
    'components/PipelineTool.vue',
    'views/Workspace.vue',
  ]
  const contents = await Promise.all(paths.map(source))

  for (const content of contents) {
    assert.doesNotMatch(content, /<svg\b/)
    assert.match(content, /<Icon\b/)
  }
})

test('workspace navigation remains compact without covering desktop content', async () => {
  const workspace = await source('views/Workspace.vue')

  assert.match(workspace, /'mobile-nav-open': mobileNavOpen/)
  assert.match(workspace, /'has-admin-tools': isAdmin/)
  assert.match(workspace, /grid-template-columns:\s*232px minmax\(0, 1fr\) 52px/)
  assert.match(workspace, /\.admin-runtime-tools\s*\{[\s\S]*?position:\s*static/)
})

test('scroll regions use one quiet global scrollbar policy', async () => {
  const [app, pipelineTool, fileManager, systemPerformance] = await Promise.all([
    source('App.vue'),
    source('components/PipelineTool.vue'),
    source('components/FileManagerOptimized.vue'),
    source('components/SystemPerformance.vue'),
  ])

  assert.match(app, /::-webkit-scrollbar\s*\{[\s\S]*?width:\s*6px/)
  assert.match(app, /::-webkit-scrollbar-track\s*\{\s*background:\s*transparent/)
  assert.doesNotMatch(pipelineTool, /\.param-list::-webkit-scrollbar/)
  assert.doesNotMatch(pipelineTool, /\.tool-interface-container::-webkit-scrollbar/)
  assert.doesNotMatch(fileManager, /\.virtual-scroll-container::-webkit-scrollbar/)
  assert.doesNotMatch(systemPerformance, /\.performance-content::-webkit-scrollbar/)

  const parameterListRule = pipelineTool.match(/\.param-list\s*\{([^}]*)\}/)?.[1] || ''
  assert.doesNotMatch(parameterListRule, /overflow-y|max-height/)
})
