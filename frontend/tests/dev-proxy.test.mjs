import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'

const config = await readFile(new URL('../vite.config.js', import.meta.url), 'utf8')

test('development API proxy normalizes its origin to the backend target', () => {
  assert.match(config, /const apiOrigin = new URL\(apiTarget\)\.origin/)
  assert.match(config, /headers:\s*\{\s*Origin:\s*apiOrigin/)
  assert.match(config, /rewriteWsOrigin:\s*true/)
})
