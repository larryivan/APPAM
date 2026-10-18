import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'


const filePickerSource = await readFile(
  new URL('../src/components/FilePicker.vue', import.meta.url),
  'utf8',
)

test('file picker uses an adaptive clipped dialog instead of a fixed empty panel', () => {
  assert.match(filePickerSource, /role="dialog"/)
  assert.match(filePickerSource, /max-height: min\(430px, calc\(100dvh - 210px\)\)/)
  assert.match(filePickerSource, /overflow: hidden/)
  assert.doesNotMatch(filePickerSource, /min-height: 300px/)
  assert.doesNotMatch(filePickerSource, /Debug Info/)
  assert.doesNotMatch(filePickerSource, /Double-click to enter/)
})

test('file picker supports failure recovery and aborts stale directory requests', () => {
  assert.match(filePickerSource, /v-else-if="loadError"/)
  assert.match(filePickerSource, /loadController\?\.abort\(\)/)
})

test('file picker delegates dismissal and focus handling to the shared overlay', async () => {
  // Escape used to be handled inline here. It now lives in lib/overlay.js so
  // every dialog also restores focus and releases the page scroll lock.
  const overlaySource = await readFile(
    new URL('../src/lib/overlay.js', import.meta.url),
    'utf8',
  )
  assert.match(filePickerSource, /useOverlay\(/)
  assert.match(filePickerSource, /panelRef: pickerPanel/)
  assert.match(overlaySource, /event\.key === 'Escape'/)
  assert.match(overlaySource, /previouslyFocused/)
})
