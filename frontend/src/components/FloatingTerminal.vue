<template>
  <div>
    <!-- 浮动按钮 -->
    <div class="terminal-trigger">
      <button @click="toggleTerminal" class="terminal-button" :title="isOpen ? 'Hide Terminal' : 'Show Terminal'">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
        <line x1="8" y1="21" x2="16" y2="21"></line>
        <line x1="12" y1="17" x2="12" y2="21"></line>
          <path d="m6 7 4 4-4 4"></path>
          <path d="m13 7 4 4-4 4"></path>
      </svg>
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
          <span class="terminal-title">{{ isMobile ? 'Terminal' : `Terminal - ${projectName}` }}</span>
        </div>
        <div class="header-right">
          <!-- 移动端专用控制按钮 -->
          <template v-if="isMobile">
            <button class="control-btn mobile-keyboard-btn" @click="focusTerminal" title="Activate Keyboard">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
                <line x1="8" y1="21" x2="16" y2="21"></line>
                <line x1="12" y1="17" x2="12" y2="21"></line>
              </svg>
            </button>
            <button class="control-btn mobile-clear-btn" @click="clearTerminal" title="Clear Screen">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 6h18"></path>
                <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
              </svg>
            </button>
          </template>
          <!-- 桌面端控制按钮 -->
          <template v-else>
          <button class="control-btn maximize-btn" @click="toggleFullscreen" title="Toggle Fullscreen">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path v-if="!isFullscreen" d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>
              <path v-else d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"></path>
            </svg>
          </button>
          </template>
          <button class="control-btn close-btn" @click="closeTerminal" title="Close Terminal">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
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
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { Terminal } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import { WebLinksAddon } from 'xterm-addon-web-links'
import io from 'socket.io-client'
import 'xterm/css/xterm.css'

const route = useRoute()
const projectId = computed(() => route.params.id)
const projectName = ref('APPAM')

const getThemeValue = (variableName, fallback) => {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(variableName)
  return value ? value.trim() : fallback
}

// 窗口状态
const isOpen = ref(false)
const isFullscreen = ref(false)
const isMobile = ref(false)

// 窗口位置和大小
const windowPosition = ref({ x: window.innerWidth - 650, y: window.innerHeight - 450 })
const windowSize = ref({ width: 600, height: 400 })

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
      borderRadius: isMobile.value ? '0' : 'var(--radius-lg, 12px)'
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
  if (!isOpen.value) {
  isOpen.value = true
    isFullscreen.value = isMobile.value
  
  nextTick(() => {
      initTerminal()
    connectSocket()
  })
  }
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
    socket.emit('terminal_disconnect')
    socket.disconnect()
    socket = null
  }
  
  if (terminal) {
    terminal.dispose()
    terminal = null
  }
  
  isOpen.value = false
  isFullscreen.value = false
}

// 切换全屏
const toggleFullscreen = () => {
  // 移动端不允许退出全屏
  if (isMobile.value) return
  
  isFullscreen.value = !isFullscreen.value
  
  if (fitAddon) {
    setTimeout(() => {
      fitAddon.fit()
      if (socket) {
        const { rows, cols } = terminal
        socket.emit('terminal_resize', { rows, cols })
      }
    }, 100)
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
  const primary400 = getThemeValue('--primary-400', '#5f8cff')
  const primary500 = getThemeValue('--primary-500', '#2563eb')
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
  fitAddon.fit()
  
    // 移动端自动聚焦可能导致软键盘弹出，延迟聚焦
    if (!isMobile.value) {
  terminal.focus()
    }
  }, 100)
}

// 连接 Socket
const connectSocket = () => {
  socket = io('/', {
    transports: ['websocket'],
    upgrade: false
  })
  
  socket.on('connect', () => {
    socket.emit('terminal_connect', { project_id: projectId.value })
  })
  
  socket.on('terminal_connected', (data) => {
    console.log('Terminal connected:', data)
    // 移除冗余的提示信息，让用户直接使用终端
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
  })
  
  // 处理终端输入
  terminal.onData((data) => {
    if (socket && socket.connected) {
      socket.emit('terminal_input', { input: data })
    }
  })
  
  // 处理终端大小变化
  terminal.onResize(({ rows, cols }) => {
    if (socket && socket.connected) {
      socket.emit('terminal_resize', { rows, cols })
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
    setTimeout(() => {
      fitAddon.fit()
      const { rows, cols } = terminal
      if (socket) {
        socket.emit('terminal_resize', { rows, cols })
      }
    }, 50)
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
    setTimeout(() => {
      fitAddon.fit()
      if (socket && terminal) {
        const { rows, cols } = terminal
        socket.emit('terminal_resize', { rows, cols })
      }
    }, 100)
  }
}

// 生命周期
onMounted(() => {
  // 监听窗口大小变化
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  closeTerminal()
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
  border: var(--border-width) solid rgba(var(--accent-rgb), 0.25);
  border-radius: 50%;
  width: 48px;
  height: 48px;
  color: var(--primary-600);
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.terminal-button:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  background: var(--surface-2);
}

/* 终端窗口 */
.terminal-window {
  background: var(--surface-1);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: var(--border-width) solid var(--border-color-light);
  animation: scaleIn 0.2s ease-out;
}

/* 标题栏 */
.terminal-header {
  background: linear-gradient(180deg, rgba(var(--accent-rgb), 0.12) 0%, rgba(255, 255, 255, 0.96) 85%);
  color: var(--gray-900);
  padding: 12px 16px;
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
  font-size: 14px;
  font-weight: var(--font-semibold);
  margin: 0;
  font-family: var(--font-family-display);
}

.header-right {
  display: flex;
  gap: 8px;
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
  box-shadow: var(--shadow-xs);
}

.control-btn:hover {
  background: var(--surface-2);
  color: var(--gray-800);
  border-color: var(--border-color);
  transform: translateY(-1px);
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
.terminal-window:has(.terminal-header) {
  animation: scaleIn 0.2s ease-out;
}

/* 动画 */
@keyframes scaleIn {
  from {
    transform: scale(0.95);
    opacity: 0;
  }
  to {
    transform: scale(1);
    opacity: 1;
  }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
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
  background: linear-gradient(180deg, rgba(var(--accent-rgb), 0.12) 0%, rgba(255, 255, 255, 0.96) 85%);
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
    box-shadow: var(--shadow-sm);
    background: var(--surface-1);
  }
  
  .terminal-button:active {
    transform: scale(0.95);
    transition-duration: 0.1s;
  }
  
  .control-btn:hover {
    background: var(--surface-1);
    color: var(--gray-600);
    border-color: var(--border-color-light);
    transform: none;
  }
  
  .control-btn:active {
    transform: scale(0.96);
    transition-duration: 0.1s;
  }
}
</style> 
