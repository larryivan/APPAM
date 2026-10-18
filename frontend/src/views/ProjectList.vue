<template>
  <div class="project-list-container">
    <div class="project-list-content">
      <main class="pl-main">
      <PageHeader eyebrow="Workspace" title="Projects">
        <template #meta>
          <span class="project-count">{{ filteredProjects.length }} {{ filteredProjects.length === 1 ? 'project' : 'projects' }}</span>
        </template>
        <template #actions>
          <button @click="showCreateModal = true" class="btn btn-primary">
            <Icon name="plus" :size="16" />
            New project
          </button>
        </template>
      </PageHeader>

      <div v-if="pageError" class="page-notice error" role="alert">
        <span>{{ pageError }}</span>
        <button type="button" @click="fetchProjects">Try again</button>
      </div>

      <div class="controls-bar">
        <div class="search-box">
          <Icon name="search" :size="16" class="search-icon" />
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search projects"
            class="search-input"
          >
          <button v-if="searchQuery" @click="clearSearch" class="clear-btn" aria-label="Clear search">
            <Icon name="x" :size="14" />
          </button>
        </div>

      </div>

      <!-- 项目列表 -->
      <div v-if="projectsLoading" class="empty-state" aria-live="polite">
        <Icon name="rotate-ccw" :size="28" spin />
        <h3>Loading projects</h3>
      </div>
      <div v-else-if="!pageError && filteredProjects.length === 0" class="empty-state">
        <div class="empty-icon"><Icon name="folder-open" :size="40" :stroke-width="1.5" /></div>
        <h3>No projects</h3>
        <p v-if="searchQuery">No projects found matching "{{ searchQuery }}"</p>
        <p v-else>Create your first project to get started</p>
        <button v-if="!searchQuery" @click="showCreateModal = true" class="empty-create-btn">Create project</button>
      </div>
      
      <div v-else class="projects-container">
        <div
          v-for="project in filteredProjects"
          :key="project.id"
          class="project-card"
          @click="openWorkspace(project.id)"
        >
          <div class="project-info">
            <div class="project-header">
              <h3>{{ project.name }}</h3>
              <span v-if="project.access_role !== 'owner'" class="access-badge" :class="project.access_role">
                {{ accessRoleLabel(project.access_role) }}
              </span>
            </div>
            <div class="project-summary">
              <span class="project-last-opened">{{ formatRelativeDate(project.last_accessed || project.created_at) }}</span>
            </div>
            <p v-if="project.description" class="project-description">{{ project.description }}</p>
          </div>
          <div class="project-actions">
            <button @click.stop="openWorkspace(project.id)" class="open-btn">Continue</button>
            <details v-if="canManageProject(project)" class="project-menu" @click.stop>
              <summary title="Project actions" aria-label="Project actions">
                <Icon name="more-horizontal" :size="18" />
              </summary>
              <div class="project-menu__items" @click="closeCardMenu">
                <button type="button" @click="openMembersModal(project)"><Icon name="users" :size="15" /> Access</button>
                <button type="button" @click="openEditModal(project)"><Icon name="pencil" :size="15" /> Edit</button>
                <button type="button" class="danger" @click="deleteProject(project.id)"><Icon name="trash-2" :size="15" /> Delete</button>
              </div>
            </details>
          </div>
        </div>
      </div>
    </main>

    <!-- 创建项目弹窗 -->
    <div v-if="showCreateModal" class="modal-overlay app-modal-viewport app-modal-backdrop" @click="closeCreateModal">
      <div class="app-modal project-modal" @click.stop ref="createPanel" role="dialog" aria-modal="true" :aria-labelledby="createTitleId" tabindex="-1">
        <div class="modal-header app-modal-header">
          <h3 :id="createTitleId">New project</h3>
          <button type="button" class="close-btn app-modal-close" title="Close" aria-label="Close" @click="closeCreateModal">
            <Icon name="x" :size="17" />
          </button>
        </div>
        <form @submit.prevent="createProject" class="project-form app-modal-body">
          <div class="form-group">
            <label for="name">Project Name *</label>
            <input v-model="newProject.name" id="name" type="text" placeholder="Project name" required>
          </div>
          <div class="form-group">
            <label for="description">Project Description</label>
            <textarea v-model="newProject.description" id="description" placeholder="Optional"></textarea>
          </div>
          <p v-if="createError" class="form-error" role="alert">{{ createError }}</p>
          <div class="form-actions">
            <button type="button" @click="closeCreateModal" class="cancel-btn">Cancel</button>
            <button type="submit" class="submit-btn" :disabled="creatingProject">
              {{ creatingProject ? 'Creating...' : 'Create project' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- 编辑项目弹窗 -->
    <div v-if="showEditModal" class="modal-overlay app-modal-viewport app-modal-backdrop" @click="closeEditModal">
      <div class="app-modal project-modal" @click.stop ref="editPanel" role="dialog" aria-modal="true" :aria-labelledby="editTitleId" tabindex="-1">
        <div class="modal-header app-modal-header">
          <h3 :id="editTitleId">Project settings</h3>
          <button type="button" class="close-btn app-modal-close" title="Close" aria-label="Close" @click="closeEditModal">
            <Icon name="x" :size="17" />
          </button>
        </div>
        <form @submit.prevent="updateProject" class="project-form app-modal-body">
          <div class="form-group">
            <label for="edit-name">Project Name *</label>
            <input v-model="editingProject.name" id="edit-name" type="text" required>
          </div>
          <div class="form-group">
            <label for="edit-description">Project Description</label>
            <textarea v-model="editingProject.description" id="edit-description"></textarea>
          </div>
          <p v-if="editError" class="form-error" role="alert">{{ editError }}</p>
          <div class="form-actions">
            <button type="button" @click="closeEditModal" class="cancel-btn">Cancel</button>
            <button type="submit" class="submit-btn">Save changes</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="showMembersModal" class="modal-overlay app-modal-viewport app-modal-backdrop" @click="closeMembersModal">
      <div class="app-modal members-modal" @click.stop ref="membersPanel" role="dialog" aria-modal="true" :aria-labelledby="membersTitleId" tabindex="-1">
        <div class="modal-header app-modal-header">
          <div>
            <h3 :id="membersTitleId">Access</h3>
            <p class="members-subtitle">{{ membersProject?.name }}</p>
          </div>
          <button type="button" class="close-btn app-modal-close" title="Close" aria-label="Close" @click="closeMembersModal">
            <Icon name="x" :size="17" />
          </button>
        </div>

        <div class="members-content app-modal-body">
          <form class="member-form" @submit.prevent="addMember">
            <label>
              <span>User</span>
              <select v-model="memberForm.user_id" required>
                <option disabled value="">Select a user</option>
                <option v-for="user in availableUsers" :key="user.id" :value="user.id">
                  {{ user.display_name || user.username }} (@{{ user.username }})
                </option>
              </select>
            </label>

            <label>
              <span>Role</span>
              <select v-model="memberForm.role">
                <option value="viewer">Viewer</option>
                <option value="editor">Editor</option>
              </select>
            </label>

            <button class="submit-btn" type="submit">Add Member</button>
          </form>

          <p v-if="membersError" class="members-error">{{ membersError }}</p>

          <div class="members-list">
            <div v-for="member in projectMembers" :key="member.user_id" class="member-row">
              <div class="member-ident">
                <strong>{{ member.display_name || member.username }}</strong>
                <span>@{{ member.username }}</span>
              </div>
              <div class="member-controls">
                <select
                  :value="member.project_role"
                  :disabled="member.project_role === 'owner'"
                  @change="changeMemberRole(member, $event.target.value)"
                >
                  <option value="editor">Editor</option>
                  <option value="viewer">Viewer</option>
                </select>
                <button
                  class="danger-link"
                  type="button"
                  :disabled="member.project_role === 'owner'"
                  @click="removeMember(member)"
                >
                  Remove
                </button>
              </div>
            </div>
            <div v-if="!projectMembers.length" class="empty-members">
              No members found.
            </div>
          </div>
        </div>
      </div>
    </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, reactive } from 'vue';
import { confirmAction } from '@/lib/notify.js'
import { nextOverlayId, useOverlay } from '@/lib/overlay.js'
import { useRouter } from 'vue-router';
import PageHeader from '../components/ui/PageHeader.vue'
import Icon from '../components/ui/Icon.vue'

const projects = ref([]);
const router = useRouter();

// 弹窗状态
const showCreateModal = ref(false);
const showEditModal = ref(false);
const showMembersModal = ref(false);
const projectsLoading = ref(true);
const creatingProject = ref(false);
const pageError = ref('');
const createError = ref('');
const editError = ref('');

// 项目数据
const newProject = ref({
  name: '',
  description: ''
});

const editingProject = ref({});
const membersProject = ref(null);
const projectMembers = ref([]);
const userDirectory = ref([]);
const membersError = ref('');
const memberForm = reactive({
  user_id: '',
  role: 'viewer'
})

// 搜索和排序状态
const searchQuery = ref('');
const availableUsers = computed(() => {
  const existing = new Set(projectMembers.value.map((member) => member.user_id))
  return userDirectory.value.filter((user) => !existing.has(user.id))
})

// 计算过滤和排序后的项目列表
const filteredProjects = computed(() => {
  let filtered = [...projects.value];
  
  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    filtered = filtered.filter(project => 
      project.name.toLowerCase().includes(query) ||
      (project.creator && project.creator.toLowerCase().includes(query)) ||
      (project.description && project.description.toLowerCase().includes(query))
    );
  }
  
  filtered.sort((a, b) => {
    const aTime = new Date(a.last_accessed || a.created_at || 0).getTime()
    const bTime = new Date(b.last_accessed || b.created_at || 0).getTime()
    return bTime - aTime
  })
  
  return filtered;
});

// 清除搜索
const clearSearch = () => {
  searchQuery.value = '';
};

const canManageProject = (project) => {
  return project?.access_role === 'owner' || project?.access_role === 'admin'
}

const accessRoleLabel = (role) => {
  if (role === 'admin') return 'Admin'
  if (role === 'owner') return 'Owner'
  if (role === 'editor') return 'Editor'
  return 'Viewer'
}

const fetchProjects = async () => {
  projectsLoading.value = true;
  pageError.value = '';
  try {
    const response = await fetch('/api/projects/');
    if (!response.ok) throw new Error('Failed to fetch projects');
    projects.value = await response.json();
  } catch (error) {
    console.error('Error fetching projects:', error);
    pageError.value = error.message || 'Projects could not be loaded.';
  } finally {
    projectsLoading.value = false;
  }
};

const createProject = async () => {
  if (!newProject.value.name.trim()) return;
  createError.value = '';
  creatingProject.value = true;
  try {
    const response = await fetch('/api/projects/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newProject.value)
    });
    const createdProject = await response.json();
    if (!response.ok) {
      throw new Error(createdProject.error || 'Failed to create project');
    }
    projects.value.unshift(createdProject);
    closeCreateModal();
    router.push({ name: 'Overview', params: { id: createdProject.id } });
  } catch (error) {
    console.error('Error creating project:', error);
    createError.value = error.message || 'The project could not be created.';
  } finally {
    creatingProject.value = false;
  }
};

const updateProject = async () => {
  editError.value = '';
  try {
    const response = await fetch(`/api/projects/${editingProject.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: editingProject.value.name,
        description: editingProject.value.description
      })
    });
    
    if (response.ok) {
      const updatedProject = await response.json();
      // 更新本地数据
      const index = projects.value.findIndex(p => p.id === updatedProject.id);
      if (index !== -1) {
        projects.value[index] = updatedProject;
      }
      closeEditModal();
    } else {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || 'Failed to update project');
    }
  } catch (error) {
    console.error('Error updating project:', error);
    editError.value = error.message || 'The project could not be updated.';
  }
};

// A <details> menu stays open after its buttons are clicked, so it would hang
// above whatever dialog the action opens.
function closeCardMenu(event) {
  event.currentTarget.closest('details')?.removeAttribute('open')
}

const deleteProject = async (id) => {
  const project = projects.value.find(p => p.id === id);
  if (!project) return;
  const confirmed = await confirmAction({
    title: `Delete "${project.name}"?`,
    message: 'The project and all of its files, runs and results are removed. This cannot be undone.',
    confirmLabel: 'Delete project',
    tone: 'danger',
  });
  if (!confirmed) return;
  try {
    const response = await fetch(`/api/projects/${id}`, { method: 'DELETE' });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || 'The project could not be deleted.');
    }
    projects.value = projects.value.filter(p => p.id !== id);
  } catch (error) {
    console.error('Error deleting project:', error);
    pageError.value = error.message || 'The project could not be deleted.';
  }
};

const openWorkspace = async (id) => {
  await accessProject(id);
};

const fetchProjectMembers = async (projectId) => {
  const response = await fetch(`/api/projects/${projectId}/members`)
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload?.error || 'Failed to load project members.')
  }
  projectMembers.value = payload.members || []
}

const fetchUserDirectory = async () => {
  const response = await fetch('/api/auth/users/search')
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload?.error || 'Failed to load users.')
  }
  userDirectory.value = payload.users || []
}

const openMembersModal = async (project) => {
  if (!project) return
  membersProject.value = project
  membersError.value = ''
  memberForm.user_id = ''
  memberForm.role = 'viewer'
  showMembersModal.value = true
  try {
    await Promise.all([
      fetchProjectMembers(project.id),
      fetchUserDirectory(),
    ])
  } catch (error) {
    membersError.value = error.message || 'Failed to load project access.'
  }
}

const closeMembersModal = () => {
  showMembersModal.value = false
  membersProject.value = null
  projectMembers.value = []
  userDirectory.value = []
  membersError.value = ''
  memberForm.user_id = ''
  memberForm.role = 'viewer'
}

const createPanel = ref(null)
const editPanel = ref(null)
const membersPanel = ref(null)
const createTitleId = nextOverlayId('project-create-title')
const editTitleId = nextOverlayId('project-edit-title')
const membersTitleId = nextOverlayId('project-members-title')

// The close handlers are declared further down; resolving them only when a
// dialog actually closes keeps setup clear of the temporal dead zone.
useOverlay(() => showCreateModal.value, { onClose: () => closeCreateModal(), panelRef: createPanel })
useOverlay(() => showEditModal.value, { onClose: () => closeEditModal(), panelRef: editPanel })
useOverlay(() => showMembersModal.value, { onClose: () => closeMembersModal(), panelRef: membersPanel })

const addMember = async () => {
  if (!membersProject.value || !memberForm.user_id) return
  membersError.value = ''
  try {
    const response = await fetch(`/api/projects/${membersProject.value.id}/members`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: memberForm.user_id,
        role: memberForm.role,
      }),
    })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload?.error || 'Failed to add project member.')
    }
    projectMembers.value = payload.members || []
    memberForm.user_id = ''
    memberForm.role = 'viewer'
  } catch (error) {
    membersError.value = error.message || 'Failed to add project member.'
  }
}

const changeMemberRole = async (member, role) => {
  if (!membersProject.value || member.project_role === 'owner') return
  membersError.value = ''
  try {
    const response = await fetch(`/api/projects/${membersProject.value.id}/members/${member.user_id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role }),
    })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload?.error || 'Failed to update project member.')
    }
    projectMembers.value = payload.members || []
  } catch (error) {
    membersError.value = error.message || 'Failed to update project member.'
  }
}

const removeMember = async (member) => {
  if (!membersProject.value || member.project_role === 'owner') return
  const confirmed = await confirmAction({
    title: `Remove ${member.display_name || member.username}?`,
    message: 'They lose access to this project immediately. Project data is not affected.',
    confirmLabel: 'Remove access',
    tone: 'danger',
  })
  if (!confirmed) return
  membersError.value = ''
  try {
    const response = await fetch(`/api/projects/${membersProject.value.id}/members/${member.user_id}`, {
      method: 'DELETE',
    })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload?.error || 'Failed to remove project member.')
    }
    projectMembers.value = payload.members || []
  } catch (error) {
    membersError.value = error.message || 'Failed to remove project member.'
  }
}

const accessProject = async (id) => {
  try {
    await fetch(`/api/projects/${id}/access`, { method: 'POST' });
    // 更新本地数据
    const project = projects.value.find(p => p.id === id);
    if (project) {
      project.last_accessed = new Date().toISOString();
    }
  } catch (error) {
    console.error('Error updating access time:', error);
  }
  
  // 导航到项目概览页面
  router.push({ name: 'Overview', params: { id } });
};

// 弹窗控制
const closeCreateModal = () => {
  showCreateModal.value = false;
  newProject.value = {
    name: '',
    description: ''
  };
  createError.value = '';
};

const closeEditModal = () => {
  showEditModal.value = false;
  editingProject.value = {};
  editError.value = '';
};

const openEditModal = (project) => {
  editingProject.value = { 
    ...project
  };
  showEditModal.value = true;
};

const formatRelativeDate = (dateString) => {
  if (!dateString) return 'Not opened yet'
  const timestamp = new Date(dateString).getTime()
  if (!Number.isFinite(timestamp)) return 'Recently opened'
  const elapsedDays = Math.floor((Date.now() - timestamp) / 86400000)
  if (elapsedDays <= 0) return 'Opened today'
  if (elapsedDays === 1) return 'Opened yesterday'
  if (elapsedDays < 30) return `Opened ${elapsedDays} days ago`
  return `Opened ${new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(timestamp))}`
}

onMounted(fetchProjects);
</script>

<style scoped>
.project-list-container {
  height: 100%;
  overflow-y: auto;
  scroll-behavior: smooth;
}

.project-list-content {
  width: 100%;
  max-width: var(--content-width);
  margin: 0 auto;
  padding: var(--spacing-6);
}

.project-count {
  color: var(--gray-600);
  font-size: var(--text-sm);
  background: var(--surface-2);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-sm);
  border: var(--border-width) solid var(--border-color-light);
}

.controls-bar {
  display: flex;
  align-items: center;
  max-width: 520px;
  margin-bottom: var(--spacing-5);
}

.search-box {
  flex: 1;
  position: relative;
  display: flex;
  align-items: center;
}

.search-icon {
  position: absolute;
  left: 12px;
  color: var(--gray-400);
  font-size: var(--text-sm);
}

.search-input {
  min-height: var(--control-height);
  width: 100%;
  padding: 0 34px 0 36px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-base);
  font-size: var(--text-sm);
  background: var(--surface-1);
  transition: border-color 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: var(--primary-500);
  box-shadow: 0 0 0 2px rgba(var(--accent-rgb), 0.12);
}

.clear-btn {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  color: var(--gray-400);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  font-size: 1.1rem;
}

.clear-btn:hover {
  color: var(--gray-600);
  background: var(--surface-2);
}

.empty-state {
  text-align: center;
  padding: 48px 20px;
  color: var(--gray-600);
}

.empty-icon {
  margin-bottom: 12px;
  color: var(--gray-400);
}

.empty-state h3 {
  margin: 0 0 8px 0;
  font-size: 1.2rem;
  color: var(--gray-800);
}

.empty-state p {
  margin: 0 0 24px 0;
  font-size: var(--text-sm);
}

.page-notice {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-4);
  margin-bottom: var(--spacing-4);
  padding: var(--spacing-3) var(--spacing-4);
  border: 1px solid rgba(220, 38, 38, 0.22);
  border-radius: var(--radius-sm);
  background: var(--error-50);
  color: var(--error-600);
  font-size: var(--text-sm);
}

.page-notice button {
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  font-weight: var(--font-semibold);
  cursor: pointer;
}

.empty-create-btn {
  background: var(--gradient-primary);
  color: white;
  border: none;
  min-height: var(--control-height);
  padding: 0 14px;
  border-radius: var(--radius-base);
  cursor: pointer;
  font-weight: 500;
}

.projects-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: var(--spacing-3);
}

.project-card {
  position: relative;
  display: flex;
  min-height: 156px;
  flex-direction: column;
  padding: var(--spacing-5);
  background: var(--surface-1);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color-light);
  transition: all 0.2s ease;
  cursor: pointer;
  box-shadow: none;
}

.project-card:hover {
  border-color: rgba(var(--accent-rgb), 0.32);
  box-shadow: var(--shadow-xs);
}

.project-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
}

.project-header h3 {
  margin: 0;
  flex: 1;
}

.project-info {
  flex-grow: 1;
  cursor: pointer;
  margin-bottom: var(--spacing-4);
}

.project-info h3 {
  margin: 0 0 10px 0;
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--gray-900);
}

.project-description {
  margin: var(--spacing-3) 0 0;
  font-size: 0.9em;
  color: var(--gray-600);
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.project-actions {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-2);
  align-items: center;
}

.project-summary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--spacing-2);
}

.project-last-opened {
  color: var(--gray-500);
  font-size: var(--text-xs);
}

.access-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border-radius: var(--radius-full);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0;
  white-space: nowrap;
}

.access-badge.viewer {
  background: var(--surface-2);
  color: var(--gray-600);
}

.access-badge.editor {
  background: rgba(14, 165, 233, 0.12);
  color: var(--secondary-color);
}

.access-badge.owner,
.access-badge.admin {
  background: rgba(var(--accent-rgb), 0.12);
  color: var(--primary-700);
}

.open-btn {
  background: var(--primary-600);
  color: white;
  border: 1px solid var(--primary-600);
  min-height: 34px;
  padding: 0 12px;
  border-radius: var(--radius-base);
  cursor: pointer;
  font-weight: var(--font-semibold);
  transition: background-color 0.2s;
}

.open-btn:hover {
  background: var(--primary-700);
}

.project-menu {
  position: relative;
}

.project-menu summary {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  color: var(--gray-600);
  cursor: pointer;
  list-style: none;
}

.project-menu summary::-webkit-details-marker { display: none; }

.project-menu summary:hover,
.project-menu[open] summary {
  background: var(--surface-2);
  color: var(--gray-900);
}

.project-menu__items {
  position: absolute;
  z-index: var(--z-dropdown);
  right: 0;
  bottom: calc(100% + 6px);
  display: grid;
  width: 150px;
  padding: 6px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  background: var(--surface-1);
  box-shadow: var(--shadow-md);
}

.project-menu__items button {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  min-height: 36px;
  padding: 0 var(--spacing-3);
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--gray-700);
  font: inherit;
  font-size: var(--text-sm);
  text-align: left;
  cursor: pointer;
}

.project-menu__items button:hover { background: var(--surface-2); }
.project-menu__items button.danger { color: var(--error-600); }

.project-modal {
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.members-modal {
  max-width: 720px;
}

.members-subtitle {
  margin: 4px 0 0;
  color: var(--gray-500);
  font-size: var(--text-sm);
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: var(--gray-700);
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  min-height: var(--control-height);
  padding: 0 11px;
  font-size: 1em;
  transition: border-color 0.2s;
  box-sizing: border-box;
  background: var(--surface-1);
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--primary-500);
  box-shadow: 0 0 0 2px rgba(var(--accent-rgb), 0.12);
}

.form-group textarea {
  min-height: 80px;
  padding-block: 9px;
  resize: vertical;
}

.form-error {
  margin: 0;
  padding: var(--spacing-3);
  border-radius: var(--radius-sm);
  background: var(--error-50);
  color: var(--error-600);
  font-size: var(--text-sm);
}

.submit-btn:disabled {
  cursor: wait;
  opacity: 0.65;
}

.form-hint {
  display: block;
  margin-top: 5px;
  font-size: 0.8em;
  color: var(--gray-500);
  font-style: italic;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 18px;
}

.cancel-btn {
  background-color: var(--surface-2);
  color: var(--gray-700);
  border: 1px solid var(--border-color);
  min-height: var(--control-height);
  padding: 0 14px;
  border-radius: var(--radius-base);
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}

.cancel-btn:hover {
  background-color: var(--surface-3);
}

.submit-btn {
  background: var(--gradient-primary);
  color: white;
  border: none;
  min-height: var(--control-height);
  padding: 0 14px;
  border-radius: var(--radius-base);
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}

.submit-btn:hover {
  background: var(--primary-700);
}

/* 项目详情样式 */
.detail-item {
  margin-bottom: 15px;
}

.detail-item strong {
  color: var(--gray-700);
  display: inline-block;
  min-width: 80px;
}

.description-text {
  margin-top: 5px;
  color: var(--gray-600);
  line-height: 1.5;
  white-space: pre-wrap;
}

.detail-actions {
  display: flex;
  gap: 12px;
  margin-top: 25px;
  padding-top: 20px;
  border-top: 1px solid var(--border-color-light);
}

.primary-btn {
  background: var(--gradient-primary);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
  flex: 1;
}

.primary-btn:hover {
  background: var(--primary-700);
}

.secondary-btn {
  background-color: var(--surface-2);
  color: var(--gray-700);
  border: 1px solid var(--border-color);
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
  flex: 1;
}

.secondary-btn:hover {
  background-color: var(--surface-3);
}

.members-content {
  display: grid;
  gap: var(--spacing-5);
}

.member-form {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(0, 1fr) auto;
  gap: var(--spacing-3);
  align-items: end;
}

.member-form label {
  display: grid;
  gap: var(--spacing-2);
}

.member-form span {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--gray-700);
}

.member-form select {
  width: 100%;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  min-height: var(--control-height);
  padding: 0 10px;
  background: var(--surface-1);
  font: inherit;
}

.members-error {
  margin: 0;
  padding: var(--spacing-3) var(--spacing-4);
  border-radius: var(--radius-base);
  background: var(--error-50);
  color: var(--error-600);
  font-size: var(--text-sm);
}

.members-list {
  display: grid;
  gap: var(--spacing-3);
}

.member-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-4);
  padding: var(--spacing-4);
  border-radius: var(--radius-base);
  background: var(--surface-2);
  border: 1px solid var(--border-color-light);
}

.member-ident {
  display: grid;
  gap: 4px;
}

.member-ident span {
  color: var(--gray-500);
  font-size: var(--text-sm);
}

.member-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.member-controls select {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 9px 12px;
  background: white;
  font: inherit;
}

.danger-link {
  border: 0;
  background: transparent;
  color: var(--error-600);
  font: inherit;
  font-weight: var(--font-semibold);
  cursor: pointer;
}

.danger-link:disabled {
  color: var(--gray-400);
  cursor: not-allowed;
}

.empty-members {
  padding: var(--spacing-4);
  text-align: center;
  color: var(--gray-500);
  border-radius: var(--radius-base);
  background: var(--surface-2);
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .controls-bar {
    flex-wrap: wrap;
    gap: 12px;
  }
  
  .projects-container {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
  }
}

@media (max-width: 768px) {
  .controls-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .projects-container {
    grid-template-columns: 1fr;
  }

  .member-form {
    grid-template-columns: 1fr;
  }

  .member-row {
    flex-direction: column;
    align-items: stretch;
  }

  .member-controls {
    justify-content: space-between;
  }

}

@media (max-width: 480px) {
  .project-list-container {
    padding: var(--spacing-3);
  }
  
  .project-count {
    display: none;
  }
  
  .controls-bar {
    padding: var(--spacing-3);
  }
  
  .search-input {
    font-size: 16px; /* 防止iOS缩放 */
  }
}
</style>
