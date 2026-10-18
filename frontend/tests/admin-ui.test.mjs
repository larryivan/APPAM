import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('administration routes share one layout and one scrolling content region', async () => {
  const [router, layout, system, users, worker] = await Promise.all([
    source('router.js'),
    source('views/AdminLayoutView.vue'),
    source('views/AdminCenterView.vue'),
    source('views/AdminUsersView.vue'),
    source('views/WorkerStatusView.vue'),
  ])

  assert.match(router, /path:\s*'\/admin'[\s\S]*?component:\s*AdminLayoutView[\s\S]*?children:/)
  assert.match(layout, /class="admin-content"[\s\S]*?<router-view/)
  assert.match(layout, /\.admin-content\s*\{[\s\S]*?overflow-y:\s*auto/)
  assert.doesNotMatch(system, /<AdminNav/)
  assert.doesNotMatch(users, /<AdminNav/)
  assert.doesNotMatch(worker, /<AdminNav/)
})

test('system administration prioritizes blockers and keeps diagnostics collapsible', async () => {
  const system = await source('views/AdminCenterView.vue')

  assert.match(system, /Priority actions/)
  assert.match(system, /priorityChecks/)
  assert.match(system, /<details[\s\S]*?v-for="group in report\.groups"/)
  assert.match(system, /copyText\(check\.action\)/)
  assert.doesNotMatch(system, /readiness-strip|setup-group/)
})

test('user administration supports account creation and contained management actions', async () => {
  const users = await source('views/AdminUsersView.vue')

  assert.match(users, /Add user/)
  assert.match(users, /method:\s*'POST'[\s\S]*?JSON\.stringify\(createForm\)/)
  assert.match(users, /<SidePanel[\s\S]*?panelMode === 'manage'/)
  assert.match(users, /Temporary password/)
  assert.match(users, /class="confirm-dialog app-modal"/)
  assert.doesNotMatch(users, /window\.confirm/)
})

test('queue administration keeps operational details behind a disclosure', async () => {
  const worker = await source('views/WorkerStatusView.vue')

  assert.match(worker, /Worker online/)
  assert.match(worker, /Queue is clear/)
  assert.match(worker, /<details class="worker-details">/)
  assert.match(worker, /Updates every 5 seconds/)
  assert.doesNotMatch(worker, /worker-card|worker-counts/)
})
