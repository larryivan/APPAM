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
    <div v-if="showCreateModal" class="modal-overlay app-modal-viewport app-modal-backdrop" @click="closeCreateModal">
      <div class="app-modal project-modal" @click.stop>
        <div class="modal-header app-modal-header">
          <h3>Create New Project</h3>
          <button @click="closeCreateModal" class="close-btn app-modal-close">×</button>
        </div>
        <form @submit.prevent="createProject" class="project-form app-modal-body">
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
          <div class="form-actions">
            <button type="button" @click="closeCreateModal" class="cancel-btn">Cancel</button>
            <button type="submit" class="submit-btn">Create Project</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 编辑项目弹窗 -->
    <div v-if="showEditModal" class="modal-overlay app-modal-viewport app-modal-backdrop" @click="closeEditModal">
      <div class="app-modal project-modal" @click.stop>
        <div class="modal-header app-modal-header">
          <h3>Edit Project Information</h3>
          <button @click="closeEditModal" class="close-btn app-modal-close">×</button>
        </div>
        <form @submit.prevent="updateProject" class="project-form app-modal-body">
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
          <div class="form-actions">
            <button type="button" @click="closeEditModal" class="cancel-btn">Cancel</button>
            <button type="submit" class="submit-btn">Save Changes</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 项目详情弹窗 -->
    <div v-if="showDetailsModal" class="modal-overlay app-modal-viewport app-modal-backdrop" @click="closeDetailsModal">
      <div class="app-modal project-modal" @click.stop>
        <div class="modal-header app-modal-header">
          <h3>Project Details</h3>
          <button @click="closeDetailsModal" class="close-btn app-modal-close">×</button>
        </div>
        <div class="project-details app-modal-body">
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

// 项目数据
const newProject = ref({
  name: '',
  creator: '',
  description: ''
});

const editingProject = ref({});
const selectedProject = ref(null);

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
  if (!confirm('Are you sure you want to delete this project and all related data?')) return;
  try {
    await fetch(`/api/projects/${id}`, { method: 'DELETE' });
    projects.value = projects.value.filter(p => p.id !== id);
  } catch (error) {
    console.error('Error deleting project:', error);
  }
};

const openWorkspace = async (id) => {
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
  newProject.value = { name: '', creator: '', description: '' };
};

const closeEditModal = () => {
  showEditModal.value = false;
  editingProject.value = {};
};

const closeDetailsModal = () => {
  showDetailsModal.value = false;
  selectedProject.value = null;
};

const openEditModal = (project) => {
  editingProject.value = { 
    ...project
  };
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
  padding: var(--spacing-6);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-6);
  padding-bottom: var(--spacing-4);
  border-bottom: var(--border-width) solid var(--border-color-light);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-4);
}

.page-header h1 {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--gray-900);
  margin: 0;
}

.project-count {
  color: var(--gray-600);
  font-size: var(--text-sm);
  background: var(--surface-2);
  padding: var(--spacing-1) var(--spacing-3);
  border-radius: var(--radius-xl);
  border: var(--border-width) solid var(--border-color-light);
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
  box-shadow: 0 10px 20px rgba(var(--accent-rgb), 0.2);
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
  background: var(--surface-2);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color-light);
  box-shadow: var(--shadow-xs);
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
  font-size: 0.9rem;
}

.search-input {
  width: 100%;
  padding: 10px 12px 10px 36px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-base);
  font-size: 0.9rem;
  background: var(--surface-1);
  transition: border-color 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.16);
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

.sort-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sort-label {
  font-size: 0.85rem;
  color: var(--gray-600);
  font-weight: 500;
}

.sort-select {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  background: var(--surface-1);
  cursor: pointer;
}

.sort-order-btn {
  background: var(--surface-1);
  border: 1px solid var(--border-color);
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.9rem;
  color: var(--gray-600);
  transition: all 0.2s;
}

.sort-order-btn:hover {
  background: var(--surface-2);
  color: var(--gray-800);
}

.view-controls {
  display: flex;
  gap: 4px;
}

.view-btn {
  background: var(--surface-1);
  border: 1px solid var(--border-color);
  padding: 8px 10px;
  cursor: pointer;
  font-size: 0.9rem;
  color: var(--gray-600);
  transition: all 0.2s;
}

.view-btn:first-child {
  border-radius: 6px 0 0 6px;
}

.view-btn:last-child {
  border-radius: 0 6px 6px 0;
}

.view-btn:hover {
  background: var(--surface-2);
}

.view-btn.active {
  background: var(--gradient-primary);
  color: white;
  border-color: transparent;
}

/* 空状态样式 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--gray-600);
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-state h3 {
  margin: 0 0 8px 0;
  font-size: 1.2rem;
  color: var(--gray-800);
}

.empty-state p {
  margin: 0 0 24px 0;
  font-size: 0.9rem;
}

.empty-create-btn {
  background: var(--gradient-primary);
  color: white;
  border: none;
  padding: 10px 24px;
  border-radius: var(--radius-base);
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
  background: var(--surface-1);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color-light);
  transition: all 0.2s ease;
  cursor: pointer;
  box-shadow: var(--shadow-xs);
}

.project-card:hover {
  border-color: rgba(var(--accent-rgb), 0.28);
  box-shadow: var(--shadow-base);
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
  color: var(--gray-900);
}

.project-meta {
  margin: 5px 0;
  font-size: 0.85em;
  color: var(--gray-600);
}

.project-description {
  margin: 10px 0 0 0;
  font-size: 0.9em;
  color: var(--gray-600);
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
  background-color: var(--surface-2);
  color: var(--gray-700);
  border: 1px solid var(--border-color);
  padding: 8px 15px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
  flex: 1;
}

.open-btn:hover, .edit-btn:hover {
  background-color: var(--surface-3);
}

.delete-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2em;
  opacity: 0.6;
  transition: opacity 0.2s;
  padding: 8px;
  color: var(--gray-500);
}

.delete-btn:hover {
  opacity: 1;
  color: var(--gray-800);
}

/* 弹窗样式 */
.project-modal {
  max-width: 500px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: 500;
  color: var(--gray-700);
}

.form-group input,
.form-group textarea {
  width: 100%;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
  font-size: 1em;
  transition: border-color 0.2s;
  box-sizing: border-box;
  background: var(--surface-1);
}

.form-group input:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.16);
}

.form-group textarea {
  min-height: 80px;
  resize: vertical;
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
  margin-top: 25px;
}

.cancel-btn {
  background-color: var(--surface-2);
  color: var(--gray-700);
  border: 1px solid var(--border-color);
  padding: 10px 20px;
  border-radius: var(--radius-sm);
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
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}

.submit-btn:hover {
  background: linear-gradient(135deg, #1d4ed8 0%, #0ea5e9 100%);
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
  background: linear-gradient(135deg, #1d4ed8 0%, #0ea5e9 100%);
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
