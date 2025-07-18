<template>
  <div class="project-list-container">
    <div class="project-list-content">
      <main class="pl-main">
      <!-- 精简头部 -->
      <div class="page-header">
        <div class="header-left">
          <h1>Projects</h1>
          <span class="project-count">{{ filteredProjects.length }} projects</span>
        </div>
        <button @click="showCreateModal = true" class="create-btn">
          <span class="btn-icon">+</span>
          New Project
        </button>
      </div>
      
      <!-- 搜索和筛选区 -->
      <div class="controls-bar">
        <div class="search-box">
          <span class="search-icon">🔍</span>
          <input 
            v-model="searchQuery" 
            type="text" 
            placeholder="Search project name, creator or description..."
            class="search-input"
          >
          <button v-if="searchQuery" @click="clearSearch" class="clear-btn">×</button>
        </div>
        
        <div class="sort-controls">
          <label class="sort-label">Sort:</label>
          <select v-model="sortBy" class="sort-select">
            <option value="last_accessed">Last Accessed</option>
            <option value="created_at">Created Date</option>
            <option value="name">Name</option>
          </select>
          <button @click="toggleSortOrder" class="sort-order-btn" :title="sortOrder === 'desc' ? 'Descending' : 'Ascending'">
            {{ sortOrder === 'desc' ? '↓' : '↑' }}
          </button>
        </div>
        
        <div class="view-controls">
          <button 
            @click="viewMode = 'grid'" 
            :class="['view-btn', { active: viewMode === 'grid' }]"
            title="Grid View"
          >▦</button>
          <button 
            @click="viewMode = 'list'" 
            :class="['view-btn', { active: viewMode === 'list' }]"
            title="List View"
          >☰</button>
        </div>
      </div>

      <!-- 项目列表 -->
      <div v-if="filteredProjects.length === 0" class="empty-state">
        <div class="empty-icon">📁</div>
        <h3>No Projects</h3>
        <p v-if="searchQuery">No projects found matching "{{ searchQuery }}"</p>
        <p v-else>Create your first project to get started</p>
        <button v-if="!searchQuery" @click="showCreateModal = true" class="empty-create-btn">Create Project</button>
      </div>
      
      <div v-else :class="['projects-container', viewMode]">
        <div v-for="project in filteredProjects" :key="project.id" :class="['project-card', viewMode]">
          <div class="project-info" @click="showProjectDetails(project)">
            <div class="project-header">
            <h3>{{ project.name }}</h3>
              <span v-if="project.has_password" class="password-protected" title="This project requires password access">
                🔒
              </span>
            </div>
            <p class="project-meta">Creator: {{ project.creator || 'Unknown' }}</p>
            <p class="project-meta">Created: {{ formatDate(project.created_at) }}</p>
            <p class="project-meta">Last Accessed: {{ formatDate(project.last_accessed) }}</p>
            <p v-if="project.description" class="project-description">{{ project.description }}</p>
          </div>
          <div class="project-actions">
            <button @click="openWorkspace(project.id)" class="open-btn">Open</button>
            <button @click="openEditModal(project)" class="edit-btn" title="Edit Project">✏️</button>
            <button @click="deleteProject(project.id)" class="delete-btn" title="Delete Project">🗑️</button>
          </div>
        </div>
      </div>
    </main>

    <!-- 创建项目弹窗 -->
    <div v-if="showCreateModal" class="modal-overlay" @click="closeCreateModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>Create New Project</h3>
          <button @click="closeCreateModal" class="close-btn">×</button>
        </div>
        <form @submit.prevent="createProject" class="project-form">
          <div class="form-group">
            <label for="name">Project Name *</label>
            <input v-model="newProject.name" id="name" type="text" placeholder="Enter project name..." required>
          </div>
          <div class="form-group">
            <label for="creator">Creator</label>
            <input v-model="newProject.creator" id="creator" type="text" placeholder="Enter creator name...">
          </div>
          <div class="form-group">
            <label for="description">Project Description</label>
            <textarea v-model="newProject.description" id="description" placeholder="Describe the project goals and content..."></textarea>
          </div>
          <div class="form-group">
            <label for="password">Project Password (Optional)</label>
            <input v-model="newProject.password" id="password" type="password" placeholder="Set project password, leave empty for no password">
            <small class="form-hint">Setting a password will require verification when accessing the project</small>
          </div>
          <div class="form-actions">
            <button type="button" @click="closeCreateModal" class="cancel-btn">Cancel</button>
            <button type="submit" class="submit-btn">Create Project</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 编辑项目弹窗 -->
    <div v-if="showEditModal" class="modal-overlay" @click="closeEditModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>Edit Project Information</h3>
          <button @click="closeEditModal" class="close-btn">×</button>
        </div>
        <form @submit.prevent="updateProject" class="project-form">
          <div class="form-group">
            <label for="edit-name">Project Name *</label>
            <input v-model="editingProject.name" id="edit-name" type="text" required>
          </div>
          <div class="form-group">
            <label for="edit-creator">Creator</label>
            <input v-model="editingProject.creator" id="edit-creator" type="text">
          </div>
          <div class="form-group">
            <label for="edit-description">Project Description</label>
            <textarea v-model="editingProject.description" id="edit-description"></textarea>
          </div>
          <div class="form-group" v-if="editingProject.has_password">
            <label for="edit-current-password">Current Password *</label>
            <input v-model="editingProject.current_password" id="edit-current-password" type="password" placeholder="Enter current password to verify identity">
            <small class="form-hint">Modifying password-protected project information requires current password verification</small>
          </div>
          <div class="form-group">
            <label for="edit-password">Project Password</label>
            <input v-model="editingProject.password" id="edit-password" type="password" placeholder="Modify project password, leave empty to keep unchanged">
            <small class="form-hint">Leave empty to keep current password, enter new password to change</small>
          </div>
          <div class="form-actions">
            <button type="button" @click="closeEditModal" class="cancel-btn">Cancel</button>
            <button type="submit" class="submit-btn">Save Changes</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 项目详情弹窗 -->
    <div v-if="showDetailsModal" class="modal-overlay" @click="closeDetailsModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>Project Details</h3>
          <button @click="closeDetailsModal" class="close-btn">×</button>
        </div>
        <div class="project-details">
          <div class="detail-item">
            <strong>Project Name:</strong> {{ selectedProject?.name }}
          </div>
          <div class="detail-item">
            <strong>Project ID:</strong> {{ selectedProject?.id }}
          </div>
          <div class="detail-item">
            <strong>Creator:</strong> {{ selectedProject?.creator || 'Unknown' }}
          </div>
          <div class="detail-item">
            <strong>Created:</strong> {{ formatDate(selectedProject?.created_at) }}
          </div>
          <div class="detail-item">
            <strong>Last Accessed:</strong> {{ formatDate(selectedProject?.last_accessed) }}
          </div>
          <div class="detail-item">
            <strong>Password Protected:</strong> {{ selectedProject?.has_password ? 'Yes' : 'No' }}
          </div>
          <div v-if="selectedProject?.description" class="detail-item">
            <strong>Project Description:</strong> 
            <p class="description-text">{{ selectedProject.description }}</p>
          </div>
          <div class="detail-actions">
            <button @click="openWorkspace(selectedProject?.id)" class="primary-btn">Open Project</button>
            <button @click="openEditModal(selectedProject)" class="secondary-btn">Edit Information</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 密码验证弹窗 -->
    <div v-if="showPasswordModal" class="modal-overlay" @click="closePasswordModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>🔒 Enter Project Password</h3>
          <button @click="closePasswordModal" class="close-btn">×</button>
        </div>
        <div class="password-form">
          <div class="form-group">
            <label for="verify-password">Please enter the access password for "{{ pendingProject?.name }}":</label>
            <input 
              v-model="verifyPassword" 
              id="verify-password" 
              type="password" 
              placeholder="Enter password..."
              @keyup.enter="submitPassword"
              autofocus
            >
            <div v-if="passwordError" class="error-message">{{ passwordError }}</div>
          </div>
          <div class="form-actions">
            <button @click="closePasswordModal" class="cancel-btn">Cancel</button>
            <button @click="submitPassword" class="submit-btn" :disabled="!verifyPassword.trim()">
              {{ isVerifying ? 'Verifying...' : 'Confirm' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 删除项目弹窗 -->
    <div v-if="showDeletePasswordModal" class="modal-overlay" @click="closeDeletePasswordModal">
      <div class="modal-content" @click.stop>
        <div class="modal-header">
          <h3>🔒 Confirm Project Deletion</h3>
          <button @click="closeDeletePasswordModal" class="close-btn">×</button>
        </div>
        <div class="password-form">
          <div class="form-group">
            <label for="delete-password">Please enter the access password for "{{ deletingProject?.name }}" to confirm deletion:</label>
            <input 
              v-model="deletePassword" 
              id="delete-password" 
              type="password" 
              placeholder="Enter password..."
              @keyup.enter="confirmDeleteProject"
              autofocus
            >
            <div v-if="deletePasswordError" class="error-message">{{ deletePasswordError }}</div>
          </div>
          <div class="form-actions">
            <button @click="closeDeletePasswordModal" class="cancel-btn">Cancel</button>
            <button @click="confirmDeleteProject" class="submit-btn" :disabled="!deletePassword.trim()">
              {{ isDeleting ? 'Deleting...' : 'Confirm Delete' }}
            </button>
          </div>
        </div>
      </div>
    </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';

const projects = ref([]);
const router = useRouter();

// 弹窗状态
const showCreateModal = ref(false);
const showEditModal = ref(false);
const showDetailsModal = ref(false);
const showPasswordModal = ref(false);

// 项目数据
const newProject = ref({
  name: '',
  creator: '',
  description: '',
  password: ''
});

const editingProject = ref({});
const selectedProject = ref(null);

// 密码验证相关
const pendingProject = ref(null);
const verifyPassword = ref('');
const passwordError = ref('');
const isVerifying = ref(false);

// 删除项目弹窗相关
const showDeletePasswordModal = ref(false);
const deletingProject = ref(null);
const deletePassword = ref('');
const deletePasswordError = ref('');
const isDeleting = ref(false);

// 搜索和排序状态
const searchQuery = ref('');
const sortBy = ref('last_accessed');
const sortOrder = ref('desc');
const viewMode = ref('grid');

// 计算过滤和排序后的项目列表
const filteredProjects = computed(() => {
  let filtered = projects.value;
  
  // 搜索过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    filtered = filtered.filter(project => 
      project.name.toLowerCase().includes(query) ||
      (project.creator && project.creator.toLowerCase().includes(query)) ||
      (project.description && project.description.toLowerCase().includes(query))
    );
  }
  
  // 排序
  filtered.sort((a, b) => {
    let aValue = a[sortBy.value];
    let bValue = b[sortBy.value];
    
    // 处理日期字段
    if (sortBy.value === 'last_accessed' || sortBy.value === 'created_at') {
      aValue = new Date(aValue).getTime();
      bValue = new Date(bValue).getTime();
    }
    
    // 处理字符串字段
    if (typeof aValue === 'string') {
      aValue = aValue.toLowerCase();
      bValue = bValue.toLowerCase();
    }
    
    if (sortOrder.value === 'desc') {
      return bValue > aValue ? 1 : -1;
    } else {
      return aValue > bValue ? 1 : -1;
    }
  });
  
  return filtered;
});

// 切换排序顺序
const toggleSortOrder = () => {
  sortOrder.value = sortOrder.value === 'desc' ? 'asc' : 'desc';
};

// 清除搜索
const clearSearch = () => {
  searchQuery.value = '';
};

const fetchProjects = async () => {
  try {
    const response = await fetch('/api/projects/');
    if (!response.ok) throw new Error('Failed to fetch projects');
    projects.value = await response.json();
  } catch (error) {
    console.error('Error fetching projects:', error);
  }
};

const createProject = async () => {
  if (!newProject.value.name.trim()) return;
  
  try {
    const response = await fetch('/api/projects/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newProject.value)
    });
    const createdProject = await response.json();
    projects.value.unshift(createdProject);
    closeCreateModal();
    router.push({ name: 'Workspace', params: { id: createdProject.id } });
  } catch (error) {
    console.error('Error creating project:', error);
  }
};

const updateProject = async () => {
  try {
    const response = await fetch(`/api/projects/${editingProject.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editingProject.value)
    });
    
    if (response.ok) {
      const updatedProject = await response.json();
      // 更新本地数据
      const index = projects.value.findIndex(p => p.id === updatedProject.id);
      if (index !== -1) {
        projects.value[index] = updatedProject;
      }
      closeEditModal();
    } else if (response.status === 401) {
      // 密码验证失败
      const errorData = await response.json();
      alert(errorData.error || 'Current password is incorrect, please try again');
    } else {
      console.error('Failed to update project');
    }
  } catch (error) {
    console.error('Error updating project:', error);
  }
};

const deleteProject = async (id) => {
  const project = projects.value.find(p => p.id === id);
  if (!project) return;
  if (project.has_password) {
    // 弹窗输入密码
    deletingProject.value = project;
    deletePassword.value = '';
    deletePasswordError.value = '';
    showDeletePasswordModal.value = true;
    return;
  }
  // 无密码直接删除
  if (!confirm('Are you sure you want to delete this project and all related data?')) return;
  try {
    await fetch(`/api/projects/${id}`, { method: 'DELETE' });
    projects.value = projects.value.filter(p => p.id !== id);
  } catch (error) {
    console.error('Error deleting project:', error);
  }
};

const confirmDeleteProject = async () => {
  if (!deletingProject.value) return;
  if (!deletePassword.value.trim()) {
    deletePasswordError.value = 'Please enter password';
    return;
  }
  isDeleting.value = true;
  deletePasswordError.value = '';
  try {
    const response = await fetch(`/api/projects/${deletingProject.value.id}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password: deletePassword.value })
    });
    if (response.status === 204) {
      // 删除成功
      projects.value = projects.value.filter(p => p.id !== deletingProject.value.id);
      showDeletePasswordModal.value = false;
      deletingProject.value = null;
      deletePassword.value = '';
    } else if (response.status === 401) {
      const data = await response.json();
      deletePasswordError.value = data.error || 'Incorrect password, cannot delete project';
    } else {
      deletePasswordError.value = 'Delete failed';
    }
  } catch (e) {
    deletePasswordError.value = 'Request failed';
  } finally {
    isDeleting.value = false;
  }
};

const closeDeletePasswordModal = () => {
  showDeletePasswordModal.value = false;
  deletingProject.value = null;
  deletePassword.value = '';
  deletePasswordError.value = '';
  isDeleting.value = false;
};

const openWorkspace = async (id) => {
  const project = projects.value.find(p => p.id === id);
  
  // 如果项目有密码保护，显示密码验证弹窗
  if (project && project.has_password) {
    pendingProject.value = project;
    showPasswordModal.value = true;
    return;
  }
  
  // 无密码保护，直接访问
  await accessProject(id);
};

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
  newProject.value = { name: '', creator: '', description: '', password: '' };
};

const closeEditModal = () => {
  showEditModal.value = false;
  editingProject.value = {};
};

const closeDetailsModal = () => {
  showDetailsModal.value = false;
  selectedProject.value = null;
};

const closePasswordModal = () => {
  showPasswordModal.value = false;
  pendingProject.value = null;
  verifyPassword.value = '';
  passwordError.value = '';
  isVerifying.value = false;
};

const submitPassword = async () => {
  if (!verifyPassword.value.trim()) return;
  
  // 检查 pendingProject 是否存在
  if (!pendingProject.value) {
    passwordError.value = 'Project information lost, please try again';
    return;
  }
  
  isVerifying.value = true;
  passwordError.value = '';
  
  // 保存项目ID，防止在closePasswordModal中被清空
  const projectId = pendingProject.value.id;
  
  try {
    const response = await fetch(`/api/projects/${projectId}/verify-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password: verifyPassword.value })
    });
    
    const result = await response.json();
    
    if (response.ok && result.success) {
      // 密码验证成功，关闭弹窗并访问项目
      closePasswordModal();
      await accessProject(projectId);
    } else {
      // 密码验证失败
      passwordError.value = result.message || 'Incorrect password, please try again';
      verifyPassword.value = '';
    }
  } catch (error) {
    console.error('Error verifying password:', error);
    passwordError.value = 'Verification failed, please try again';
  } finally {
    isVerifying.value = false;
  }
};

const openEditModal = (project) => {
  editingProject.value = { 
    ...project, 
    password: '', 
    current_password: '' // 初始化当前密码字段
  }; // Don't pre-fill password for security
  showEditModal.value = true;
  showDetailsModal.value = false;
};

const showProjectDetails = (project) => {
  selectedProject.value = project;
  showDetailsModal.value = true;
};

// 日期格式化
const formatDate = (dateString) => {
  if (!dateString) return 'Unknown';
  const date = new Date(dateString);
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

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
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-4);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-6);
  padding-bottom: var(--spacing-4);
  border-bottom: var(--border-width) solid var(--border-color);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.page-header h1 {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--gray-800);
  margin: 0;
}

.project-count {
  color: var(--gray-600);
  font-size: var(--text-sm);
  background: var(--gray-100);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-xl);
}

.create-btn {
  background: var(--gradient-primary);
  color: white;
  border: none;
  padding: var(--spacing-3) var(--spacing-5);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  border-radius: var(--radius-base);
  cursor: pointer;
  transition: all var(--transition-base);
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
  box-shadow: var(--shadow-sm);
}

.create-btn:hover {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-icon {
  font-size: 1.2em;
  font-weight: normal;
}

/* 控制栏样式 */
.controls-bar {
  display: flex;
  gap: 16px;
  align-items: center;
  margin-bottom: 24px;
  padding: 16px;
  background: #f9fafb;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
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
  color: #9ca3af;
  font-size: 0.9rem;
}

.search-input {
  width: 100%;
  padding: 10px 12px 10px 36px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.9rem;
  background: white;
  transition: border-color 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.clear-btn {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  font-size: 1.1rem;
}

.clear-btn:hover {
  color: #6b7280;
  background: #f3f4f6;
}

.sort-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sort-label {
  font-size: 0.85rem;
  color: #6b7280;
  font-weight: 500;
}

.sort-select {
  padding: 6px 10px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 0.85rem;
  background: white;
  cursor: pointer;
}

.sort-order-btn {
  background: white;
  border: 1px solid #d1d5db;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
  color: #6b7280;
  transition: all 0.2s;
}

.sort-order-btn:hover {
  background: #f9fafb;
  color: #374151;
}

.view-controls {
  display: flex;
  gap: 4px;
}

.view-btn {
  background: white;
  border: 1px solid #d1d5db;
  padding: 8px 10px;
  cursor: pointer;
  font-size: 0.9rem;
  color: #6b7280;
  transition: all 0.2s;
}

.view-btn:first-child {
  border-radius: 6px 0 0 6px;
}

.view-btn:last-child {
  border-radius: 0 6px 6px 0;
}

.view-btn:hover {
  background: #f9fafb;
}

.view-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

/* 空状态样式 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #6b7280;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state h3 {
  margin: 0 0 8px 0;
  font-size: 1.2rem;
  color: #374151;
}

.empty-state p {
  margin: 0 0 24px 0;
  font-size: 0.9rem;
}

.empty-create-btn {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 10px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
}

/* 项目容器样式 */
.projects-container.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.projects-container.list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 项目卡片基础样式 */
.project-card {
  background: white;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  transition: all 0.2s ease;
  cursor: pointer;
}

.project-card:hover {
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
  transform: translateY(-2px);
}

/* 网格视图样式 */
.project-card.grid {
  padding: 20px;
  display: flex;
  flex-direction: column;
}

/* 列表视图样式 */
.project-card.list {
  padding: 16px 20px;
  display: flex;
  flex-direction: row;
  align-items: center;
}

.project-card.list .project-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 0;
}

.project-card.list .project-info h3 {
  margin: 0;
  min-width: 200px;
}

.project-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.project-header h3 {
  margin: 0;
  flex: 1;
}

.password-protected {
  font-size: 1.2em;
  color: #f59e0b;
  margin-left: 8px;
  cursor: help;
}

.password-form {
  padding: 25px;
}

.error-message {
  color: #dc2626;
  font-size: 0.9em;
  margin-top: 5px;
  font-weight: 500;
}

.project-card.list .project-meta {
  margin: 0;
  font-size: 0.8rem;
  min-width: 120px;
}

.project-card.list .project-description {
  margin: 0;
  font-size: 0.85rem;
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-card.list .project-actions {
  margin-left: 20px;
}

.project-info {
  flex-grow: 1;
  cursor: pointer;
  margin-bottom: 15px;
}

.project-info h3 {
  margin: 0 0 10px 0;
  font-size: 1.3em;
  font-weight: 600;
  color: #1f2937;
}

.project-meta {
  margin: 5px 0;
  font-size: 0.85em;
  color: #6b7280;
}

.project-description {
  margin: 10px 0 0 0;
  font-size: 0.9em;
  color: #4b5563;
  font-style: italic;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.project-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.open-btn, .edit-btn {
  background-color: #f3f4f6;
  color: #374151;
  border: 1px solid #e5e7eb;
  padding: 8px 15px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
  flex: 1;
}

.open-btn:hover, .edit-btn:hover {
  background-color: #e5e7eb;
}

.delete-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2em;
  opacity: 0.6;
  transition: opacity 0.2s;
  padding: 8px;
}

.delete-btn:hover {
  opacity: 1;
}

/* 弹窗样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 12px;
  padding: 0;
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 25px;
  border-bottom: 1px solid #e5e7eb;
}

.modal-header h3 {
  margin: 0;
  font-size: 1.3em;
  font-weight: 600;
  color: #1f2937;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5em;
  cursor: pointer;
  color: #6b7280;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.close-btn:hover {
  color: #374151;
}

.project-form {
  padding: 25px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: #374151;
}

.form-group input,
.form-group textarea {
  width: 100%;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 1em;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #3a6ffb;
  box-shadow: 0 0 0 3px rgba(58, 111, 251, 0.1);
}

.form-group textarea {
  min-height: 80px;
  resize: vertical;
}

.form-hint {
  display: block;
  margin-top: 5px;
  font-size: 0.8em;
  color: #6b7280;
  font-style: italic;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 25px;
}

.cancel-btn {
  background-color: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}

.cancel-btn:hover {
  background-color: #e5e7eb;
}

.submit-btn {
  background-color: #3a6ffb;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}

.submit-btn:hover {
  background-color: #255aee;
}

/* 项目详情样式 */
.project-details {
  padding: 25px;
}

.detail-item {
  margin-bottom: 15px;
}

.detail-item strong {
  color: #374151;
  display: inline-block;
  min-width: 80px;
}

.description-text {
  margin-top: 5px;
  color: #4b5563;
  line-height: 1.5;
  white-space: pre-wrap;
}

.detail-actions {
  display: flex;
  gap: 12px;
  margin-top: 25px;
  padding-top: 20px;
  border-top: 1px solid #e5e7eb;
}

.primary-btn {
  background-color: #3a6ffb;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
  flex: 1;
}

.primary-btn:hover {
  background-color: #255aee;
}

.secondary-btn {
  background-color: #f3f4f6;
  color: #374151;
  border: 1px solid #d1d5db;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
  flex: 1;
}

.secondary-btn:hover {
  background-color: #e5e7eb;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .controls-bar {
    flex-wrap: wrap;
    gap: 12px;
  }
  
  .projects-container.grid {
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 12px;
  }
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .header-left {
    width: 100%;
  }
  
  .create-btn {
    width: 100%;
    justify-content: center;
  }
  
  .controls-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  
  .sort-controls,
  .view-controls {
    justify-content: space-between;
  }
  
  .projects-container.grid {
    grid-template-columns: 1fr;
  }
  
  .project-card.list {
    flex-direction: column;
    align-items: stretch;
  }
  
  .project-card.list .project-info {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
    margin-bottom: 12px;
  }
  
  .project-card.list .project-info h3 {
    min-width: auto;
  }
  
  .project-card.list .project-meta {
    min-width: auto;
  }
  
  .project-card.list .project-actions {
    margin-left: 0;
    justify-content: center;
  }
}

@media (max-width: 480px) {
  .project-list-container {
    padding: 12px;
  }
  
  .project-count {
    display: none;
  }
  
  .controls-bar {
    padding: 12px;
  }
  
  .search-input {
    font-size: 16px; /* 防止iOS缩放 */
  }
}
</style>
