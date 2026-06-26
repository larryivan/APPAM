<template>
  <div class="topbar">
    <div class="topbar-content">
      <router-link to="/" class="logo-section">
        <img src="/assets/logo.svg" alt="APPAM Logo" />
        <h1 class="logo-title">APPAM</h1>
      </router-link>
      
      <!-- Desktop Navigation -->
      <nav class="nav-section desktop-nav">
        <router-link to="/" class="nav-item" :class="{ active: isActive('/') }">
          <span>Index</span>
        </router-link>
        <router-link to="/documentation" class="nav-item" :class="{ active: isActive('/documentation') }">
          <span>Documentation</span>
        </router-link>
        <router-link v-if="authState.user" to="/projects" class="nav-item" :class="{ active: isActive('/projects') }">
          <span>Projects</span>
        </router-link>
        <router-link v-if="authState.user" to="/settings" class="nav-item" :class="{ active: isActive('/settings') }">
          <span>Settings</span>
        </router-link>
        <router-link v-if="authState.user?.role === 'admin'" to="/admin/users" class="nav-item" :class="{ active: isActive('/admin/users') }">
          <span>Admin</span>
        </router-link>
        <router-link v-if="authState.user?.role === 'admin'" to="/admin/worker" class="nav-item" :class="{ active: isActive('/admin/worker') }">
          <span>Worker</span>
        </router-link>
      </nav>

      <div class="auth-actions desktop-auth">
        <template v-if="authState.user">
          <div class="user-badge-wrap">
            <span class="user-badge">{{ authDisplayName }}</span>
            <span class="role-badge">{{ authRoleLabel }}</span>
          </div>
          <button class="auth-btn secondary" type="button" @click="handleLogout">Logout</button>
        </template>
        <router-link v-else to="/login" class="auth-btn primary">Login</router-link>
      </div>

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
          v-if="authState.user"
          to="/projects" 
          class="mobile-nav-item" 
          :class="{ active: isActive('/projects') }"
          @click="closeMobileMenu"
          role="menuitem"
        >
          <span>Projects</span>
        </router-link>
        <router-link
          v-if="authState.user"
          to="/settings"
          class="mobile-nav-item"
          :class="{ active: isActive('/settings') }"
          @click="closeMobileMenu"
          role="menuitem"
        >
          <span>Settings</span>
        </router-link>
        <router-link
          v-if="authState.user?.role === 'admin'"
          to="/admin/users"
          class="mobile-nav-item"
          :class="{ active: isActive('/admin/users') }"
          @click="closeMobileMenu"
          role="menuitem"
        >
          <span>Admin</span>
        </router-link>
        <router-link
          v-if="authState.user?.role === 'admin'"
          to="/admin/worker"
          class="mobile-nav-item"
          :class="{ active: isActive('/admin/worker') }"
          @click="closeMobileMenu"
          role="menuitem"
        >
          <span>Worker</span>
        </router-link>
        <router-link
          v-if="!authState.user"
          to="/login"
          class="mobile-nav-item"
          :class="{ active: isActive('/login') }"
          @click="closeMobileMenu"
          role="menuitem"
        >
          <span>Login</span>
        </router-link>
        <button
          v-else
          class="mobile-nav-item mobile-action-btn"
          type="button"
          @click="handleLogout"
          role="menuitem"
        >
          <span>Logout</span>
        </button>
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
import { computed, ref, onMounted, onUnmounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { authState, logout } from '../lib/auth'

const route = useRoute();
const router = useRouter();
const showMobileMenu = ref(false);
const authDisplayName = computed(() => authState.user?.display_name || authState.user?.username || 'User')
const authRoleLabel = computed(() => authState.user?.role === 'admin' ? 'Admin' : 'User')

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

const handleLogout = async () => {
  await logout()
  closeMobileMenu()
  router.replace('/login')
}

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
  background: var(--surface-1);
  border-bottom: var(--border-width) solid var(--border-color-light);
  padding: 0 var(--spacing-4);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: var(--z-fixed); /* 确保topbar在最上层 */
}

.topbar-content {
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--spacing-4);
  height: var(--header-height);
}

.topbar-content > * {
  min-width: 0;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  z-index: 1031; /* 确保在移动菜单之上 */
  position: relative;
  flex: 0 0 auto;
  min-width: 0;
  text-decoration: none;
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
  letter-spacing: -0.03em;
  font-family: var(--font-family-display);
  white-space: nowrap;
}

/* 桌面端导航 */
.desktop-nav {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  width: 100%;
  justify-content: center;
  overflow: hidden;
}

.desktop-auth {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
  justify-content: flex-end;
  max-width: min(36vw, 320px);
}

.auth-actions {
  margin-left: 0;
}

.user-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.45rem 0.8rem;
  border-radius: var(--radius-full);
  background: rgba(var(--accent-rgb), 0.12);
  color: var(--primary-700);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-badge-wrap {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  min-width: 0;
  max-width: 100%;
}

.role-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.35rem 0.65rem;
  border-radius: var(--radius-full);
  background: var(--surface-2);
  color: var(--gray-600);
  font-size: 0.78rem;
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.auth-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 88px;
  padding: 0.65rem 0.95rem;
  border-radius: var(--radius-base);
  border: 0;
  text-decoration: none;
  font: inherit;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  cursor: pointer;
  transition: all var(--transition-base);
}

.auth-btn.primary {
  background: var(--primary-600);
  color: white;
}

.auth-btn.primary:hover {
  background: var(--primary-700);
}

.auth-btn.secondary {
  background: var(--surface-1);
  color: var(--gray-700);
  border: var(--border-width) solid var(--border-color);
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
  background: var(--surface-2);
  color: var(--gray-900);
}

.nav-item.active {
  background: rgba(var(--accent-rgb), 0.14);
  color: var(--primary-700);
  box-shadow: inset 0 0 0 1px rgba(var(--accent-rgb), 0.2);
}

.nav-item.active::before {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%);
  width: 4px;
  height: 4px;
  background: var(--primary-600);
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
  background: var(--surface-1);
  border-bottom: var(--border-width) solid var(--border-color);
  box-shadow: var(--shadow-md);
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

.mobile-action-btn {
  width: 100%;
  background: transparent;
  border: 0;
  font: inherit;
  text-align: left;
}

.mobile-nav-item:hover {
  background: var(--surface-2);
  color: var(--gray-900);
  border-color: var(--border-color);
  transform: translateX(4px);
}

.mobile-nav-item.active {
  background: rgba(var(--accent-rgb), 0.16);
  color: var(--primary-700);
  border-color: rgba(var(--accent-rgb), 0.3);
  font-weight: var(--font-semibold);
  box-shadow: none;
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
  background: rgba(15, 23, 42, 0.45);
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

  .desktop-auth {
    gap: var(--spacing-2);
    max-width: 220px;
  }

  .auth-btn {
    min-width: 74px;
    padding: 0.55rem 0.8rem;
  }
}

@media (max-width: 1180px) {
  .role-badge {
    display: none;
  }
}

@media (max-width: 980px) {
  .topbar-content {
    gap: var(--spacing-3);
  }

  .desktop-nav {
    justify-content: flex-start;
  }

  .user-badge-wrap {
    display: none;
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

  .desktop-auth {
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
    background: var(--surface-1);
    z-index: 1025; /* 低于topbar */
    transform: translateY(-100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), visibility 0.3s ease;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
    max-height: calc(100vh - var(--header-height));
    box-shadow: var(--shadow-md);
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
    background: rgba(15, 23, 42, 0.45);
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
</style>
