<template>
  <div class="users-admin">
    <PageHeader title="Users" description="Accounts, roles, and project access">
      <template #meta>
        <span>{{ userSummary }}</span>
      </template>
      <template #actions>
        <button class="btn btn-primary" type="button" @click="openCreatePanel">
          <Icon name="plus" :size="16" />
          Add user
        </button>
      </template>
    </PageHeader>

    <div v-if="pageMessage" :class="['users-message', `users-message--${pageMessage.type}`]" role="status">
      <Icon :name="pageMessage.type === 'success' ? 'circle-check' : 'circle-x'" :size="17" />
      <span>{{ pageMessage.text }}</span>
      <button type="button" title="Dismiss" aria-label="Dismiss" @click="pageMessage = null">
        <Icon name="x" :size="15" />
      </button>
    </div>

    <section class="users-toolbar">
      <label class="users-search">
        <Icon name="search" :size="16" />
        <input
          v-model.trim="searchQuery"
          type="search"
          placeholder="Search users"
          aria-label="Search users"
          @input="scheduleFetchUsers"
        />
      </label>
      <span>{{ loading ? 'Loading' : `${users.length} shown` }}</span>
    </section>

    <section class="users-table-wrap" aria-label="User accounts">
      <table class="users-table">
        <thead>
          <tr>
            <th>User</th>
            <th>Access</th>
            <th>Projects</th>
            <th>Last sign-in</th>
            <th><span class="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading && !users.length" v-for="index in 3" :key="`loading-${index}`" class="users-table__loading">
            <td colspan="5"><span></span></td>
          </tr>
          <tr v-for="user in users" :key="user.id" :class="{ 'is-disabled': user.status === 'disabled' }">
            <td>
              <button class="user-identity" type="button" @click="openUserPanel(user)">
                <span class="user-avatar">{{ getInitials(user) }}</span>
                <span class="user-name">
                  <strong>{{ user.display_name || user.username }}</strong>
                  <small>@{{ user.username }}</small>
                </span>
              </button>
            </td>
            <td>
              <span class="access-line">
                <span class="pill" :class="user.role === 'admin' ? 'pill--info' : 'pill--muted'">
                  {{ user.role === 'admin' ? 'Admin' : 'User' }}
                </span>
                <span v-if="user.status === 'disabled'" class="pill pill--danger">Disabled</span>
              </span>
            </td>
            <td>
              <span class="project-count">
                <strong>{{ (user.owned_projects_count || 0) + (user.member_projects_count || 0) }}</strong>
                <small>{{ user.owned_projects_count || 0 }} owned</small>
              </span>
            </td>
            <td class="users-table__muted">{{ formatDate(user.last_login_at) }}</td>
            <td class="users-table__action">
              <button type="button" title="Manage user" :aria-label="`Manage ${user.username}`" @click="openUserPanel(user)">
                <Icon name="chevron-right" :size="17" />
              </button>
            </td>
          </tr>
          <tr v-if="!loading && !users.length">
            <td colspan="5" class="users-empty">
              <Icon name="users" :size="20" />
              <strong>No users found</strong>
              <span>Try a different search.</span>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <SidePanel
      :open="panelMode === 'create'"
      title="Add user"
      eyebrow="New account"
      title-id="create-user-title"
      @close="closePanel"
    >
      <template #subtitle>
        <span class="side-panel-subtitle">Create an account and set its initial access level</span>
      </template>

      <form id="create-user-form" class="panel-form" @submit.prevent="createUser">
        <label class="panel-field">
          <span>Username</span>
          <input v-model.trim="createForm.username" class="input" type="text" autocomplete="off" required minlength="3" maxlength="32" placeholder="e.g. jsmith" />
          <small>3-32 letters, numbers, dots, underscores, or hyphens</small>
        </label>
        <label class="panel-field">
          <span>Display name <small>Optional</small></span>
          <input v-model.trim="createForm.display_name" class="input" type="text" maxlength="80" placeholder="Jane Smith" />
        </label>
        <label class="panel-field">
          <span>Initial password</span>
          <div class="password-input">
            <input v-model="createForm.password" class="input" :type="showCreatePassword ? 'text' : 'password'" autocomplete="new-password" required minlength="8" />
            <button type="button" :title="showCreatePassword ? 'Hide password' : 'Show password'" :aria-label="showCreatePassword ? 'Hide password' : 'Show password'" @click="showCreatePassword = !showCreatePassword">
              <Icon :name="showCreatePassword ? 'eye-off' : 'eye'" :size="16" />
            </button>
          </div>
        </label>
        <label class="panel-field">
          <span>Role</span>
          <select v-model="createForm.role" class="input">
            <option value="user">User</option>
            <option value="admin">Administrator</option>
          </select>
          <small>Administrators can manage users, runtime settings, and project terminals.</small>
        </label>

        <p v-if="panelError" class="panel-error" role="alert">{{ panelError }}</p>
      </form>

      <template #footer>
        <button class="btn btn-secondary" type="button" @click="closePanel">Cancel</button>
        <button class="btn btn-primary" type="submit" form="create-user-form" :disabled="panelSubmitting">
          {{ panelSubmitting ? 'Creating' : 'Create user' }}
        </button>
      </template>
    </SidePanel>

    <SidePanel
      :open="panelMode === 'manage'"
      :title="selectedUser?.display_name || selectedUser?.username || 'User'"
      eyebrow="Account"
      title-id="manage-user-title"
      @close="closePanel"
    >
      <template #subtitle>
        <span v-if="selectedUser" class="side-panel-subtitle">@{{ selectedUser.username }}</span>
      </template>

      <div v-if="detailLoading" class="panel-loading" aria-label="Loading account details">
        <span></span><span></span><span></span>
      </div>

      <template v-else-if="selectedUser">
        <section class="account-overview">
          <div>
            <span>Role</span>
            <strong>{{ selectedUser.role === 'admin' ? 'Administrator' : 'User' }}</strong>
          </div>
          <div>
            <span>Status</span>
            <strong :class="selectedUser.status === 'active' ? 'status-text--success' : 'status-text--danger'">
              {{ selectedUser.status === 'active' ? 'Active' : 'Disabled' }}
            </strong>
          </div>
          <div>
            <span>Projects</span>
            <strong>{{ projectTotal(selectedUser) }}</strong>
          </div>
        </section>

        <section class="panel-section">
          <header>
            <h3>Access</h3>
            <span>Changes apply immediately</span>
          </header>
          <label class="panel-field panel-field--compact">
            <span>Role</span>
            <select
              class="input"
              :value="selectedUser.role"
              :disabled="panelSubmitting"
              @change="updateUser(selectedUser, { role: $event.target.value })"
            >
              <option value="user">User</option>
              <option value="admin">Administrator</option>
            </select>
          </label>
          <button class="settings-row" type="button" :disabled="panelSubmitting" @click="requestStatusChange(selectedUser)">
            <span>
              <strong>{{ selectedUser.status === 'active' ? 'Disable account' : 'Enable account' }}</strong>
              <small>{{ selectedUser.status === 'active' ? 'Prevents sign-in and closes privileged sessions' : 'Restores access to existing projects' }}</small>
            </span>
            <Icon name="chevron-right" :size="17" />
          </button>
        </section>

        <section class="panel-section">
          <header>
            <h3>Security</h3>
          </header>
          <button class="settings-row" type="button" :disabled="panelSubmitting" @click="requestPasswordReset(selectedUser)">
            <span>
              <strong>Reset password</strong>
              <small>Generate a one-time temporary password</small>
            </span>
            <Icon name="key-round" :size="17" />
          </button>
          <div v-if="resetPasswordResult" class="temporary-password">
            <span>Temporary password</span>
            <div>
              <code>{{ resetPasswordResult }}</code>
              <button type="button" :title="passwordCopied ? 'Copied' : 'Copy password'" :aria-label="passwordCopied ? 'Copied' : 'Copy password'" @click="copyPassword">
                <Icon :name="passwordCopied ? 'check' : 'copy'" :size="16" />
              </button>
            </div>
            <small>Shown only in this panel. Share it securely.</small>
          </div>
        </section>

        <section class="panel-section">
          <header>
            <h3>Activity</h3>
          </header>
          <dl class="activity-list">
            <div><dt>Last sign-in</dt><dd>{{ formatDate(selectedUser.last_login_at) }}</dd></div>
            <div><dt>Owned projects</dt><dd>{{ selectedImpact?.owned_projects_count || 0 }}</dd></div>
            <div><dt>Shared projects</dt><dd>{{ selectedImpact?.member_projects_count || 0 }}</dd></div>
            <div><dt>Active jobs</dt><dd>{{ selectedImpact?.active_jobs_count || 0 }}</dd></div>
          </dl>
          <details v-if="projectTotal(selectedUser)" class="project-details">
            <summary>
              View project access
              <Icon name="chevron-down" :size="15" />
            </summary>
            <div>
              <article v-for="project in selectedImpact?.owned_projects || []" :key="`owned-${project.id}`">
                <strong>{{ project.name }}</strong><span>Owner</span>
              </article>
              <article v-for="project in selectedImpact?.member_projects || []" :key="`member-${project.id}`">
                <strong>{{ project.name }}</strong><span>{{ project.project_role }}</span>
              </article>
            </div>
          </details>
        </section>

        <section class="panel-section panel-section--danger">
          <header><h3>Danger zone</h3></header>
          <button class="settings-row settings-row--danger" type="button" :disabled="panelSubmitting || selectedUser.id === authState.user?.id" @click="requestDelete(selectedUser)">
            <span>
              <strong>Delete account</strong>
              <small v-if="selectedUser.id === authState.user?.id">You cannot delete your own account</small>
              <small v-else-if="selectedImpact?.can_delete">Permanently removes this account</small>
              <small v-else>Transfer owned projects before deletion</small>
            </span>
            <Icon name="trash-2" :size="17" />
          </button>
        </section>

        <p v-if="panelError" class="panel-error" role="alert">{{ panelError }}</p>
      </template>
    </SidePanel>

    <div v-if="confirmation" class="confirm-layer app-modal-viewport app-modal-backdrop" @mousedown.self="confirmation = null">
      <div class="confirm-dialog app-modal" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title">
        <div class="confirm-dialog__icon" :class="`confirm-dialog__icon--${confirmation.tone}`">
          <Icon :name="confirmation.icon" :size="20" />
        </div>
        <h2 id="confirm-title">{{ confirmation.title }}</h2>
        <p>{{ confirmation.message }}</p>
        <ul v-if="confirmation.warnings?.length">
          <li v-for="warning in confirmation.warnings" :key="warning">{{ warning }}</li>
        </ul>
        <div class="confirm-dialog__actions">
          <button class="btn btn-secondary" type="button" @click="confirmation = null">Cancel</button>
          <button :class="['btn', confirmation.tone === 'danger' ? 'btn-danger' : 'btn-primary']" type="button" :disabled="panelSubmitting" @click="runConfirmation">
            {{ panelSubmitting ? 'Working' : confirmation.confirmLabel }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'

import Icon from '../components/ui/Icon.vue'
import PageHeader from '../components/ui/PageHeader.vue'
import SidePanel from '../components/ui/SidePanel.vue'
import { authState, setCurrentUser } from '../lib/auth'

const users = ref([])
const searchQuery = ref('')
const loading = ref(false)
const pageMessage = ref(null)
const panelMode = ref('')
const panelSubmitting = ref(false)
const panelError = ref('')
const detailLoading = ref(false)
const selectedUser = ref(null)
const selectedImpact = ref(null)
const resetPasswordResult = ref('')
const showCreatePassword = ref(false)
const passwordCopied = ref(false)
const confirmation = ref(null)
let searchTimer = null
let copiedTimer = null

const createForm = reactive({
  username: '',
  display_name: '',
  password: '',
  role: 'user',
})

const userSummary = computed(() => {
  const admins = users.value.filter((user) => user.role === 'admin' && user.status === 'active').length
  const disabled = users.value.filter((user) => user.status === 'disabled').length
  const parts = [`${users.value.length} account${users.value.length === 1 ? '' : 's'}`, `${admins} admin${admins === 1 ? '' : 's'}`]
  if (disabled) parts.push(`${disabled} disabled`)
  return parts.join(' · ')
})

function resetCreateForm() {
  Object.assign(createForm, { username: '', display_name: '', password: '', role: 'user' })
  showCreatePassword.value = false
}

function openCreatePanel() {
  resetCreateForm()
  panelError.value = ''
  panelMode.value = 'create'
}

async function openUserPanel(user) {
  panelMode.value = 'manage'
  selectedUser.value = user
  selectedImpact.value = null
  resetPasswordResult.value = ''
  panelError.value = ''
  await fetchUserDetails(user.id)
}

function closePanel() {
  if (panelSubmitting.value) return
  panelMode.value = ''
  selectedUser.value = null
  selectedImpact.value = null
  resetPasswordResult.value = ''
  panelError.value = ''
}

function showPageMessage(type, text) {
  pageMessage.value = { type, text }
}

async function fetchUsers() {
  loading.value = true
  try {
    const response = await fetch(`/api/admin/users?search=${encodeURIComponent(searchQuery.value)}`)
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(payload.error || 'Failed to load users.')
    users.value = payload.users || []
  } catch (error) {
    showPageMessage('error', error.message || 'Failed to load users.')
  } finally {
    loading.value = false
  }
}

function scheduleFetchUsers() {
  window.clearTimeout(searchTimer)
  searchTimer = window.setTimeout(fetchUsers, 220)
}

function syncUserInList(user) {
  const index = users.value.findIndex((entry) => entry.id === user.id)
  if (index !== -1) users.value[index] = { ...users.value[index], ...user }
}

async function fetchUserDetails(userId) {
  detailLoading.value = true
  panelError.value = ''
  try {
    const response = await fetch(`/api/admin/users/${userId}`)
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(payload.error || 'Failed to load account details.')
    selectedUser.value = payload.user
    selectedImpact.value = payload.impact
    syncUserInList(payload.user)
  } catch (error) {
    panelError.value = error.message || 'Failed to load account details.'
  } finally {
    detailLoading.value = false
  }
}

async function createUser() {
  panelSubmitting.value = true
  panelError.value = ''
  try {
    const response = await fetch('/api/admin/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(createForm),
    })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(payload.error || 'Failed to create user.')
    closePanelAfterSubmit()
    await fetchUsers()
    showPageMessage('success', `Created ${payload.user.username}.`)
  } catch (error) {
    panelError.value = error.message || 'Failed to create user.'
  } finally {
    panelSubmitting.value = false
  }
}

function closePanelAfterSubmit() {
  panelMode.value = ''
  selectedUser.value = null
  selectedImpact.value = null
  resetPasswordResult.value = ''
}

async function updateUser(user, patch) {
  panelSubmitting.value = true
  panelError.value = ''
  try {
    const response = await fetch(`/api/admin/users/${user.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(payload.error || 'Failed to update user.')
    syncUserInList(payload.user)
    selectedUser.value = { ...selectedUser.value, ...payload.user }
    if (payload.user.id === authState.user?.id) setCurrentUser(payload.user)
    await fetchUserDetails(payload.user.id)
    showPageMessage('success', `Updated ${payload.user.username}.`)
  } catch (error) {
    panelError.value = error.message || 'Failed to update user.'
    await fetchUsers()
  } finally {
    panelSubmitting.value = false
  }
}

function requestStatusChange(user) {
  const disabling = user.status === 'active'
  confirmation.value = {
    type: 'status',
    title: disabling ? 'Disable this account?' : 'Enable this account?',
    message: disabling
      ? `${user.display_name || user.username} will be signed out and unable to access APPAM.`
      : `${user.display_name || user.username} will regain access to existing projects.`,
    warnings: disabling ? selectedImpact.value?.warnings || [] : [],
    confirmLabel: disabling ? 'Disable account' : 'Enable account',
    tone: disabling ? 'danger' : 'primary',
    icon: disabling ? 'triangle-alert' : 'circle-check',
    run: () => updateUser(user, { status: disabling ? 'disabled' : 'active' }),
  }
}

function requestPasswordReset(user) {
  confirmation.value = {
    type: 'password',
    title: 'Reset this password?',
    message: `The current password for ${user.display_name || user.username} will stop working immediately.`,
    confirmLabel: 'Reset password',
    tone: 'primary',
    icon: 'key-round',
    run: () => resetPassword(user),
  }
}

function requestDelete(user) {
  if (!selectedImpact.value?.can_delete) {
    panelError.value = 'Transfer or remove owned projects before deleting this account.'
    return
  }
  confirmation.value = {
    type: 'delete',
    title: 'Delete this account?',
    message: `${user.display_name || user.username} will be permanently removed. This cannot be undone.`,
    warnings: selectedImpact.value?.warnings || [],
    confirmLabel: 'Delete account',
    tone: 'danger',
    icon: 'trash-2',
    run: () => deleteUser(user),
  }
}

async function runConfirmation() {
  const action = confirmation.value?.run
  confirmation.value = null
  if (action) await action()
}

async function resetPassword(user) {
  panelSubmitting.value = true
  panelError.value = ''
  resetPasswordResult.value = ''
  try {
    const response = await fetch(`/api/admin/users/${user.id}/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(payload.error || 'Failed to reset password.')
    resetPasswordResult.value = payload.temporary_password
    syncUserInList(payload.user)
    showPageMessage('success', `Password reset for ${payload.user.username}.`)
  } catch (error) {
    panelError.value = error.message || 'Failed to reset password.'
  } finally {
    panelSubmitting.value = false
  }
}

async function deleteUser(user) {
  panelSubmitting.value = true
  panelError.value = ''
  try {
    const response = await fetch(`/api/admin/users/${user.id}`, { method: 'DELETE' })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(payload.error || 'Failed to delete user.')
    users.value = users.value.filter((entry) => entry.id !== user.id)
    closePanelAfterSubmit()
    showPageMessage('success', `Deleted ${payload.user.username}.`)
  } catch (error) {
    panelError.value = error.message || 'Failed to delete user.'
  } finally {
    panelSubmitting.value = false
  }
}

async function copyPassword() {
  try {
    await navigator.clipboard.writeText(resetPasswordResult.value)
    passwordCopied.value = true
    window.clearTimeout(copiedTimer)
    copiedTimer = window.setTimeout(() => { passwordCopied.value = false }, 1800)
  } catch {
    passwordCopied.value = false
  }
}

function projectTotal(user) {
  return (user?.owned_projects_count || selectedImpact.value?.owned_projects_count || 0)
    + (user?.member_projects_count || selectedImpact.value?.member_projects_count || 0)
}

function getInitials(user) {
  return (user?.display_name || user?.username || 'A')
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || '')
    .join('')
}

function formatDate(dateString) {
  if (!dateString) return 'Never'
  const date = new Date(String(dateString).replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return dateString
  return new Intl.DateTimeFormat('en', {
    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
  }).format(date)
}

onMounted(fetchUsers)
onBeforeUnmount(() => {
  window.clearTimeout(searchTimer)
  window.clearTimeout(copiedTimer)
})
</script>

<style scoped>
.users-admin {
  min-width: 0;
}

.users-message {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr) 28px;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 7px 8px 7px 11px;
  margin-bottom: 14px;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-base);
  font-size: var(--text-xs);
}

.users-message--success { border-color: #c9e7d8; background: var(--success-50); color: var(--success-600); }
.users-message--error { border-color: #f0c7c3; background: var(--error-50); color: var(--error-600); }

.users-message button {
  display: grid;
  width: 28px;
  height: 28px;
  place-items: center;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.users-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin: 20px 0 12px;
}

.users-toolbar > span {
  flex: 0 0 auto;
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.users-search {
  display: grid;
  grid-template-columns: 20px minmax(0, 1fr);
  align-items: center;
  width: min(340px, 100%);
  min-height: var(--control-height);
  padding: 0 9px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-base);
  background: var(--surface-1);
  color: var(--gray-400);
}

.users-search:focus-within {
  border-color: var(--primary-500);
  box-shadow: 0 0 0 2px rgb(var(--accent-rgb) / 0.1);
}

.users-search input {
  width: 100%;
  min-width: 0;
  height: 34px;
  padding: 0 3px;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--gray-900);
  font-size: var(--text-sm);
}

.users-search input::placeholder {
  color: var(--gray-400);
}

.users-table-wrap {
  min-width: 0;
  overflow-x: auto;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-md);
  background: var(--surface-1);
}

.users-table {
  width: 100%;
  min-width: 720px;
  border-collapse: collapse;
}

.users-table th,
.users-table td {
  padding: 11px 14px;
  border-bottom: 1px solid var(--border-color-light);
  text-align: left;
  vertical-align: middle;
}

.users-table tr:last-child td {
  border-bottom: 0;
}

.users-table th {
  height: 38px;
  background: var(--gray-50);
  color: var(--gray-500);
  font-size: 11px;
  font-weight: var(--font-medium);
}

.users-table tbody tr:not(.users-table__loading):hover {
  background: var(--gray-50);
}

.users-table tbody tr.is-disabled {
  opacity: 0.68;
}

.user-identity {
  display: flex;
  width: 100%;
  min-width: 0;
  align-items: center;
  gap: 10px;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.user-avatar {
  display: grid;
  width: 32px;
  height: 32px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: var(--radius-full);
  background: var(--primary-50);
  color: var(--primary-700);
  font-size: 11px;
  font-weight: var(--font-semibold);
}

.user-name,
.project-count {
  display: grid;
  min-width: 0;
}

.user-name strong {
  overflow: hidden;
  color: var(--gray-900);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-name small,
.project-count small {
  margin-top: 1px;
  color: var(--gray-500);
  font-size: 11px;
}

.access-line {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.project-count strong {
  color: var(--gray-800);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.users-table__muted {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.users-table__action {
  width: 54px;
  text-align: right !important;
}

.users-table__action button {
  display: inline-grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 0;
  border-radius: var(--radius-base);
  background: transparent;
  color: var(--gray-400);
  cursor: pointer;
}

.users-table__action button:hover {
  background: var(--surface-2);
  color: var(--gray-800);
}

.users-table__loading td {
  height: 58px;
}

.users-table__loading span,
.panel-loading span {
  display: block;
  height: 12px;
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  animation: users-pulse 1.2s ease-in-out infinite alternate;
}

.users-empty {
  height: 180px;
  color: var(--gray-400);
  text-align: center !important;
}

.users-empty :deep(svg),
.users-empty strong,
.users-empty span {
  display: block;
  margin: 0 auto;
}

.users-empty strong {
  margin-top: 8px;
  color: var(--gray-700);
  font-weight: var(--font-medium);
}

.users-empty span {
  margin-top: 3px;
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.panel-form,
.panel-loading {
  display: grid;
  gap: 16px;
}

.panel-loading span:nth-child(1) { width: 70%; }
.panel-loading span:nth-child(2) { width: 100%; height: 80px; }
.panel-loading span:nth-child(3) { width: 88%; }

.panel-field {
  display: grid;
  gap: 6px;
}

.panel-field > span {
  color: var(--gray-700);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.panel-field > span small {
  margin-left: 4px;
  color: var(--gray-400);
  font-weight: var(--font-normal);
}

.panel-field > small {
  color: var(--gray-500);
  font-size: 11px;
  line-height: 1.45;
}

.panel-field--compact {
  margin-bottom: 10px;
}

.password-input {
  position: relative;
}

.password-input .input {
  padding-right: 40px;
}

.password-input button {
  position: absolute;
  top: 3px;
  right: 3px;
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--gray-500);
  cursor: pointer;
}

.panel-error {
  margin: 0;
  padding: 10px 11px;
  border: 1px solid #f0c7c3;
  border-radius: var(--radius-base);
  background: var(--error-50);
  color: var(--error-600);
  font-size: var(--text-xs);
}

.account-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding-bottom: 18px;
  border-bottom: 1px solid var(--border-color-light);
}

.account-overview > div {
  min-width: 0;
  padding: 0 12px;
  border-right: 1px solid var(--border-color-light);
}

.account-overview > div:first-child { padding-left: 0; }
.account-overview > div:last-child { padding-right: 0; border-right: 0; }

.account-overview span,
.account-overview strong {
  display: block;
}

.account-overview span {
  color: var(--gray-500);
  font-size: 11px;
}

.account-overview strong {
  margin-top: 3px;
  overflow-wrap: anywhere;
  color: var(--gray-800);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.status-text--success { color: var(--success-600) !important; }
.status-text--danger { color: var(--error-600) !important; }

.panel-section {
  margin-top: 24px;
}

.panel-section > header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color-light);
}

.panel-section > header h3 {
  margin: 0;
  color: var(--gray-900);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.panel-section > header span {
  color: var(--gray-500);
  font-size: 11px;
}

.panel-section--danger > header h3 {
  color: var(--error-600);
}

.settings-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 20px;
  align-items: center;
  gap: 12px;
  width: 100%;
  min-height: 56px;
  padding: 9px 2px;
  border: 0;
  border-bottom: 1px solid var(--border-color-light);
  background: transparent;
  color: var(--gray-500);
  text-align: left;
  cursor: pointer;
}

.settings-row > span {
  display: grid;
  min-width: 0;
}

.settings-row strong {
  color: var(--gray-800);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.settings-row small {
  margin-top: 2px;
  color: var(--gray-500);
  font-size: 11px;
}

.settings-row:hover:not(:disabled) {
  color: var(--gray-800);
}

.settings-row:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.settings-row--danger,
.settings-row--danger strong {
  color: var(--error-600);
}

.temporary-password {
  margin-top: 12px;
  padding: 12px;
  border: 1px solid var(--primary-200);
  border-radius: var(--radius-base);
  background: var(--primary-50);
}

.temporary-password > span,
.temporary-password > small {
  display: block;
  color: var(--primary-800);
  font-size: 11px;
}

.temporary-password > div {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 30px;
  align-items: center;
  gap: 6px;
  margin: 7px 0;
}

.temporary-password code {
  min-width: 0;
  overflow-wrap: anywhere;
  color: var(--gray-900);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.temporary-password button {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 0;
  border-radius: var(--radius-sm);
  background: rgb(255 255 255 / 0.65);
  color: var(--primary-700);
  cursor: pointer;
}

.activity-list {
  margin: 0;
}

.activity-list div {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  padding: 9px 2px;
  border-bottom: 1px solid var(--border-color-light);
  font-size: var(--text-xs);
}

.activity-list dt { color: var(--gray-500); }
.activity-list dd { margin: 0; color: var(--gray-800); font-weight: var(--font-medium); text-align: right; }

.project-details {
  margin-top: 10px;
}

.project-details summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 36px;
  color: var(--primary-700);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  cursor: pointer;
  list-style: none;
}

.project-details summary::-webkit-details-marker { display: none; }
.project-details[open] summary :deep(svg) { transform: rotate(180deg); }

.project-details article {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 2px;
  border-top: 1px solid var(--border-color-light);
  font-size: var(--text-xs);
}

.project-details article strong { color: var(--gray-700); font-weight: var(--font-medium); }
.project-details article span { color: var(--gray-500); text-transform: capitalize; }

.confirm-layer {
  z-index: calc(var(--z-modal) + 2);
}

.confirm-dialog {
  display: block;
  width: min(390px, calc(100% - 28px));
  padding: 22px;
}

.confirm-dialog__icon {
  display: grid;
  width: 36px;
  height: 36px;
  place-items: center;
  margin-bottom: 14px;
  border-radius: var(--radius-full);
  background: var(--primary-50);
  color: var(--primary-700);
}

.confirm-dialog__icon--danger { background: var(--error-50); color: var(--error-600); }

.confirm-dialog h2 {
  margin: 0;
  color: var(--gray-900);
  font-size: 18px;
  font-weight: var(--font-semibold);
}

.confirm-dialog > p,
.confirm-dialog > ul {
  margin: 7px 0 0;
  color: var(--gray-600);
  font-size: var(--text-xs);
  line-height: 1.55;
}

.confirm-dialog > ul {
  padding-left: 18px;
}

.confirm-dialog__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@keyframes users-pulse { to { opacity: 0.45; } }

@media (max-width: 760px) {
  .users-table {
    min-width: 0;
  }

  .users-table th:nth-child(3),
  .users-table td:nth-child(3),
  .users-table th:nth-child(4),
  .users-table td:nth-child(4) {
    display: none;
  }
}

@media (max-width: 520px) {
  .users-toolbar {
    align-items: stretch;
    flex-direction: column;
    gap: 7px;
  }

  .users-search {
    width: 100%;
  }

  .users-toolbar > span {
    text-align: right;
  }

  .users-table th,
  .users-table td {
    padding-inline: 10px;
  }

  .users-table th:nth-child(2),
  .users-table td:nth-child(2) {
    display: none;
  }
}
</style>
