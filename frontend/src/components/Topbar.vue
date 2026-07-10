<template>
  <header class="topbar">
    <div class="topbar-content">
      <router-link :to="homeRoute" class="brand" aria-label="APPAM home">
        <img src="/assets/logo.svg" alt="">
        <span>APPAM</span>
      </router-link>

      <nav class="primary-nav" aria-label="Primary navigation">
        <router-link v-if="authState.user" to="/projects" :class="{ active: isActive('/projects') }">
          Projects
        </router-link>
        <router-link v-if="authState.user?.role === 'admin'" to="/admin" :class="{ active: isActive('/admin') }">
          Admin
        </router-link>
        <router-link v-if="!authState.user" to="/documentation" :class="{ active: isActive('/documentation') }">
          Documentation
        </router-link>
      </nav>

      <div class="account-area">
        <details v-if="authState.user" ref="accountMenu" class="account-menu">
          <summary>
            <span class="account-name">{{ authDisplayName }}</span>
            <span v-if="authState.user.role === 'admin'" class="admin-label">Admin</span>
            <Icon name="chevron-down" :size="15" />
          </summary>
          <div class="account-popover">
            <router-link to="/settings" @click="closeMenus">Profile</router-link>
            <router-link to="/documentation" @click="closeMenus">Documentation</router-link>
            <button type="button" @click="handleLogout">Log out</button>
          </div>
        </details>
        <router-link v-else to="/login" class="login-button">Log in</router-link>

        <button
          v-if="authState.user"
          class="mobile-menu-button"
          type="button"
          :aria-expanded="mobileMenuOpen"
          aria-controls="mobile-navigation"
          aria-label="Open navigation"
          @click="mobileMenuOpen = !mobileMenuOpen"
        >
          <Icon :name="mobileMenuOpen ? 'x' : 'align-justify'" :size="20" />
        </button>
      </div>
    </div>

    <nav v-if="authState.user" id="mobile-navigation" class="mobile-nav" :class="{ open: mobileMenuOpen }">
      <router-link to="/projects" @click="closeMenus">Projects</router-link>
      <router-link v-if="authState.user.role === 'admin'" to="/admin" @click="closeMenus">Admin</router-link>
      <router-link to="/settings" @click="closeMenus">Profile</router-link>
      <router-link to="/documentation" @click="closeMenus">Documentation</router-link>
      <button type="button" @click="handleLogout">Log out</button>
    </nav>
  </header>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import Icon from './ui/Icon.vue'
import { authState, logout } from '../lib/auth'

const route = useRoute()
const router = useRouter()
const accountMenu = ref(null)
const mobileMenuOpen = ref(false)

const authDisplayName = computed(() => authState.user?.display_name || authState.user?.username || 'Account')
const homeRoute = computed(() => authState.user ? '/projects' : '/login')

function isActive(path) {
  return route.path.startsWith(path)
}

function closeMenus() {
  mobileMenuOpen.value = false
  if (accountMenu.value) accountMenu.value.open = false
}

async function handleLogout() {
  await logout()
  closeMenus()
  await router.replace('/login')
}

watch(() => route.fullPath, closeMenus)
</script>

<style scoped>
.topbar {
  position: fixed;
  z-index: var(--z-fixed);
  inset: 0 0 auto;
  height: var(--header-height);
  border-bottom: 1px solid var(--border-color-light);
  background: var(--surface-1);
}

.topbar-content {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--spacing-6);
  width: min(1200px, 100%);
  height: 100%;
  margin: 0 auto;
  padding: 0 var(--spacing-5);
}

.brand {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  color: var(--gray-900);
  font-family: var(--font-family-display);
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  letter-spacing: 0;
  text-decoration: none;
}

.brand img {
  width: 30px;
  height: 30px;
}

.primary-nav {
  display: flex;
  align-items: center;
  gap: var(--spacing-1);
}

.primary-nav a {
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  color: var(--gray-600);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  text-decoration: none;
}

.primary-nav a:hover,
.primary-nav a.active {
  background: var(--surface-2);
  color: var(--gray-900);
}

.account-area {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.account-menu {
  position: relative;
}

.account-menu summary {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  min-height: 36px;
  padding: 0 var(--spacing-3);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--gray-700);
  font-size: var(--text-sm);
  cursor: pointer;
  list-style: none;
}

.account-menu summary::-webkit-details-marker {
  display: none;
}

.account-menu[open] summary,
.account-menu summary:hover {
  background: var(--surface-2);
}

.account-name {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.admin-label {
  color: var(--primary-700);
  font-size: 11px;
  font-weight: var(--font-semibold);
}

.account-popover {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  display: grid;
  width: 180px;
  padding: 6px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--surface-1);
  box-shadow: var(--shadow-md);
}

.account-popover a,
.account-popover button {
  min-height: 36px;
  padding: 0 var(--spacing-3);
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-700);
  font: inherit;
  font-size: var(--text-sm);
  line-height: 36px;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
}

.account-popover a:hover,
.account-popover button:hover {
  background: var(--surface-2);
  color: var(--gray-900);
}

.login-button {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 var(--spacing-4);
  border-radius: var(--radius-sm);
  background: var(--primary-600);
  color: white;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  text-decoration: none;
}

.mobile-menu-button,
.mobile-nav {
  display: none;
}

@media (max-width: 700px) {
  .topbar-content {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: var(--spacing-3);
    padding: 0 var(--spacing-3);
  }

  .primary-nav,
  .account-menu {
    display: none;
  }

  .mobile-menu-button {
    display: grid;
    place-items: center;
    width: 36px;
    height: 36px;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-sm);
    background: var(--surface-1);
    color: var(--gray-700);
    cursor: pointer;
  }

  .mobile-nav {
    position: absolute;
    top: var(--header-height);
    right: 0;
    left: 0;
    display: none;
    padding: var(--spacing-2) var(--spacing-3) var(--spacing-3);
    border-bottom: 1px solid var(--border-color);
    background: var(--surface-1);
    box-shadow: var(--shadow-md);
  }

  .mobile-nav.open {
    display: grid;
  }

  .mobile-nav a,
  .mobile-nav button {
    min-height: 42px;
    padding: 0 var(--spacing-3);
    border: 0;
    border-radius: var(--radius-sm);
    background: transparent;
    color: var(--gray-700);
    font: inherit;
    font-size: var(--text-sm);
    line-height: 42px;
    text-align: left;
    text-decoration: none;
  }

  .mobile-nav a:hover,
  .mobile-nav button:hover {
    background: var(--surface-2);
  }
}
</style>
