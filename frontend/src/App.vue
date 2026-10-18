<template>
  <div class="app">
    <Topbar />
    <main class="main-content">
      <router-view />
    </main>
    <FeedbackHost />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import Topbar from './components/Topbar.vue'
import FeedbackHost from './components/ui/FeedbackHost.vue'
import { loadCurrentUser } from './lib/auth'

onMounted(() => {
  loadCurrentUser()
})
</script>

<style>
/* Global Styles */
@import './styles/account-ui.css';

:root {
  /* ------------------------------------------------------------------
     Ink & paper.
     Neutrals carry the whole interface. Ink is the only strong value and
     it belongs to primary actions and headings. The accent is a single
     restrained blue reserved for focus, links and the current selection,
     so colour always means something.
     ------------------------------------------------------------------ */

  /* Ink — primary actions, headings, strong emphasis */
  --primary-50: #f2f4f6;
  --primary-100: #e5e8ec;
  --primary-200: #cbd1d8;
  --primary-300: #a3acb6;
  --primary-400: #6b757f;
  --primary-500: #333b44;
  --primary-600: #212930;
  --primary-700: #171d23;
  --primary-800: #11161b;
  --primary-900: #0b0f13;

  /* Accent — focus, links, current selection. Used sparingly. */
  --accent-50: #eef3fb;
  --accent-100: #dce7f7;
  --accent-200: #bcd0ee;
  --accent-500: #2f62c4;
  --accent-600: #2653ab;
  --accent-700: #1f458d;
  --accent-rgb: 47, 98, 196;
  --primary-color: var(--primary-600);
  --secondary-color: #0f6b73;

  /* Retained for compatibility with older rules; flat, never gradients. */
  --gradient-primary: var(--primary-600);
  --gradient-secondary: var(--primary-500);
  --gradient-accent: var(--accent-600);

  /* Neutrals — a low-chroma ramp with even perceptual steps */
  --gray-50: #f7f8f9;
  --gray-100: #eef0f2;
  --gray-200: #e2e5e8;
  --gray-300: #ccd1d6;
  --gray-400: #8d969e;
  --gray-500: #677079;
  --gray-600: #4c545c;
  --gray-700: #363d44;
  --gray-800: #232930;
  --gray-900: #12161a;

  /* Surfaces — paper over a slightly recessed ground */
  --surface-0: #f6f7f8;
  --surface-1: #ffffff;
  --surface-2: #f1f3f4;
  --surface-3: #e8eaed;

  /* Semantic — desaturated to sit beside the neutrals without shouting */
  --success-50: #eef6f1;
  --success-500: #1f7a52;
  --success-600: #176141;
  --warning-50: #fdf6e9;
  --warning-500: #a9700f;
  --warning-600: #8a5a0a;
  --error-50: #fdf1f1;
  --error-500: #bb4646;
  --error-600: #9c3636;

  /* Type */
  --font-family-base: Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  --font-family-display: var(--font-family-base);
  --font-family-mono: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;

  --text-xs: 0.75rem;     /* 12px */
  --text-sm: 0.875rem;    /* 14px */
  --text-base: 1rem;      /* 16px */
  --text-lg: 1.125rem;    /* 18px */
  --text-xl: 1.25rem;     /* 20px */
  --text-2xl: 1.5rem;     /* 24px */
  --text-3xl: 1.875rem;   /* 30px */
  --text-4xl: 2.25rem;    /* 36px */

  --font-normal: 400;
  --font-medium: 500;
  --font-semibold: 600;
  --font-bold: 700;

  --leading-tight: 1.25;
  --leading-normal: 1.5;
  --leading-relaxed: 1.625;

  /* Tracking — display sizes tighten, micro-labels open up */
  --tracking-tight: -0.018em;
  --tracking-snug: -0.008em;
  --tracking-normal: 0;
  --tracking-wide: 0.06em;

  /* Spacing */
  --spacing-1: 0.25rem;
  --spacing-2: 0.5rem;
  --spacing-3: 0.75rem;
  --spacing-4: 1rem;
  --spacing-5: 1.25rem;
  --spacing-6: 1.5rem;
  --spacing-8: 2rem;
  --spacing-10: 2.5rem;
  --spacing-12: 3rem;
  --spacing-16: 4rem;
  --spacing-xs: var(--spacing-1);
  --spacing-sm: var(--spacing-2);
  --spacing-md: var(--spacing-3);
  --spacing-lg: var(--spacing-4);
  --spacing-xl: var(--spacing-6);
  --spacing-2xl: var(--spacing-8);

  /* Radius — 6 / 8 / 12, so nothing looks accidental. Cards stay at 8px by
     an earlier deliberate decision; only true overlays get the larger step. */
  --radius-none: 0;
  --radius-sm: 0.375rem;  /* 6px  — controls, chips */
  --radius-base: 0.5rem;  /* 8px  — inputs, cards */
  --radius-md: 0.5rem;    /* 8px  — panels */
  --radius-lg: 0.5rem;
  --radius-xl: 0.75rem;   /* 12px — overlays */
  --radius-full: 9999px;

  /* Elevation — structure comes from hairlines; shadow only lifts overlays */
  --shadow-xs: 0 1px 1px rgb(18 22 26 / 0.03);
  --shadow-sm: 0 1px 2px rgb(18 22 26 / 0.04), 0 1px 3px rgb(18 22 26 / 0.03);
  --shadow-base: 0 2px 4px rgb(18 22 26 / 0.04), 0 4px 12px rgb(18 22 26 / 0.05);
  --shadow-md: 0 4px 8px rgb(18 22 26 / 0.05), 0 12px 28px rgb(18 22 26 / 0.07);
  --shadow-lg: 0 8px 16px rgb(18 22 26 / 0.06), 0 24px 56px rgb(18 22 26 / 0.10);
  --shadow-xl: 0 16px 32px rgb(18 22 26 / 0.08), 0 40px 88px rgb(18 22 26 / 0.14);

  /* Borders — the hairline is the primary structural device */
  --border-width: 1px;
  --border-width-2: 2px;
  --border-color: #dfe2e6;
  --border-color-light: #eaecef;
  --border-color-dark: #ccd1d6;

  /* Focus — one ring, everywhere */
  --focus-ring-width: 2px;
  --focus-ring-offset: 2px;
  --focus-ring-color: rgb(var(--accent-rgb) / 0.55);

  /* Motion — quick, with a decelerating curve; honours reduced motion */
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);
  --ease-exit: cubic-bezier(0.4, 0, 1, 1);
  --duration-fast: 120ms;
  --duration-base: 180ms;
  --duration-slow: 260ms;
  --transition-fast: var(--duration-fast) var(--ease-standard);
  --transition-base: var(--duration-base) var(--ease-standard);
  --transition-slow: var(--duration-slow) var(--ease-standard);

  /* Z-index */
  --z-dropdown: 1000;
  --z-sticky: 1020;
  --z-fixed: 1030;
  --z-modal-backdrop: 1040;
  --z-modal: 1050;
  --z-popover: 1060;
  --z-tooltip: 1070;
  --z-toast: 1080;

  /* Layout */
  --header-height: 68px;
  --sidebar-width: 280px;
  --sidebar-width-collapsed: 64px;
  --content-width: 1160px;
  --control-height: 36px;

  /* Breakpoints. CSS cannot read variables inside @media, so these are the
     canonical values to type by hand. Do not introduce new ones. */
  --bp-sm: 640px;
  --bp-md: 768px;
  --bp-lg: 1024px;
  --bp-xl: 1280px;
  --bp-2xl: 1536px;

  --dark-bg: #10141a;
  --dark-bg-secondary: #171d24;
  --text-light: #e6e9ec;
  --text-muted: #98a1a9;
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
  color-scheme: light;
}

body {
  margin: 0;
  background-color: var(--surface-0);
  color: var(--gray-900);
  font-size: var(--text-sm);
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

h1, h2, h3, h4, .display-text {
  font-family: var(--font-family-display);
  letter-spacing: var(--tracking-snug);
  line-height: var(--leading-tight);
  color: var(--gray-900);
  text-wrap: balance;
}

/* Larger type needs proportionally tighter tracking to stay optically even. */
h1, .display-text {
  letter-spacing: var(--tracking-tight);
}

/* Long-form paragraphs read better without orphaned last words. */
p {
  text-wrap: pretty;
}

/* Numeric columns and metrics must not wobble as values change. */
.tabular,
[data-tabular] {
  font-variant-numeric: tabular-nums;
  font-feature-settings: 'tnum' 1;
}

button,
input,
select,
textarea {
  font: inherit;
  letter-spacing: 0;
}

button,
a,
summary,
input,
select,
textarea {
  -webkit-tap-highlight-color: transparent;
}

button:focus-visible,
a:focus-visible,
summary:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible,
[tabindex]:focus-visible {
  outline: var(--focus-ring-width) solid var(--focus-ring-color);
  outline-offset: var(--focus-ring-offset);
  border-radius: var(--radius-sm);
}

::selection {
  background: var(--accent-100);
  color: var(--gray-900);
}

/* Respect the system setting. Motion becomes instant rather than removed, so
   nothing that relies on a transition ending silently breaks. */
@media (prefers-reduced-motion: reduce) {
  :root {
    --duration-fast: 1ms;
    --duration-base: 1ms;
    --duration-slow: 1ms;
  }

  *,
  *::before,
  *::after {
    animation-duration: 1ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 1ms !important;
    scroll-behavior: auto !important;
  }
}

/* Scroll regions stay functional without drawing permanent inner rails. */
* {
  scrollbar-width: thin;
  scrollbar-color: transparent transparent;
}

*:hover,
*:focus-within {
  scrollbar-color: var(--gray-300) transparent;
}

::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  border: 1px solid transparent;
  border-radius: var(--radius-full);
  background: transparent;
  background-clip: padding-box;
  transition: background-color var(--transition-base);
}

*:hover::-webkit-scrollbar-thumb,
*:focus-within::-webkit-scrollbar-thumb,
::-webkit-scrollbar-thumb:hover {
  background: var(--gray-400);
  background-clip: padding-box;
}

::-webkit-scrollbar-corner {
  background: transparent;
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
  min-height: var(--control-height);
  padding: 0 var(--spacing-3);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  line-height: 1;
  border-radius: var(--radius-base);
  border: var(--border-width) solid transparent;
  cursor: pointer;
  transition: background-color var(--transition-fast), border-color var(--transition-fast), color var(--transition-fast), box-shadow var(--transition-fast);
  text-decoration: none;
  user-select: none;
}

.btn:disabled {
  opacity: 1;
  background: var(--gray-200);
  border-color: var(--gray-200);
  color: var(--gray-400);
  cursor: not-allowed;
}

.btn-primary {
  background: var(--primary-600);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-700);
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

.btn-danger {
  background: var(--error-500);
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: var(--error-600);
}

/* 尺寸修饰符 */
.btn-sm {
  min-height: 30px;
  padding: 0 var(--spacing-2);
  font-size: var(--text-xs);
}

.btn-lg {
  min-height: 40px;
  padding: 0 var(--spacing-4);
  font-size: var(--text-sm);
}

/* 纯图标按钮 */
.btn-icon {
  padding: var(--spacing-2);
  aspect-ratio: 1;
}
.btn-icon.btn-sm { padding: var(--spacing-1); }

/* 输入框基础样式 */
.input {
  display: block;
  width: 100%;
  min-height: var(--control-height);
  padding: 0 var(--spacing-3);
  font-size: var(--text-sm);
  line-height: var(--leading-tight);
  color: var(--gray-800);
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-base);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.input:focus {
  outline: none;
  border-color: var(--primary-500);
  box-shadow: 0 0 0 2px rgba(var(--accent-rgb), 0.12);
}

.input::placeholder {
  color: var(--gray-400);
}

/* 卡片基础样式 */
.card {
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: none;
}

/* 统一状态标签 (status pill) —— 低饱和底色 + 同色系文字,取代各处大色块 */
.pill {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  padding: 2px var(--spacing-3);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  line-height: 1.6;
  border-radius: var(--radius-full);
  background: var(--surface-2);
  color: var(--gray-600);
  white-space: nowrap;
}
.pill .pill-dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: currentColor;
  flex-shrink: 0;
}
.pill--success { background: var(--success-50); color: var(--success-600); }
.pill--running,
.pill--info    { background: var(--primary-50); color: var(--primary-600); }
.pill--warning { background: var(--warning-50); color: var(--warning-600); }
.pill--danger,
.pill--error   { background: var(--error-50); color: var(--error-600); }
.pill--muted   { background: var(--surface-2); color: var(--gray-500); }

/* 软色徽章 (类别标记),如工作流类型 */
.badge-soft {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-1);
  padding: 2px var(--spacing-2);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  border-radius: var(--radius-sm);
  background: var(--primary-50);
  color: var(--primary-700);
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
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  display: flex;
  flex-direction: column;
  animation: appModalIn 0.22s ease-out;
}

.app-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  background: var(--surface-1);
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
  padding: 10px 16px;
  background: var(--surface-1);
  border-top: var(--border-width) solid var(--border-color-light);
}

.app-modal-close {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-base);
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
  flex: 0 0 calc(100vh - var(--header-height));
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--header-height));
  min-height: 0;
  overflow: hidden;
  margin-top: var(--header-height);
}

@supports (height: 100dvh) {
  .main-content {
    flex-basis: calc(100dvh - var(--header-height));
    height: calc(100dvh - var(--header-height));
  }
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
