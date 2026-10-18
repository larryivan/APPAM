<template>
  <div class="admin-layout">
    <aside class="admin-sidebar">
      <div class="admin-sidebar__heading">
        <span class="admin-sidebar__mark">
          <Icon name="sliders-horizontal" :size="18" />
        </span>
        <span class="admin-sidebar__title">
          <strong>Administration</strong>
          <small>Lab controls</small>
        </span>
      </div>

      <AdminNav />

      <footer class="admin-sidebar__account">
        <span class="admin-sidebar__avatar">{{ initials }}</span>
        <span class="admin-sidebar__identity">
          <strong>{{ displayName }}</strong>
          <small>Administrator</small>
        </span>
      </footer>
    </aside>

    <main class="admin-content">
      <div class="admin-content__inner">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'

import AdminNav from '../components/AdminNav.vue'
import Icon from '../components/ui/Icon.vue'
import { authState } from '../lib/auth'

const displayName = computed(() => (
  authState.user?.display_name || authState.user?.username || 'Administrator'
))

const initials = computed(() => displayName.value
  .split(/\s+/)
  .slice(0, 2)
  .map((part) => part[0]?.toUpperCase() || '')
  .join(''))
</script>

<style scoped>
.admin-layout {
  display: grid;
  grid-template-columns: 216px minmax(0, 1fr);
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  background: var(--surface-0);
}

.admin-sidebar {
  display: flex;
  min-width: 0;
  flex-direction: column;
  padding: 20px 14px 14px;
  border-right: 1px solid var(--border-color-light);
  background: var(--surface-1);
}

.admin-sidebar__heading,
.admin-sidebar__account {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 10px;
}

.admin-sidebar__heading {
  min-height: 42px;
  padding: 0 8px;
  margin-bottom: 20px;
}

.admin-sidebar__mark,
.admin-sidebar__avatar {
  display: grid;
  flex: 0 0 auto;
  place-items: center;
}

.admin-sidebar__mark {
  width: 32px;
  height: 32px;
  border: 1px solid var(--primary-200);
  border-radius: var(--radius-base);
  background: var(--primary-50);
  color: var(--primary-700);
}

.admin-sidebar__title,
.admin-sidebar__identity {
  display: grid;
  min-width: 0;
  line-height: 1.25;
}

.admin-sidebar__title strong {
  color: var(--gray-900);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.admin-sidebar__title small,
.admin-sidebar__identity small {
  margin-top: 3px;
  overflow: hidden;
  color: var(--gray-500);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.admin-sidebar__account {
  margin-top: auto;
  padding: 14px 8px 2px;
  border-top: 1px solid var(--border-color-light);
}

.admin-sidebar__avatar {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-full);
  background: var(--surface-2);
  color: var(--gray-700);
  font-size: 11px;
  font-weight: var(--font-semibold);
}

.admin-sidebar__identity strong {
  overflow: hidden;
  color: var(--gray-800);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.admin-content {
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.admin-content__inner {
  width: min(1080px, calc(100% - 48px));
  margin: 0 auto;
  padding: 30px 0 52px;
}

@media (max-width: 760px) {
  .admin-layout {
    grid-template-columns: minmax(0, 1fr);
    grid-template-rows: auto minmax(0, 1fr);
  }

  .admin-sidebar {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    align-items: center;
    gap: 12px;
    padding: 10px 12px;
    border-right: 0;
    border-bottom: 1px solid var(--border-color-light);
  }

  .admin-sidebar__heading {
    min-height: 36px;
    padding: 0;
    margin: 0;
  }

  .admin-sidebar__mark {
    width: 30px;
    height: 30px;
  }

  .admin-sidebar__title small,
  .admin-sidebar__account {
    display: none;
  }

  .admin-content__inner {
    width: min(100% - 28px, 1080px);
    padding: 22px 0 40px;
  }
}

@media (max-width: 520px) {
  .admin-sidebar {
    display: block;
    padding: 9px 10px 10px;
  }

  .admin-sidebar__heading {
    display: none;
  }

  .admin-content__inner {
    width: min(100% - 20px, 1080px);
    padding-top: 18px;
  }
}
</style>
