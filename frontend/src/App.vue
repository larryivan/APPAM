<template>
  <div class="app">
    <Topbar />
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import Topbar from './components/Topbar.vue'
</script>

<style>
/* Global Styles */
@import url('https://fonts.googleapis.com/css2?family=Gabarito:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');

:root {
  /* 主要色彩系统 */
  --primary-50: #eef4ff;
  --primary-100: #dbe7ff;
  --primary-200: #bfd3ff;
  --primary-300: #93b4ff;
  --primary-400: #5f8cff;
  --primary-500: #2563eb;
  --primary-600: #1d4ed8;
  --primary-700: #1e40af;
  --primary-800: #1e3a8a;
  --primary-900: #172554;

  --accent-500: var(--primary-500);
  --accent-600: var(--primary-600);
  --accent-700: var(--primary-700);
  --accent-rgb: 37, 99, 235;
  --primary-color: var(--primary-500);
  --secondary-color: #0ea5e9;
  
  /* 渐变色系统 */
  --gradient-primary: linear-gradient(135deg, #2563eb 0%, #0ea5e9 100%);
  --gradient-secondary: linear-gradient(135deg, #0ea5e9 0%, #38bdf8 100%);
  --gradient-accent: linear-gradient(135deg, #0f766e 0%, #14b8a6 100%);
  
  /* 中性色系统 */
  --gray-50: #f7f8fb;
  --gray-100: #eef2f7;
  --gray-200: #e5eaf1;
  --gray-300: #d5dde8;
  --gray-400: #9aa6b2;
  --gray-500: #6b7280;
  --gray-600: #4b5563;
  --gray-700: #374151;
  --gray-800: #1f2937;
  --gray-900: #0f172a;

  /* 表面色 */
  --surface-0: #f6f7fb;
  --surface-1: #ffffff;
  --surface-2: #f1f5f9;
  --surface-3: #e9eef5;
  
  /* 语义色彩 */
  --success-50: #ecfdf3;
  --success-500: #16a34a;
  --success-600: #15803d;
  --warning-50: #fff7ed;
  --warning-500: #f59e0b;
  --warning-600: #d97706;
  --error-50: #fef2f2;
  --error-500: #ef4444;
  --error-600: #dc2626;
  
  /* 字体系统 */
  --font-family-base: 'IBM Plex Sans', 'Segoe UI', -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
  --font-family-display: 'Gabarito', 'IBM Plex Sans', 'Segoe UI', sans-serif;
  --font-family-mono: 'IBM Plex Mono', 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
  
  /* 字体大小 */
  --text-xs: 0.75rem;     /* 12px */
  --text-sm: 0.875rem;    /* 14px */
  --text-base: 1rem;      /* 16px */
  --text-lg: 1.125rem;    /* 18px */
  --text-xl: 1.25rem;     /* 20px */
  --text-2xl: 1.5rem;     /* 24px */
  --text-3xl: 1.875rem;   /* 30px */
  --text-4xl: 2.25rem;    /* 36px */
  
  /* 字体权重 */
  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;
  
  /* 行高 */
  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --leading-relaxed: 1.625;
  
  /* 间距系统 */
  --spacing-1: 0.25rem;   /* 4px */
  --spacing-2: 0.5rem;    /* 8px */
  --spacing-3: 0.75rem;   /* 12px */
  --spacing-4: 1rem;      /* 16px */
  --spacing-5: 1.25rem;   /* 20px */
  --spacing-6: 1.5rem;    /* 24px */
  --spacing-8: 2rem;      /* 32px */
  --spacing-10: 2.5rem;   /* 40px */
  --spacing-12: 3rem;     /* 48px */
  --spacing-16: 4rem;     /* 64px */
  --spacing-xs: var(--spacing-1);
  --spacing-sm: var(--spacing-2);
  --spacing-md: var(--spacing-3);
  --spacing-lg: var(--spacing-4);
  --spacing-xl: var(--spacing-6);
  --spacing-2xl: var(--spacing-8);
  
  /* 圆角系统 */
  --radius-none: 0;
  --radius-sm: 0.5rem;    /* 8px */
  --radius-base: 0.625rem;  /* 10px */
  --radius-md: 0.875rem;  /* 14px */
  --radius-lg: 1.125rem;  /* 18px */
  --radius-xl: 1.75rem;   /* 28px */
  --radius-full: 9999px;
  
  /* 阴影系统 */
  --shadow-xs: 0 1px 2px rgb(15 23 42 / 0.04);
  --shadow-sm: 0 4px 10px rgb(15 23 42 / 0.08);
  --shadow-base: 0 8px 18px rgb(15 23 42 / 0.1);
  --shadow-md: 0 12px 24px rgb(15 23 42 / 0.14);
  --shadow-lg: 0 18px 40px rgb(15 23 42 / 0.18);
  --shadow-xl: 0 30px 60px rgb(15 23 42 / 0.22);
  
  /* 边框系统 */
  --border-width: 1px;
  --border-width-2: 2px;
  --border-color: rgb(15 23 42 / 0.12);
  --border-color-light: rgb(15 23 42 / 0.08);
  --border-color-dark: rgb(15 23 42 / 0.16);
  
  /* 过渡动画 */
  --transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-base: 200ms cubic-bezier(0.4, 0, 0.2, 1);
  --transition-slow: 300ms cubic-bezier(0.4, 0, 0.2, 1);
  
  /* Z-index层级 */
  --z-dropdown: 1000;
  --z-sticky: 1020;
  --z-fixed: 1030;
  --z-modal-backdrop: 1040;
  --z-modal: 1050;
  --z-popover: 1060;
  --z-tooltip: 1070;
  --z-toast: 1080;
  
  /* 布局尺寸 */
  --header-height: 60px;
  --sidebar-width: 280px;
  --sidebar-width-collapsed: 64px;
  
  /* 响应式断点 (for reference) */
  --bp-sm: 640px;
  --bp-md: 768px;
  --bp-lg: 1024px;
  --bp-xl: 1280px;
  --bp-2xl: 1536px;

  --dark-bg: #0b1220;
  --dark-bg-secondary: #101a2f;
  --text-light: #e2e8f0;
  --text-muted: #94a3b8;
}

/* 基础重置和全局样式 */
* {
  box-sizing: border-box;
}

html {
  font-family: var(--font-family-base);
  line-height: var(--leading-normal);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  height: 100%;
  overflow: hidden; /* 禁用全局滚动，让组件自己管理 */
}

body {
  margin: 0;
  background-color: var(--surface-0);
  background-image:
    radial-gradient(1200px 800px at -10% -20%, rgba(var(--accent-rgb), 0.08) 0%, transparent 60%),
    radial-gradient(1000px 600px at 110% -10%, rgba(14, 165, 233, 0.08) 0%, transparent 55%);
  color: var(--gray-900);
  font-size: var(--text-base);
  font-weight: var(--font-normal);
  height: 100%;
  overflow: hidden; /* 禁用body滚动 */
}

body.modal-open .content-wrapper {
  overflow: hidden;
}

body.modal-open {
  overscroll-behavior: contain;
}

h1, h2, h3, .display-text {
  font-family: var(--font-family-display);
  letter-spacing: -0.02em;
}

/* 统一滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--surface-2);
  border-radius: var(--radius-base);
}

::-webkit-scrollbar-thumb {
  background: var(--gray-300);
  border-radius: var(--radius-base);
  transition: background-color var(--transition-base);
}

::-webkit-scrollbar-thumb:hover {
  background: var(--gray-400);
}

/* 通用工具类 */
.text-xs { font-size: var(--text-xs); }
.text-sm { font-size: var(--text-sm); }
.text-base { font-size: var(--text-base); }
.text-lg { font-size: var(--text-lg); }
.text-xl { font-size: var(--text-xl); }
.text-2xl { font-size: var(--text-2xl); }
.text-3xl { font-size: var(--text-3xl); }

.font-normal { font-weight: var(--font-normal); }
.font-medium { font-weight: var(--font-medium); }
.font-semibold { font-weight: var(--font-semibold); }
.font-bold { font-weight: var(--font-bold); }

.text-gray-500 { color: var(--gray-500); }
.text-gray-600 { color: var(--gray-600); }
.text-gray-700 { color: var(--gray-700); }
.text-gray-800 { color: var(--gray-800); }

.bg-white { background-color: var(--surface-1); }
.bg-gray-50 { background-color: var(--gray-50); }
.bg-gray-100 { background-color: var(--gray-100); }

.border { border: var(--border-width) solid var(--border-color); }
.border-light { border: var(--border-width) solid var(--border-color-light); }
.border-dark { border: var(--border-width) solid var(--border-color-dark); }

.rounded-sm { border-radius: var(--radius-sm); }
.rounded { border-radius: var(--radius-base); }
.rounded-md { border-radius: var(--radius-md); }
.rounded-lg { border-radius: var(--radius-lg); }
.rounded-xl { border-radius: var(--radius-xl); }

.shadow-xs { box-shadow: var(--shadow-xs); }
.shadow-sm { box-shadow: var(--shadow-sm); }
.shadow { box-shadow: var(--shadow-base); }
.shadow-md { box-shadow: var(--shadow-md); }
.shadow-lg { box-shadow: var(--shadow-lg); }

.transition { transition: all var(--transition-base); }
.transition-fast { transition: all var(--transition-fast); }
.transition-slow { transition: all var(--transition-slow); }

/* 按钮基础样式 */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-2);
  padding: var(--spacing-3) var(--spacing-4);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  line-height: 1;
  border-radius: var(--radius-base);
  border: var(--border-width) solid transparent;
  cursor: pointer;
  transition: all var(--transition-base);
  text-decoration: none;
  user-select: none;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--gradient-primary);
  color: white;
  box-shadow: 0 8px 16px rgba(var(--accent-rgb), 0.2);
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #1d4ed8 0%, #0ea5e9 100%);
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(var(--accent-rgb), 0.24);
}

.btn-secondary {
  background: var(--surface-1);
  color: var(--gray-700);
  border-color: var(--border-color);
}

.btn-secondary:hover:not(:disabled) {
  background: var(--gray-50);
  border-color: var(--border-color-dark);
}

.btn-ghost {
  background: transparent;
  color: var(--gray-600);
}

.btn-ghost:hover:not(:disabled) {
  background: var(--surface-2);
  color: var(--gray-800);
}

/* 输入框基础样式 */
.input {
  display: block;
  width: 100%;
  padding: var(--spacing-3) var(--spacing-4);
  font-size: var(--text-sm);
  line-height: var(--leading-tight);
  color: var(--gray-800);
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-base);
  transition: all var(--transition-base);
}

.input:focus {
  outline: none;
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.16);
}

.input::placeholder {
  color: var(--gray-400);
}

/* 卡片基础样式 */
.card {
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-xs);
  transition: all var(--transition-base);
}

.card:hover {
  box-shadow: var(--shadow-base);
}

/* Modal base styles */
.app-modal-viewport {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal);
}

.app-modal-backdrop {
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(6px);
}

.app-modal {
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-color-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  animation: appModalIn 0.22s ease-out;
}

.app-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-4) var(--spacing-6);
  background: var(--surface-2);
  border-bottom: var(--border-width) solid var(--border-color-light);
}

.app-modal-header h3,
.app-modal-header h4 {
  margin: 0;
  color: var(--gray-900);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}

.app-modal-body {
  padding: var(--spacing-4) var(--spacing-6);
}

.app-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-3);
  padding: var(--spacing-4) var(--spacing-6);
  background: var(--surface-2);
  border-top: var(--border-width) solid var(--border-color-light);
}

.app-modal-close {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm);
  border: var(--border-width) solid var(--border-color);
  background: var(--surface-1);
  color: var(--gray-600);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-base);
}

.app-modal-close:hover {
  background: var(--surface-3);
  color: var(--gray-800);
}

@keyframes appModalIn {
  from {
    transform: translateY(8px) scale(0.98);
    opacity: 0;
  }
  to {
    transform: translateY(0) scale(1);
    opacity: 1;
  }
}

/* App布局 */
.app {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin-top: var(--header-height);
}

/* 针对旧版浏览器的兼容 */
@supports not (color: rgb(0 0 0 / 0.1)) {
  .shadow-xs { box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05); }
  .shadow-sm { box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px -1px rgba(0, 0, 0, 0.1); }
  .shadow { box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1); }
  .shadow-md { box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1); }
  .shadow-lg { box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1); }
}
</style>
