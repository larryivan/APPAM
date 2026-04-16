<template>
  <div class="admin-users">
    <div class="admin-users__shell">
      <header class="admin-users__header">
        <div>
          <span class="admin-users__label">Administration</span>
          <h1>User Management</h1>
          <p>Manage account state, role assignments, password resets, and deletion impact.</p>
        </div>
        <div class="admin-users__stats">
          <span v-for="item in summaryStats" :key="item.label" class="admin-users__stat">
            <strong>{{ item.value }}</strong>
            <span>{{ item.label }}</span>
          </span>
        </div>
      </header>

      <section class="admin-users__toolbar">
        <div class="admin-users__search">
          <input
            v-model.trim="searchQuery"
            type="search"
            placeholder="Search username or display name"
            @input="fetchUsers"
          />
        </div>
        <span class="admin-users__count">{{ users.length }} visible</span>
      </section>

      <p v-if="pageMessage" :class="['admin-users__message', `admin-users__message--${pageMessage.type}`]">{{ pageMessage.text }}</p>

      <section class="admin-users__table-card">
        <table class="admin-users__table">
          <thead>
            <tr>
              <th>User</th>
              <th>Role</th>
              <th>Status</th>
              <th>Projects</th>
              <th>Last Login</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id">
              <td>
                <div class="admin-users__user">
                  <div class="admin-users__avatar">{{ getInitials(user) }}</div>
                  <div>
                    <strong>{{ user.display_name || user.username }}</strong>
                    <span>@{{ user.username }}</span>
                  </div>
                </div>
              </td>
              <td>
                <select class="admin-users__select" :value="user.role" @change="updateUser(user, { role: $event.target.value })">
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                </select>
              </td>
              <td>
                <span class="admin-users__status" :class="`admin-users__status--${user.status}`">{{ user.status }}</span>
              </td>
              <td class="admin-users__projects">
                <span>{{ user.owned_projects_count || 0 }} owned</span>
                <span>{{ user.member_projects_count || 0 }} shared</span>
              </td>
              <td class="admin-users__muted">{{ formatDate(user.last_login_at) }}</td>
              <td>
                <div class="admin-users__actions">
                  <button class="admin-users__button admin-users__button--subtle" type="button" @click="openUserDetails(user)">Details</button>
                  <button class="admin-users__button admin-users__button--subtle" type="button" @click="toggleUserStatus(user)">
                    {{ user.status === 'active' ? 'Disable' : 'Enable' }}
                  </button>
                  <button class="admin-users__button admin-users__button--danger" type="button" @click="deleteUser(user)">Delete</button>
                </div>
              </td>
            </tr>
            <tr v-if="!users.length">
              <td colspan="6" class="admin-users__empty">No matching users.</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>

    <div v-if="detailOpen" class="admin-users__overlay app-modal-viewport app-modal-backdrop" @click="closeDetails">
      <div class="admin-users__modal app-modal" @click.stop>
        <div class="app-modal-header admin-users__modal-header">
          <div>
            <span class="admin-users__label">Account Detail</span>
            <h3>{{ selectedUser?.display_name || selectedUser?.username || 'User' }}</h3>
            <p v-if="selectedUser" class="admin-users__muted">@{{ selectedUser.username }}</p>
          </div>
          <button @click="closeDetails" class="close-btn app-modal-close">×</button>
        </div>

        <div class="app-modal-body admin-users__modal-body">
          <p v-if="detailLoading" class="admin-users__muted">Loading account details...</p>

          <template v-else-if="selectedUser">
            <div class="admin-users__summary">
              <div class="admin-users__summary-item">
                <span>Role</span>
                <strong>{{ selectedUser.role }}</strong>
              </div>
              <div class="admin-users__summary-item">
                <span>Status</span>
                <strong>{{ selectedUser.status }}</strong>
              </div>
              <div class="admin-users__summary-item">
                <span>Owned Projects</span>
                <strong>{{ selectedImpact?.owned_projects_count || 0 }}</strong>
              </div>
              <div class="admin-users__summary-item">
                <span>Shared Projects</span>
                <strong>{{ selectedImpact?.member_projects_count || 0 }}</strong>
              </div>
            </div>

            <div v-if="selectedImpact?.warnings?.length" class="admin-users__impact">
              <strong>Impact Warning</strong>
              <ul>
                <li v-for="warning in selectedImpact.warnings" :key="warning">{{ warning }}</li>
              </ul>
            </div>

            <div v-if="resetPasswordResult" class="admin-users__password">
              <strong>Temporary Password</strong>
              <code>{{ resetPasswordResult }}</code>
              <p>This value is shown once. Share it securely with the user.</p>
            </div>

            <div class="admin-users__actions admin-users__actions--detail">
              <button class="admin-users__button admin-users__button--solid" type="button" @click="resetPassword(selectedUser)">Reset Password</button>
              <button class="admin-users__button admin-users__button--subtle" type="button" @click="toggleUserStatus(selectedUser)">
                {{ selectedUser.status === 'active' ? 'Disable User' : 'Enable User' }}
              </button>
              <button class="admin-users__button admin-users__button--danger" type="button" @click="deleteUser(selectedUser)">Delete User</button>
            </div>

            <div class="admin-users__sections">
              <section class="admin-users__section">
                <h4>Owned Projects</h4>
                <div v-if="selectedImpact?.owned_projects?.length" class="admin-users__list">
                  <article v-for="project in selectedImpact.owned_projects" :key="project.id">
                    <strong>{{ project.name }}</strong>
                    <span>{{ formatDate(project.last_accessed) }}</span>
                  </article>
                </div>
                <p v-else class="admin-users__muted">This user does not own any projects.</p>
              </section>

              <section class="admin-users__section">
                <h4>Shared Projects</h4>
                <div v-if="selectedImpact?.member_projects?.length" class="admin-users__list">
                  <article v-for="project in selectedImpact.member_projects" :key="project.id">
                    <strong>{{ project.name }}</strong>
                    <span>{{ project.project_role }}</span>
                  </article>
                </div>
                <p v-else class="admin-users__muted">This user is not a member of any shared projects.</p>
              </section>

              <section class="admin-users__section">
                <h4>Active Jobs</h4>
                <div v-if="selectedImpact?.active_jobs?.length" class="admin-users__list">
                  <article v-for="job in selectedImpact.active_jobs" :key="job.id">
                    <strong>{{ job.tool_name }}</strong>
                    <span>{{ job.status }}</span>
                  </article>
                </div>
                <p v-else class="admin-users__muted">No queued or running jobs.</p>
              </section>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { authState, setCurrentUser } from '../lib/auth'

const users = ref([])
const searchQuery = ref('')
const pageMessage = ref(null)
const detailOpen = ref(false)
const detailLoading = ref(false)
const selectedUser = ref(null)
const selectedImpact = ref(null)
const resetPasswordResult = ref('')

const summaryStats = computed(() => {
  const total = users.value.length
  const admins = users.value.filter((user) => user.role === 'admin').length
  const disabled = users.value.filter((user) => user.status === 'disabled').length
  const withProjects = users.value.filter((user) => (user.owned_projects_count || 0) + (user.member_projects_count || 0) > 0).length
  return [
    { label: 'Total', value: total },
    { label: 'Admins', value: admins },
    { label: 'Disabled', value: disabled },
    { label: 'With Projects', value: withProjects },
  ]
})

const fetchUsers = async () => {
  try {
    const response = await fetch(`/api/admin/users?search=${encodeURIComponent(searchQuery.value)}`)
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload?.error || 'Failed to load users.')
    }
    users.value = payload.users || []
  } catch (error) {
    pageMessage.value = { type: 'error', text: error.message || 'Failed to load users.' }
  }
}

const syncUserInList = (user) => {
  const index = users.value.findIndex((entry) => entry.id === user.id)
  if (index !== -1) {
    users.value[index] = {
      ...users.value[index],
      ...user,
    }
  }
}

const fetchUserDetails = async (userId) => {
  detailLoading.value = true
  try {
    const response = await fetch(`/api/admin/users/${userId}`)
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload?.error || 'Failed to load user details.')
    }
    selectedUser.value = payload.user
    selectedImpact.value = payload.impact
    resetPasswordResult.value = ''
    syncUserInList(payload.user)
    return payload
  } finally {
    detailLoading.value = false
  }
}

const openUserDetails = async (user) => {
  detailOpen.value = true
  pageMessage.value = null
  try {
    await fetchUserDetails(user.id)
  } catch (error) {
    pageMessage.value = { type: 'error', text: error.message || 'Failed to load user details.' }
  }
}

const closeDetails = () => {
  detailOpen.value = false
  selectedUser.value = null
  selectedImpact.value = null
  resetPasswordResult.value = ''
}

const updateUser = async (user, patch) => {
  pageMessage.value = null
  try {
    const response = await fetch(`/api/admin/users/${user.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload?.error || 'Failed to update user.')
    }

    syncUserInList(payload.user)
    if (selectedUser.value?.id === payload.user.id) {
      selectedUser.value = payload.user
      if (selectedImpact.value) {
        const details = await fetchUserDetails(payload.user.id)
        selectedImpact.value = details.impact
      }
    }
    if (payload.user?.id === authState.user?.id) {
      setCurrentUser(payload.user)
    }
    pageMessage.value = { type: 'success', text: `Updated ${payload.user.username}.` }
  } catch (error) {
    pageMessage.value = { type: 'error', text: error.message || 'Failed to update user.' }
    await fetchUsers()
  }
}

const buildImpactText = (user, impact, actionLabel) => {
  const lines = [`${actionLabel} ${user.display_name || user.username}?`]
  if (impact?.warnings?.length) {
    lines.push('')
    lines.push(...impact.warnings)
  }
  if (impact?.owned_projects?.length) {
    lines.push('')
    lines.push(`Owned projects: ${impact.owned_projects.map((project) => project.name).join(', ')}`)
  }
  return lines.join('\n')
}

const ensureImpactLoaded = async (user) => {
  if (selectedUser.value?.id === user.id && selectedImpact.value) {
    return { user: selectedUser.value, impact: selectedImpact.value }
  }
  return fetchUserDetails(user.id)
}

const toggleUserStatus = async (user) => {
  pageMessage.value = null
  try {
    const details = await ensureImpactLoaded(user)
    const nextStatus = details.user.status === 'active' ? 'disabled' : 'active'
    if (nextStatus === 'disabled') {
      const confirmed = window.confirm(buildImpactText(details.user, details.impact, 'Disable'))
      if (!confirmed) return
    }
    await updateUser(details.user, { status: nextStatus })
  } catch (error) {
    pageMessage.value = { type: 'error', text: error.message || 'Failed to update user status.' }
  }
}

const resetPassword = async (user) => {
  pageMessage.value = null
  resetPasswordResult.value = ''
  const confirmed = window.confirm(`Reset the password for ${user.display_name || user.username}?`)
  if (!confirmed) return

  try {
    const response = await fetch(`/api/admin/users/${user.id}/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload?.error || 'Failed to reset password.')
    }
    syncUserInList(payload.user)
    if (selectedUser.value?.id === payload.user.id) {
      selectedUser.value = payload.user
    }
    resetPasswordResult.value = payload.temporary_password
    pageMessage.value = { type: 'success', text: `Password reset for ${payload.user.username}.` }
  } catch (error) {
    pageMessage.value = { type: 'error', text: error.message || 'Failed to reset password.' }
  }
}

const deleteUser = async (user) => {
  pageMessage.value = null
  try {
    const details = await ensureImpactLoaded(user)
    if (!details.impact?.can_delete) {
      detailOpen.value = true
      pageMessage.value = { type: 'error', text: 'Transfer or remove owned projects before deleting this user.' }
      return
    }

    const confirmed = window.confirm(buildImpactText(details.user, details.impact, 'Delete'))
    if (!confirmed) return

    const response = await fetch(`/api/admin/users/${details.user.id}`, {
      method: 'DELETE',
    })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload?.error || 'Failed to delete user.')
    }

    users.value = users.value.filter((entry) => entry.id !== details.user.id)
    if (selectedUser.value?.id === details.user.id) {
      closeDetails()
    }
    pageMessage.value = { type: 'success', text: `Deleted ${payload.user.username}.` }
  } catch (error) {
    pageMessage.value = { type: 'error', text: error.message || 'Failed to delete user.' }
  }
}

const getInitials = (user) => {
  const source = (user?.display_name || user?.username || 'A').trim()
  return source
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || '')
    .join('')
}

const formatDate = (dateString) => {
  if (!dateString) return 'Never'
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

onMounted(() => {
  fetchUsers()
})
</script>
