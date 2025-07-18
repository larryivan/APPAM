<template>
  <div class="workspace-layout">
    <!-- 左侧工具栏 -->
    <nav class="workspace-sidebar" :class="{ collapsed: sidebarCollapsed, mobile: isMobile, animating: sidebarAnimating }">
      <!-- 顶部控制栏 -->
      <div class="sidebar-controls">
        <router-link to="/projects" class="logo-link" title="Back to Project List" v-if="!sidebarCollapsed">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
            <polyline points="9 22 9 12 15 12 15 22"></polyline>
          </svg>
          <span class="logo-text">APPAM</span>
        </router-link>
        <button @click="toggleSidebar" class="sidebar-toggle-btn" :title="sidebarCollapsed ? 'Expand Sidebar' : 'Collapse Sidebar'">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline :points="sidebarCollapsed ? '9 18 15 12 9 6' : '15 18 9 12 15 6'"></polyline>
          </svg>
        </button>
      </div>
      
      <div class="sidebar-content" v-if="!sidebarCollapsed">
        <!-- 工作区板块 -->
        <div class="nav-section">
          <div class="section-header" @click="toggleSection('workspace')">
            <div class="section-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <rect x="8" y="8" width="8" height="8"></rect>
              </svg>
            </div>
            <span class="section-title">Workspace</span>
            <svg class="section-arrow" :class="{ rotated: !expandedSections.workspace }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
          <div class="section-content" v-show="expandedSections.workspace">
            <router-link :to="`/workspace/${$route.params.id}/overview`" class="nav-link">
              <div class="link-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="3"></circle>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1 1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09A1.65 1.65 0 0 0 15.4 4.6a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09A1.65 1.65 0 0 0 19.4 15z"></path>
                </svg>
              </div>
              <span class="link-text">Project Overview</span>
            </router-link>
            <router-link :to="`/workspace/${$route.params.id}/filemanager`" class="nav-link">
              <div class="link-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                </svg>
              </div>
              <span class="link-text">File Manager</span>
            </router-link>
          </div>
        </div>
        
        <!-- 预处理板块 -->
        <div class="nav-section">
          <div class="section-header" @click="toggleSection('preprocessing')">
            <div class="section-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                <polyline points="14 2 14 8 20 8"></polyline>
                <line x1="12" y1="18" x2="12" y2="12"></line>
                <line x1="9" y1="15" x2="15" y2="15"></line>
              </svg>
            </div>
            <span class="section-title">Preprocessing</span>
            <svg class="section-arrow" :class="{ rotated: !expandedSections.preprocessing }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
          <div class="section-content" v-show="expandedSections.preprocessing">
            <router-link v-for="tool in preprocessingTools" :key="tool" :to="getToolLink(tool)" class="nav-link">
              <div class="link-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="3"></circle>
                  <path d="M12 1v6m0 6v6m11-11h-6m-6 0H1"></path>
                </svg>
              </div>
              <span class="link-text">{{ tool }}</span>
            </router-link>
          </div>
        </div>
        
        <!-- 序列分析板块 -->
        <div class="nav-section">
          <div class="section-header" @click="toggleSection('analysis')">
            <div class="section-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="20" x2="18" y2="10"></line>
                <line x1="12" y1="20" x2="12" y2="4"></line>
                <line x1="6" y1="20" x2="6" y2="14"></line>
              </svg>
            </div>
            <span class="section-title">Sequence Analysis</span>
            <svg class="section-arrow" :class="{ rotated: !expandedSections.analysis }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
          <div class="section-content" v-show="expandedSections.analysis">
            <router-link v-for="tool in analysisTools" :key="tool" :to="getToolLink(tool)" class="nav-link">
              <div class="link-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                </svg>
              </div>
              <span class="link-text">{{ tool }}</span>
            </router-link>
          </div>
        </div>
        
        <!-- 组装与分箱板块 -->
        <div class="nav-section">
          <div class="section-header" @click="toggleSection('assembly')">
            <div class="section-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7"></rect>
                <rect x="14" y="3" width="7" height="7"></rect>
                <rect x="14" y="14" width="7" height="7"></rect>
                <rect x="3" y="14" width="7" height="7"></rect>
              </svg>
            </div>
            <span class="section-title">Assembly & Binning</span>
            <svg class="section-arrow" :class="{ rotated: !expandedSections.assembly }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
          <div class="section-content" v-show="expandedSections.assembly">
            <router-link v-for="tool in assemblyTools" :key="tool" :to="getToolLink(tool)" class="nav-link">
              <div class="link-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                  <polyline points="2 17 12 22 22 17"></polyline>
                  <polyline points="2 12 12 17 22 12"></polyline>
                </svg>
              </div>
              <span class="link-text">{{ tool }}</span>
            </router-link>
          </div>
        </div>
        
        <!-- MAG分析板块 -->
        <div class="nav-section">
          <div class="section-header" @click="toggleSection('mag')">
            <div class="section-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
                <line x1="12" y1="22.08" x2="12" y2="12"></line>
              </svg>
            </div>
            <span class="section-title">MAG Analysis</span>
            <svg class="section-arrow" :class="{ rotated: !expandedSections.mag }" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"></polyline>
            </svg>
          </div>
          <div class="section-content" v-show="expandedSections.mag">
            <router-link v-for="tool in magTools" :key="tool" :to="getToolLink(tool)" class="nav-link">
              <div class="link-icon">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"></circle>
                  <path d="M8 12h8"></path>
                  <path d="M12 8v8"></path>
                </svg>
              </div>
              <span class="link-text">{{ tool }}</span>
            </router-link>
          </div>
        </div>
      </div>
      
      <!-- 折叠状态的快捷图标 -->
      <div class="sidebar-shortcuts" v-if="sidebarCollapsed && !isMobile">
        <router-link :to="`/workspace/${$route.params.id}/overview`" class="shortcut-link" title="Project Overview">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1 1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09A1.65 1.65 0 0 0 15.4 4.6a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09A1.65 1.65 0 0 0 19.4 15z"></path>
          </svg>
        </router-link>
        <router-link :to="`/workspace/${$route.params.id}/filemanager`" class="shortcut-link" title="File Manager">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
          </svg>
        </router-link>
        <div class="shortcut-divider"></div>
        <button class="shortcut-link" title="Preprocessing" @click="quickToggle('preprocessing')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
          </svg>
        </button>
        <button class="shortcut-link" title="Sequence Analysis" @click="quickToggle('analysis')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="20" x2="18" y2="10"></line>
            <line x1="12" y1="20" x2="12" y2="4"></line>
            <line x1="6" y1="20" x2="6" y2="14"></line>
          </svg>
        </button>
        <button class="shortcut-link" title="Assembly & Binning" @click="quickToggle('assembly')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="7" height="7"></rect>
            <rect x="14" y="3" width="7" height="7"></rect>
            <rect x="14" y="14" width="7" height="7"></rect>
            <rect x="3" y="14" width="7" height="7"></rect>
          </svg>
        </button>
        <button class="shortcut-link" title="MAG Analysis" @click="quickToggle('mag')">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
          </svg>
        </button>
      </div>
      

    </nav>

    <!-- 主内容区 -->
    <main class="main-content" style = "margin-top: 0" @click="handleMainContentClick">
      <!-- 移动端菜单按钮 -->
      <button 
        v-if="isMobile && sidebarCollapsed" 
        @click="handleMenuButtonClick" 
        class="mobile-sidebar-trigger" 
        :class="{ 'with-notification': hasNotifications }"
      >
        <div class="trigger-icon">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <line x1="3" y1="6" x2="21" y2="6"></line>
          <line x1="3" y1="12" x2="21" y2="12"></line>
          <line x1="3" y1="18" x2="21" y2="18"></line>
        </svg>
        </div>
        <div class="trigger-hint">Tools</div>
        <div v-if="hasNotifications" class="notification-dot"></div>
      </button>
      
      <div class="content-wrapper">
        <router-view />
      </div>
    </main>
    
    <!-- 移动端遮罩层 -->
    <div v-if="!sidebarCollapsed && isMobile" class="mobile-overlay" @click="closeSidebar" @touchstart.passive="closeSidebar"></div>

    <!-- AI助手组件 - 新的浮动按钮设计 -->
    <Chatbot />

    <!-- 浮动系统监视器 -->
    <FloatingSystemMonitor />

    <!-- 浮动终端 -->
    <FloatingTerminal />

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import FloatingTerminal from '@/components/FloatingTerminal.vue'
import Chatbot from '@/components/Chatbot.vue'
import FloatingSystemMonitor from '@/components/FloatingSystemMonitor.vue'

const route = useRoute()
const router = useRouter()

// 状态管理
const sidebarCollapsed = ref(false)
const isMobile = ref(false)
const hasNotifications = ref(false)
const sidebarAnimating = ref(false)
const windowWidth = ref(window.innerWidth)

// 侧边栏展开状态
const expandedSections = ref({
  workspace: true,
  preprocessing: true,
  analysis: true,
  assembly: true,
  mag: true
})

// 工具分组
const preprocessingTools = ['FastQC', 'MultiQC', 'AdapterRemoval']
const analysisTools = ['bwa', 'PMDtools', 'bedtools', 'KrakenUniq', 'Krona']
const assemblyTools = ['MEGAHIT', 'SPAdes', 'QUAST', 'Bowtie2', 'Samtools', 'PyDamage', 'MetaBAT2', 'MaxBin2']
const magTools = ['CheckM', 'GTDB-Tk', 'PROKKA', 'RGI', 'antiSMASH']

const getToolLink = (tool) => {
  return `/workspace/${route.params.id}/tool/${tool.toLowerCase()}`
}

const toggleSidebar = () => {
  console.log('toggleSidebar called', { isMobile: isMobile.value, sidebarCollapsed: sidebarCollapsed.value })
  sidebarAnimating.value = true
  sidebarCollapsed.value = !sidebarCollapsed.value
  
  // 动画完成后重置状态
  setTimeout(() => {
    sidebarAnimating.value = false
  }, 300)
}

// 处理菜单按钮点击
const handleMenuButtonClick = (event) => {
  console.log('Menu button clicked!', {
    event: event,
    isMobile: isMobile.value,
    sidebarCollapsed: sidebarCollapsed.value,
    target: event.target
  })
  event.preventDefault()
  event.stopPropagation()
  toggleSidebar()
}

const closeSidebar = () => {
  if (isMobile.value) {
    sidebarAnimating.value = true
    sidebarCollapsed.value = true
    setTimeout(() => {
      sidebarAnimating.value = false
    }, 300)
  }
}

const handleMainContentClick = () => {
  if (isMobile.value && !sidebarCollapsed.value) {
    sidebarCollapsed.value = true
  }
}

const toggleSection = (section) => {
  expandedSections.value[section] = !expandedSections.value[section]
}

const quickToggle = (section) => {
  sidebarCollapsed.value = false
  setTimeout(() => {
    expandedSections.value[section] = true
    // 滚动到对应部分
    const element = document.querySelector(`.nav-section:has(.section-title:contains("${getSectionTitle(section)}"))`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, 300)
}

const getSectionTitle = (section) => {
  const titles = {
    preprocessing: 'Preprocessing',
    analysis: 'Sequence Analysis',
    assembly: 'Assembly & Binning',
    mag: 'MAG Analysis'
  }
  return titles[section] || ''
}



// 触摸手势支持
let touchStartX = 0
let touchStartY = 0
let isTouching = false

const handleTouchStart = (e) => {
  if (!isMobile.value) return
  touchStartX = e.touches[0].clientX
  touchStartY = e.touches[0].clientY
  isTouching = true
}

const handleTouchMove = (e) => {
  if (!isMobile.value || !isTouching) return
  
  const touchCurrentX = e.touches[0].clientX
  const touchCurrentY = e.touches[0].clientY
  const deltaX = touchCurrentX - touchStartX
  const deltaY = touchCurrentY - touchStartY
  
  // 水平滑动距离大于垂直滑动距离，且大于阈值
  if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
    // 从左边缘向右滑动，打开侧边栏
    if (touchStartX < 30 && deltaX > 0 && sidebarCollapsed.value) {
      e.preventDefault()
      toggleSidebar()
      isTouching = false
    }
    // 在侧边栏内向左滑动，关闭侧边栏
    else if (!sidebarCollapsed.value && deltaX < -50) {
      e.preventDefault()
      closeSidebar()
      isTouching = false
    }
  }
}

const handleTouchEnd = () => {
  isTouching = false
}

// 移动端检测函数
const detectMobile = () => {
  const userAgent = navigator.userAgent.toLowerCase()
  const mobileKeywords = ['mobile', 'iphone', 'android', 'blackberry', 'nokia', 'opera mini', 'windows mobile', 'windows phone', 'iemobile']
  const isMobileDevice = mobileKeywords.some(keyword => userAgent.includes(keyword))
  const isSmallScreen = window.innerWidth <= 768
  return isMobileDevice || isSmallScreen
}

// 窗口尺寸变化时自适应
const handleResize = () => {
  const wasMobile = isMobile.value
  windowWidth.value = window.innerWidth
  isMobile.value = detectMobile()
  
  console.log('检测设备状态:', {
    innerWidth: window.innerWidth,
    userAgent: navigator.userAgent.toLowerCase(),
    isMobile: isMobile.value,
    wasMobile: wasMobile
  })
  
  if (isMobile.value) {
    sidebarCollapsed.value = true
    // 设置随机通知状态用于演示
    hasNotifications.value = Math.random() > 0.7
  } else {
    // 桌面端自动展开侧边栏
    sidebarCollapsed.value = false
    hasNotifications.value = false
  }
}

onMounted(async () => {
  handleResize()
  window.addEventListener('resize', handleResize)
  
  // 添加触摸事件监听器
  if ('ontouchstart' in window) {
    document.addEventListener('touchstart', handleTouchStart, { passive: true })
    document.addEventListener('touchmove', handleTouchMove, { passive: false })
    document.addEventListener('touchend', handleTouchEnd, { passive: true })
  }
  
  // 从localStorage恢复展开状态
  const savedState = localStorage.getItem('sidebarExpandedSections')
  if (savedState) {
    try {
      expandedSections.value = JSON.parse(savedState)
    } catch (e) {
      console.error('Failed to parse saved state:', e)
    }
  }
  
  // 检查项目访问权限
  await checkProjectAccess()
})

// 检查项目访问权限
const checkProjectAccess = async () => {
  const projectId = route.params.id
  if (!projectId) return
  
  try {
    const response = await fetch(`/api/projects/${projectId}`)
    
    if (response.status === 401) {
      // 需要密码验证
      const data = await response.json()
      if (data.has_password) {
        // 显示密码验证弹窗
        showPasswordVerification(projectId)
      }
    } else if (response.status === 404) {
      // 项目不存在，跳转到项目列表
      router.push('/projects')
    }
  } catch (error) {
    console.error('Error checking project access:', error)
  }
}

// 显示密码验证弹窗
const showPasswordVerification = (projectId) => {
  // 创建密码验证弹窗
  const modal = document.createElement('div')
  modal.className = 'password-modal-overlay'
  modal.innerHTML = `
    <div class="password-modal-content">
      <div class="password-modal-header">
        <h3>🔒 Project Access Verification</h3>
        <button class="close-btn" onclick="this.closest('.password-modal-overlay').remove()">×</button>
      </div>
      <div class="password-form">
        <div class="form-group">
          <label for="project-password">Please enter the project access password:</label>
          <input 
            id="project-password" 
            type="password" 
            placeholder="Enter password..."
            class="password-input"
          >
          <div id="password-error" class="error-message" style="display: none;"></div>
        </div>
        <div class="form-actions">
          <button onclick="this.closest('.password-modal-overlay').remove(); window.location.href='/projects'" class="cancel-btn">Cancel</button>
          <button onclick="verifyProjectPassword('${projectId}')" class="submit-btn">Confirm</button>
        </div>
      </div>
    </div>
  `
  
  document.body.appendChild(modal)
  
  // 添加样式
  const style = document.createElement('style')
  style.textContent = `
    .password-modal-overlay {
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 9999;
    }
    .password-modal-content {
      background: white;
      border-radius: 12px;
      padding: 24px;
      max-width: 400px;
      width: 90%;
      box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    }
    .password-modal-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }
    .password-modal-header h3 {
      margin: 0;
      color: #374151;
    }
    .close-btn {
      background: none;
      border: none;
      font-size: 24px;
      cursor: pointer;
      color: #9ca3af;
    }
    .password-input {
      width: 100%;
      padding: 12px;
      border: 1px solid #d1d5db;
      border-radius: 8px;
      font-size: 14px;
      margin-top: 8px;
    }
    .form-actions {
      display: flex;
      gap: 12px;
      margin-top: 20px;
    }
    .cancel-btn, .submit-btn {
      flex: 1;
      padding: 12px;
      border-radius: 8px;
      border: none;
      cursor: pointer;
      font-size: 14px;
    }
    .cancel-btn {
      background: #f3f4f6;
      color: #374151;
    }
    .submit-btn {
      background: #3b82f6;
      color: white;
    }
    .error-message {
      color: #ef4444;
      font-size: 12px;
      margin-top: 8px;
    }
  `
  document.head.appendChild(style)
  
  // 聚焦到密码输入框
  setTimeout(() => {
    const input = modal.querySelector('#project-password')
    if (input) input.focus()
  }, 100)
}

// 验证项目密码
const verifyProjectPassword = async (projectId) => {
  const input = document.getElementById('project-password')
  const errorDiv = document.getElementById('password-error')
  const password = input.value.trim()
  
  if (!password) {
    errorDiv.textContent = 'Please enter password'
    errorDiv.style.display = 'block'
    return
  }
  
  try {
    const response = await fetch(`/api/projects/${projectId}/verify-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password })
    })
    
    const result = await response.json()
    
    if (response.ok && result.success) {
      // 密码验证成功，移除弹窗
      const modal = document.querySelector('.password-modal-overlay')
      if (modal) modal.remove()
    } else {
      // 密码验证失败
      errorDiv.textContent = result.message || 'Incorrect password, please try again'
      errorDiv.style.display = 'block'
      input.value = ''
      input.focus()
    }
  } catch (error) {
    console.error('Error verifying password:', error)
    errorDiv.textContent = 'Verification failed, please try again'
    errorDiv.style.display = 'block'
  }
}

// 将验证函数添加到全局作用域
window.verifyProjectPassword = verifyProjectPassword

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  
  // 清理触摸事件监听器
  if ('ontouchstart' in window) {
    document.removeEventListener('touchstart', handleTouchStart)
    document.removeEventListener('touchmove', handleTouchMove)
    document.removeEventListener('touchend', handleTouchEnd)
  }
  
  // 保存展开状态
  localStorage.setItem('sidebarExpandedSections', JSON.stringify(expandedSections.value))
})
</script>

<style scoped>
.workspace-layout {
  display: flex;
  height: 100%;
  width: 100%;
  background: var(--gray-50, #f8fafc);
  overflow: hidden;
  --sidebar-width: 280px;
  --sidebar-width-collapsed: 64px;
}

/* 现代化侧边栏 */
.workspace-sidebar {
  width: var(--sidebar-width);
  background: white;
  border-right: 1px solid #e5e7eb;
  transition: width 0.3s ease, transform 0.3s ease;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1);
}

.workspace-sidebar.collapsed {
  width: var(--sidebar-width-collapsed);
}

/* 顶部控制栏 */
.sidebar-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-3) var(--spacing-4);
  border-bottom: var(--border-width) solid var(--border-color-light);
  background: var(--gray-50);
  min-height: 56px;
  flex-shrink: 0;
}

.workspace-sidebar.collapsed .sidebar-controls {
  justify-content: center;
  padding: var(--spacing-4) var(--spacing-2);
}

.logo-link {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  text-decoration: none;
  color: var(--gray-700);
  font-weight: var(--font-semibold);
  transition: all var(--transition-base);
  font-size: var(--text-base);
}

.logo-link:hover {
  color: var(--primary-600);
  transform: translateX(2px);
}

.logo-text {
  font-weight: var(--font-bold);
  letter-spacing: -0.02em;
}

.sidebar-toggle-btn {
  width: 32px;
  height: 32px;
  background: var(--gray-50);
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-base);
  color: var(--gray-500);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-base);
}

.sidebar-toggle-btn:hover {
  background: var(--gray-100);
  color: var(--gray-700);
  border-color: var(--border-color-dark);
  transform: scale(1.05);
}

/* 内容区域 */
.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--spacing-2) var(--spacing-3);
}

.nav-section {
  margin-bottom: var(--spacing-2);
}

.section-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3) var(--spacing-4);
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: all var(--transition-base);
  user-select: none;
  background: var(--gray-50);
  margin-bottom: var(--spacing-1);
}

.section-header:hover {
  background: var(--gray-100);
  transform: translateX(2px);
}

.section-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--gray-500);
}

.section-title {
  flex: 1;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--gray-700);
}

.section-arrow {
  color: var(--gray-400);
  transition: transform var(--transition-base);
}

.section-arrow.rotated {
  transform: rotate(-90deg);
}

.section-content {
  margin-left: var(--spacing-3);
  padding-left: var(--spacing-5);
  border-left: var(--border-width-2) solid var(--border-color);
  margin-bottom: var(--spacing-2);
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  padding: var(--spacing-3) var(--spacing-4);
  margin: var(--spacing-1) 0;
  color: var(--gray-500);
  text-decoration: none;
  border-radius: var(--radius-base);
  transition: all var(--transition-base);
  font-size: var(--text-sm);
}

.nav-link:hover {
  background: var(--gray-100);
  color: var(--gray-700);
  transform: translateX(4px);
}

.nav-link.router-link-active {
  background: var(--gradient-primary);
  color: white;
  box-shadow: var(--shadow-md);
}

.nav-link.router-link-active .link-icon {
  color: white;
}

.link-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--gray-400);
}

.link-text {
  font-weight: var(--font-medium);
}

/* 折叠状态的快捷方式 */
.sidebar-shortcuts {
  padding: 16px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.shortcut-link {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  color: #64748b;
  text-decoration: none;
  transition: all 0.2s;
  background: transparent;
  border: none;
  cursor: pointer;
}

.shortcut-link:hover {
  background: #f1f5f9;
  color: #334155;
}

.shortcut-link.router-link-active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.shortcut-divider {
  width: 24px;
  height: 1px;
  background: #e2e8f0;
  margin: 4px 0;
}

/* 侧边栏底部 */
.sidebar-footer {
  padding: var(--spacing-3);
  border-top: var(--border-width) solid var(--border-color);
  background: var(--gray-50);
}

.ai-sidebar-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3);
  background: var(--gradient-primary);
  color: white;
  border: none;
  border-radius: var(--radius-base);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: all var(--transition-base);
}

.ai-sidebar-btn:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.workspace-sidebar.collapsed .ai-sidebar-btn span {
  display: none;
}

/* 主内容区 */
.main-content {
  flex: 1;
  background: var(--gray-50);
  overflow: hidden;
  position: relative;
}

.content-wrapper {
  height: 100%;
  overflow-y: auto;
  background: white;
  /* 优化滚动性能 */
  scroll-behavior: smooth;
  -webkit-overflow-scrolling: touch;
  transform: translateZ(0);
  will-change: scroll-position;
  /* 自定义滚动条样式 */
  scrollbar-width: thin;
  scrollbar-color: var(--gray-400) var(--gray-100);
}

.content-wrapper::-webkit-scrollbar {
  width: 8px;
}

.content-wrapper::-webkit-scrollbar-track {
  background: var(--gray-100);
  border-radius: var(--radius-md);
}

.content-wrapper::-webkit-scrollbar-thumb {
  background: var(--gray-400);
  border-radius: var(--radius-md);
  transition: background var(--transition-base);
}

.content-wrapper::-webkit-scrollbar-thumb:hover {
  background: var(--gray-500);
}

/* 自定义滚动条 */
.sidebar-content::-webkit-scrollbar {
  width: 6px;
}

.sidebar-content::-webkit-scrollbar-track {
  background: transparent;
}

.sidebar-content::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 3px;
}

.sidebar-content::-webkit-scrollbar-thumb:hover {
  background: #cbd5e1;
}

/* 移动端遮罩层 */
.mobile-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
  z-index: 150;
}

/* 精致的移动端侧边栏触发按钮 */
.mobile-sidebar-trigger {
  position: fixed;
  bottom: 20px;
  left: 20px;
  width: 56px;
  height: 56px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3), 0 2px 8px rgba(0, 0, 0, 0.1);
  color: white;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 1100;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  backdrop-filter: blur(10px);
  overflow: hidden;
}

.mobile-sidebar-trigger::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.2) 0%, transparent 50%);
  border-radius: 16px;
  transition: opacity 0.3s;
  opacity: 0;
}

.mobile-sidebar-trigger:hover::before {
  opacity: 1;
}

.mobile-sidebar-trigger:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4), 0 4px 12px rgba(0, 0, 0, 0.15);
}

.mobile-sidebar-trigger:active {
  transform: translateY(-1px) scale(1.02);
  transition-duration: 0.1s;
}

.trigger-icon {
  margin-bottom: 2px;
  transition: transform 0.3s;
}

.mobile-sidebar-trigger:hover .trigger-icon {
  transform: rotate(-5deg) scale(1.1);
}

.trigger-hint {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.5px;
  opacity: 0.9;
  text-transform: uppercase;
}

.notification-dot {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 12px;
  height: 12px;
  background: linear-gradient(135deg, #ff6b6b, #ff5722);
  border-radius: 50%;
  border: 2px solid white;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(255, 107, 107, 0.7);
  }
  70% {
    transform: scale(1);
    box-shadow: 0 0 0 8px rgba(255, 107, 107, 0);
  }
  100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(255, 107, 107, 0);
  }
}

.mobile-sidebar-trigger.with-notification {
  animation: glow 3s ease-in-out infinite alternate;
}

@keyframes glow {
  from {
    box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3), 0 2px 8px rgba(0, 0, 0, 0.1);
  }
  to {
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5), 0 4px 12px rgba(0, 0, 0, 0.15);
  }
}

/* AI助手组件样式由Chatbot.vue组件提供 */



/* 响应式设计 */
@media (max-width: 1200px) {
  .workspace-sidebar {
    width: 260px;
  }
}

@media (max-width: 1024px) {
  .workspace-sidebar {
    width: 240px;
  }
  
  .workspace-layout {
    overflow-x: hidden;
  }
}

@media (max-width: 768px) {
  .workspace-layout {
    position: relative;
    overflow: hidden;
  }
  
  .workspace-sidebar {
    position: fixed;
    left: 0;
    top: 0;
    height: 100vh;
    width: 320px;
    z-index: 200;
    transform: translateX(-100%);
    transition: transform 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    box-shadow: none;
    border-top-right-radius: 20px;
    border-bottom-right-radius: 20px;
    overflow: hidden;
  }
  
  .workspace-sidebar.mobile {
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.2);
  }
  
  .workspace-sidebar:not(.collapsed) {
    transform: translateX(0);
    box-shadow: 8px 0 40px rgba(0, 0, 0, 0.12), 4px 0 20px rgba(0, 0, 0, 0.08);
  }
  
  .workspace-sidebar.animating {
    will-change: transform;
  }
  
  /* 移动端侧边栏头部优化 */
  .workspace-sidebar.mobile .sidebar-controls {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-bottom: none;
    padding: 20px 20px 16px;
    border-radius: 20px 20px 0 0;
  }
  
  .workspace-sidebar.mobile .logo-link {
    color: white;
    font-size: 18px;
    font-weight: 700;
  }
  
  .workspace-sidebar.mobile .logo-text {
    background: linear-gradient(135deg, #ffffff, #e2e8f0);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  
  .workspace-sidebar.mobile .sidebar-toggle-btn {
    background: rgba(255, 255, 255, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.3);
    color: white;
  }
  
  .workspace-sidebar.mobile .sidebar-toggle-btn:hover {
    background: rgba(255, 255, 255, 0.3);
    border-color: rgba(255, 255, 255, 0.4);
    color: white;
  }
  
  /* 移动端导航链接优化 */
  .workspace-sidebar.mobile .nav-link {
    margin: 6px 12px;
    border-radius: 12px;
    font-size: 15px;
    padding: 12px 16px;
    backdrop-filter: blur(10px);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }
  
  .workspace-sidebar.mobile .nav-link:hover {
    background: rgba(102, 126, 234, 0.1);
    transform: translateX(8px) scale(1.02);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
  }
  
  .workspace-sidebar.mobile .nav-link.router-link-active {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3);
    transform: translateX(6px);
  }
  
  .workspace-sidebar.mobile .section-header {
    margin: 8px 12px 4px;
    border-radius: 12px;
    background: rgba(102, 126, 234, 0.05);
    border: 1px solid rgba(102, 126, 234, 0.1);
  }
  
  .workspace-sidebar.mobile .section-header:hover {
    background: rgba(102, 126, 234, 0.1);
    border-color: rgba(102, 126, 234, 0.2);
  }
  
  /* 移动端AI助手按钮 */
  .workspace-sidebar.mobile .ai-sidebar-btn {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 16px;
    padding: 16px;
    font-size: 16px;
    box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
    margin: 12px;
  }
  
  .main-content {
    width: 100vw;
    margin-left: 0;
    min-height: 100vh;
    position: relative;
  }
  
  .content-wrapper {
    border-radius: 0;
    padding: 0;
    height: 100vh;
    overflow-y: auto;
  }
  
  /* 增强遮罩层 */
  .mobile-overlay {
    background: rgba(0, 0, 0, 0.4);
    backdrop-filter: blur(4px);
    animation: fadeIn 0.3s ease-out;
  }
  
  @keyframes fadeIn {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
}

@media (max-width: 480px) {
  .workspace-sidebar {
    width: calc(100vw - 20px);
    max-width: 340px;
    border-radius: 0 20px 20px 0;
  }
  
  .mobile-sidebar-trigger {
    width: 48px;
    height: 48px;
    bottom: 16px;
    left: 16px;
    border-radius: 12px;
  }
  
  .trigger-hint {
    font-size: 9px;
  }
  
  .workspace-sidebar.mobile .sidebar-controls {
    padding: 16px;
  }
  
  .workspace-sidebar.mobile .logo-link {
    font-size: 16px;
  }
  
  .sidebar-content {
    padding: 8px;
  }
  
  .workspace-sidebar.mobile .section-header {
    margin: 6px 8px 2px;
    padding: 10px 12px;
    font-size: 14px;
  }
  
  .workspace-sidebar.mobile .nav-link {
    margin: 4px 8px;
    padding: 10px 12px;
    font-size: 14px;
  }
  
  .workspace-sidebar.mobile .ai-sidebar-btn {
    margin: 8px;
    padding: 14px;
    font-size: 15px;
  }
  
  /* 超小屏优化 */
  .link-text {
    font-size: 14px;
  }
  
  .section-title {
    font-size: 12px;
  }
}

/* 横屏模式优化 */
@media (max-height: 600px) and (orientation: landscape) {
  .workspace-sidebar.mobile .sidebar-controls {
    padding: 12px 16px 8px;
  }
  
  .workspace-sidebar.mobile .logo-link {
    font-size: 15px;
  }
  
  .workspace-sidebar.mobile .section-header {
    padding: 8px 12px;
  }
  
  .workspace-sidebar.mobile .nav-link {
    padding: 8px 12px;
    font-size: 13px;
  }
  
  .mobile-sidebar-trigger {
    width: 48px;
    height: 48px;
    bottom: 12px;
    left: 12px;
  }
  
  .trigger-hint {
    font-size: 8px;
  }
}



/* 触摸设备优化 */
@media (hover: none) and (pointer: coarse) {
  .workspace-sidebar.mobile .nav-link:hover {
    transform: translateX(4px);
  }
  
  .workspace-sidebar.mobile .section-header:hover {
    transform: translateX(2px);
  }
  
  .mobile-sidebar-trigger:hover {
    transform: none;
  }
  
  .mobile-sidebar-trigger:active {
    transform: scale(0.95);
  }
}
</style>