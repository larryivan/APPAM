<template>
  <div class="system-performance">
    <div class="performance-header">
      <h3>System Performance Monitor</h3>
      <div class="header-controls">
        <button @click="refreshData" class="refresh-btn" :class="{ loading: loading }">
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
      <button @click="refreshData" class="retry-btn">Retry</button>
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
              <button @click="clearCpuHistory" class="clear-btn">Clear History</button>
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
              <button @click="clearLoadHistory" class="clear-btn">Clear History</button>
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

  const option = {
    tooltip: {
      trigger: 'axis',
      formatter: '{a}: {c}%'
    },
    xAxis: {
      type: 'category',
      data: cpuHistory.value.map(item => item.time),
      axisLabel: { fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { formatter: '{value}%', fontSize: 12 }
    },
    series: [{
      name: 'CPU Usage',
      type: 'line',
      data: cpuHistory.value.map(item => item.value),
      smooth: true,
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
          { offset: 1, color: 'rgba(59, 130, 246, 0.1)' }
        ])
      },
      lineStyle: { color: '#3B82F6', width: 2 },
      itemStyle: { color: '#3B82F6' }
    }],
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true }
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
          itemStyle: { color: '#EF4444' }
        },
        { 
          value: available, 
          name: `Available (${formatBytes(available)})`,
          itemStyle: { color: '#10B981' }
        }
      ],
      label: {
        show: true,
        formatter: '{b}: {d}%',
        fontSize: 12
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
      axisLabel: { fontSize: 12, rotate: 45 }
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { formatter: '{value}%', fontSize: 12 }
    },
    series: [{
      name: 'Usage',
      type: 'bar',
      data: disks.map(disk => ({
        value: disk.usage_percent,
        itemStyle: {
          color: disk.usage_percent > 90 ? '#EF4444' : 
                 disk.usage_percent > 70 ? '#F59E0B' : '#10B981'
        }
      })),
      barWidth: '60%'
    }],
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true }
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
      textStyle: { fontSize: 12 }
    },
    xAxis: {
      type: 'category',
      data: times,
      axisLabel: { fontSize: 12 }
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 12 }
    },
    series: [
      {
        name: '1 minute',
        type: 'line',
        data: load1,
        smooth: true,
        lineStyle: { color: '#3B82F6', width: 2 },
        itemStyle: { color: '#3B82F6' }
      },
      {
        name: '5 minutes',
        type: 'line',
        data: load5,
        smooth: true,
        lineStyle: { color: '#10B981', width: 2 },
        itemStyle: { color: '#10B981' }
      },
      {
        name: '15 minutes',
        type: 'line',
        data: load15,
        smooth: true,
        lineStyle: { color: '#F59E0B', width: 2 },
        itemStyle: { color: '#F59E0B' }
      }
    ],
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true }
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
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e2e8f0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.performance-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}

.performance-header h3 {
  margin: 0;
  color: #1f2937;
  font-size: 1.25rem;
  font-weight: 600;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f3f4f6;
  border: none;
  border-radius: 8px;
  color: #374151;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.refresh-btn:hover {
  background: #e5e7eb;
}

.refresh-btn.loading svg {
  animation: spin 1s linear infinite;
}



.update-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #6b7280;
}

.update-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d1d5db;
  transition: all 0.3s ease;
}

.update-dot.active {
  background: #10b981;
  animation: pulse 2s infinite;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 64px 24px;
  color: #6b7280;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top: 3px solid #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

.error-icon {
  font-size: 3rem;
  margin-bottom: 16px;
}

.retry-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  margin-top: 16px;
}

/* Status Overview */
.status-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.status-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  transition: all 0.3s ease;
}

.status-card.normal {
  border-left: 4px solid #10b981;
}

.status-card.warning {
  border-left: 4px solid #f59e0b;
  background: #fffbeb;
}

.status-card.critical {
  border-left: 4px solid #ef4444;
  background: #fef2f2;
}

.status-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.status-info {
  flex: 1;
}

.status-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 4px;
}

.status-label {
  font-size: 14px;
  color: #6b7280;
  font-weight: 500;
}

.status-details {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-end;
}

.detail-item {
  font-size: 12px;
  color: #9ca3af;
}

/* Chart Container */
.charts-container {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 16px;
}

.chart-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 16px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.chart-header h4 {
  margin: 0;
  color: #374151;
  font-size: 1rem;
  font-weight: 600;
}

.chart-controls {
  display: flex;
  gap: 8px;
}

.clear-btn {
  background: #e5e7eb;
  color: #6b7280;
  border: none;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.clear-btn:hover {
  background: #d1d5db;
}

.chart-container {
  width: 100%;
  height: 250px;
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
    padding: 16px;
  }

  .performance-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
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
  padding-right: 8px;
  min-height: 0;
}

.performance-content::-webkit-scrollbar {
  width: 4px;
}

.performance-content::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 2px;
}

.performance-content::-webkit-scrollbar-track {
  background: transparent;
}
</style> 