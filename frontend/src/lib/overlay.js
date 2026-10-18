import { nextTick, onBeforeUnmount, watch } from 'vue'

// Every overlay in APPAM shares this behaviour, so it lives in one place:
// Escape closes, focus moves in and comes back, Tab cannot walk out into the
// page behind, and the page behind does not scroll.

const FOCUSABLE = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled]):not([type="hidden"])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  'summary',
  '[tabindex]:not([tabindex="-1"])',
].join(',')

let overlayDepth = 0
let sequence = 0

/** Stable, unique DOM id so two open overlays never collide on aria-labelledby. */
export function nextOverlayId(prefix = 'overlay') {
  sequence += 1
  return `${prefix}-${sequence}`
}

function lockScroll() {
  overlayDepth += 1
  document.body.classList.add('modal-open')
}

function unlockScroll() {
  overlayDepth = Math.max(0, overlayDepth - 1)
  // Only the last overlay to close releases the page.
  if (overlayDepth === 0) document.body.classList.remove('modal-open')
}

function focusableWithin(root) {
  if (!root) return []
  return Array.from(root.querySelectorAll(FOCUSABLE)).filter(
    (element) => element.offsetParent !== null || element === document.activeElement,
  )
}

/**
 * Wire an overlay's keyboard and focus behaviour to an `open` ref.
 *
 * @param {import('vue').Ref<boolean>|(() => boolean)} open
 * @param {object} options
 * @param {() => void} options.onClose      called for Escape
 * @param {import('vue').Ref<HTMLElement|null>} options.panelRef  the dialog element
 * @param {boolean} [options.closeOnEscape=true]
 */
export function useOverlay(open, { onClose, panelRef, closeOnEscape = true } = {}) {
  const isOpen = typeof open === 'function' ? open : () => open.value
  let previouslyFocused = null
  let listening = false

  function handleKeydown(event) {
    if (!isOpen()) return

    if (event.key === 'Escape' && closeOnEscape) {
      event.stopPropagation()
      onClose?.()
      return
    }

    if (event.key !== 'Tab') return

    const panel = panelRef?.value
    if (!panel) return
    const items = focusableWithin(panel)
    if (!items.length) {
      // Nothing to land on: keep focus on the panel rather than letting it escape.
      event.preventDefault()
      panel.focus?.()
      return
    }

    const first = items[0]
    const last = items[items.length - 1]
    const active = document.activeElement

    if (!panel.contains(active)) {
      event.preventDefault()
      ;(event.shiftKey ? last : first).focus()
      return
    }
    if (event.shiftKey && active === first) {
      event.preventDefault()
      last.focus()
    } else if (!event.shiftKey && active === last) {
      event.preventDefault()
      first.focus()
    }
  }

  function activate() {
    if (listening) return
    listening = true
    previouslyFocused = document.activeElement
    lockScroll()
    window.addEventListener('keydown', handleKeydown, true)
    nextTick(() => {
      const panel = panelRef?.value
      if (!panel) return
      const [firstFocusable] = focusableWithin(panel)
      ;(firstFocusable || panel).focus?.({ preventScroll: true })
    })
  }

  function deactivate() {
    if (!listening) return
    listening = false
    unlockScroll()
    window.removeEventListener('keydown', handleKeydown, true)
    // Return the user to whatever opened the overlay.
    const target = previouslyFocused
    previouslyFocused = null
    if (target && document.contains(target)) {
      target.focus?.({ preventScroll: true })
    }
  }

  watch(isOpen, (value) => (value ? activate() : deactivate()), { immediate: true })
  onBeforeUnmount(deactivate)

  return { activate, deactivate }
}
