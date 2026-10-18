import { computed, ref } from 'vue'

// Floating tool windows (system monitor, terminal, assistant) share one layer:
// above the page and the top bar (--z-fixed), below dialogs (--z-modal-backdrop)
// and toasts. Whichever window was opened or clicked last is drawn on top.
const BASE_Z_INDEX = 1031
const stack = ref([])

export function useFloatingWindow(id) {
  const zIndex = computed(() => BASE_Z_INDEX + Math.max(0, stack.value.indexOf(id)))

  const bringToFront = () => {
    if (stack.value[stack.value.length - 1] === id) return
    stack.value = [...stack.value.filter((entry) => entry !== id), id]
  }

  const release = () => {
    stack.value = stack.value.filter((entry) => entry !== id)
  }

  return { zIndex, bringToFront, release }
}

// Keep a window's title bar reachable after the viewport shrinks or when a
// default position computed for another screen size no longer fits.
export function clampToViewport({ x, y }, { width, height }, margin = 8) {
  const maxX = Math.max(margin, window.innerWidth - width - margin)
  const maxY = Math.max(margin, window.innerHeight - height - margin)
  return {
    x: Math.min(Math.max(margin, x), maxX),
    y: Math.min(Math.max(margin, y), maxY),
  }
}
