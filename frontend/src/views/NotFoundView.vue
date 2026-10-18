<template>
  <section class="notfound">
    <div class="notfound-inner">
      <span class="notfound-eyebrow">Page not found</span>
      <h1>This page does not exist</h1>
      <p>
        The address <code>{{ attemptedPath }}</code> did not match anything in APPAM.
        It may have been renamed, or the link may be out of date.
      </p>
      <div class="notfound-actions">
        <router-link :to="homeRoute" class="notfound-primary">
          <Icon :name="authState.user ? 'folder-open' : 'home'" :size="17" />
          <span>{{ authState.user ? 'Go to projects' : 'Go to the home page' }}</span>
        </router-link>
        <button type="button" class="notfound-secondary" @click="goBack">
          <Icon name="arrow-left" :size="17" />
          <span>Back</span>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import Icon from '@/components/ui/Icon.vue'
import { authState } from '@/lib/auth.js'

const route = useRoute()
const router = useRouter()

const attemptedPath = computed(() => route.fullPath)
const homeRoute = computed(() => (authState.user ? '/projects' : '/'))

function goBack() {
  if (window.history.length > 1) router.back()
  else router.replace(homeRoute.value)
}
</script>

<style scoped>
.notfound {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - var(--header-height));
  padding: var(--spacing-8) var(--spacing-6);
  background: var(--surface-0);
}

.notfound-inner {
  width: min(560px, 100%);
}

.notfound-eyebrow {
  display: inline-flex;
  color: var(--gray-500);
  font-size: 11px;
  font-weight: var(--font-medium);
  letter-spacing: var(--tracking-wide);
  text-transform: uppercase;
}

.notfound-inner h1 {
  margin: var(--spacing-2) 0 0;
  font-size: var(--text-2xl);
  font-weight: var(--font-semibold);
}

.notfound-inner p {
  margin: var(--spacing-3) 0 0;
  max-width: 52ch;
  color: var(--gray-600);
  line-height: var(--leading-relaxed);
}

.notfound-inner code {
  padding: 1px 5px;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  font-family: var(--font-family-mono);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.notfound-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-2);
  margin-top: var(--spacing-6);
}

.notfound-primary,
.notfound-secondary {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-2);
  min-height: var(--control-height);
  padding: 0 var(--spacing-4);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-base);
  background: var(--surface-1);
  color: var(--gray-700);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  text-decoration: none;
  cursor: pointer;
  transition: background var(--transition-fast), border-color var(--transition-fast);
}

.notfound-primary {
  border-color: var(--primary-600);
  background: var(--primary-600);
  color: #fff;
}

.notfound-primary:hover { background: var(--primary-700); border-color: var(--primary-700); }
.notfound-secondary:hover { background: var(--surface-2); }
</style>
