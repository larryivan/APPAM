<template>
  <nav class="admin-nav" aria-label="Administration">
    <router-link to="/admin" :class="{ active: active === 'setup' }">
      <Icon name="wrench" :size="16" />
      Setup
    </router-link>
    <router-link to="/admin/users" :class="{ active: active === 'users' }">
      <Icon name="users" :size="16" />
      Users
    </router-link>
    <router-link to="/admin/worker" :class="{ active: active === 'worker' }">
      <Icon name="activity" :size="16" />
      Worker
    </router-link>
  </nav>
</template>

<script setup>
import Icon from './ui/Icon.vue'

defineProps({
  active: {
    type: String,
    required: true,
  },
})
</script>

<style scoped>
.admin-nav {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  margin-bottom: 24px;
  border: 1px solid var(--border-color);
  border-radius: 6px;
  background: var(--surface-2);
}

.admin-nav a {
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 0 13px;
  border-radius: 4px;
  color: var(--gray-600);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  text-decoration: none;
}

.admin-nav a:hover {
  color: var(--gray-900);
}

.admin-nav a.active {
  color: var(--primary-700);
  background: var(--surface-1);
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}

@media (max-width: 520px) {
  .admin-nav {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    width: 100%;
  }

  .admin-nav a {
    justify-content: center;
    padding: 0 8px;
  }
}
</style>
