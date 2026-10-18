<template>
  <div>
    <div v-if="showTrigger" class="terminal-trigger">
      <button type="button" @click="toggleTerminal" class="terminal-button" :title="triggerLabel" :aria-label="triggerLabel">
        <Icon name="square-terminal" :size="20" />
      </button>
    </div>

    <!-- 终端窗口 -->
    <div
      v-if="isOpen"
      class="terminal-window"
      :style="windowStyle"
      @mousedown="startDrag"
    >
      <!-- 标题栏 -->
      <div class="terminal-header" :class="{ mobile: isMobile }" @mousedown="handleHeaderMouseDown">
        <div class="header-left">
          <span class="terminal-title">{{ windowTitle }}</span>
        </div>
        <div class="header-right">
          <!-- 移动端专用控制按钮 -->
          <template v-if="isMobile">
            <button type="button" class="control-btn mobile-keyboard-btn" @click="focusTerminal" title="Activate keyboard">
              <Icon name="keyboard" :size="16" />
            </button>
            <button type="button" class="control-btn mobile-clear-btn" @click="clearTerminal" title="Clear terminal">
              <Icon name="trash-2" :size="16" />
            </button>
          </template>
          <!-- 桌面端控制按钮 -->
          <template v-else>
          <button type="button" class="control-btn maximize-btn" @click="toggleFullscreen" title="Toggle fullscreen">
            <Icon :name="isFullscreen ? 'minimize-2' : 'maximize-2'" :size="14" />
          </button>
          </template>
          <button type="button" class="control-btn close-btn" @click="closeTerminal" :title="`Close ${title}`">
            <Icon name="x" :size="14" />
          </button>
        </div>
      </div>

      <!-- 终端内容 -->
      <div class="terminal-body" ref="terminalContainer"></div>

      <!-- 调整大小控制点 -->
      <div v-if="!isMobile && !isFullscreen" class="resize-handles">
        <div class="resize-handle resize-n" @mousedown="(e) => startResize('n', e)"></div>
        <div class="resize-handle resize-e" @mousedown="(e) => startResize('e', e)"></div>
        <div class="resize-handle resize-s" @mousedown="(e) => startResize('s', e)"></div>
        <div class="resize-handle resize-w" @mousedown="(e) => startResize('w', e)"></div>
        <div class="resize-handle resize-ne" @mousedown="(e) => startResize('ne', e)"></div>
        <div class="resize-handle resize-nw" @mousedown="(e) => startResize('nw', e)"></div>
        <div class="resize-handle resize-se" @mousedown="(e) => startResize('se', e)"></div>
        <div class="resize-handle resize-sw" @mousedown="(e) => startResize('sw', e)"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { WebLinksAddon } from '@xterm/addon-web-links'
import io from 'socket.io-client'
import '@xterm/xterm/css/xterm.css'

const props = defineProps({
  preset: { type: String, default: 'shell' },
  title: { type: String, default: 'Terminal' },
  showTrigger: { type: Boolean, default: true },
})

const route = useRoute()
const projectId = computed(() => String(route.params.id || ''))

const getThemeValue = (variableName, fallback) => {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(variableName)
  return value ? value.trim() : fallback
}

// 窗口状态
const isOpen = ref(false)
const isFullscreen = ref(false)
const isMobile = ref(false)
const triggerLabel = computed(() => `${isOpen.value ? 'Hide' : 'Open'} ${props.title.toLowerCase()}`)
const windowTitle = computed(() => {
  if (isMobile.value) return props.title
  return `${props.title} - ${projectId.value.slice(0, 8) || 'No project'}`
})

// 窗口位置和大小
const windowPosition = ref(props.preset === 'opencode'
  ? { x: window.innerWidth - 700, y: 80 }
  : { x: window.innerWidth - 650, y: window.innerHeight - 450 })
const windowSize = ref(props.preset === 'opencode'
  ? { width: 640, height: 520 }
  : { width: 600, height: 400 })

// 移动端检测
const detectMobile = () => {
  const userAgent = navigator.userAgent.toLowerCase()
  const mobileKeywords = ['mobile', 'iphone', 'android', 'blackberry', 'nokia', 'opera mini', 'windows mobile', 'windows phone', 'iemobile']
  return mobileKeywords.some(keyword => userAgent.includes(keyword)) || window.innerWidth <= 768
}

// 拖拽状态
const isDragging = ref(false)
const dragOffset = ref({ x: 0, y: 0 })

// 调整大小状态
const isResizing = ref(false)
const resizeDirection = ref('')
const resizeStartPos = ref({ x: 0, y: 0 })
const resizeStartSize = ref({ width: 0, height: 0 })
const resizeStartWindowPos = ref({ x: 0, y: 0 })

// 终端实例
const terminalContainer = ref(null)
let terminal = null
let fitAddon = null
let socket = null
let resizeObserver = null
let fitPending = false
let fitQueued = false
const sessionKey = ref('')
const sessionReady = ref(false)
const createSessionKey = () => `${props.preset}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`

const resetSessionKey = () => {
  sessionKey.value = createSessionKey()
}

const ensureSessionKey = () => {
  if (!sessionKey.value) {
    resetSessionKey()
  }
  return sessionKey.value
}

const scheduleFit = (delay = 0) => {
  if (!fitAddon || !terminal) return
  if (fitPending) {
    fitQueued = true
    return
  }
  fitPending = true

  const run = () => {
    fitPending = false
    if (!fitAddon || !terminal) return
    fitAddon.fit()
    if (sessionReady.value && socket && socket.connected) {
      const { rows, cols } = terminal
      socket.emit('terminal_resize', { rows, cols, session_key: sessionKey.value })
    }
    if (fitQueued) {
      fitQueued = false
      scheduleFit(0)
    }
  }

  if (delay > 0) {
    setTimeout(run, delay)
  } else {
    requestAnimationFrame(run)
  }
}

const attachResizeObserver = () => {
  if (!terminalContainer.value || typeof ResizeObserver === 'undefined') return
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
  resizeObserver = new ResizeObserver(() => {
    scheduleFit()
  })
  resizeObserver.observe(terminalContainer.value)
}

const detachResizeObserver = () => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
}

// 计算窗口样式
const windowStyle = computed(() => {
  // 移动端始终使用全屏布局
  if (isMobile.value || isFullscreen.value) {
    return {
      position: 'fixed',
      top: isMobile.value ? '0' : '0',
      left: '0',
      width: '100vw',
      height: isMobile.value ? '100vh' : '100vh',
      zIndex: 9999,
      borderRadius: '0'
    }
  }

  // 桌面端浮动窗口
  return {
    position: 'fixed',
    top: `${windowPosition.value.y}px`,
    left: `${windowPosition.value.x}px`,
    width: `${windowSize.value.width}px`,
    height: `${windowSize.value.height}px`,
    zIndex: 1000
  }
})

// 打开终端
const openTerminal = () => {
  if (isOpen.value) return
  isMobile.value = detectMobile()
  resetSessionKey()
  sessionReady.value = false
  isOpen.value = true
  isFullscreen.value = isMobile.value

  nextTick(() => {
    initTerminal()
    connectSocket()
    attachResizeObserver()
    scheduleFit(140)
  })
}

const toggleTerminal = () => {
  if (isOpen.value) {
    closeTerminal()
  } else {
    openTerminal()
  }
}

// 关闭终端
const closeTerminal = () => {
  if (socket) {
    socket.emit('terminal_disconnect', { session_key: sessionKey.value })
    socket.disconnect()
    socket = null
  }

  if (terminal) {
    terminal.dispose()
    terminal = null
  }

  detachResizeObserver()
  fitPending = false
  fitQueued = false
  isOpen.value = false
  isFullscreen.value = false
  sessionReady.value = false
  sessionKey.value = ''
}

defineExpose({
  openWindow: openTerminal,
  closeWindow: closeTerminal,
  toggleWindow: toggleTerminal,
  isOpen,
})

// 切换全屏
const toggleFullscreen = () => {
  // 移动端不允许退出全屏
  if (isMobile.value) return

  isFullscreen.value = !isFullscreen.value

  if (fitAddon) {
    scheduleFit(120)
  }
}

// 移动端专用：聚焦终端（激活软键盘）
const focusTerminal = () => {
  if (terminal) {
    terminal.focus()
  }
}

// 移动端专用：清屏
const clearTerminal = () => {
  if (terminal) {
    terminal.clear()
    terminal.write('\x1b[H\x1b[2J') // 额外的清屏命令
  }
}

// 初始化终端
const initTerminal = () => {
  const darkBg = getThemeValue('--dark-bg', '#0b1220')
  const textLight = getThemeValue('--text-light', '#e2e8f0')
  const primary400 = getThemeValue('--accent-200', '#bcd0ee')
  const primary500 = getThemeValue('--accent-500', '#2f62c4')
  const success500 = getThemeValue('--success-500', '#16a34a')
  const warning500 = getThemeValue('--warning-500', '#f59e0b')
  const error500 = getThemeValue('--error-500', '#ef4444')
  const secondaryColor = getThemeValue('--secondary-color', '#0ea5e9')
  const gray700 = getThemeValue('--gray-700', '#374151')
  const monoFont = getThemeValue('--font-family-mono', 'Menlo, Monaco, "Courier New", monospace')

  // 移动端优化配置
  const terminalConfig = {
    theme: {
      background: darkBg,
      foreground: textLight,
      cursor: primary400,
      black: darkBg,
      red: error500,
      green: success500,
      yellow: warning500,
      blue: primary500,
      magenta: primary400,
      cyan: secondaryColor,
      white: textLight,
      brightBlack: gray700,
      brightRed: error500,
      brightGreen: success500,
      brightYellow: warning500,
      brightBlue: primary500,
      brightMagenta: primary400,
      brightCyan: secondaryColor,
      brightWhite: textLight
    },
    fontFamily: monoFont,
    fontSize: isMobile.value ? 12 : 14,
    lineHeight: isMobile.value ? 1.4 : 1.2,
    cursorBlink: true,
    scrollback: isMobile.value ? 500 : 1000,
    tabStopWidth: 4,
    // 移动端优化选项
    ...(isMobile.value && {
      disableStdin: false,
      convertEol: true,
      screenReaderMode: false,
      allowTransparency: false
    })
  }

  terminal = new Terminal(terminalConfig)

  // 添加插件
  fitAddon = new FitAddon()
  terminal.loadAddon(fitAddon)
  terminal.loadAddon(new WebLinksAddon())

  // 挂载到 DOM
  terminal.open(terminalContainer.value)

  // 延迟调整大小以确保DOM渲染完成
  setTimeout(() => {
  scheduleFit()

    // 移动端自动聚焦可能导致软键盘弹出，延迟聚焦
    if (!isMobile.value) {
  terminal.focus()
    }
  }, 100)
}

// 连接 Socket
const connectSocket = () => {
  socket = io('/', {
    withCredentials: true
  })

  socket.on('connect', () => {
    sessionReady.value = false
    socket.emit('terminal_connect', {
      project_id: projectId.value,
      session_key: ensureSessionKey(),
      keep_alive: false,
      preset: props.preset
    })
  })

  socket.on('terminal_connected', (data) => {
    sessionReady.value = true
    if (data?.session_key) {
      sessionKey.value = data.session_key
    }
    scheduleFit(80)
  })

  socket.on('terminal_output', (data) => {
    if (terminal && data.output) {
      terminal.write(data.output)
    }
  })

  socket.on('terminal_error', (data) => {
    if (terminal) {
      terminal.write(`\r\n\x1b[31mError: ${data.error}\x1b[0m\r\n`)
    }
    if (data?.error && (
      data.error.includes('Terminal session not found') ||
      data.error.includes('Terminal session ended') ||
      data.error.includes('Failed to start terminal command')
    )) {
      sessionReady.value = false
      socket?.disconnect()
    }
  })

  socket.on('terminal_exit', () => {
    sessionReady.value = false
    if (terminal) {
      terminal.write(`\r\n\x1b[33m${props.title} exited. Close and reopen the panel to start a fresh session.\x1b[0m\r\n`)
    }
    socket?.disconnect()
  })

  socket.on('disconnect', (reason) => {
    sessionReady.value = false
    if (terminal && isOpen.value && reason !== 'io client disconnect') {
      terminal.write(`\r\n\x1b[33m${props.title} disconnected. Reopen the panel to reconnect.\x1b[0m\r\n`)
    }
  })

  // 处理终端输入
  terminal.onData((data) => {
    if (sessionReady.value && socket && socket.connected) {
      socket.emit('terminal_input', { input: data, session_key: sessionKey.value })
    }
  })

  // 处理终端大小变化
  terminal.onResize(({ rows, cols }) => {
    if (sessionReady.value && socket && socket.connected) {
      socket.emit('terminal_resize', { rows, cols, session_key: sessionKey.value })
    }
  })
}

// 拖拽功能
const startDrag = (e) => {
  // 移动端或全屏状态下禁用拖拽
  if (isMobile.value || isFullscreen.value || e.target.closest('.control-btn')) {
    return
  }

  isDragging.value = true
  dragOffset.value = {
    x: e.clientX - windowPosition.value.x,
    y: e.clientY - windowPosition.value.y
  }

  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
}

const handleHeaderMouseDown = (e) => {
  // 移动端或全屏状态下禁用拖拽
  if (isMobile.value || isFullscreen.value || e.target.closest('.control-btn')) {
    return
  }

  isDragging.value = true
  dragOffset.value = {
    x: e.clientX - windowPosition.value.x,
    y: e.clientY - windowPosition.value.y
  }

  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
}

const handleMouseMove = (e) => {
  if (isDragging.value) {
    windowPosition.value = {
      x: Math.max(0, Math.min(e.clientX - dragOffset.value.x, window.innerWidth - windowSize.value.width)),
      y: Math.max(0, Math.min(e.clientY - dragOffset.value.y, window.innerHeight - windowSize.value.height))
    }
  }

  if (isResizing.value) {
    handleResizeDrag(e)
  }
}

const handleMouseUp = () => {
  isDragging.value = false
  isResizing.value = false
  resizeDirection.value = ''
  document.removeEventListener('mousemove', handleMouseMove)
  document.removeEventListener('mouseup', handleMouseUp)
}

// 调整大小功能
const startResize = (direction, event) => {
  event.preventDefault()
  event.stopPropagation()

  isResizing.value = true
  resizeDirection.value = direction
  resizeStartPos.value = { x: event.clientX, y: event.clientY }
  resizeStartSize.value = { ...windowSize.value }
  resizeStartWindowPos.value = { ...windowPosition.value }

  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
}

const handleResizeDrag = (e) => {
  const deltaX = e.clientX - resizeStartPos.value.x
  const deltaY = e.clientY - resizeStartPos.value.y

  let newWidth = resizeStartSize.value.width
  let newHeight = resizeStartSize.value.height
  let newX = resizeStartWindowPos.value.x
  let newY = resizeStartWindowPos.value.y

  const minWidth = 400
  const minHeight = 300
  const maxWidth = window.innerWidth - 20
  const maxHeight = window.innerHeight - 20

  if (resizeDirection.value.includes('e')) {
    newWidth = Math.max(minWidth, Math.min(maxWidth, resizeStartSize.value.width + deltaX))
  }
  if (resizeDirection.value.includes('w')) {
    newWidth = Math.max(minWidth, Math.min(maxWidth, resizeStartSize.value.width - deltaX))
    newX = resizeStartWindowPos.value.x + (resizeStartSize.value.width - newWidth)
  }
  if (resizeDirection.value.includes('s')) {
    newHeight = Math.max(minHeight, Math.min(maxHeight, resizeStartSize.value.height + deltaY))
  }
  if (resizeDirection.value.includes('n')) {
    newHeight = Math.max(minHeight, Math.min(maxHeight, resizeStartSize.value.height - deltaY))
    newY = resizeStartWindowPos.value.y + (resizeStartSize.value.height - newHeight)
  }

  // 边界检查
  if (newX < 0) {
    newWidth += newX
    newX = 0
  }
  if (newY < 0) {
    newHeight += newY
    newY = 0
  }
  if (newX + newWidth > window.innerWidth) {
    newWidth = window.innerWidth - newX
  }
  if (newY + newHeight > window.innerHeight) {
    newHeight = window.innerHeight - newY
  }

  windowSize.value = { width: newWidth, height: newHeight }
  windowPosition.value = { x: newX, y: newY }

  // 调整终端大小
  if (fitAddon && terminal) {
    scheduleFit(60)
  }
}

// 窗口大小变化处理
const handleResize = () => {
  // 重新检测移动端状态
  const wasMobile = isMobile.value
  isMobile.value = detectMobile()

  // 如果从桌面端切换到移动端，自动全屏
  if (!wasMobile && isMobile.value && isOpen.value) {
    isFullscreen.value = true
  }

  // 调整终端大小
  if (fitAddon && isOpen.value) {
    scheduleFit(120)
  }
}

// 生命周期
onMounted(() => {
  isMobile.value = detectMobile()
  window.addEventListener('resize', handleResize)
})

watch(projectId, () => {
  if (!isOpen.value) return
  closeTerminal()
  openTerminal()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  closeTerminal()
  detachResizeObserver()
})
</script>

<style scoped>
/* 浮动按钮 */
.terminal-trigger {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 1000;
}

.terminal-button {
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-base);
  width: 40px;
  height: 40px;
  color: var(--primary-600);
  cursor: pointer;
  box-shadow: none;
  transition: background var(--transition-fast), color var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.terminal-button:hover {
  background: var(--surface-2);
}

/* 终端窗口 */
.terminal-window {
  background: var(--surface-1);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: var(--border-width) solid var(--border-color-light);
  animation: windowIn var(--transition-base);
}

/* 标题栏 */
.terminal-header {
  background: var(--surface-2);
  color: var(--gray-900);
  min-height: 44px;
  padding: 0 10px 0 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: var(--border-width) solid var(--border-color-light);
  cursor: move;
  user-select: none;
}

.header-left {
  display: flex;
  align-items: center;
}

.terminal-title {
  font-size: 13px;
  font-weight: var(--font-semibold);
  margin: 0;
  font-family: var(--font-family-display);
}

.header-right {
  display: flex;
  gap: 4px;
}

.control-btn {
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-color-light);
  color: var(--gray-600);
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: none;
}

.control-btn:hover {
  background: var(--surface-2);
  color: var(--gray-800);
  border-color: var(--border-color);
}

.close-btn:hover {
  background: var(--error-50);
  border-color: rgba(239, 68, 68, 0.25);
  color: var(--error-600);
}

/* 终端主体 */
.terminal-body {
  flex: 1;
  overflow: hidden;
  background: var(--dark-bg);
}

/* xterm.js 样式覆盖 */
:deep(.xterm) {
  padding: var(--spacing-3, 12px);
  color: var(--text-light);
  font-family: var(--font-family-mono);
}

:deep(.xterm-viewport) {
  background: var(--dark-bg);
}

:deep(.xterm-screen) {
  background: var(--dark-bg);
}

/* 全屏状态下的特殊样式 */
@keyframes windowIn {
  from {
    transform: translateY(4px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

/* 调整大小控制点 */
.resize-handles {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.resize-handle {
  position: absolute;
  pointer-events: auto;
  background: transparent;
}

.resize-n {
  top: 0;
  left: 8px;
  right: 8px;
  height: 4px;
  cursor: n-resize;
}

.resize-s {
  bottom: 0;
  left: 8px;
  right: 8px;
  height: 4px;
  cursor: s-resize;
}

.resize-e {
  top: 8px;
  right: 0;
  bottom: 8px;
  width: 4px;
  cursor: e-resize;
}

.resize-w {
  top: 8px;
  left: 0;
  bottom: 8px;
  width: 4px;
  cursor: w-resize;
}

.resize-ne {
  top: 0;
  right: 0;
  width: 8px;
  height: 8px;
  cursor: ne-resize;
}

.resize-nw {
  top: 0;
  left: 0;
  width: 8px;
  height: 8px;
  cursor: nw-resize;
}

.resize-se {
  bottom: 0;
  right: 0;
  width: 8px;
  height: 8px;
  cursor: se-resize;
}

.resize-sw {
  bottom: 0;
  left: 0;
  width: 8px;
  height: 8px;
  cursor: sw-resize;
}

/* 安全区域适配 */
@supports (padding: max(0px)) {
  @media (max-width: 768px) {
    .terminal-header.mobile {
      padding-top: max(16px, env(safe-area-inset-top));
      padding-left: max(20px, env(safe-area-inset-left));
      padding-right: max(20px, env(safe-area-inset-right));
    }

    .terminal-body {
      padding-left: max(0px, env(safe-area-inset-left));
      padding-right: max(0px, env(safe-area-inset-right));
      padding-bottom: max(0px, env(safe-area-inset-bottom));
    }
  }
}

/* 移动端安全区域 */
@media (max-width: 768px) {
  .terminal-trigger {
    bottom: max(20px, env(safe-area-inset-bottom));
    right: max(4px, calc(4px + env(safe-area-inset-right)));
  }

  .terminal-window {
    padding-bottom: env(safe-area-inset-bottom);
    padding-left: env(safe-area-inset-left);
    padding-right: env(safe-area-inset-right);
  }
}

/* 移动端特定样式 */
.terminal-header.mobile {
  padding: 16px 20px;
  cursor: default;
  user-select: none;
  background: var(--surface-2);
  border-bottom: var(--border-width) solid var(--border-color-light);
}

.terminal-header.mobile .terminal-title {
  font-size: 16px;
  font-weight: var(--font-semibold);
}

.mobile-keyboard-btn,
.mobile-clear-btn {
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-color-light);
  backdrop-filter: blur(10px);
}

.mobile-keyboard-btn:hover,
.mobile-clear-btn:hover {
  background: var(--surface-2);
  border-color: var(--border-color);
}

/* 触摸设备优化 */
@media (hover: none) and (pointer: coarse) {
  .terminal-button:hover {
    transform: none;
    box-shadow: none;
    background: var(--surface-1);
  }

  .terminal-button:active {
    background: var(--surface-3);
  }

  .control-btn:hover {
    background: var(--surface-1);
    color: var(--gray-600);
    border-color: var(--border-color-light);
    transform: none;
  }

  .control-btn:active {
    background: var(--surface-3);
  }
}
</style>
