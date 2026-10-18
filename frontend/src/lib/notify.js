import { reactive, readonly, shallowReactive } from 'vue'

// Replaces window.alert / window.confirm. Native dialogs block the page, cannot
// be styled, and — after a few in a row — Chrome offers "prevent this page from
// creating more dialogs", which silently swallows every later error.

const toasts = reactive([])
const confirmState = shallowReactive({
  open: false,
  title: '',
  message: '',
  detail: '',
  confirmLabel: 'Confirm',
  cancelLabel: 'Cancel',
  tone: 'default',
  resolve: null,
})

let sequence = 0

const DEFAULT_DURATION = { success: 4000, info: 5000, error: 9000 }

export const toastList = readonly(toasts)
export const confirmDialogState = confirmState

export function dismissToast(id) {
  const index = toasts.findIndex((toast) => toast.id === id)
  if (index !== -1) toasts.splice(index, 1)
}

/**
 * Show a transient message.
 * @param {string} message
 * @param {{tone?: 'success'|'error'|'info', title?: string, detail?: string, duration?: number}} options
 */
export function notify(message, options = {}) {
  const tone = options.tone || 'info'
  const text = String(message ?? '').trim()
  if (!text && !options.title) return null

  sequence += 1
  const id = sequence
  const duration = options.duration ?? DEFAULT_DURATION[tone] ?? DEFAULT_DURATION.info

  toasts.push({
    id,
    tone,
    title: options.title || '',
    message: text,
    // Long server text stays available but does not dominate the toast.
    detail: options.detail || '',
  })

  // Keep the stack shallow; the oldest is the least relevant.
  while (toasts.length > 4) toasts.shift()

  if (duration > 0) {
    // Bare setTimeout, not window.setTimeout: this module is imported by tests
    // and by the router, neither of which is guaranteed a browser global.
    const timer = setTimeout(() => dismissToast(id), duration)
    // In Node (tests) a pending timer keeps the process alive; unref is a no-op
    // in the browser, where setTimeout returns a number.
    timer?.unref?.()
  }
  return id
}

export const notifySuccess = (message, options) => notify(message, { ...options, tone: 'success' })
export const notifyInfo = (message, options) => notify(message, { ...options, tone: 'info' })

/** Errors keep their technical text behind a disclosure instead of in the headline. */
export function notifyError(error, options = {}) {
  const raw = error instanceof Error ? error.message : String(error ?? '')
  const headline = options.message || raw || 'Something went wrong.'
  const detail = options.detail ?? (options.message && raw !== options.message ? raw : '')
  return notify(headline, { ...options, detail, tone: 'error' })
}

/**
 * Ask the user to confirm a destructive or irreversible action.
 * @returns {Promise<boolean>} resolves true when confirmed
 */
export function confirmAction({
  title,
  message = '',
  detail = '',
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  tone = 'default',
} = {}) {
  // A second request supersedes the first rather than stacking dialogs.
  confirmState.resolve?.(false)

  return new Promise((resolve) => {
    confirmState.open = true
    confirmState.title = title || 'Are you sure?'
    confirmState.message = message
    confirmState.detail = detail
    confirmState.confirmLabel = confirmLabel
    confirmState.cancelLabel = cancelLabel
    confirmState.tone = tone
    confirmState.resolve = resolve
  })
}

export function settleConfirm(result) {
  const resolve = confirmState.resolve
  confirmState.open = false
  confirmState.resolve = null
  resolve?.(Boolean(result))
}
