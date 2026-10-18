import assert from 'node:assert/strict'
import test from 'node:test'

// Unlike the source-text checks elsewhere in this directory, these exercise the
// module: lib/notify.js is plain reactive state, so it runs under node:test
// without a DOM.
const {
  confirmAction,
  confirmDialogState,
  dismissToast,
  notify,
  notifyError,
  notifySuccess,
  settleConfirm,
  toastList,
} = await import('../src/lib/notify.js')

function clearToasts() {
  for (const toast of [...toastList]) dismissToast(toast.id)
}

test('a toast carries its tone and can be dismissed by id', () => {
  clearToasts()
  const id = notifySuccess('File saved.')
  assert.equal(toastList.length, 1)
  assert.equal(toastList[0].tone, 'success')
  assert.equal(toastList[0].message, 'File saved.')

  dismissToast(id)
  assert.equal(toastList.length, 0)
})

test('errors keep the technical text separate from the headline', () => {
  clearToasts()
  notifyError(new Error('HTTP 500: gtdbtk_db not found at /databases/gtdbtk_r226'), {
    message: 'Could not start the analysis.',
  })
  const [toast] = toastList
  assert.equal(toast.tone, 'error')
  assert.equal(toast.message, 'Could not start the analysis.')
  assert.match(toast.detail, /gtdbtk_db not found/)
  clearToasts()
})

test('a bare error still shows its own message rather than nothing', () => {
  clearToasts()
  notifyError(new Error('Network request failed'))
  assert.equal(toastList[0].message, 'Network request failed')
  assert.equal(toastList[0].detail, '')
  clearToasts()
})

test('the stack stays shallow so old toasts cannot bury the page', () => {
  clearToasts()
  for (let index = 0; index < 9; index += 1) notify(`message ${index}`, { duration: 0 })
  assert.equal(toastList.length, 4)
  assert.equal(toastList[3].message, 'message 8')
  clearToasts()
})

test('empty messages are ignored instead of rendering a blank toast', () => {
  clearToasts()
  assert.equal(notify('   '), null)
  assert.equal(toastList.length, 0)
})

test('confirmAction resolves true only when confirmed', async () => {
  const accepted = confirmAction({ title: 'Delete project?', confirmLabel: 'Delete' })
  assert.equal(confirmDialogState.open, true)
  assert.equal(confirmDialogState.confirmLabel, 'Delete')
  settleConfirm(true)
  assert.equal(await accepted, true)
  assert.equal(confirmDialogState.open, false)

  const declined = confirmAction({ title: 'Delete project?' })
  settleConfirm(false)
  assert.equal(await declined, false)
})

test('a second confirm supersedes the first instead of stacking dialogs', async () => {
  const first = confirmAction({ title: 'First' })
  const second = confirmAction({ title: 'Second' })
  assert.equal(await first, false, 'the superseded request must not stay pending')
  assert.equal(confirmDialogState.title, 'Second')
  settleConfirm(true)
  assert.equal(await second, true)
})

test('dismissing the dialog without choosing resolves false', async () => {
  const pending = confirmAction({ title: 'Discard changes?' })
  settleConfirm(undefined)
  assert.equal(await pending, false)
})
