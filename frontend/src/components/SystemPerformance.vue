<template>
  <div class="system-performance">
    <div class="performance-header">
      <h3>System Performance Monitor</h3>
      <div class="header-controls">
        <button @click="refreshData" class="btn btn-secondary refresh-btn" :class="{ loading: loading }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="m3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
          Refresh
        </button>

        <div class="update-indicator">
          <span class="update-dot" :class="{ active: isRealtime }"></span>
          <span class="update-text">{{ isRealtime ? 'Real-time Update' : 'Paused' }}</span>
        </div>
      </div>
    </div>

    <div v-if="loading && !systemInfo" class="loading-state">
      <div class="loading-spinner"></div>
      <p>Loading system information...</p>
    </div>

    <div v-else-if="error" class="error-state">
      <div class="error-icon">⚠️</div>
      <p>{{ error }}</p>
      <button @click="refreshData" class="btn btn-primary retry-btn">Retry</button>
    </div>

    <div v-else-if="systemInfo" class="performance-content">
      <!-- System Status Overview -->
      <div class="status-overview">
        <div class="status-card cpu" :class="getStatusClass(systemInfo.cpu?.usage_percent)">
          <div class="status-icon">🖥️</div>
          <div class="status-info">
            <div class="status-value">{{ systemInfo.cpu?.usage_percent?.toFixed(1) || '0' }}%</div>
            <div class="status-label">CPU Usage</div>
          </div>
          <div class="status-details">
            <div class="detail-item">
              <span>{{ systemInfo.cpu?.logical_cores || 0 }} cores</span>
            </div>
            <div class="detail-item" v-if="systemInfo.cpu?.frequency?.current">
              <span>{{ (systemInfo.cpu.frequency.current / 1000).toFixed(1) }} GHz</span>
            </div>
          </div>
        </div>

        <div class="status-card memory" :class="getStatusClass(systemInfo.memory?.usage_percent)">
          <div class="status-icon">💾</div>
          <div class="status-info">
            <div class="status-value">{{ systemInfo.memory?.usage_percent?.toFixed(1) || '0' }}%</div>
            <div class="status-label">Memory Usage</div>
          </div>
          <div class="status-details">
            <div class="detail-item">
              <span>{{ formatBytes(systemInfo.memory?.used || 0) }} / {{ formatBytes(systemInfo.memory?.total || 0) }}</span>
            </div>
            <div class="detail-item">
              <span>Available: {{ formatBytes(systemInfo.memory?.available || 0) }}</span>
            </div>
          </div>
        </div>

        <div class="status-card disk" :class="getDiskStatusClass()">
          <div class="status-icon">💽</div>
          <div class="status-info">
            <div class="status-value">{{ getTotalDiskUsage().toFixed(1) }}%</div>
            <div class="status-label">Disk Usage</div>
          </div>
          <div class="status-details">
            <div class="detail-item">
              <span>{{ formatBytes(getTotalDiskUsed()) }} / {{ formatBytes(getTotalDiskSpace()) }}</span>
            </div>
            <div class="detail-item">
              <span>Available: {{ formatBytes(getTotalDiskFree()) }}</span>
            </div>
          </div>
        </div>

        <div class="status-card load" :class="getLoadStatusClass()">
          <div class="status-icon">⚡</div>
          <div class="status-info">
            <div class="status-value">{{ (systemInfo.load?.load_1min || 0).toFixed(2) }}</div>
            <div class="status-label">System Load</div>
          </div>
          <div class="status-details">
            <div class="detail-item" v-if="systemInfo.load?.load_5min !== null">
              <span>5min: {{ (systemInfo.load?.load_5min || 0).toFixed(2) }}</span>
            </div>
            <div class="detail-item" v-if="systemInfo.load?.load_15min !== null">
              <span>15min: {{ (systemInfo.load?.load_15min || 0).toFixed(2) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Charts Area -->
      <div class="charts-container">
        <!-- CPU Usage History Chart -->
        <div class="chart-card">
          <div class="chart-header">
            <h4>CPU Usage Trend</h4>
            <div class="chart-controls">
              <button @click="clearCpuHistory" class="btn btn-ghost clear-btn">Clear History</button>
            </div>
          </div>
          <div ref="cpuChart" class="chart-container"></div>
        </div>

        <!-- Memory Usage -->
        <div class="chart-card">
          <div class="chart-header">
            <h4>Memory Usage Distribution</h4>
          </div>
          <div ref="memoryChart" class="chart-container"></div>
        </div>

        <!-- Disk Usage -->
        <div class="chart-card">
          <div class="chart-header">
            <h4>Disk Space Usage</h4>
          </div>
          <div ref="diskChart" class="chart-container"></div>
        </div>

        <!-- System Load -->
        <div class="chart-card">
          <div class="chart-header">
            <h4>System Load Trend</h4>
            <div class="chart-controls">
              <button @click="clearLoadHistory" class="btn btn-ghost clear-btn">Clear History</button>
            </div>
          </div>
          <div ref="loadChart" class="chart-container"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

// Reactive data
const loading = ref(false)
const error = ref(null)
const isRealtime = ref(true)
const systemInfo = ref(null)

// Chart references
const cpuChart = ref(null)
const memoryChart = ref(null)
const diskChart = ref(null)
const loadChart = ref(null)

// ECharts instances
let cpuChartInstance = null
let memoryChartInstance = null
let diskChartInstance = null
let loadChartInstance = null

// Historical data
const cpuHistory = ref([])
const loadHistory = ref([])
const maxHistoryPoints = 20

let chartTheme = null

// Timer
let updateInterval = null

// Methods
const fetchSystemInfo = async () => {
  try {
    loading.value = true
    error.value = null

    // Get system information
    const response = await fetch('/api/system/info')

    if (!response.ok) {
      throw new Error('Failed to get system information')
    }

    const data = await response.json()

    if (data.success) {
      systemInfo.value = data.data
      
      // Add to history records
      const now = new Date()
      const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      
      // CPU history
      cpuHistory.value.push({
        time: timeStr,
        value: data.data.cpu?.usage_percent || 0
      })
      if (cpuHistory.value.length > maxHistoryPoints) {
        cpuHistory.value.shift()
      }

      // Load history
      if (data.data.load?.load_1min !== null) {
        loadHistory.value.push({
          time: timeStr,
          load_1min: data.data.load.load_1min || 0,
          load_5min: data.data.load.load_5min || 0,
          load_15min: data.data.load.load_15min || 0
        })
        if (loadHistory.value.length > maxHistoryPoints) {
          loadHistory.value.shift()
        }
      }

      // Update charts
      nextTick(() => {
        console.log('Data fetched, updating charts...')
        updateCharts()
      })
    } else {
      throw new Error(data.message || 'Failed to get system information')
    }

  } catch (err) {
    console.error('Failed to get system information:', err)
    error.value = err.message
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  fetchSystemInfo()
}

const getThemeValue = (name, fallback) => {
  if (typeof window === 'undefined') return fallback
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return value || fallback
}

const getChartTheme = () => {
  const accentRgb = getThemeValue('--accent-rgb', '37, 99, 235')
  return {
    accentRgb,
    primary: getThemeValue('--primary-500', '#2563eb'),
    primary700: getThemeValue('--primary-700', '#1e40af'),
    success: getThemeValue('--success-500', '#16a34a'),
    warning: getThemeValue('--warning-500', '#f59e0b'),
    error: getThemeValue('--error-500', '#ef4444'),
    gray400: getThemeValue('--gray-400', '#9aa6b2'),
    gray500: getThemeValue('--gray-500', '#6b7280'),
    gray600: getThemeValue('--gray-600', '#4b5563'),
    surface2: getThemeValue('--surface-2', '#f1f5f9'),
    surface3: getThemeValue('--surface-3', '#e9eef5')
  }
}

const ensureChartTheme = () => {
  if (!chartTheme) {
    chartTheme = getChartTheme()
  }
  return chartTheme
}

const initCharts = () => {
  console.log('Initializing charts...')
  console.log('Chart refs:', {
    cpuChart: cpuChart.value,
    memoryChart: memoryChart.value, 
    diskChart: diskChart.value,
    loadChart: loadChart.value
  })
  
  try {
    if (cpuChart.value && !cpuChartInstance) {
      console.log('Initializing CPU chart')
      cpuChartInstance = echarts.init(cpuChart.value)
      console.log('CPU chart initialized:', cpuChartInstance)
    } else if (!cpuChart.value) {
      console.error('CPU chart ref is null')
    }
    
    if (memoryChart.value && !memoryChartInstance) {
      console.log('Initializing memory chart')
      memoryChartInstance = echarts.init(memoryChart.value)
      console.log('Memory chart initialized:', memoryChartInstance)
    } else if (!memoryChart.value) {
      console.error('Memory chart ref is null')
    }
    
    if (diskChart.value && !diskChartInstance) {
      console.log('Initializing disk chart')
      diskChartInstance = echarts.init(diskChart.value)
      console.log('Disk chart initialized:', diskChartInstance)
    } else if (!diskChart.value) {
      console.error('Disk chart ref is null')
    }
    
    if (loadChart.value && !loadChartInstance) {
      console.log('Initializing load chart')
      loadChartInstance = echarts.init(loadChart.value)
      console.log('Load chart initialized:', loadChartInstance)
    } else if (!loadChart.value) {
      console.error('Load chart ref is null')
    }
    
    console.log('Chart instances:', {
      cpuChartInstance: !!cpuChartInstance,
      memoryChartInstance: !!memoryChartInstance,
      diskChartInstance: !!diskChartInstance,
      loadChartInstance: !!loadChartInstance
    })
  } catch (error) {
    console.error('Error initializing charts:', error)
  }

  // Listen for window resize
  window.addEventListener('resize', handleResize)
}

const retryInitCharts = (retryCount = 0) => {
  console.log(`Retrying chart initialization (attempt ${retryCount + 1})...`)
  
  if (retryCount >= 3) {
    console.error('Max retry attempts reached, chart initialization failed')
    return
  }
  
  setTimeout(() => {
    const allInitialized = cpuChartInstance && memoryChartInstance && diskChartInstance && loadChartInstance
    
    if (!allInitialized) {
      console.log('Some charts not initialized, retrying...')
      initCharts()
      retryInitCharts(retryCount + 1)
    } else {
      console.log('All charts successfully initialized')
    }
  }, 1000)
}



const updateCharts = () => {
  console.log('Updating charts...')
  console.log('System info:', systemInfo.value)
  console.log('CPU history:', cpuHistory.value)
  console.log('Load history:', loadHistory.value)
  
  updateCpuChart()
  updateMemoryChart()
  updateDiskChart()
  updateLoadChart()
}

const updateCpuChart = () => {
  console.log('Updating CPU chart...')
  if (!cpuChartInstance) {
    console.log('CPU chart instance not available')
    return
  }
  
  if (cpuHistory.value.length === 0) {
    console.log('No CPU history data')
    return
  }

  const theme = ensureChartTheme()
  const areaColor = new echarts.graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: `rgba(${theme.accentRgb}, 0.32)` },
    { offset: 1, color: `rgba(${theme.accentRgb}, 0.06)` }
  ])

  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: '{a}: {c}%'
    },
    xAxis: {
      type: 'category',
      data: cpuHistory.value.map(item => item.time),
      axisLabel: { fontSize: 11, color: theme.gray500 },
      axisLine: { lineStyle: { color: theme.surface3 } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { formatter: '{value}%', fontSize: 11, color: theme.gray500 },
      splitLine: { lineStyle: { color: theme.surface2 } }
    },
    series: [{
      name: 'CPU Usage',
      type: 'line',
      data: cpuHistory.value.map(item => item.value),
      smooth: true,
      areaStyle: {
        color: areaColor
      },
      lineStyle: { color: theme.primary, width: 2 },
      itemStyle: { color: theme.primary }
    }],
    grid: { left: '5%', right: '4%', bottom: '6%', top: '12%', containLabel: true }
  }

  console.log('Setting CPU chart option:', option)
  cpuChartInstance.setOption(option)
}

const updateMemoryChart = () => {
  console.log('Updating memory chart...')
  if (!memoryChartInstance) {
    console.log('Memory chart instance not available')
    return
  }
  
  if (!systemInfo.value?.memory) {
    console.log('No memory data')
    return
  }

  const theme = ensureChartTheme()
  const memory = systemInfo.value.memory
  const used = memory.used || 0
  const available = memory.available || 0

  const option = {
    tooltip: {
      trigger: 'item',
      formatter: '{a}: {b}<br/>{c} ({d}%)'
    },
    series: [{
      name: 'Memory',
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '55%'],
      data: [
        { 
          value: used, 
          name: `Used (${formatBytes(used)})`,
          itemStyle: { color: theme.error }
        },
        { 
          value: available, 
          name: `Available (${formatBytes(available)})`,
          itemStyle: { color: theme.success }
        }
      ],
      label: {
        show: true,
        formatter: '{b}: {d}%',
        fontSize: 12,
        color: theme.gray600
      },
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }]
  }

  console.log('Setting memory chart option:', option)
  memoryChartInstance.setOption(option)
}

const updateDiskChart = () => {
  console.log('Updating disk chart...')
  if (!diskChartInstance) {
    console.log('Disk chart instance not available')
    return
  }
  
  if (!systemInfo.value?.disk) {
    console.log('No disk data')
    return
  }

  const theme = ensureChartTheme()
  const disks = systemInfo.value.disk
  
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: function(params) {
        const data = params[0]
        const disk = disks[data.dataIndex]
        return `${disk.device}<br/>Used: ${formatBytes(disk.used)}<br/>Total: ${formatBytes(disk.total)}<br/>Usage: ${data.value.toFixed(1)}%`
      }
    },
    xAxis: {
      type: 'category',
      data: disks.map(disk => disk.device),
      axisLabel: { fontSize: 11, rotate: 35, color: theme.gray500 },
      axisLine: { lineStyle: { color: theme.surface3 } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { formatter: '{value}%', fontSize: 11, color: theme.gray500 },
      splitLine: { lineStyle: { color: theme.surface2 } }
    },
    series: [{
      name: 'Usage',
      type: 'bar',
      data: disks.map(disk => ({
        value: disk.usage_percent,
        itemStyle: {
          color: disk.usage_percent > 90 ? theme.error : 
                 disk.usage_percent > 70 ? theme.warning : theme.success
        }
      })),
      barWidth: '56%',
      itemStyle: { borderRadius: [6, 6, 0, 0] }
    }],
    grid: { left: '5%', right: '4%', bottom: '18%', top: '12%', containLabel: true }
  }

  console.log('Setting disk chart option:', option)
  diskChartInstance.setOption(option)
}

const updateLoadChart = () => {
  console.log('Updating load chart...')
  if (!loadChartInstance) {
    console.log('Load chart instance not available')
    return
  }
  
  if (loadHistory.value.length === 0) {
    console.log('No load history data')
    return
  }

  const theme = ensureChartTheme()
  const times = loadHistory.value.map(item => item.time)
  const load1 = loadHistory.value.map(item => item.load_1min)
  const load5 = loadHistory.value.map(item => item.load_5min)
  const load15 = loadHistory.value.map(item => item.load_15min)

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    legend: {
      data: ['1 minute', '5 minutes', '15 minutes'],
      bottom: 5,
      textStyle: { fontSize: 11, color: theme.gray500 }
    },
    xAxis: {
      type: 'category',
      data: times,
      axisLabel: { fontSize: 11, color: theme.gray500 },
      axisLine: { lineStyle: { color: theme.surface3 } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 11, color: theme.gray500 },
      splitLine: { lineStyle: { color: theme.surface2 } }
    },
    series: [
      {
        name: '1 minute',
        type: 'line',
        data: load1,
        smooth: true,
        lineStyle: { color: theme.primary, width: 2 },
        itemStyle: { color: theme.primary }
      },
      {
        name: '5 minutes',
        type: 'line',
        data: load5,
        smooth: true,
        lineStyle: { color: theme.success, width: 2 },
        itemStyle: { color: theme.success }
      },
      {
        name: '15 minutes',
        type: 'line',
        data: load15,
        smooth: true,
        lineStyle: { color: theme.warning, width: 2 },
        itemStyle: { color: theme.warning }
      }
    ],
    grid: { left: '5%', right: '4%', bottom: '18%', top: '12%', containLabel: true }
  }

  console.log('Setting load chart option:', option)
  loadChartInstance.setOption(option)
}

const handleResize = () => {
  cpuChartInstance?.resize()
  memoryChartInstance?.resize()
  diskChartInstance?.resize()
  loadChartInstance?.resize()
}

const clearCpuHistory = () => {
  cpuHistory.value = []
  if (cpuChartInstance) {
    cpuChartInstance.clear()
  }
}

const clearLoadHistory = () => {
  loadHistory.value = []
  if (loadChartInstance) {
    loadChartInstance.clear()
  }
}

// Utility functions
const formatBytes = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const getStatusClass = (percentage) => {
  if (percentage > 90) return 'critical'
  if (percentage > 70) return 'warning'
  return 'normal'
}

const getDiskStatusClass = () => {
  const usage = getTotalDiskUsage()
  return getStatusClass(usage)
}

const getLoadStatusClass = () => {
  const load = systemInfo.value?.load?.load_1min || 0
  const cores = systemInfo.value?.cpu?.logical_cores || 1
  const loadPercentage = (load / cores) * 100
  return getStatusClass(loadPercentage)
}

const getTotalDiskSpace = () => {
  if (!systemInfo.value?.disk) return 0
  return systemInfo.value.disk.reduce((total, disk) => total + disk.total, 0)
}

const getTotalDiskUsed = () => {
  if (!systemInfo.value?.disk) return 0
  return systemInfo.value.disk.reduce((total, disk) => total + disk.used, 0)
}

const getTotalDiskFree = () => {
  if (!systemInfo.value?.disk) return 0
  return systemInfo.value.disk.reduce((total, disk) => total + disk.free, 0)
}

const getTotalDiskUsage = () => {
  const total = getTotalDiskSpace()
  const used = getTotalDiskUsed()
  return total > 0 ? (used / total) * 100 : 0
}

const startRealTimeUpdate = () => {
  if (updateInterval) {
    clearInterval(updateInterval)
  }
  
  updateInterval = setInterval(() => {
    if (isRealtime.value) {
      fetchSystemInfo()
    }
  }, 5000) // Update every 5 seconds
}

const stopRealTimeUpdate = () => {
  if (updateInterval) {
    clearInterval(updateInterval)
    updateInterval = null
  }
}

// Lifecycle
onMounted(() => {
  console.log('Component mounted')
  
  // Ensure DOM is fully rendered before initializing charts
  nextTick(() => {
    console.log('DOM updated, initializing charts...')
    initCharts()
    
    // Check if all charts are successfully initialized, retry if not
    setTimeout(() => {
      const allInitialized = cpuChartInstance && memoryChartInstance && diskChartInstance && loadChartInstance
      if (!allInitialized) {
        console.log('Some charts failed to initialize, starting retry...')
        retryInitCharts()
      }
    }, 500)
    
    // Then fetch data
    setTimeout(() => {
      fetchSystemInfo()
      startRealTimeUpdate()
    }, 100)
  })
})

onUnmounted(() => {
  stopRealTimeUpdate()
  window.removeEventListener('resize', handleResize)
  
  // Destroy chart instances
  cpuChartInstance?.dispose()
  memoryChartInstance?.dispose()
  diskChartInstance?.dispose()
  loadChartInstance?.dispose()
})
</script>

<style scoped>
.system-performance {
  background: var(--surface-1);
  border-radius: var(--radius-lg);
  padding: var(--spacing-6);
  box-shadow: var(--shadow-sm);
  border: var(--border-width) solid var(--border-color-light);
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.performance-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-5);
  padding-bottom: var(--spacing-4);
  border-bottom: var(--border-width) solid var(--border-color-light);
  gap: var(--spacing-4);
  flex-shrink: 0;
}

.performance-header h3 {
  margin: 0;
  color: var(--gray-900);
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  font-family: var(--font-family-display);
}

.header-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
  flex-wrap: wrap;
  justify-content: flex-end;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: var(--spacing-2) var(--spacing-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.refresh-btn:hover {
  transform: translateY(-1px);
}

.refresh-btn.loading svg {
  animation: spin 1s linear infinite;
}



.update-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-xs);
  color: var(--gray-600);
  background: var(--surface-2);
  border: var(--border-width) solid var(--border-color-light);
  padding: var(--spacing-2) var(--spacing-3);
  border-radius: var(--radius-full);
}

.update-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--gray-300);
  transition: all var(--transition-base);
}

.update-dot.active {
  background: var(--success-500);
  box-shadow: 0 0 0 4px rgba(22, 163, 74, 0.15);
  animation: pulse 2s infinite;
}

.loading-state,
.error-state {
  text-align: center;
  padding: var(--spacing-8) var(--spacing-6);
  color: var(--gray-500);
  background: var(--surface-2);
  border-radius: var(--radius-lg);
  border: var(--border-width) solid var(--border-color-light);
}

.error-state {
  color: var(--error-600);
  background: var(--error-50);
  border-color: rgba(239, 68, 68, 0.2);
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-color-light);
  border-top: 3px solid var(--primary-500);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

.error-icon {
  font-size: 3rem;
  margin-bottom: 16px;
  color: var(--error-500);
}

.retry-btn {
  margin-top: var(--spacing-4);
}

/* Status Overview */
.status-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-5);
}

.status-card {
  background: linear-gradient(180deg, var(--surface-1) 0%, var(--surface-2) 100%);
  border: var(--border-width) solid var(--border-color-light);
  border-radius: var(--radius-lg);
  padding: var(--spacing-4);
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: var(--spacing-4);
  transition: transform var(--transition-base), box-shadow var(--transition-base), border-color var(--transition-base);
  position: relative;
  overflow: hidden;
}

.status-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--border-color-dark);
}

.status-card.normal {
  border-left: 4px solid var(--success-500);
}

.status-card.warning {
  border-left: 4px solid var(--warning-500);
  background: linear-gradient(180deg, var(--warning-50) 0%, var(--surface-1) 60%);
}

.status-card.critical {
  border-left: 4px solid var(--error-500);
  background: linear-gradient(180deg, var(--error-50) 0%, var(--surface-1) 60%);
}

.status-icon {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-md);
  border: var(--border-width) solid var(--border-color-light);
  background: var(--surface-1);
  box-shadow: var(--shadow-xs);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  flex-shrink: 0;
}

.status-card.cpu .status-icon {
  color: var(--primary-600);
}

.status-card.memory .status-icon {
  color: var(--success-600);
}

.status-card.disk .status-icon {
  color: var(--warning-600);
}

.status-card.load .status-icon {
  color: var(--primary-700);
}

.status-info {
  flex: 1;
}

.status-value {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--gray-900);
  margin-bottom: var(--spacing-1);
}

.status-label {
  font-size: var(--text-xs);
  color: var(--gray-500);
  font-weight: var(--font-medium);
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.status-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-end;
  text-align: right;
}

.detail-item {
  font-size: var(--text-xs);
  color: var(--gray-500);
  font-family: var(--font-family-mono);
}

/* Chart Container */
.charts-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: var(--spacing-5);
}

.chart-card {
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-color-light);
  border-radius: var(--radius-lg);
  padding: var(--spacing-4);
  box-shadow: var(--shadow-xs);
  display: flex;
  flex-direction: column;
  min-height: 320px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-3);
}

.chart-header h4 {
  margin: 0;
  color: var(--gray-800);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.chart-controls {
  display: flex;
  gap: 8px;
}

.clear-btn {
  padding: var(--spacing-1) var(--spacing-3);
  font-size: var(--text-xs);
}

.chart-container {
  width: 100%;
  flex: 1;
  min-height: 220px;
  height: 240px;
}

/* Animations */
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Responsive */
@media (max-width: 768px) {
  .system-performance {
    padding: var(--spacing-4);
  }

  .performance-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-4);
  }

  .status-overview {
    grid-template-columns: 1fr;
  }

  .charts-container {
    grid-template-columns: 1fr;
  }

  .chart-container {
    height: 240px;
  }
}

.performance-content {
  flex: 1;
  overflow-y: auto;
  padding-right: var(--spacing-2);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-5);
  min-height: 0;
}

.performance-content::-webkit-scrollbar {
  width: 4px;
}

.performance-content::-webkit-scrollbar-thumb {
  background: var(--gray-300);
  border-radius: 2px;
}

.performance-content::-webkit-scrollbar-track {
  background: transparent;
}
</style> 
