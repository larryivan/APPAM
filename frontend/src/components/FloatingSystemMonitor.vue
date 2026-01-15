<template>
  <div class="floating-system-monitor">
    <!-- 浮动触发按钮 -->
    <div class="monitor-trigger">
      <button @click="toggleWindow" class="monitor-button" :title="isVisible ? 'Hide system monitor' : 'Show system monitor'">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
          <line x1="8" y1="21" x2="16" y2="21"></line>
          <line x1="12" y1="17" x2="12" y2="21"></line>
          <polyline points="6 8 10 12 14 10 18 14"></polyline>
        </svg>
      </button>
    </div>

    <!-- 浮动窗口 -->
    <div
      v-if="isVisible"
      ref="windowRef"
      class="monitor-window"
      :style="windowStyle"
    >
      <!-- Header control bar -->
      <div
        class="monitor-header"
        @mousedown="startDrag"
        @touchstart="startDrag"
      >
        <div class="header-info">
          <h3>System Performance Monitor</h3>
          <div class="status-indicator">
            <div class="status-dot" :class="systemStatus"></div>
            <span>{{ getStatusText() }}</span>
          </div>
        </div>
        <div class="header-actions">
          <button @click="toggleFullscreen" class="control-btn" title="Toggle fullscreen">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path v-if="!isFullscreen" d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>
              <path v-else d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"></path>
            </svg>
          </button>
          <button @click="minimizeWindow" class="control-btn" title="Minimize">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M6 19h12"></path>
            </svg>
          </button>
          <button @click="closeWindow" class="control-btn close-btn" title="Close">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12"></path>
            </svg>
          </button>
        </div>
      </div>

      <!-- System performance content -->
      <div class="monitor-content">
        <SystemPerformance />
      </div>

      <!-- Resize control handles -->
      <div class="resize-handles" v-if="!isFullscreen">
        <div class="resize-handle resize-n" @mousedown="(e) => startResize('n', e)" @touchstart="(e) => startResize('n', e)"></div>
        <div class="resize-handle resize-s" @mousedown="(e) => startResize('s', e)" @touchstart="(e) => startResize('s', e)"></div>
        <div class="resize-handle resize-e" @mousedown="(e) => startResize('e', e)" @touchstart="(e) => startResize('e', e)"></div>
        <div class="resize-handle resize-w" @mousedown="(e) => startResize('w', e)" @touchstart="(e) => startResize('w', e)"></div>
        <div class="resize-handle resize-ne" @mousedown="(e) => startResize('ne', e)" @touchstart="(e) => startResize('ne', e)"></div>
        <div class="resize-handle resize-nw" @mousedown="(e) => startResize('nw', e)" @touchstart="(e) => startResize('nw', e)"></div>
        <div class="resize-handle resize-se" @mousedown="(e) => startResize('se', e)" @touchstart="(e) => startResize('se', e)"></div>
        <div class="resize-handle resize-sw" @mousedown="(e) => startResize('sw', e)" @touchstart="(e) => startResize('sw', e)"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import SystemPerformance from './SystemPerformance.vue'

// Window state
const isVisible = ref(false)
const isFullscreen = ref(false)
const isMinimized = ref(false)
const isDragging = ref(false)
const isResizing = ref(false)
const resizeDirection = ref('')
const systemStatus = ref('normal')

// Window position and size
const windowRef = ref(null)
const windowPosition = ref({ x: 100, y: 100 })
const windowSize = ref({ width: 800, height: 600 })
const dragOffset = ref({ x: 0, y: 0 })

// Resize-related state
const resizeStartPos = ref({ x: 0, y: 0 })
const resizeStartSize = ref({ width: 0, height: 0 })
const resizeStartWindowPos = ref({ x: 0, y: 0 })

// Window boundaries (dynamically calculated)
const getMinWidth = () => Math.min(600, window.innerWidth - 40)
const getMinHeight = () => Math.min(400, window.innerHeight - 40)

// Mobile device detection
const isMobile = ref(false)

// Initialize window position (centered)
const initWindowPosition = () => {
  const screenWidth = window.innerWidth
  const screenHeight = window.innerHeight
  
  // Adjust initial window size based on screen size
  const initialWidth = Math.min(800, screenWidth - 40)
  const initialHeight = Math.min(600, screenHeight - 40)
  
  windowSize.value = { width: initialWidth, height: initialHeight }
  windowPosition.value = {
    x: Math.max(20, (screenWidth - initialWidth) / 2),
    y: Math.max(20, (screenHeight - initialHeight) / 2)
  }
}

// 计算窗口样式
const windowStyle = computed(() => {
  if (isFullscreen.value) {
    return {
      position: 'fixed',
      top: '0',
      left: '0',
      width: '100vw',
      height: '100vh',
      zIndex: 9999,
      transform: 'none'
    }
  }

  if (isMobile.value) {
    return {
      position: 'fixed',
      top: '0',
      left: '0',
      width: '100vw',
      height: '100vh',
      zIndex: 9999,
      transform: 'none'
    }
  }

  return {
    position: 'fixed',
    left: `${windowPosition.value.x}px`,
    top: `${windowPosition.value.y}px`,
    width: `${windowSize.value.width}px`,
    height: `${windowSize.value.height}px`,
    zIndex: 9999
  }
})

// 方法
const toggleWindow = () => {
  isVisible.value = !isVisible.value
  
  // Auto fullscreen on mobile
  if (isVisible.value && isMobile.value) {
    nextTick(() => {
      isFullscreen.value = true
    })
  }
}

const closeWindow = () => {
  isVisible.value = false
  isFullscreen.value = false
  isMinimized.value = false
}

const minimizeWindow = () => {
  isMinimized.value = true
  isVisible.value = false
}

const toggleFullscreen = () => {
  isFullscreen.value = !isFullscreen.value
}

const getStatusText = () => {
  const statusMap = {
    normal: 'Normal',
    warning: 'Warning',
    critical: 'Critical'
  }
  return statusMap[systemStatus.value] || 'Unknown'
}

// Drag functionality
const startDrag = (e) => {
  if (isFullscreen.value || isMobile.value) return
  
  // If clicked on resize handle, don't start dragging
  if (e.target.classList.contains('resize-handle')) return
  
  // Ensure dragging only starts when clicking on header
  const header = e.target.closest('.monitor-header')
  if (!header) return
  
  e.preventDefault()
  isDragging.value = true
  
  const clientX = e.clientX || e.touches[0].clientX
  const clientY = e.clientY || e.touches[0].clientY
  
  dragOffset.value = {
    x: clientX - windowPosition.value.x,
    y: clientY - windowPosition.value.y
  }
  
  document.addEventListener('mousemove', handleDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchmove', handleDrag, { passive: false })
  document.addEventListener('touchend', stopDrag)
}

const handleDrag = (e) => {
  if (!isDragging.value) return
  
  e.preventDefault()
  
  const clientX = e.clientX || e.touches[0].clientX
  const clientY = e.clientY || e.touches[0].clientY
  
  const newX = clientX - dragOffset.value.x
  const newY = clientY - dragOffset.value.y
  
  // 边界检查
  const maxX = window.innerWidth - windowSize.value.width
  const maxY = window.innerHeight - windowSize.value.height
  
  windowPosition.value = {
    x: Math.max(0, Math.min(newX, maxX)),
    y: Math.max(0, Math.min(newY, maxY))
  }
}

const stopDrag = () => {
  isDragging.value = false
  document.removeEventListener('mousemove', handleDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', handleDrag)
  document.removeEventListener('touchend', stopDrag)
}

// Resize functionality
const startResize = (direction, e) => {
  if (isFullscreen.value || isMobile.value) return
  
  e.preventDefault()
  e.stopPropagation()
  
  isResizing.value = true
  resizeDirection.value = direction
  
  // Save state when starting to resize
  const clientX = e.clientX || (e.touches && e.touches[0].clientX)
  const clientY = e.clientY || (e.touches && e.touches[0].clientY)
  
  resizeStartPos.value = { 
    x: clientX, 
    y: clientY 
  }
  resizeStartSize.value = { ...windowSize.value }
  resizeStartWindowPos.value = { ...windowPosition.value }
  
  document.addEventListener('mousemove', handleResize)
  document.addEventListener('mouseup', stopResize)
  document.addEventListener('touchmove', handleResize, { passive: false })
  document.addEventListener('touchend', stopResize)
}

const handleResize = (e) => {
  if (!isResizing.value) return
  
  e.preventDefault()
  
  const clientX = e.clientX || (e.touches && e.touches[0].clientX)
  const clientY = e.clientY || (e.touches && e.touches[0].clientY)
  
  const deltaX = clientX - resizeStartPos.value.x
  const deltaY = clientY - resizeStartPos.value.y
  
  let newWidth = resizeStartSize.value.width
  let newHeight = resizeStartSize.value.height
  let newX = resizeStartWindowPos.value.x
  let newY = resizeStartWindowPos.value.y
  
  // Adjust size based on direction
  if (resizeDirection.value.includes('e')) {
    newWidth = resizeStartSize.value.width + deltaX
  }
  if (resizeDirection.value.includes('w')) {
    const potentialWidth = resizeStartSize.value.width - deltaX
    if (potentialWidth >= getMinWidth()) {
      newWidth = potentialWidth
      newX = resizeStartWindowPos.value.x + deltaX
    }
  }
  if (resizeDirection.value.includes('s')) {
    newHeight = resizeStartSize.value.height + deltaY
  }
  if (resizeDirection.value.includes('n')) {
    const potentialHeight = resizeStartSize.value.height - deltaY
    if (potentialHeight >= getMinHeight()) {
      newHeight = potentialHeight
      newY = resizeStartWindowPos.value.y + deltaY
    }
  }
  
  // 确保尺寸在合理范围内
  newWidth = Math.max(getMinWidth(), Math.min(window.innerWidth - newX - 20, newWidth))
  newHeight = Math.max(getMinHeight(), Math.min(window.innerHeight - newY - 20, newHeight))
  
  // 边界检查
  newX = Math.max(0, newX)
  newY = Math.max(0, newY)
  
  windowSize.value = { width: newWidth, height: newHeight }
  windowPosition.value = { x: newX, y: newY }
}

const stopResize = () => {
  isResizing.value = false
  resizeDirection.value = ''
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)
  document.removeEventListener('touchmove', handleResize)
  document.removeEventListener('touchend', stopResize)
}

// Responsive handling
const handleWindowResize = () => {
  isMobile.value = window.innerWidth <= 768
  
  if (isMobile.value && isVisible.value) {
    isFullscreen.value = true
  }
  
  // Adjust window position to ensure it's within screen bounds
  const currentMaxWidth = window.innerWidth - 20
  const currentMaxHeight = window.innerHeight - 20
  
  // Adjust window size to fit new screen dimensions
  if (windowSize.value.width > currentMaxWidth) {
    windowSize.value.width = currentMaxWidth
  }
  if (windowSize.value.height > currentMaxHeight) {
    windowSize.value.height = currentMaxHeight
  }
  
  // Adjust window position to ensure it's within screen bounds
  const maxX = window.innerWidth - windowSize.value.width
  const maxY = window.innerHeight - windowSize.value.height
  
  if (windowPosition.value.x > maxX) {
    windowPosition.value.x = Math.max(0, maxX)
  }
  if (windowPosition.value.y > maxY) {
    windowPosition.value.y = Math.max(0, maxY)
  }
}

// 键盘快捷键
const handleKeydown = (e) => {
  if (e.key === 'Escape' && isVisible.value) {
    if (isFullscreen.value) {
      isFullscreen.value = false
    } else {
      closeWindow()
    }
  }
}

onMounted(() => {
  initWindowPosition()
  handleWindowResize()
  window.addEventListener('resize', handleWindowResize)
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleWindowResize)
  window.removeEventListener('keydown', handleKeydown)
  document.removeEventListener('mousemove', handleDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', handleDrag)
  document.removeEventListener('touchend', stopDrag)
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)
  document.removeEventListener('touchmove', handleResize)
  document.removeEventListener('touchend', stopResize)
})
</script>

<style scoped>
/* 浮动触发按钮 */
.monitor-trigger {
  position: fixed;
  bottom: 24px;
  right: 152px;
  z-index: 1000;
}

.monitor-button {
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

.monitor-button:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  background: var(--surface-2);
}

/* Monitor window */
.monitor-window {
  background: var(--surface-1);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: var(--border-width) solid var(--border-color-light);
  animation: scaleIn 0.2s ease-out;
}

/* 头部 */
.monitor-header {
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

.header-info h3 {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: var(--font-semibold);
  font-family: var(--font-family-display);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--gray-600);
}

.status-indicator .status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-indicator .status-dot.normal {
  background: var(--success-500);
}

.status-indicator .status-dot.warning {
  background: var(--warning-500);
  animation: pulse 2s infinite;
}

.status-indicator .status-dot.critical {
  background: var(--error-500);
  animation: pulse 2s infinite;
}

.header-actions {
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

/* 内容区域 */
.monitor-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Resize control handles */
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

/* 触摸设备优化 */
@media (hover: none) and (pointer: coarse) {
  .monitor-button:hover {
    transform: none;
    box-shadow: var(--shadow-sm);
    background: var(--surface-1);
  }
  
  .monitor-button:active {
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

/* Responsive design */
@media (max-width: 768px) {
  .monitor-trigger {
    right: 92px;
    bottom: 20px;
  }
  
  .monitor-button {
    width: 44px;
    height: 44px;
  }
  
  .monitor-window {
    border-radius: 0;
    box-shadow: none;
  }
  
  .monitor-header {
    padding: 16px;
  }
  
  .header-info h3 {
    font-size: 16px;
  }
  
  .status-indicator {
    font-size: 14px;
  }
}

/* Mobile safe area */
@media (max-width: 768px) {
  .monitor-trigger {
    bottom: max(20px, env(safe-area-inset-bottom));
    right: max(92px, calc(92px + env(safe-area-inset-right)));
  }
  
  .monitor-window {
    padding-bottom: env(safe-area-inset-bottom);
    padding-left: env(safe-area-inset-left);
    padding-right: env(safe-area-inset-right);
  }
}
</style> 
