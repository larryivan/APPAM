<template>
  <div class="topbar">
    <div class="topbar-content">
      <div class="logo-section">
        <img src="/assets/logo.svg" alt="APPAM Logo" />
        <h1 class="logo-title">APPAM</h1>
      </div>
      
      <!-- Desktop Navigation -->
      <nav class="nav-section desktop-nav">
        <router-link to="/" class="nav-item" :class="{ active: isActive('/') }">
          <span>Index</span>
        </router-link>
        <router-link to="/documentation" class="nav-item" :class="{ active: isActive('/documentation') }">
          <span>Documentation</span>
        </router-link>
        <router-link to="/projects" class="nav-item" :class="{ active: isActive('/projects') }">
          <span>Projects</span>
        </router-link>
      </nav>

      <!-- Mobile hamburger menu button -->
      <button 
        class="mobile-menu-btn"
        @click="toggleMobileMenu"
        :class="{ active: showMobileMenu }"
        :aria-expanded="showMobileMenu"
        :aria-controls="'mobile-nav'"
        aria-label="Toggle navigation menu"
        type="button"
      >
        <span class="hamburger-line" aria-hidden="true"></span>
        <span class="hamburger-line" aria-hidden="true"></span>
        <span class="hamburger-line" aria-hidden="true"></span>
      </button>
    </div>

    <!-- Mobile navigation menu -->
    <nav 
      id="mobile-nav"
      class="mobile-nav" 
      :class="{ show: showMobileMenu }"
      role="navigation"
      aria-label="Mobile navigation"
      :aria-hidden="!showMobileMenu"
    >
      <div class="mobile-nav-content">
        <router-link 
          to="/" 
          class="mobile-nav-item" 
          :class="{ active: isActive('/') }"
          @click="closeMobileMenu"
          role="menuitem"
        >
          <span>Index</span>
        </router-link>
        <router-link 
          to="/documentation" 
          class="mobile-nav-item" 
          :class="{ active: isActive('/documentation') }"
          @click="closeMobileMenu"
          role="menuitem"
        >
          <span>Documentation</span>
        </router-link>
        <router-link 
          to="/projects" 
          class="mobile-nav-item" 
          :class="{ active: isActive('/projects') }"
          @click="closeMobileMenu"
          role="menuitem"
        >
          <span>Projects</span>
        </router-link>
      </div>
    </nav>

    <!-- Mobile overlay -->
    <div 
      class="mobile-overlay" 
      :class="{ show: showMobileMenu }"
      @click="closeMobileMenu"
    ></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();
const showMobileMenu = ref(false);

const isActive = (path) => {
  if (path === '/') {
    return route.path === '/';
  }
  return route.path.startsWith(path);
};

const toggleMobileMenu = () => {
  showMobileMenu.value = !showMobileMenu.value;
  
  // Prevent background scrolling
  if (showMobileMenu.value) {
    document.body.style.overflow = 'hidden';
    document.documentElement.style.overflow = 'hidden';
    // Prevent elastic scrolling on iOS Safari
    document.body.style.position = 'fixed';
    document.body.style.width = '100%';
  } else {
    document.body.style.overflow = '';
    document.documentElement.style.overflow = '';
    document.body.style.position = '';
    document.body.style.width = '';
  }
};

const closeMobileMenu = () => {
  showMobileMenu.value = false;
  document.body.style.overflow = '';
  document.documentElement.style.overflow = '';
  document.body.style.position = '';
  document.body.style.width = '';
};

// Listen to window resize changes, automatically close mobile menu when on desktop
const handleResize = () => {
  if (window.innerWidth >= 768 && showMobileMenu.value) {
    closeMobileMenu();
  }
};

// Listen to keyboard events
const handleKeyDown = (e) => {
  if (e.key === 'Escape' && showMobileMenu.value) {
    closeMobileMenu();
  }
};

// Listen to route changes, automatically close mobile menu
const handleRouteChange = () => {
  if (showMobileMenu.value) {
    closeMobileMenu();
  }
};

onMounted(() => {
  window.addEventListener('resize', handleResize);
  document.addEventListener('keydown', handleKeyDown);
  // Listen to route changes
  route.fullPath; // Trigger reactivity
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  document.removeEventListener('keydown', handleKeyDown);
  document.body.style.overflow = '';
  document.documentElement.style.overflow = '';
  document.body.style.position = '';
  document.body.style.width = '';
});

// Listen to route changes, automatically close mobile menu
watch(() => route.fullPath, handleRouteChange);
</script>

<style scoped>
.topbar {
  background: white;
  border-bottom: var(--border-width) solid var(--border-color);
  padding: 0 var(--spacing-4);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: var(--z-fixed); /* 确保topbar在最上层 */
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(8px);
}

.topbar-content {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: var(--header-height);
}

.logo-section {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  z-index: 1031; /* 确保在移动菜单之上 */
  position: relative;
}

.logo-section img {
  width: 32px;
  height: 32px;
  transition: transform var(--transition-base);
  flex-shrink: 0;
}

.logo-section img:hover {
  transform: scale(1.05);
}

.logo-title {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--gray-800);
  margin: 0;
  letter-spacing: -0.02em;
  white-space: nowrap;
}

/* 桌面端导航 */
.desktop-nav {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.nav-item {
  display: flex;
  align-items: center;
  padding: var(--spacing-2) var(--spacing-4);
  text-decoration: none;
  color: var(--gray-600);
  font-weight: var(--font-medium);
  font-size: var(--text-sm);
  border-radius: var(--radius-base);
  transition: all var(--transition-base);
  position: relative;
  white-space: nowrap;
}

.nav-item:hover {
  background: var(--gray-100);
  color: var(--gray-800);
  transform: translateY(-1px);
}

.nav-item.active {
  background: var(--primary-500);
  color: white;
  box-shadow: var(--shadow-sm);
}

.nav-item.active::before {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 4px;
  background: white;
  border-radius: var(--radius-full);
}

.nav-item span {
  font-size: var(--text-sm);
}

/* 移动端汉堡菜单按钮 */
.mobile-menu-btn {
  display: none;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  width: 44px;
  height: 44px;
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: var(--radius-base);
  transition: all var(--transition-base);
  z-index: 1031; /* 确保在移动菜单之上 */
  position: relative;
  flex-shrink: 0;
  -webkit-tap-highlight-color: transparent; /* 移除点击高亮 */
}

.mobile-menu-btn:hover {
  background: var(--gray-100);
}

.mobile-menu-btn:active {
  background: var(--gray-200);
  transform: scale(0.95);
}

.hamburger-line {
  width: 22px;
  height: 2px;
  background: var(--gray-700);
  border-radius: 1px;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  transform-origin: center;
  display: block;
  position: relative;
}

.hamburger-line:not(:last-child) {
  margin-bottom: 4px;
}

/* 汉堡菜单动画 */
.mobile-menu-btn.active .hamburger-line:nth-child(1) {
  transform: translateY(6px) rotate(45deg);
}

.mobile-menu-btn.active .hamburger-line:nth-child(2) {
  opacity: 0;
  transform: scaleX(0);
}

.mobile-menu-btn.active .hamburger-line:nth-child(3) {
  transform: translateY(-6px) rotate(-45deg);
}

/* 移动端导航菜单 */
.mobile-nav {
  position: fixed;
  top: var(--header-height);
  left: 0;
  right: 0;
  background: white;
  border-bottom: var(--border-width) solid var(--border-color);
  box-shadow: var(--shadow-lg);
  transform: translateY(-100%);
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), visibility 0.3s ease;
  z-index: 1025; /* 低于topbar的z-index (1030) */
  display: none;
  max-height: calc(100vh - var(--header-height));
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  visibility: hidden; /* 初始状态隐藏 */
  pointer-events: none; /* 初始状态不响应点击 */
}

.mobile-nav.show {
  transform: translateY(0);
  visibility: visible; /* 显示时才可见 */
  pointer-events: auto; /* 显示时才响应点击 */
}

.mobile-nav-content {
  padding: var(--spacing-4) var(--spacing-4) var(--spacing-6);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-2);
  min-height: 100%;
}

.mobile-nav-item {
  display: flex;
  align-items: center;
  padding: var(--spacing-4) var(--spacing-4);
  text-decoration: none;
  color: var(--gray-700);
  font-weight: var(--font-medium);
  font-size: var(--text-lg);
  border-radius: var(--radius-lg);
  transition: all var(--transition-base);
  border: 1px solid transparent;
  min-height: 48px;
  position: relative;
  touch-action: manipulation; /* 改善触摸体验 */
}

.mobile-nav-item:hover {
  background: var(--gray-50);
  color: var(--gray-900);
  border-color: var(--gray-200);
  transform: translateX(4px);
}

.mobile-nav-item.active {
  background: var(--primary-500);
  color: white;
  border-color: var(--primary-600);
  font-weight: var(--font-semibold);
  box-shadow: var(--shadow-md);
}

.mobile-nav-item.active::before {
  content: '';
  position: absolute;
  left: var(--spacing-2);
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 24px;
  background: white;
  border-radius: var(--radius-full);
}

/* 移动端遮罩层 */
.mobile-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
  opacity: 0;
  visibility: hidden;
  transition: all 0.3s ease;
  display: none;
}

.mobile-overlay.show {
  opacity: 1;
  visibility: visible;
}

/* 移动端安全区域支持 */
@supports (padding: max(0px)) {
  @media (max-width: 767px) {
    .topbar {
      padding-left: max(var(--spacing-4), env(safe-area-inset-left));
      padding-right: max(var(--spacing-4), env(safe-area-inset-right));
    }
    
    .mobile-nav {
      padding-left: env(safe-area-inset-left);
      padding-right: env(safe-area-inset-right);
    }
    
    .mobile-nav-content {
      padding-bottom: max(var(--spacing-6), env(safe-area-inset-bottom));
    }
  }
  
  @media (max-width: 479px) {
    .topbar {
      padding-left: max(var(--spacing-3), env(safe-area-inset-left));
      padding-right: max(var(--spacing-3), env(safe-area-inset-right));
    }
  }
}

/* 触摸设备优化 */
@media (hover: none) and (pointer: coarse) {
  .mobile-menu-btn:hover {
    background: transparent;
  }
  
  .mobile-menu-btn:active {
    background: var(--gray-200);
  }
  
  .mobile-nav-item:hover {
    background: transparent;
    color: var(--gray-700);
    border-color: transparent;
    transform: none;
  }
  
  .mobile-nav-item:active {
    background: var(--gray-100);
    transform: scale(0.98);
  }
  
  .mobile-nav-item.active:hover {
    background: var(--primary-500);
    color: white;
    border-color: var(--primary-600);
  }
}

/* 高对比度模式支持 */
@media (prefers-contrast: high) {
  .mobile-menu-btn {
    border: 1px solid var(--gray-400);
  }
  
  .mobile-nav-item {
    border: 1px solid var(--gray-300);
  }
  
  .mobile-nav-item.active {
    border: 2px solid var(--primary-700);
  }
}

/* 减少动画模式 */
@media (prefers-reduced-motion: reduce) {
  .mobile-nav,
  .mobile-overlay,
  .mobile-menu-btn,
  .hamburger-line,
  .mobile-nav-item {
    transition: none;
  }
  
  .mobile-nav-item:hover {
    transform: none;
  }
}

/* 响应式断点 */

/* 平板端 (768px - 1023px) */
@media (max-width: 1023px) {
  .topbar {
    padding: 0 var(--spacing-4);
  }
  
  .topbar-content {
    padding: 0 var(--spacing-2);
  }
  
  .nav-item {
    padding: var(--spacing-2) var(--spacing-3);
    font-size: var(--text-xs);
  }
  
  .logo-title {
    font-size: var(--text-lg);
  }
}

/* 移动端 (最大 767px) */
@media (max-width: 767px) {
  .topbar {
    padding: 0 var(--spacing-4);
    height: var(--header-height);
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: var(--z-fixed);
  }
  
  .topbar-content {
    padding: 0;
    height: 100%;
    max-width: none;
    position: relative;
  }
  
  .logo-section {
    gap: var(--spacing-2);
    flex: 1;
    min-width: 0; /* 防止内容溢出 */
  }
  
  .logo-section img {
    width: 28px;
    height: 28px;
    flex-shrink: 0;
  }
  
  .logo-title {
    font-size: var(--text-lg);
    font-weight: var(--font-semibold);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  /* 隐藏桌面导航，显示移动菜单按钮 */
  .desktop-nav {
    display: none;
  }
  
  .mobile-menu-btn {
    display: flex;
    flex-shrink: 0;
    position: relative;
    z-index: 1031; /* 确保按钮在菜单上方 */
  }
  
  .mobile-nav {
    display: block;
    position: fixed;
    top: var(--header-height);
    left: 0;
    right: 0;
    background: white;
    z-index: 1025; /* 低于topbar */
    transform: translateY(-100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), visibility 0.3s ease;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
    max-height: calc(100vh - var(--header-height));
    box-shadow: var(--shadow-lg);
    visibility: hidden;
    pointer-events: none;
  }
  
  .mobile-nav.show {
    transform: translateY(0);
    visibility: visible;
    pointer-events: auto;
  }
  
  .mobile-overlay {
    display: block;
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 1020; /* 低于topbar但高于其他内容 */
    opacity: 0;
    visibility: hidden;
    transition: all 0.3s ease;
    pointer-events: none;
  }
  
  .mobile-overlay.show {
    opacity: 1;
    visibility: visible;
    pointer-events: auto;
  }
}

/* 小屏手机 (最大 479px) */
@media (max-width: 479px) {
  .topbar {
    padding: 0 var(--spacing-3);
  }
  
  .logo-section {
    gap: var(--spacing-2);
    min-width: 0;
  }
  
  .logo-section img {
    width: 24px;
    height: 24px;
  }
  
  .logo-title {
    font-size: var(--text-base);
    font-weight: var(--font-medium);
  }
  
  .mobile-menu-btn {
    width: 40px;
    height: 40px;
    padding: 6px;
  }
  
  .hamburger-line {
    width: 18px;
    height: 2px;
  }
  
  .hamburger-line:not(:last-child) {
    margin-bottom: 3px;
  }
  
  .mobile-nav-content {
    padding: var(--spacing-3) var(--spacing-3) var(--spacing-5);
  }
  
  .mobile-nav-item {
    padding: var(--spacing-3) var(--spacing-4);
    font-size: var(--text-base);
    min-height: 44px;
  }
  
  /* 小屏汉堡菜单动画调整 */
  .mobile-menu-btn.active .hamburger-line:nth-child(1) {
    transform: translateY(5px) rotate(45deg);
  }
  
  .mobile-menu-btn.active .hamburger-line:nth-child(3) {
    transform: translateY(-5px) rotate(-45deg);
  }
}

/* 超大屏幕优化 (1200px+) */
@media (min-width: 1200px) {
  .topbar-content {
    padding: 0 var(--spacing-6);
  }
  
  .nav-item {
    padding: var(--spacing-3) var(--spacing-5);
  }
}

/* 深色模式支持 */
@media (prefers-color-scheme: dark) {
  .topbar {
    background: var(--gray-900);
    border-bottom-color: var(--gray-700);
  }
  
  .logo-title {
    color: var(--gray-100);
  }
  
  .nav-item {
    color: var(--gray-300);
  }
  
  .nav-item:hover {
    background: var(--gray-800);
    color: var(--gray-100);
  }
  
  .mobile-menu-btn:hover {
    background: var(--gray-800);
  }
  
  .hamburger-line {
    background: var(--gray-300);
  }
  
  .mobile-nav {
    background: var(--gray-900);
    border-bottom-color: var(--gray-700);
  }
  
  .mobile-nav-item {
    color: var(--gray-300);
  }
  
  .mobile-nav-item:hover {
    background: var(--gray-800);
    color: var(--gray-100);
    border-color: var(--gray-600);
  }
  
  .mobile-nav-item.active {
    background: var(--primary-900);
    color: var(--primary-200);
    border-color: var(--primary-700);
  }
}
</style>