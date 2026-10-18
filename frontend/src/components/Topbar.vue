<template>
  <header ref="topbarRoot" class="topbar">
    <div class="topbar-content">
      <div class="topbar-leading">
        <router-link to="/" class="brand" aria-label="APPAM home">
          <span class="brand-mark" aria-hidden="true">
            <img src="/assets/logo.svg" alt="">
          </span>
          <span class="brand-name">APPAM</span>
        </router-link>

        <nav class="primary-nav" aria-label="Primary navigation">
          <router-link v-if="authState.user" to="/projects" :class="{ active: projectsActive }">
            <Icon name="layout-grid" :size="18" />
            <span>Projects</span>
          </router-link>
          <router-link v-if="authState.user?.role === 'admin'" to="/admin" :class="{ active: isActive('/admin') }">
            <Icon name="shield-check" :size="18" />
            <span>Admin</span>
          </router-link>
          <router-link v-if="!authState.user" to="/documentation" :class="{ active: isActive('/documentation') }">
            <Icon name="book-open" :size="18" />
            <span>Documentation</span>
          </router-link>
        </nav>
      </div>

      <div class="account-area">
        <details v-if="authState.user" ref="accountMenu" class="account-menu">
          <summary :aria-label="`Open account menu for ${authDisplayName}`">
            <span class="account-avatar" aria-hidden="true">{{ accountInitials }}</span>
            <span class="account-copy">
              <strong>{{ authDisplayName }}</strong>
              <small>{{ roleLabel }}</small>
            </span>
            <Icon class="account-chevron" name="chevron-down" :size="16" />
          </summary>

          <div class="account-popover">
            <div class="account-popover__identity">
              <span class="account-avatar large" aria-hidden="true">{{ accountInitials }}</span>
              <span>
                <strong>{{ authDisplayName }}</strong>
                <small>{{ roleLabel }}</small>
              </span>
            </div>
            <nav aria-label="Account navigation">
              <router-link to="/settings" @click="closeMenus">
                <Icon name="user-round" :size="17" />
                <span>Profile</span>
              </router-link>
              <router-link to="/documentation" @click="closeMenus">
                <Icon name="book-open" :size="17" />
                <span>Documentation</span>
              </router-link>
            </nav>
            <div class="account-popover__divider"></div>
            <button type="button" class="logout-action" @click="handleLogout">
              <Icon name="log-out" :size="17" />
              <span>Log out</span>
            </button>
          </div>
        </details>

        <router-link v-else to="/login" class="login-button">
          <span>Log in</span>
          <Icon name="log-in" :size="17" />
        </router-link>

        <button
          v-if="authState.user"
          class="mobile-menu-button"
          type="button"
          :aria-expanded="mobileMenuOpen"
          aria-controls="mobile-navigation"
          :aria-label="mobileMenuOpen ? 'Close navigation' : 'Open navigation'"
          @click="mobileMenuOpen = !mobileMenuOpen"
        >
          <Icon :name="mobileMenuOpen ? 'x' : 'align-justify'" :size="21" />
        </button>
      </div>
    </div>

    <nav v-if="authState.user" id="mobile-navigation" class="mobile-nav" :class="{ open: mobileMenuOpen }" aria-label="Mobile navigation">
      <div class="mobile-identity">
        <span class="account-avatar large" aria-hidden="true">{{ accountInitials }}</span>
        <span>
          <strong>{{ authDisplayName }}</strong>
          <small>{{ roleLabel }}</small>
        </span>
      </div>
      <router-link to="/projects" @click="closeMenus">
        <Icon name="layout-grid" :size="18" />
        <span>Projects</span>
      </router-link>
      <router-link v-if="authState.user.role === 'admin'" to="/admin" @click="closeMenus">
        <Icon name="shield-check" :size="18" />
        <span>Admin</span>
      </router-link>
      <router-link to="/settings" @click="closeMenus">
        <Icon name="user-round" :size="18" />
        <span>Profile</span>
      </router-link>
      <router-link to="/documentation" @click="closeMenus">
        <Icon name="book-open" :size="18" />
        <span>Documentation</span>
      </router-link>
      <button type="button" class="logout-action" @click="handleLogout">
        <Icon name="log-out" :size="18" />
        <span>Log out</span>
      </button>
    </nav>
  </header>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import Icon from './ui/Icon.vue'
import { authState, logout } from '../lib/auth'

const route = useRoute()
const router = useRouter()
const topbarRoot = ref(null)
const accountMenu = ref(null)
const mobileMenuOpen = ref(false)

const authDisplayName = computed(() => authState.user?.display_name || authState.user?.username || 'Account')
const roleLabel = computed(() => authState.user?.role === 'admin' ? 'Administrator' : 'Member')
const projectsActive = computed(() => route.path.startsWith('/projects') || route.path.startsWith('/workspace'))
const accountInitials = computed(() => {
  const parts = authDisplayName.value.trim().split(/\s+/).filter(Boolean)
  if (parts.length > 1) return `${Array.from(parts[0])[0] || ''}${Array.from(parts.at(-1))[0] || ''}`.toUpperCase()
  return Array.from(parts[0] || 'A').slice(0, 2).join('').toUpperCase()
})

function isActive(path) {
  return route.path.startsWith(path)
}

function closeMenus() {
  mobileMenuOpen.value = false
  if (accountMenu.value) accountMenu.value.open = false
}

function handleDocumentPointerDown(event) {
  if (accountMenu.value?.open && !accountMenu.value.contains(event.target)) {
    accountMenu.value.open = false
  }
  if (mobileMenuOpen.value && !topbarRoot.value?.contains(event.target)) {
    mobileMenuOpen.value = false
  }
}

function handleKeydown(event) {
  if (event.key === 'Escape') closeMenus()
}

async function handleLogout() {
  await logout()
  closeMenus()
  await router.replace('/')
}

watch(() => route.fullPath, closeMenus)

onMounted(() => {
  document.addEventListener('pointerdown', handleDocumentPointerDown)
  document.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.topbar {
  position: fixed;
  z-index: var(--z-fixed);
  inset: 0 0 auto;
  height: var(--header-height);
  border-bottom: 1px solid var(--border-color-light);
  background: rgb(255 255 255 / 0.97);
  box-shadow: 0 1px 8px rgb(21 29 41 / 0.035);
  backdrop-filter: saturate(140%) blur(12px);
}

.topbar-content {
  display: flex;
  width: 100%;
  height: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 28px;
  padding: 0 clamp(20px, 2.5vw, 36px);
}

.topbar-leading {
  display: flex;
  min-width: 0;
  height: 100%;
  flex: 1;
  align-items: center;
  gap: 22px;
}

.brand {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 10px;
  color: var(--gray-900);
  font-family: var(--font-family-display);
  text-decoration: none;
}

.brand-mark {
  display: grid;
  width: 38px;
  height: 38px;
  place-items: center;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-md);
  background: var(--surface-1);
  box-shadow: var(--shadow-xs);
}

.brand img {
  width: 28px;
  height: 28px;
}

.brand-name {
  font-size: 17px;
  font-weight: var(--font-bold);
  line-height: 1;
}

.primary-nav {
  display: flex;
  height: 42px;
  min-width: 0;
  align-items: center;
  gap: 4px;
  padding-left: 20px;
  border-left: 1px solid var(--border-color-light);
}

.primary-nav a {
  position: relative;
  display: inline-flex;
  min-height: 42px;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border-radius: var(--radius-base);
  color: var(--gray-500);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  text-decoration: none;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.primary-nav a::after {
  position: absolute;
  right: 12px;
  bottom: -13px;
  left: 12px;
  height: 2px;
  border-radius: 2px 2px 0 0;
  background: var(--primary-600);
  content: '';
  opacity: 0;
  transform: scaleX(0.55);
  transition: opacity var(--transition-fast), transform var(--transition-fast);
}

.primary-nav a:hover {
  background: var(--surface-2);
  color: var(--gray-800);
}

.primary-nav a.active {
  color: var(--primary-700);
}

.primary-nav a.active::after {
  opacity: 1;
  transform: scaleX(1);
}

.account-area {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--spacing-2);
}

.account-menu {
  position: relative;
}

.account-menu summary {
  display: grid;
  grid-template-columns: 34px minmax(0, auto) 16px;
  min-height: 46px;
  align-items: center;
  gap: 9px;
  padding: 4px 8px 4px 5px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  color: var(--gray-700);
  cursor: pointer;
  list-style: none;
  transition: background var(--transition-fast), border-color var(--transition-fast);
}

.account-menu summary::-webkit-details-marker {
  display: none;
}

.account-menu[open] summary,
.account-menu summary:hover {
  border-color: var(--border-color-light);
  background: var(--surface-2);
}

.account-avatar {
  display: grid;
  width: 34px;
  height: 34px;
  place-items: center;
  flex: 0 0 34px;
  border: 1px solid var(--primary-100);
  border-radius: 50%;
  background: var(--primary-50);
  color: var(--primary-700);
  font-size: 11px;
  font-weight: var(--font-bold);
  line-height: 1;
}

.account-avatar.large {
  width: 38px;
  height: 38px;
  flex-basis: 38px;
  font-size: 12px;
}

.account-copy,
.account-popover__identity > span:last-child,
.mobile-identity > span:last-child {
  display: grid;
  min-width: 0;
  gap: 1px;
}

.account-copy strong,
.account-popover__identity strong,
.mobile-identity strong {
  overflow: hidden;
  color: var(--gray-800);
  font-size: 13px;
  font-weight: var(--font-semibold);
  line-height: 1.25;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.account-copy small,
.account-popover__identity small,
.mobile-identity small {
  color: var(--gray-500);
  font-size: 11px;
  line-height: 1.25;
}

.account-copy strong {
  max-width: 150px;
}

.account-chevron {
  color: var(--gray-400);
  transition: transform var(--transition-fast);
}

.account-menu[open] .account-chevron {
  transform: rotate(180deg);
}

.account-popover {
  position: absolute;
  top: calc(100% + 9px);
  right: 0;
  display: grid;
  width: 232px;
  padding: 7px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--surface-1);
  box-shadow: var(--shadow-lg);
}

.account-popover__identity,
.mobile-identity {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
  padding: 9px 8px 11px;
}

.account-popover__identity > span:last-child,
.mobile-identity > span:last-child {
  flex: 1;
}

.account-popover nav {
  display: grid;
  gap: 2px;
}

.account-popover a,
.account-popover button,
.mobile-nav a,
.mobile-nav button {
  display: flex;
  width: 100%;
  min-height: 40px;
  align-items: center;
  gap: 10px;
  padding: 0 10px;
  border: 0;
  border-radius: var(--radius-base);
  background: transparent;
  color: var(--gray-700);
  font: inherit;
  font-size: var(--text-sm);
  text-align: left;
  text-decoration: none;
  cursor: pointer;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.account-popover a:hover,
.account-popover button:hover,
.mobile-nav a:hover,
.mobile-nav button:hover {
  background: var(--surface-2);
  color: var(--gray-900);
}

.account-popover__divider {
  height: 1px;
  margin: 6px 4px;
  background: var(--border-color-light);
}

.account-popover .logout-action,
.mobile-nav .logout-action {
  color: var(--error-600);
}

.login-button {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  gap: 8px;
  padding: 0 14px;
  border: 1px solid var(--primary-600);
  border-radius: var(--radius-base);
  background: var(--primary-600);
  color: white;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  text-decoration: none;
  transition: background var(--transition-fast), border-color var(--transition-fast);
}

.login-button:hover {
  border-color: var(--primary-700);
  background: var(--primary-700);
}

.mobile-menu-button,
.mobile-nav {
  display: none;
}

@media (max-width: 760px) {
  .topbar-content {
    gap: var(--spacing-3);
    padding: 0 14px;
  }

  .topbar-leading {
    gap: 0;
  }

  .brand-mark {
    width: 36px;
    height: 36px;
  }

  .brand img {
    width: 26px;
    height: 26px;
  }

  .primary-nav,
  .account-menu {
    display: none;
  }

  .mobile-menu-button {
    display: grid;
    width: 40px;
    height: 40px;
    place-items: center;
    padding: 0;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-base);
    background: var(--surface-1);
    color: var(--gray-700);
    cursor: pointer;
  }

  .mobile-menu-button:hover,
  .mobile-menu-button[aria-expanded='true'] {
    background: var(--surface-2);
  }

  .mobile-nav {
    position: absolute;
    top: calc(var(--header-height) - 5px);
    right: 12px;
    display: none;
    width: min(340px, calc(100% - 24px));
    max-height: calc(100dvh - var(--header-height) - 12px);
    padding: 7px;
    overflow-y: auto;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    background: var(--surface-1);
    box-shadow: var(--shadow-lg);
  }

  .mobile-nav.open {
    display: grid;
    gap: 2px;
  }

  .mobile-identity {
    margin-bottom: 4px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-color-light);
  }

  .mobile-nav a,
  .mobile-nav button {
    min-height: 44px;
  }

  .mobile-nav .logout-action {
    margin-top: 4px;
    border-top: 1px solid var(--border-color-light);
    border-radius: 0 0 var(--radius-base) var(--radius-base);
  }
}

@media (max-width: 420px) {
  .brand-name {
    font-size: 16px;
  }

  .login-button {
    min-height: 38px;
    padding: 0 11px;
  }
}
</style>
