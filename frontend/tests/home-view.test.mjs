import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const source = (path) => readFile(new URL(`../src/${path}`, import.meta.url), 'utf8')

test('root route renders the lightweight home view', async () => {
  const router = await source('router.js')

  assert.match(router, /path:\s*'\/'[\s\S]*?name:\s*'Home'[\s\S]*?component:\s*HomeView/)
  assert.doesNotMatch(router, /path:\s*'\/'\s*,\s*redirect:/)
})

test('home view adapts its primary action to authentication state', async () => {
  const home = await source('views/HomeView.vue')

  assert.match(home, /authState\.user \? 'Open projects' : 'Sign in'/)
  assert.match(home, /authState\.user \? '\/projects' : '\/login'/)
  assert.match(home, /v-for="workflow in workflows"/)
  assert.doesNotMatch(home, /linear-gradient|radial-gradient/)
})

test('the APPAM brand and logout return to the home route', async () => {
  const topbar = await source('components/Topbar.vue')

  assert.match(topbar, /<router-link to="\/" class="brand"/)
  assert.match(topbar, /router\.replace\('\/'\)/)
})
