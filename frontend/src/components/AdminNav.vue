<template>
  <nav class="admin-nav" aria-label="Administration">
    <router-link v-for="item in items" :key="item.to" :to="item.to" :class="{ active: isActive(item) }">
      <Icon :name="item.icon" :size="17" />
      <span>
        <strong>{{ item.label }}</strong>
        <small>{{ item.description }}</small>
      </span>
    </router-link>
  </nav>
</template>

<script setup>
import { useRoute } from 'vue-router'

import Icon from './ui/Icon.vue'

const route = useRoute()
const items = [
  { to: '/admin', label: 'System', description: 'Runtime and setup', icon: 'wrench', exact: true },
  { to: '/admin/users', label: 'Users', description: 'Accounts and access', icon: 'users' },
  { to: '/admin/worker', label: 'Queue', description: 'Worker and jobs', icon: 'activity' },
]

function isActive(item) {
  return item.exact ? route.path === item.to : route.path.startsWith(item.to)
}
</script>

<style scoped>
.admin-nav {
  display: grid;
  gap: 3px;
}

.admin-nav a {
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  align-items: center;
  gap: 8px;
  min-height: 50px;
  padding: 7px 10px;
  border-radius: var(--radius-base);
  color: var(--gray-600);
  text-decoration: none;
  transition: background-color var(--transition-fast), color var(--transition-fast);
}

.admin-nav a:hover {
  background: var(--surface-2);
  color: var(--gray-900);
}

.admin-nav a.active {
  color: var(--primary-700);
  background: var(--primary-50);
}

.admin-nav a > span {
  display: grid;
  min-width: 0;
}

.admin-nav strong {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.admin-nav small {
  margin-top: 2px;
  color: var(--gray-500);
  font-size: 11px;
}

@media (max-width: 760px) {
  .admin-nav {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .admin-nav a {
    display: flex;
    justify-content: center;
    min-height: 36px;
    padding: 0 9px;
  }

  .admin-nav a > span {
    display: block;
  }

  .admin-nav small {
    display: none;
  }
}

@media (max-width: 420px) {
  .admin-nav a {
    gap: 5px;
    padding-inline: 6px;
  }
}
</style>
