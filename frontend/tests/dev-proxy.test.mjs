import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const config = await readFile(new URL('../vite.config.js', import.meta.url), 'utf8')

test('development API proxy normalizes its origin to the backend target', () => {
  assert.match(config, /const apiOrigin = new URL\(apiTarget\)\.origin/)
  assert.match(config, /headers:\s*\{\s*Origin:\s*apiOrigin/)
})

test('development socket proxy presents an http origin so websockets upgrade', () => {
  // rewriteWsOrigin sent the ws:// target as Origin; the backend rejected the
  // upgrade and every terminal fell back to HTTP long-polling.
  assert.doesNotMatch(config, /rewriteWsOrigin/)
  assert.match(config, /const wsOrigin = new URL\(wsTarget\.replace\(\/\^ws\/, 'http'\)\)\.origin/)
  assert.match(config, /'\/socket\.io':\s*\{[\s\S]*?headers:\s*\{\s*Origin:\s*wsOrigin/)
})
