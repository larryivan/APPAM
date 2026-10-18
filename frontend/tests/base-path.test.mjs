import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

import { createBasePath } from '../src/lib/basePath.js'

const source = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('root deployments leave every URL unchanged', () => {
  const { base, withBase, withoutBase } = createBasePath('/')
  assert.equal(base, '')
  assert.equal(withBase('/api/projects/'), '/api/projects/')
  assert.equal(withoutBase('/workspace/1/overview'), '/workspace/1/overview')
})

test('a gateway prefix is added once and removed again', () => {
  const { withBase, withoutBase } = createBasePath('/proxy/relative/172.16.17.93/25078/')
  assert.equal(withBase('/api/auth/me'), '/proxy/relative/172.16.17.93/25078/api/auth/me')
  assert.equal(withBase('/proxy/relative/172.16.17.93/25078/api/auth/me'), '/proxy/relative/172.16.17.93/25078/api/auth/me')
  assert.equal(withBase('https://example.org/x'), 'https://example.org/x')
  assert.equal(withBase('//cdn.example.org/x'), '//cdn.example.org/x')
  assert.equal(withBase('relative/path'), 'relative/path')
  assert.equal(withoutBase('/proxy/relative/172.16.17.93/25078/api/auth/me'), '/api/auth/me')
  assert.equal(withoutBase('/proxy/relative/172.16.17.93/25078'), '/')
})

test('requests, navigation and sockets follow the base path', async () => {
  const [api, router, terminal, vite] = await Promise.all([
    source('lib/api.js'),
    source('router.js'),
    source('components/FloatingTerminal.vue'),
    readFile(new URL('../vite.config.js', import.meta.url), 'utf8'),
  ])
  assert.match(api, /const target = typeof input === 'string' \? withBase\(input\) : input/)
  assert.match(api, /withoutBase\(parsed\.pathname\)/)
  assert.match(router, /createWebHistory\(import\.meta\.env\.BASE_URL\)/)
  assert.match(terminal, /path: `\$\{BASE_PATH\}\/socket\.io`/)
  assert.match(vite, /base,\n\s*plugins:/)
})

test('links, images and report frames built from API paths carry the base path', async () => {
  const files = ['components/FileManagerOptimized.vue', 'views/PlotStudioView.vue', 'views/ReportCenterView.vue', 'views/WorkflowView.vue']
  for (const file of files) {
    const text = await source(file)
    // fetch() is prefixed centrally; anything else must go through withBase.
    assert.doesNotMatch(text, /(href = |return )`\/api\//, `${file} builds an unprefixed API URL`)
  }
  for (const file of ['components/Topbar.vue', 'views/HomeView.vue']) {
    assert.doesNotMatch(await source(file), /src="\/assets\/logo\.svg"/, `${file} hard-codes the logo path`)
  }
})
