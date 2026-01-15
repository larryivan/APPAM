<template>
  <div class="filemanager-container" 
       @contextmenu="showContextMenu" 
       @click="hideContextMenu"
       @keydown="handleKeyDown"
       tabindex="0">
    
    <!-- Modern header navigation -->
    <header class="fm-header" :class="{ mobile: isMobile }">
      <div class="breadcrumbs" :class="{ mobile: isMobile }">
        <button @click="navigateTo('/')" class="breadcrumb-home" title="Back to root directory">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
            <polyline points="9 22 9 12 15 12 15 22"></polyline>
          </svg>
        </button>
        <!-- Mobile simplified breadcrumb -->
        <template v-if="isMobile">
          <span v-if="breadcrumbs.length > 0" class="breadcrumb-item">
            <svg class="breadcrumb-sep" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
            <button @click="navigateTo(breadcrumbs[breadcrumbs.length - 1].path)" class="breadcrumb-btn">
              {{ breadcrumbs[breadcrumbs.length - 1].name }}
            </button>
          </span>
        </template>
        <!-- Desktop full breadcrumb -->
        <template v-else>
        <span v-for="(crumb, index) in breadcrumbs" :key="index" class="breadcrumb-item">
          <svg class="breadcrumb-sep" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
          <button @click="navigateTo(crumb.path)" class="breadcrumb-btn">{{ crumb.name }}</button>
        </span>
        </template>
      </div>
      <div class="header-actions" :class="{ mobile: isMobile }">
        <div class="search-box" :class="{ mobile: isMobile }">
          <svg class="search-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.35-4.35"></path>
          </svg>
          <input 
            v-model="searchQuery" 
            @input="handleSearch" 
            @focus="isSearchFocused = true"
            @blur="isSearchFocused = false"
            :placeholder="isMobile ? 'Search...' : 'Search files...'"
            class="search-input"
            :class="{ focused: isSearchFocused, mobile: isMobile }"
          />
          <button v-if="searchQuery" @click="searchQuery = ''" class="clear-search" title="Clear search">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="view-toggle" v-if="!isMobile">
          <button 
            @click="setViewMode('list')" 
            :class="{ active: viewMode === 'list' }"
            class="toggle-btn"
            title="List View"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="8" y1="6" x2="21" y2="6"></line>
              <line x1="8" y1="12" x2="21" y2="12"></line>
              <line x1="8" y1="18" x2="21" y2="18"></line>
              <line x1="3" y1="6" x2="3.01" y2="6"></line>
              <line x1="3" y1="12" x2="3.01" y2="12"></line>
              <line x1="3" y1="18" x2="3.01" y2="18"></line>
            </svg>
          </button>
          <button 
            @click="setViewMode('grid')" 
            :class="{ active: viewMode === 'grid' }"
            class="toggle-btn"
            title="Grid View"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="7" height="7"></rect>
              <rect x="14" y="3" width="7" height="7"></rect>
              <rect x="14" y="14" width="7" height="7"></rect>
              <rect x="3" y="14" width="7" height="7"></rect>
            </svg>
          </button>
        </div>
        <!-- Mobile menu button -->
        <button v-if="isMobile" @click="showMobileMenu = !showMobileMenu" class="mobile-menu-btn" title="Menu">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>
      </div>
    </header>

    <!-- Modern toolbar -->
    <div class="fm-toolbar" :class="{ mobile: isMobile }">
      <!-- Desktop layout -->
      <template v-if="!isMobile">
      <div class="nav-group">
        <button @click="goUp" :disabled="currentPath === '/'" class="nav-btn" title="Parent Directory">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="17 11 12 6 7 11"></polyline>
            <polyline points="17 18 12 13 7 18"></polyline>
          </svg>
        </button>
        <button @click="goBack" :disabled="!canGoBack" class="nav-btn" title="Back">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>
        <button @click="goForward" :disabled="!canGoForward" class="nav-btn" title="Forward">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </button>
      </div>
      
      <div class="actions-group">
        <button @click="$refs.fileInput.click()" class="action-btn primary" title="Upload Files">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
          <span>Upload</span>
        </button>
        <input type="file" ref="fileInput" @change="handleFileUpload" multiple hidden />
        <button @click="showNewFolderModal = true" class="action-btn" title="New Folder">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            <line x1="12" y1="11" x2="12" y2="17"></line>
            <line x1="9" y1="14" x2="15" y2="14"></line>
          </svg>
          <span>New</span>
        </button>
        <button @click="refreshItems" class="action-btn" title="Refresh" :class="{ rotating: isLoading }">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"></polyline>
            <polyline points="1 20 1 14 7 14"></polyline>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
        </button>
        <button @click="showDownloadManager = true" class="action-btn download-btn" title="Download Manager">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
          <span>Download</span>
        </button>
      </div>
      </template>
      
      <!-- Mobile compact layout -->
      <template v-else>
        <div class="mobile-nav-group">
          <button @click="goUp" :disabled="currentPath === '/'" class="nav-btn mobile" title="Parent Directory">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="17 11 12 6 7 11"></polyline>
              <polyline points="17 18 12 13 7 18"></polyline>
            </svg>
          </button>
          <button @click="goBack" :disabled="!canGoBack" class="nav-btn mobile" title="Back">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
          </button>
          <button @click="$refs.fileInput.click()" class="action-btn mobile primary" title="Upload">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
          </button>
          <input type="file" ref="fileInput" @change="handleFileUpload" multiple hidden />
        </div>
        
        <div class="mobile-actions-group">
          <div class="view-toggle mobile">
            <button 
              @click="setViewMode('list')" 
              :class="{ active: viewMode === 'list' }"
              class="toggle-btn mobile"
              title="List"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="8" y1="6" x2="21" y2="6"></line>
                <line x1="8" y1="12" x2="21" y2="12"></line>
                <line x1="8" y1="18" x2="21" y2="18"></line>
                <line x1="3" y1="6" x2="3.01" y2="6"></line>
                <line x1="3" y1="12" x2="3.01" y2="12"></line>
                <line x1="3" y1="18" x2="3.01" y2="18"></line>
              </svg>
            </button>
            <button 
              @click="setViewMode('grid')" 
              :class="{ active: viewMode === 'grid' }"
              class="toggle-btn mobile"
              title="Grid"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="7" height="7"></rect>
                <rect x="14" y="3" width="7" height="7"></rect>
                <rect x="14" y="14" width="7" height="7"></rect>
                <rect x="3" y="14" width="7" height="7"></rect>
              </svg>
            </button>
          </div>
        </div>
      </template>
      
      <div class="selection-info" v-if="selectedItems.length > 0">
        <span class="count">{{ selectedItems.length }} selected</span>
        <div class="selection-actions">
          <button @click="copySelected" class="mini-btn" title="Copy (Ctrl+C)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
          </button>
          <button @click="cutSelected" class="mini-btn" title="Cut (Ctrl+X)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="6" cy="6" r="3"></circle>
              <circle cx="6" cy="18" r="3"></circle>
              <line x1="20" y1="4" x2="8.12" y2="15.88"></line>
              <line x1="14.47" y1="14.48" x2="20" y2="20"></line>
              <line x1="8.12" y1="8.12" x2="12" y2="12"></line>
            </svg>
          </button>
          <button @click="pasteItems" class="mini-btn" v-if="clipboard.length > 0" :title="`Paste (Ctrl+V) - ${clipboardOperation === 'copy' ? 'Copy' : 'Move'} ${clipboard.length} items`">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
              <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
            </svg>
          </button>
          <button @click="deleteSelected" class="mini-btn danger" title="Delete (Delete)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </div>
      
      <!-- Clipboard status information -->
      <div class="clipboard-info" v-if="clipboard.length > 0 && !selectedItems.length">
        <span class="clipboard-text">
          Clipboard: {{ clipboardOperation === 'copy' ? 'Copy' : 'Cut' }} {{ clipboard.length }} items
        </span>
        <button @click="pasteItems" class="mini-btn" title="Paste (Ctrl+V)">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
            <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
          </svg>
          Paste
        </button>
        <button @click="clearClipboard" class="mini-btn" title="Clear clipboard">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <div class="sort-group">
        <div class="sort-label">Sort:</div>
        <select v-model="sortBy" @change="sortItems" class="sort-select">
          <option value="name">Name</option>
          <option value="size">Size</option>
          <option value="type">Type</option>
          <option value="mtime">Modified</option>
          <option value="ctime">Created</option>
          <option value="atime">Accessed</option>
        </select>
        <button @click="toggleSortOrder" class="sort-btn" :title="sortAscending ? 'Descending' : 'Ascending'">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path v-if="sortAscending" d="M12 5v14m-5-5l5 5 5-5"></path>
            <path v-else d="M12 19V5m-5 5l5-5 5 5"></path>
          </svg>
        </button>
      </div>
    </div>

    <!-- Drag and Drop Upload Area -->
    <DragDropUpload
      v-if="showUploadArea"
      :project-id="projectId"
      :current-path="currentPath"
      @upload-complete="handleUploadComplete"
      @upload-error="handleUploadError"
    />

    <!-- File Content Area -->
    <div class="fm-content" :class="{ 'grid-view': viewMode === 'grid', 'list-view': viewMode === 'list' }" style="margin-top: 0;">
      <!-- Enhanced list header -->
      <div v-if="viewMode === 'list'" class="list-header" :class="{ mobile: isMobile }">
        <div class="col-select">
          <input type="checkbox" @change="toggleSelectAll" :checked="isAllSelected" />
        </div>
        <div class="col-name" @click="setSortBy('name')">
          Name {{ sortBy === 'name' ? (sortAscending ? '↑' : '↓') : '' }}
        </div>
        <div v-if="!isMobile" class="col-type" @click="setSortBy('type')">
          Type {{ sortBy === 'type' ? (sortAscending ? '↑' : '↓') : '' }}
        </div>
        <div class="col-size" @click="setSortBy('size')">
          Size {{ sortBy === 'size' ? (sortAscending ? '↑' : '↓') : '' }}
        </div>
        <div v-if="!isMobile" class="col-time" @click="setSortBy('mtime')">
          Modified {{ sortBy === 'mtime' ? (sortAscending ? '↑' : '↓') : '' }}
        </div>
        <div v-if="!isMobile" class="col-time" @click="setSortBy('ctime')">
          Created {{ sortBy === 'ctime' ? (sortAscending ? '↑' : '↓') : '' }}
        </div>
        <div v-if="!isMobile" class="col-permissions">
          Permissions
        </div>
        <div v-if="isMobile" class="col-actions">
          ⋯
        </div>
      </div>

      <!-- Empty folder notice -->
      <div v-if="filteredItems.length === 0 && !isLoading" class="empty-state">
        <svg class="empty-icon" width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path>
          <polyline points="13 2 13 9 20 9"></polyline>
          <line x1="10" y1="15" x2="14" y2="15"></line>
        </svg>
        <div class="empty-text">
          {{ searchQuery ? 'No matching files found' : 'This folder is empty' }}
        </div>
        <div class="empty-subtext">
          {{ searchQuery ? 'Try other search keywords' : 'Drag files here or click upload button' }}
        </div>
        <button v-if="!searchQuery" @click="$refs.fileInput.click()" class="upload-btn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="17 8 12 3 7 8"></polyline>
            <line x1="12" y1="3" x2="12" y2="15"></line>
          </svg>
          Upload Files
        </button>
      </div>

      <!-- Virtual Scrolling Container -->
      <div class="virtual-scroll-container" ref="scrollContainer">
        <!-- Enhanced list view -->
        <div v-if="viewMode === 'list'" class="file-list" :class="{ mobile: isMobile }">
          <div 
            v-for="item in visibleItems" 
            :key="item.name" 
            class="file-row" 
            :class="{ 
              selected: isSelected(item), 
              'read-only': !item.permissions?.writable,
              'cut-item': isCutItem(item),
              mobile: isMobile
            }"
            @click="selectItem(item, $event)"
            @dblclick="navigate(item)"
            @contextmenu.stop="showItemContextMenu(item, $event)"
            @touchstart="handleTouchStart(item, $event)"
            @touchend="handleTouchEnd"
            @touchmove="handleTouchMove"
          >
            <div class="col-select">
              <input 
                type="checkbox" 
                @click.stop="toggleSelectItem(item)" 
                :checked="isSelected(item)" 
              />
            </div>
            <div class="col-name">
              <div class="file-icon">
                <img v-if="item.thumbnail" :src="item.thumbnail" class="thumbnail" />
                <svg v-else-if="item.is_dir" class="folder-icon" :width="isMobile ? 24 : 20" :height="isMobile ? 24 : 20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                </svg>
                <div v-else class="icon" v-html="getFileIcon(item.name)"></div>
              </div>
              <div class="file-info">
                <span class="name">{{ item.name }}</span>
                <span v-if="item.extension && !isMobile" class="extension">{{ item.extension.toUpperCase() }}</span>
                <!-- Mobile display time and size -->
                <div v-if="isMobile" class="mobile-meta">
                  <span class="size">{{ formatSize(item.size) }}</span>
                  <span class="time">{{ formatDateTimeShort(item.mtime) }}</span>
              </div>
            </div>
            </div>
            <div v-if="!isMobile" class="col-type">
              <span class="type-badge" :class="getTypeBadgeClass(item.type)">
                {{ getTypeDisplayName(item.type) }}
              </span>
            </div>
            <div class="col-size" :class="{ 'mobile-hidden': isMobile }">{{ formatSize(item.size) }}</div>
            <div v-if="!isMobile" class="col-time">{{ formatDateTime(item.mtime) }}</div>
            <div v-if="!isMobile" class="col-time">{{ formatDateTime(item.ctime) }}</div>
            <div v-if="!isMobile" class="col-permissions">
              <div class="permission-icons">
                <span :class="{ active: item.permissions?.readable }" class="perm-icon read" title="Readable">R</span>
                <span :class="{ active: item.permissions?.writable }" class="perm-icon write" title="Writable">W</span>
                <span :class="{ active: item.permissions?.executable }" class="perm-icon exec" title="Executable">X</span>
              </div>
            </div>
            <div v-if="isMobile" class="col-actions">
              <button @click.stop="showItemContextMenu(item, $event)" class="mobile-menu-btn" title="Menu">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="1"></circle>
                  <circle cx="12" cy="5" r="1"></circle>
                  <circle cx="12" cy="19" r="1"></circle>
                </svg>
              </button>
            </div>
          </div>
        </div>

        <!-- Enhanced grid view -->
        <div v-else class="file-grid" :class="{ mobile: isMobile }">
          <div 
            v-for="item in visibleItems" 
            :key="item.name" 
            class="grid-item" 
            :class="{ 
              selected: isSelected(item), 
              'read-only': !item.permissions?.writable,
              'cut-item': isCutItem(item),
              mobile: isMobile
            }"
            @click="selectItem(item, $event)"
            @dblclick="navigate(item)"
            @contextmenu.stop="showItemContextMenu(item, $event)"
            @touchstart="handleTouchStart(item, $event)"
            @touchend="handleTouchEnd"
            @touchmove="handleTouchMove"
          >
            <div class="grid-icon">
              <img v-if="item.thumbnail" :src="item.thumbnail" class="thumbnail" />
              <svg v-else-if="item.is_dir" class="folder-icon" :width="isMobile ? 40 : 32" :height="isMobile ? 40 : 32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
              <div v-else class="icon" v-html="getFileIcon(item.name)"></div>
            </div>
            <div class="grid-name">{{ item.name }}</div>
            <div class="grid-meta" :class="{ mobile: isMobile }">
              <div class="meta-row">
                <span v-if="!isMobile" class="type-badge" :class="getTypeBadgeClass(item.type)">
                  {{ getTypeDisplayName(item.type) }}
                </span>
                <span class="size">{{ formatSize(item.size) }}</span>
              </div>
              <div class="meta-row" v-if="!isMobile">
                <span class="time">{{ formatDateTimeShort(item.mtime) }}</span>
                <div class="permission-icons small">
                  <span :class="{ active: item.permissions?.readable }" class="perm-icon read">R</span>
                  <span :class="{ active: item.permissions?.writable }" class="perm-icon write">W</span>
                  <span :class="{ active: item.permissions?.executable }" class="perm-icon exec">X</span>
                </div>
              </div>
              <div class="meta-row" v-else>
                <span class="time">{{ formatDateTimeShort(item.mtime) }}</span>
              </div>
            </div>
            <div class="grid-select">
              <input 
                type="checkbox" 
                @click.stop="toggleSelectItem(item)" 
                :checked="isSelected(item)" 
              />
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Mobile menu overlay -->
    <div v-if="isMobile && showMobileMenu" class="mobile-menu-overlay" @click="showMobileMenu = false">
      <div class="mobile-menu" @click.stop>
        <div class="mobile-menu-header">
          <h3>File Operations</h3>
          <button @click="showMobileMenu = false" class="close-btn">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="mobile-menu-content">
          <button @click="showNewFolderModal = true; showMobileMenu = false" class="mobile-menu-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              <line x1="12" y1="11" x2="12" y2="17"></line>
              <line x1="9" y1="14" x2="15" y2="14"></line>
            </svg>
            New Folder
          </button>
          <button @click="refreshItems(); showMobileMenu = false" class="mobile-menu-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="23 4 23 10 17 10"></polyline>
              <polyline points="1 20 1 14 7 14"></polyline>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
            </svg>
            Refresh
          </button>
          <button @click="showDownloadManager = true; showMobileMenu = false" class="mobile-menu-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
            Download Manager
          </button>
          <div v-if="selectedItems.length > 0" class="mobile-menu-divider"></div>
          <button v-if="selectedItems.length > 0" @click="copySelected(); showMobileMenu = false" class="mobile-menu-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
            </svg>
            Copy Selected
          </button>
          <button v-if="selectedItems.length > 0" @click="cutSelected(); showMobileMenu = false" class="mobile-menu-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="6" cy="6" r="3"></circle>
              <circle cx="6" cy="18" r="3"></circle>
              <line x1="20" y1="4" x2="8.12" y2="15.88"></line>
              <line x1="14.47" y1="14.48" x2="20" y2="20"></line>
              <line x1="8.12" y1="8.12" x2="12" y2="12"></line>
            </svg>
            Cut Selected
          </button>
          <button v-if="clipboard.length > 0" @click="pasteItems(); showMobileMenu = false" class="mobile-menu-item">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path>
              <rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect>
            </svg>
            Paste ({{ clipboard.length }} items)
          </button>
          <button v-if="selectedItems.length > 0" @click="deleteSelected(); showMobileMenu = false" class="mobile-menu-item danger">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
            Delete Selected
          </button>
        </div>
      </div>
    </div>

    <!-- Right-click menu -->
    <div v-if="contextMenu.show" class="context-menu" :class="{ mobile: isMobile }" :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }">
      <div class="context-item" @click="openItem" v-if="contextMenu.item">
        <span class="icon">👁️</span> Open
      </div>
      <div class="context-item" @click="copySelected" v-if="selectedItems.length > 0">
        <span class="icon">📋</span> Copy
      </div>
      <div class="context-item" @click="cutSelected" v-if="selectedItems.length > 0">
        <span class="icon">✂️</span> Cut
      </div>
      <div class="context-item" @click="pasteItems" v-if="clipboard.length > 0 && clipboardOperation">
        <span class="icon">📋</span> Paste ({{ clipboardOperation === 'copy' ? 'Copy' : 'Move' }} {{ clipboard.length }} items)
      </div>
      <hr v-if="selectedItems.length > 0" class="context-divider">
      <div class="context-item" @click="showRenameModal = true" v-if="selectedItems.length === 1">
        <span class="icon">✏️</span> Rename
      </div>
      <div class="context-item danger" @click="deleteSelected" v-if="selectedItems.length > 0">
        <span class="icon">🗑</span> Delete
      </div>
      <hr class="context-divider">
      <div class="context-item" @click="showFileDetails" v-if="selectedItems.length === 1">
        <span class="icon">ℹ️</span> Details
      </div>
    </div>

    <!-- File Preview Modal -->
    <FilePreviewModal
      :show-modal="showPreviewModal"
      :file-name="previewFileName"
      :preview-data="previewData"
      :project-id="projectId"
      :file-path="previewFilePath"
      @close="closePreview"
      @save="handlePreviewSave"
      @download="handlePreviewDownload"
    />

    <!-- Modal dialog -->
    <div v-if="showNewFolderModal" class="modal-overlay app-modal-viewport app-modal-backdrop" @click="showNewFolderModal = false">
      <div class="modal app-modal" :class="{ mobile: isMobile }" @click.stop>
        <div class="modal-header app-modal-header">
          <h3>New Folder</h3>
          <button @click="showNewFolderModal = false" class="close-btn app-modal-close">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body app-modal-body">
          <input 
            v-model="newFolderName" 
            placeholder="Enter folder name" 
            @keyup.enter="createNewFolder" 
            class="modal-input"
            :class="{ mobile: isMobile }"
            autofocus 
          />
        </div>
        <div class="modal-footer app-modal-footer">
          <button @click="createNewFolder" class="btn-primary" :class="{ mobile: isMobile }">Create</button>
          <button @click="showNewFolderModal = false" class="btn-cancel" :class="{ mobile: isMobile }">Cancel</button>
        </div>
      </div>
    </div>
    
    <div v-if="showRenameModal" class="modal-overlay app-modal-viewport app-modal-backdrop" @click="showRenameModal = false">
      <div class="modal app-modal" :class="{ mobile: isMobile }" @click.stop>
        <div class="modal-header app-modal-header">
          <h3>Rename</h3>
          <button @click="showRenameModal = false" class="close-btn app-modal-close">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
        <div class="modal-body app-modal-body">
          <input 
            v-model="newRenameName" 
            placeholder="Enter new name" 
            @keyup.enter="renameItem" 
            class="modal-input"
            :class="{ mobile: isMobile }"
            autofocus 
          />
        </div>
        <div class="modal-footer app-modal-footer">
          <button @click="renameItem" class="btn-primary" :class="{ mobile: isMobile }">Confirm</button>
          <button @click="showRenameModal = false" class="btn-cancel" :class="{ mobile: isMobile }">Cancel</button>
        </div>
      </div>
    </div>

    <!-- Loading overlay -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="spinner"></div>
      <div class="loading-text">Loading...</div>
    </div>

    <!-- Upload progress -->
    <div v-if="uploadingFiles.length > 0" class="upload-progress-modal">
      <div class="progress-content">
        <h4>Uploading Files</h4>
        <div v-for="file in uploadingFiles" :key="file.name" class="upload-item">
          <div class="upload-info">
            <span class="file-name">{{ file.name }}</span>
            <span class="progress-text">{{ file.progress.toFixed(1) }}%</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: file.progress + '%' }"></div>
          </div>
        </div>
        <p v-if="uploadError" class="upload-error">Upload error: {{ uploadError }}</p>
      </div>
    </div>

    <!-- Download manager -->
    <DownloadManager
      v-if="showDownloadManager"
      :project-id="projectId"
      :current-path="currentPath"
      @close="showDownloadManager = false"
      @file-downloaded="handleFileDownloaded"
    />

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import DragDropUpload from './DragDropUpload.vue'
import FilePreviewModal from './FilePreviewModal.vue'
import DownloadManager from './DownloadManager.vue'

const route = useRoute()
const projectId = computed(() => route.params.id)

// Core state
const items = ref([])
const currentPath = ref('/')
const selectedItems = ref([])
const isLoading = ref(false)
const focusedItem = ref(null)
const isSearchFocused = ref(false)

// Mobile/Touch support
const isMobile = ref(false)
const isTouch = ref(false)
const longPressTimer = ref(null)
const longPressDelay = 500 // 500ms for long press
const showMobileMenu = ref(false)

// Search and filter
const searchQuery = ref('')
const isSearching = ref(false)
const searchTimeout = ref(null)

// View mode
const viewMode = ref('list') // 'list' or 'grid'
const sortBy = ref('name')
const sortAscending = ref(true)

// Navigation history
const navigationHistory = ref(['/'])
const historyIndex = ref(0)

// Clipboard operations
const clipboard = ref([])
const clipboardOperation = ref('copy') // 'copy' or 'cut'

// Context menu
const contextMenu = ref({
  show: false,
  x: 0,
  y: 0,
  item: null
})

// Upload
const showUploadArea = ref(false)
const uploadingFiles = ref([])
const uploadError = ref(null)

// Preview
const showPreviewModal = ref(false)
const previewFileName = ref('')
const previewData = ref({})
const previewFilePath = ref('')

// Virtual scrolling
const scrollContainer = ref(null)
// Virtual scrolling disabled, keeping variable definition for future re-enabling
// const visibleStartIndex = ref(0)
// const visibleEndIndex = ref(50)
const itemHeight = ref(50)

// Scroll position preservation
const savedScrollPosition = ref(0)

const preserveScrollPosition = () => {
  if (scrollContainer.value) {
    savedScrollPosition.value = scrollContainer.value.scrollTop
  }
}

const restoreScrollPosition = () => {
  if (scrollContainer.value && savedScrollPosition.value > 0) {
    nextTick(() => {
      scrollContainer.value.scrollTop = savedScrollPosition.value
    })
  }
}

// Modals
const showNewFolderModal = ref(false)
const newFolderName = ref('')
const showFetchUrlModal = ref(false)
const fetchUrl = ref('')
const showRenameModal = ref(false)
const newRenameName = ref('')

// Download Manager
const showDownloadManager = ref(false)

const CHUNK_SIZE = 1024 * 1024 * 5 // 5MB chunks

// Computed properties
const filteredItems = computed(() => {
  let filtered = items.value

  // Apply search filter
  if (searchQuery.value) {
    filtered = filtered.filter(item => 
      item.name.toLowerCase().includes(searchQuery.value.toLowerCase())
    )
  }

  // Apply sorting
  filtered.sort((a, b) => {
    let aValue, bValue
    
    switch (sortBy.value) {
      case 'name':
        aValue = a.name.toLowerCase()
        bValue = b.name.toLowerCase()
        break
      case 'size':
        aValue = a.size
        bValue = b.size
        break
      case 'mtime':
        aValue = a.mtime
        bValue = b.mtime
        break
      case 'ctime':
        aValue = a.ctime
        bValue = b.ctime
        break
      case 'atime':
        aValue = a.atime
        bValue = b.atime
        break
      case 'type':
        aValue = a.type || (a.is_dir ? 'folder' : 'file')
        bValue = b.type || (b.is_dir ? 'folder' : 'file')
        break
      default:
        aValue = a.name.toLowerCase()
        bValue = b.name.toLowerCase()
    }

    // Directories always come first
    if (a.is_dir && !b.is_dir) return -1
    if (!a.is_dir && b.is_dir) return 1

    let comparison = 0
    if (aValue < bValue) comparison = -1
    if (aValue > bValue) comparison = 1
    
    return sortAscending.value ? comparison : -comparison
  })

  return filtered
})

const visibleItems = computed(() => {
  // Return all filtered items directly, disable virtual scrolling
  // For most project directories, the file count won't be too large, directly showing all items is more stable
  return filteredItems.value
})

const breadcrumbs = computed(() => {
  const pathParts = currentPath.value.split('/').filter(p => p !== '')
  let current = ''
  return pathParts.map(part => {
    current += `/${part}`
    return { name: part, path: current }
  })
})

const isAllSelected = computed(() => 
  filteredItems.value.length > 0 && selectedItems.value.length === filteredItems.value.length
)

const canGoBack = computed(() => historyIndex.value > 0)
const canGoForward = computed(() => historyIndex.value < navigationHistory.value.length - 1)

// Methods
const fetchItems = async () => {
  // Save current scroll position
  preserveScrollPosition()
  
  isLoading.value = true
  try {
    const response = await fetch(`/api/filemanager/${projectId.value}/list?path=${currentPath.value}`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const data = await response.json()
    
    // Handle both old format (array) and new format (object with items property)
    const itemsArray = Array.isArray(data) ? data : (data.items || [])
    
    items.value = itemsArray.map(item => ({
      ...item,
      thumbnail: generateThumbnail(item)
    }))
    
    // Restore scroll position (delayed to ensure DOM update completion)
    setTimeout(() => {
      restoreScrollPosition()
    }, 100)
  } catch (error) {
    console.error('Error fetching items:', error)
    alert(`Failed to load directory contents: ${error.message}`)
  } finally {
    isLoading.value = false
  }
}

const generateThumbnail = (item) => {
  if (item.is_dir) return null
  
  const ext = getFileExtension(item.name).toLowerCase()
  if (['png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'].includes(ext)) {
    return `/api/filemanager/${projectId.value}/thumbnail?path=${currentPath.value}/${item.name}&size=128`
  }
  return null
}

const navigate = (item) => {
  if (item.is_dir) {
    const newPath = `${currentPath.value === '/' ? '' : currentPath.value}/${item.name}`
    navigateTo(newPath)
  } else {
    previewItem(item)
  }
}

const navigateTo = (path) => {
  // Update navigation history
  if (historyIndex.value < navigationHistory.value.length - 1) {
    navigationHistory.value = navigationHistory.value.slice(0, historyIndex.value + 1)
  }
  navigationHistory.value.push(path)
  historyIndex.value = navigationHistory.value.length - 1
  
  currentPath.value = path
  selectedItems.value = []
  
  // Reset scroll position (new directory should start from top)
  savedScrollPosition.value = 0
  
  fetchItems()
}

const goUp = () => {
  const pathParts = currentPath.value.split('/').filter(p => p !== '')
  if (pathParts.length > 0) {
    const newPath = '/' + pathParts.slice(0, -1).join('/')
    navigateTo(newPath === '/' ? '/' : newPath)
  }
}

const goBack = () => {
  if (canGoBack.value) {
    historyIndex.value--
    currentPath.value = navigationHistory.value[historyIndex.value]
    selectedItems.value = []
    fetchItems()
  }
}

const goForward = () => {
  if (canGoForward.value) {
    historyIndex.value++
    currentPath.value = navigationHistory.value[historyIndex.value]
    selectedItems.value = []
    fetchItems()
  }
}

const refreshItems = () => {
  fetchItems()
}

const setViewMode = (mode) => {
  viewMode.value = mode
  localStorage.setItem('filemanager-view-mode', mode)
}

const sortItems = () => {
  // Sorting is handled by the computed property
}

const toggleSortOrder = () => {
  sortAscending.value = !sortAscending.value
}

const handleSearch = () => {
  isSearching.value = true
  clearTimeout(searchTimeout.value)
  searchTimeout.value = setTimeout(() => {
    isSearching.value = false
  }, 500)
}

const selectItem = (item, event) => {
  if (event.ctrlKey || event.metaKey) {
    // Multi-select
    toggleSelectItem(item)
  } else if (event.shiftKey && selectedItems.value.length > 0) {
    // Range select
    const lastSelected = selectedItems.value[selectedItems.value.length - 1]
    const startIndex = filteredItems.value.findIndex(i => i.name === lastSelected.name)
    const endIndex = filteredItems.value.findIndex(i => i.name === item.name)
    const start = Math.min(startIndex, endIndex)
    const end = Math.max(startIndex, endIndex)
    
    selectedItems.value = filteredItems.value.slice(start, end + 1)
  } else {
    // Single select
    selectedItems.value = [item]
  }
  
  focusedItem.value = item.name
}

const toggleSelectItem = (item) => {
  const index = selectedItems.value.findIndex(i => i.name === item.name)
  if (index > -1) {
    selectedItems.value.splice(index, 1)
  } else {
    selectedItems.value.push(item)
  }
}

const isSelected = (item) => selectedItems.value.some(i => i.name === item.name)

const isCutItem = (item) => {
  if (clipboardOperation.value !== 'cut') return false
  const itemPath = `${currentPath.value === '/' ? '' : currentPath.value}/${item.name}`
  return clipboard.value.some(clipItem => clipItem.fullPath === itemPath)
}

const toggleSelectAll = (event) => {
  if (event.target.checked) {
    selectedItems.value = [...filteredItems.value]
  } else {
    selectedItems.value = []
  }
}

const copySelected = () => {
  // Store complete file path information, not just file objects
  clipboard.value = selectedItems.value.map(item => ({
    ...item,
    fullPath: `${currentPath.value === '/' ? '' : currentPath.value}/${item.name}`
  }))
  clipboardOperation.value = 'copy'
  console.log('Files copied:', clipboard.value.map(item => item.fullPath))
}

const cutSelected = () => {
  // Store complete file path information, not just file objects
  clipboard.value = selectedItems.value.map(item => ({
    ...item,
    fullPath: `${currentPath.value === '/' ? '' : currentPath.value}/${item.name}`
  }))
  clipboardOperation.value = 'cut'
  console.log('Files cut:', clipboard.value.map(item => item.fullPath))
}

const clearClipboard = () => {
  clipboard.value = []
  clipboardOperation.value = ''
  console.log('Clipboard cleared')
}

const pasteItems = async () => {
  if (clipboard.value.length === 0) return
  
  isLoading.value = true
  try {
    const operation = clipboardOperation.value
    // Use saved full path as source path
    const items = clipboard.value.map(item => item.fullPath || item.name)
    
    console.log(`${operation === 'copy' ? 'Copying' : 'Moving'} files:`, items)
    console.log(`Target directory: ${currentPath.value}`)
    
    const response = await fetch(`/api/filemanager/${projectId.value}/${operation}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items, destination: currentPath.value })
    })
    
    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`)
    }
    
    const result = await response.json()
    console.log(`${operation === 'copy' ? 'Copy' : 'Move'} successful:`, result)
    
    // Clear clipboard after successful cut operation
    if (operation === 'cut') {
      clipboard.value = []
      clipboardOperation.value = ''
    }
    
    fetchItems()
  } catch (error) {
    console.error('Error pasting items:', error)
    alert(`Paste failed: ${error.message}`)
  } finally {
    isLoading.value = false
  }
}

const deleteSelected = async () => {
  if (!confirm(`Are you sure you want to delete ${selectedItems.value.length} item(s)?`)) return
  
  isLoading.value = true
  try {
    const paths = selectedItems.value.map(item => 
      `${currentPath.value === '/' ? '' : currentPath.value}/${item.name}`
    )
    
    const response = await fetch(`/api/filemanager/${projectId.value}/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: paths })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    selectedItems.value = []
    fetchItems()
  } catch (error) {
    console.error('Error deleting items:', error)
    alert(`Failed to delete items: ${error.message}`)
  } finally {
    isLoading.value = false
  }
}

const downloadSelected = async () => {
  isLoading.value = true
  try {
    const paths = selectedItems.value.map(item => 
      `${currentPath.value === '/' ? '' : currentPath.value}/${item.name}`
    )
    
    const response = await fetch(`/api/filemanager/${projectId.value}/download-zip`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items: paths })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `archive_${Date.now()}.zip`
    document.body.appendChild(a)
    a.click()
    a.remove()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Error downloading items:', error)
    alert(`Failed to download items: ${error.message}`)
  } finally {
    isLoading.value = false
  }
}

const createNewFolder = async () => {
  if (!newFolderName.value.trim()) return
  
  isLoading.value = true
  try {
    const response = await fetch(`/api/filemanager/${projectId.value}/mkdir`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        path: `${currentPath.value === '/' ? '' : currentPath.value}/${newFolderName.value}` 
      })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    showNewFolderModal.value = false
    newFolderName.value = ''
    fetchItems()
  } catch (error) {
    console.error('Error creating folder:', error)
    alert(`Failed to create folder: ${error.message}`)
  } finally {
    isLoading.value = false
  }
}

const renameItem = async () => {
  if (selectedItems.value.length !== 1 || !newRenameName.value.trim()) return
  
  isLoading.value = true
  try {
    const oldPath = `${currentPath.value === '/' ? '' : currentPath.value}/${selectedItems.value[0].name}`
    const newPath = `${currentPath.value === '/' ? '' : currentPath.value}/${newRenameName.value}`
    
    const response = await fetch(`/api/filemanager/${projectId.value}/rename`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_path: oldPath, new_path: newPath })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    showRenameModal.value = false
    newRenameName.value = ''
    selectedItems.value = []
    fetchItems()
  } catch (error) {
    console.error('Error renaming item:', error)
    alert(`Failed to rename item: ${error.message}`)
  } finally {
    isLoading.value = false
  }
}

const fetchFile = async () => {
  if (!fetchUrl.value.trim()) return
  
  isLoading.value = true
  try {
    const response = await fetch(`/api/filemanager/${projectId.value}/fetch-url`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        url: fetchUrl.value, 
        path: currentPath.value === '/' ? '' : currentPath.value 
      })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    showFetchUrlModal.value = false
    fetchUrl.value = ''
    fetchItems()
  } catch (error) {
    console.error('Error fetching file:', error)
    alert(`Failed to fetch file from URL: ${error.message}`)
  } finally {
    isLoading.value = false
  }
}

const previewItem = async (item) => {
  if (item.is_dir) return
  
  previewFileName.value = item.name
  previewFilePath.value = `${currentPath.value === '/' ? '' : currentPath.value}/${item.name}`
  
  isLoading.value = true
  try {
    const response = await fetch(`/api/filemanager/${projectId.value}/preview?path=${previewFilePath.value}`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const data = await response.json()
    
    // Handle large files
    if (data.error && data.error.includes('too large')) {
      const fileFormat = getFileFormat(item.name)
      const isBioFile = ['fasta', 'fastq', 'vcf', 'gff', 'gtf', 'bed', 'sam', 'bam'].includes(fileFormat)
      
      previewData.value = {
        type: isBioFile ? 'bioinformatics' : 'text',
        file_format: fileFormat,
        file_size: item.size,
        too_large: true,
        error: data.error,
        mimetype: data.mimetype || `text/${fileFormat}`
      }
    } else if (data.type === 'image') {
      previewData.value = { ...data, content: data.url }
    } else {
      previewData.value = data
    }
    
    showPreviewModal.value = true
  } catch (error) {
    console.error('Error previewing item:', error)
    alert(`Failed to preview item: ${error.message}`)
  } finally {
    isLoading.value = false
  }
}

// Helper function to determine file format
const getFileFormat = (fileName) => {
  const ext = getFileExtension(fileName).toLowerCase()
  const bioFormats = {
    'fasta': 'fasta',
    'fa': 'fasta',
    'fas': 'fasta',
    'fastq': 'fastq',
    'fq': 'fastq',
    'vcf': 'vcf',
    'gff': 'gff',
    'gff3': 'gff',
    'gtf': 'gtf',
    'bed': 'bed',
    'sam': 'sam',
    'bam': 'bam'
  }
  return bioFormats[ext] || 'unknown'
}

const closePreview = () => {
  showPreviewModal.value = false
  previewData.value = {}
}

const handlePreviewSave = ({ path, content }) => {
  // Refresh items after save
  fetchItems()
}

const handlePreviewDownload = ({ fileName, filePath }) => {
  // Implement download functionality
  const link = document.createElement('a')
  link.href = `/api/filemanager/${projectId.value}/download?path=${filePath}`
  link.download = fileName
  link.click()
}

const handleFileUpload = async (event) => {
  const files = Array.from(event.target.files)
  uploadingFiles.value = files.map(file => ({ name: file.name, progress: 0 }))
  uploadError.value = null
  isLoading.value = true

  for (let i = 0; i < files.length; i++) {
    const file = files[i]
    try {
      await uploadFileInChunks(file, i)
    } catch (error) {
      uploadError.value = `Failed to upload ${file.name}: ${error.message}`
      console.error('Upload error:', error)
      break
    }
  }
  
  uploadingFiles.value = []
  isLoading.value = false
  fetchItems()
}

const uploadFileInChunks = async (file, fileIndex) => {
  const totalChunks = Math.ceil(file.size / CHUNK_SIZE)
  
  for (let chunkNumber = 0; chunkNumber < totalChunks; chunkNumber++) {
    const start = chunkNumber * CHUNK_SIZE
    const end = Math.min(start + CHUNK_SIZE, file.size)
    const chunk = file.slice(start, end)

    const formData = new FormData()
    formData.append('file', chunk)
    formData.append('chunkNumber', chunkNumber + 1)
    formData.append('totalChunks', totalChunks)
    formData.append('filename', file.name)
    formData.append('path', currentPath.value === '/' ? '' : currentPath.value)

    const response = await fetch(`/api/filemanager/${projectId.value}/upload-chunk`, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const errorData = await response.json()
      throw new Error(errorData.error || 'Upload failed')
    }

    uploadingFiles.value[fileIndex].progress = ((chunkNumber + 1) / totalChunks) * 100
  }
}

const handleUploadComplete = () => {
  showUploadArea.value = false
  fetchItems()
}

const handleUploadError = (error) => {
  console.error('Upload error:', error)
  alert(`Upload failed: ${error.message}`)
}

const handleFileDownloaded = (filename) => {
  console.log('File downloaded:', filename)
  // Refresh file list to display newly downloaded files
  fetchItems()
  // Can add download completion notification
  // showNotification('File download completed', `${filename} has been successfully downloaded to current directory`)
}

const showContextMenu = (event) => {
  event.preventDefault()
  contextMenu.value = {
    show: true,
    x: event.clientX,
    y: event.clientY,
    item: null
  }
}

const showItemContextMenu = (item, event) => {
  event.preventDefault()
  contextMenu.value = {
    show: true,
    x: event.clientX,
    y: event.clientY,
    item: item
  }
}

const hideContextMenu = () => {
  contextMenu.value.show = false
  if (isMobile.value) {
    showMobileMenu.value = false
  }
}

const openItem = () => {
  if (contextMenu.value.item) {
    navigate(contextMenu.value.item)
  }
  hideContextMenu()
}

const handleScroll = () => {
  // Virtual scrolling disabled, keeping this function for future re-enabling if needed
  // Now just an empty function, performs no operation
}

const isEditableTarget = (event) => {
  const target = event.target
  if (!target) return false
  const tagName = target.tagName ? target.tagName.toLowerCase() : ''
  if (['input', 'textarea', 'select'].includes(tagName)) return true
  return Boolean(target.isContentEditable)
}

const handleKeyDown = (event) => {
  if (isEditableTarget(event)) return
  // Keyboard shortcuts
  if (event.ctrlKey || event.metaKey) {
    switch (event.key) {
      case 'c':
        event.preventDefault()
        copySelected()
        break
      case 'x':
        event.preventDefault()
        cutSelected()
        break
      case 'v':
        event.preventDefault()
        pasteItems()
        break
      case 'a':
        event.preventDefault()
        selectedItems.value = [...filteredItems.value]
        break
      case 'u':
        event.preventDefault()
        document.querySelector('input[type="file"]').click()
        break
      case 'd':
        event.preventDefault()
        downloadSelected()
        break
    }
  } else if (event.ctrlKey && event.shiftKey) {
    switch (event.key) {
      case 'N':
        event.preventDefault()
        showNewFolderModal.value = true
        break
    }
  } else if (event.altKey) {
    switch (event.key) {
      case 'ArrowUp':
        event.preventDefault()
        goUp()
        break
      case 'ArrowLeft':
        event.preventDefault()
        goBack()
        break
      case 'ArrowRight':
        event.preventDefault()
        goForward()
        break
    }
  } else {
    switch (event.key) {
      case 'Delete':
        event.preventDefault()
        deleteSelected()
        break
      case 'F2':
        event.preventDefault()
        if (selectedItems.value.length === 1) {
          showRenameModal.value = true
        }
        break
      case 'F5':
        event.preventDefault()
        refreshItems()
        break
      case 'Enter':
        event.preventDefault()
        if (selectedItems.value.length === 1) {
          navigate(selectedItems.value[0])
        }
        break
    }
  }
}

// Utility functions
const getFileIcon = (fileName) => {
  const ext = getFileExtension(fileName).toLowerCase()
  const iconClass = getFileIconClass(ext)
  return `<svg class="file-type-icon ${iconClass}" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    ${getFileIconSvg(ext)}
  </svg>`
}

const getFileIconClass = (ext) => {
  const classMap = {
    // Text/Documents
    txt: 'icon-text', log: 'icon-text', md: 'icon-text',
    pdf: 'icon-pdf', doc: 'icon-doc', docx: 'icon-doc',
    xls: 'icon-excel', xlsx: 'icon-excel', csv: 'icon-excel',
    // Code
    js: 'icon-code', ts: 'icon-code', jsx: 'icon-code', tsx: 'icon-code',
    py: 'icon-code', java: 'icon-code', cpp: 'icon-code', c: 'icon-code',
    html: 'icon-web', css: 'icon-web', scss: 'icon-web',
    // Images
    png: 'icon-image', jpg: 'icon-image', jpeg: 'icon-image', gif: 'icon-image', svg: 'icon-image',
    // Archives
    zip: 'icon-archive', tar: 'icon-archive', gz: 'icon-archive', rar: 'icon-archive',
    // Bioinformatics
    fasta: 'icon-bio', fastq: 'icon-bio', vcf: 'icon-bio', gff: 'icon-bio', bed: 'icon-bio'
  }
  return classMap[ext] || 'icon-default'
}

const getFileIconSvg = (ext) => {
  const iconMap = {
    // Default file icon
    default: '<path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"></path><polyline points="13 2 13 9 20 9"></polyline>',
    // Code/Text
    code: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline>',
    // Image
    image: '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline>',
    // Archive
    archive: '<polyline points="21 8 21 21 3 21 3 8"></polyline><rect x="1" y="3" width="22" height="5"></rect><line x1="10" y1="12" x2="14" y2="12"></line>',
    // Bio
    bio: '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"></path>'
  }
  
  const typeMap = {
    // Text/Documents
    txt: 'code', log: 'code', md: 'code',
    // Code
    js: 'code', ts: 'code', py: 'code', java: 'code',
    html: 'code', css: 'code',
    // Images
    png: 'image', jpg: 'image', jpeg: 'image', gif: 'image', svg: 'image',
    // Archives
    zip: 'archive', tar: 'archive', gz: 'archive',
    // Bio
    fasta: 'bio', fastq: 'bio', vcf: 'bio'
  }
  
  const iconType = typeMap[ext] || 'default'
  return iconMap[iconType] || iconMap.default
}

const getFileExtension = (filename) => {
  return filename.split('.').pop() || ''
}

const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp * 1000)
  return date.toLocaleString()
}

const formatDateTime = (timestamp) => {
  if (!timestamp) return '—'
  const date = new Date(timestamp * 1000)
  const now = new Date()
  const diffMs = now - date
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffDays === 0) {
    return 'Today ' + date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  } else if (diffDays === 1) {
    return 'Yesterday ' + date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  } else if (diffDays < 7) {
    return `${diffDays} days ago`
  } else {
    return date.toLocaleDateString('en-US') + ' ' + date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  }
}

const formatDateTimeShort = (timestamp) => {
  if (!timestamp) return '—'
  const date = new Date(timestamp * 1000)
  const now = new Date()
  const diffMs = now - date
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  if (diffDays === 0) {
    return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
  } else if (diffDays < 7) {
    return `${diffDays} days ago`
  } else {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }
}

const getTypeDisplayName = (type) => {
  const typeMap = {
    'folder': 'Folder',
    'fasta': 'FASTA',
    'fastq': 'FASTQ', 
    'vcf': 'VCF',
    'gff': 'GFF',
    'bed': 'BED',
    'sam': 'SAM',
    'bam': 'BAM',
    'file': 'File',
    'image': 'Image',
    'document': 'Document',
    'archive': 'Archive',
    'code': 'Code'
  }
  return typeMap[type] || 'File'
}

const getTypeBadgeClass = (type) => {
  const classMap = {
    'folder': 'type-folder',
    'fasta': 'type-bio',
    'fastq': 'type-bio',
    'vcf': 'type-bio',
    'gff': 'type-bio',
    'bed': 'type-bio',
    'sam': 'type-bio',
    'bam': 'type-bio',
    'image': 'type-image',
    'document': 'type-document',
    'archive': 'type-archive',
    'code': 'type-code',
    'file': 'type-default'
  }
  return classMap[type] || 'type-default'
}

const setSortBy = (field) => {
  if (sortBy.value === field) {
    sortAscending.value = !sortAscending.value
  } else {
    sortBy.value = field
    sortAscending.value = true
  }
  sortItems()
}

const showFileDetails = () => {
  if (selectedItems.value.length === 1) {
    const item = selectedItems.value[0]
    const details = [
      `Name: ${item.name}`,
      `Type: ${getTypeDisplayName(item.type)}`,
      `Size: ${formatSize(item.size)}`,
      `Modified: ${formatDateTime(item.mtime)}`,
      `Created: ${formatDateTime(item.ctime)}`,
      `Accessed: ${formatDateTime(item.atime)}`,
      `Permissions: ${item.permissions?.readable ? 'R' : ''}${item.permissions?.writable ? 'W' : ''}${item.permissions?.executable ? 'X' : ''}`
    ].join('\n')
    
    alert(details)
  }
  hideContextMenu()
}

// Lifecycle
// Mobile detection and touch support
const detectMobile = () => {
  const userAgent = navigator.userAgent.toLowerCase()
  const mobileKeywords = ['mobile', 'iphone', 'android', 'blackberry', 'nokia', 'opera mini', 'windows mobile', 'windows phone', 'iemobile']
  isMobile.value = mobileKeywords.some(keyword => userAgent.includes(keyword)) || window.innerWidth <= 768
  isTouch.value = 'ontouchstart' in window || navigator.maxTouchPoints > 0
}

// Handle window resize for responsive behavior
const handleResize = () => {
  detectMobile()
}

// Touch event handlers
const handleTouchStart = (item, event) => {
  if (!isTouch.value) return
  
  clearTimeout(longPressTimer.value)
  longPressTimer.value = setTimeout(() => {
    // Long press detected - show context menu
    showItemContextMenu(item, {
      clientX: event.touches[0].clientX,
      clientY: event.touches[0].clientY,
      preventDefault: () => {}
    })
  }, longPressDelay)
}

const handleTouchEnd = () => {
  clearTimeout(longPressTimer.value)
}

const handleTouchMove = () => {
  clearTimeout(longPressTimer.value)
}

onMounted(() => {
  fetchItems()
  
  // Detect mobile and touch capabilities
  detectMobile()
  
  // Load saved view mode
  const savedViewMode = localStorage.getItem('filemanager-view-mode')
  if (savedViewMode) {
    viewMode.value = savedViewMode
  }
  
  // Set default view mode for mobile
  if (isMobile.value && !savedViewMode) {
    viewMode.value = 'grid'
  }
  
  // Add global event listeners
  document.addEventListener('click', hideContextMenu)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  document.removeEventListener('click', hideContextMenu)
  window.removeEventListener('resize', handleResize)
  clearTimeout(longPressTimer.value)
})

// Watchers
watch(currentPath, fetchItems)
</script>

<style scoped>
/* Modern UI styles */
* {
  box-sizing: border-box;
}

.filemanager-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: calc(100vh - 100px);
  max-height: 100%;
  background: var(--surface-0);
  font-family: var(--font-family-base);
  color: var(--gray-900);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow: hidden;
}

/* Header styles */
.fm-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-4) var(--spacing-6);
  background: var(--surface-1);
  border-bottom: var(--border-width) solid var(--border-color-light);
  min-height: 64px;
  box-shadow: var(--shadow-xs);
}

.breadcrumbs {
  display: flex;
  align-items: center;
  gap: var(--spacing-2);
}

.breadcrumb-home {
  background: none;
  border: none;
  padding: var(--spacing-2);
  border-radius: var(--radius-base);
  cursor: pointer;
  color: var(--gray-500);
  transition: all var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
}

.breadcrumb-home:hover {
  background: var(--surface-2);
  color: var(--gray-900);
}

.breadcrumb-sep {
  color: var(--gray-300);
  margin: 0 var(--spacing-1);
  opacity: 0.5;
}

.breadcrumb-btn {
  background: none;
  border: none;
  padding: var(--spacing-2) var(--spacing-3);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--primary-600);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  transition: all var(--transition-base);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.breadcrumb-btn:hover {
  background: rgba(var(--accent-rgb), 0.1);
  color: var(--primary-700);
}

.download-btn {
  background: var(--success-500) !important;
  color: white !important;
  border-color: var(--success-500) !important;
}

.download-btn:hover {
  background: var(--success-600) !important;
  border-color: var(--success-600) !important;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-3);
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
}

.search-input {
  width: 280px;
  padding: var(--spacing-3) var(--spacing-10) var(--spacing-3) var(--spacing-10);
  border: var(--border-width) solid var(--border-color);
  border-radius: var(--radius-base);
  font-size: var(--text-sm);
  background: var(--surface-2);
  transition: all var(--transition-base);
}

.search-input:focus {
  outline: none;
  border-color: var(--primary-500);
  background: var(--surface-1);
  box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.16);
  width: 320px;
}

.search-input.focused {
  border-color: var(--primary-500);
  background: var(--surface-1);
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--gray-400);
  pointer-events: none;
}

.clear-search {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--gray-400);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.clear-search:hover {
  background: var(--surface-3);
  color: var(--gray-600);
}

.view-toggle {
  display: flex;
  gap: 0;
  background: var(--surface-3);
  border-radius: var(--radius-base);
  padding: 2px;
}

.toggle-btn {
  background: none;
  border: none;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--gray-600);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toggle-btn:hover {
  color: var(--gray-900);
}

.toggle-btn.active {
  background: var(--surface-1);
  color: var(--primary-600);
  box-shadow: var(--shadow-xs);
}

/* Toolbar styles */
.fm-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-3) var(--spacing-6);
  background: var(--surface-1);
  border-bottom: var(--border-width) solid var(--border-color-light);
  gap: var(--spacing-4);
  flex-wrap: wrap;
}

.nav-group {
  display: flex;
  gap: var(--spacing-1);
  background: var(--surface-2);
  padding: var(--spacing-1);
  border-radius: var(--radius-base);
}

.nav-btn {
  background: transparent;
  border: none;
  padding: var(--spacing-2);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--gray-500);
  transition: all var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-btn:hover:not(:disabled) {
  background: var(--surface-1);
  color: var(--gray-900);
  box-shadow: var(--shadow-xs);
}

.nav-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.actions-group {
  display: flex;
  gap: 8px;
}

.action-btn {
  background: var(--surface-1);
  border: 1px solid var(--border-color);
  padding: 8px 14px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--gray-700);
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.action-btn:hover {
  background: var(--surface-2);
  border-color: var(--border-color-dark);
  transform: translateY(-1px);
}

.action-btn.primary {
  background: var(--gradient-primary);
  border-color: transparent;
  color: white;
}

.action-btn.primary:hover {
  background: linear-gradient(135deg, #1d4ed8 0%, #0ea5e9 100%);
  box-shadow: 0 10px 18px rgba(var(--accent-rgb), 0.2);
}

.action-btn.rotating svg {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.selection-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 12px;
  background: rgba(var(--accent-rgb), 0.12);
  border: 1px solid rgba(var(--accent-rgb), 0.25);
  border-radius: 8px;
  font-size: 13px;
  color: var(--primary-700);
  font-weight: 500;
}

.selection-actions {
  display: flex;
  gap: 6px;
}

/* Clipboard information */
.clipboard-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 12px;
  background: var(--warning-50);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 8px;
  font-size: 13px;
  color: var(--warning-600);
  font-weight: 500;
}

.mini-btn {
  background: var(--surface-1);
  border: 1px solid rgba(var(--accent-rgb), 0.2);
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--primary-600);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mini-btn:hover {
  background: var(--surface-2);
  border-color: rgba(var(--accent-rgb), 0.3);
  transform: translateY(-1px);
}

.mini-btn.danger {
  color: var(--error-600);
  border-color: rgba(239, 68, 68, 0.3);
}

.mini-btn.danger:hover {
  background: var(--error-50);
  border-color: rgba(239, 68, 68, 0.45);
}

.sort-group {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface-2);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-color-light);
}

.sort-label {
  font-size: 13px;
  color: var(--gray-600);
  font-weight: 500;
}

.sort-select {
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 13px;
  background: var(--surface-1);
  color: var(--gray-700);
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.sort-select:hover {
  border-color: var(--border-color-dark);
}

.sort-select:focus {
  outline: none;
  border-color: var(--primary-500);
  box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.16);
}

.sort-btn {
  background: var(--surface-1);
  border: 1px solid var(--border-color);
  padding: 6px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--gray-600);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sort-btn:hover {
  background: var(--surface-2);
  border-color: var(--border-color-dark);
}

/* Content area */
.fm-content {
  flex: 1;
  overflow: hidden;
  background: var(--surface-1);
  min-height: 0;
}

.virtual-scroll-container {
  height: 100%;
  overflow-y: auto;
  scroll-behavior: smooth;
  padding-bottom: 20px;
}

/* Custom scrollbar */
.virtual-scroll-container::-webkit-scrollbar {
  width: 12px;
  height: 12px;
}

.virtual-scroll-container::-webkit-scrollbar-track {
  background: var(--surface-2);
  border-radius: var(--radius-sm);
  margin: 4px 0;
}

.virtual-scroll-container::-webkit-scrollbar-thumb {
  background: var(--gray-300);
  border-radius: var(--radius-sm);
  border: 2px solid var(--surface-2);
}

.virtual-scroll-container::-webkit-scrollbar-thumb:hover {
  background: var(--gray-400);
}

/* List header */
.list-header {
  display: grid;
  grid-template-columns: 40px 2fr 80px 100px 140px 140px 100px;
  gap: 12px;
  padding: 14px 20px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border-color-light);
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-600);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  position: sticky;
  top: 0;
  z-index: 10;
  border-top-left-radius: 12px;
  border-top-right-radius: 12px;
}

.list-header > div {
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 4px;
}

.list-header > div:hover {
  color: var(--primary-600);
}

/* File list */
.file-list {
  padding: 4px 0 40px 0;
}

.file-row {
  display: grid;
  grid-template-columns: 40px 2fr 80px 100px 140px 140px 100px;
  gap: 12px;
  padding: 10px 20px;
  align-items: center;
  cursor: pointer;
  transition: all 0.15s;
  margin: 0 10px;
  border-radius: 0;
  border-bottom: 1px solid var(--border-color-light);
}

.file-row.read-only {
  opacity: 0.65;
}

.file-row:hover {
  background: var(--surface-2);
  margin: 0 8px;
  padding: 10px 22px;
  border-radius: var(--radius-sm);
  border-bottom-color: transparent;
}

.file-row.selected {
  background: rgba(var(--accent-rgb), 0.12);
  border: 1px solid rgba(var(--accent-rgb), 0.3);
  margin: 0 8px;
  padding: 9px 21px;
  border-radius: var(--radius-sm);
}

.col-name {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.file-icon {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 4px;
}

.folder-icon {
  color: var(--primary-600);
}

.file-type-icon.icon-text { color: #6b7280; }
.file-type-icon.icon-code { color: #8b5cf6; }
.file-type-icon.icon-web { color: #f59e0b; }
.file-type-icon.icon-image { color: #10b981; }
.file-type-icon.icon-archive { color: #6366f1; }
.file-type-icon.icon-bio { color: #06b6d4; }
.file-type-icon.icon-pdf { color: #ef4444; }
.file-type-icon.icon-doc { color: var(--primary-600); }
.file-type-icon.icon-excel { color: #10b981; }
.file-type-icon.icon-default { color: var(--gray-400); }

.name {
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.extension {
  font-size: 10px;
  color: var(--gray-400);
  font-weight: 400;
}

.col-size, .col-time {
  font-size: 12px;
  color: var(--gray-600);
}

.col-type {
  display: flex;
  align-items: center;
}

.type-badge {
  display: inline-block;
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  transition: all 0.2s;
}

.type-folder { 
  background: #dbeafe; 
  color: #1d4ed8; 
  border: 1px solid #bfdbfe;
}
.type-bio { 
  background: #d1fae5; 
  color: #065f46; 
  border: 1px solid #a7f3d0;
}
.type-image { 
  background: #fef3c7; 
  color: #92400e; 
  border: 1px solid #fde68a;
}
.type-document { 
  background: #e0e7ff; 
  color: #3730a3; 
  border: 1px solid #c7d2fe;
}
.type-archive { 
  background: #f3e8ff; 
  color: #6b21a8; 
  border: 1px solid #e9d5ff;
}
.type-code { 
  background: #fce7f3; 
  color: #be185d; 
  border: 1px solid #fbcfe8;
}
.type-default { 
  background: #f3f4f6; 
  color: #374151; 
  border: 1px solid #e5e7eb;
}

.permission-icons {
  display: flex;
  gap: 2px;
}

.permission-icons.small {
  gap: 1px;
}

.perm-icon {
  display: inline-block;
  width: 16px;
  height: 16px;
  line-height: 16px;
  text-align: center;
  font-size: 10px;
  font-weight: 600;
  border-radius: 2px;
  background: var(--surface-2);
  color: var(--gray-400);
  transition: all 0.2s;
}

.permission-icons.small .perm-icon {
  width: 12px;
  height: 12px;
  line-height: 12px;
  font-size: 8px;
}

.perm-icon.active.read { background: #dbeafe; color: #1d4ed8; }
.perm-icon.active.write { background: #d1fae5; color: #065f46; }
.perm-icon.active.exec { background: #fef3c7; color: #92400e; }

/* Grid view */
.file-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 16px;
  padding: 20px 20px 60px 20px;
}

.grid-item {
  position: relative;
  background: var(--surface-1);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-md);
  padding: 16px 12px 12px;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s;
  overflow: hidden;
}

.grid-item:hover {
  border-color: rgba(var(--accent-rgb), 0.3);
  box-shadow: var(--shadow-sm);
  transform: translateY(-2px);
}

.grid-item.selected {
  border-color: rgba(var(--accent-rgb), 0.35);
  background: rgba(var(--accent-rgb), 0.1);
  box-shadow: 0 0 0 2px rgba(var(--accent-rgb), 0.16);
}

.grid-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.grid-icon svg {
  width: 32px;
  height: 32px;
}

.grid-name {
  font-size: 12px;
  font-weight: 500;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.grid-meta {
  font-size: 10px;
  color: var(--gray-600);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 4px;
}

.grid-item.read-only {
  opacity: 0.7;
  border-style: dashed;
}

/* Visual effects for cut files */
.file-row.cut-item {
  opacity: 0.5;
  background: var(--warning-50);
  border-left: 3px solid var(--warning-500);
}

.grid-item.cut-item {
  opacity: 0.5;
  background: var(--warning-50);
  border: 2px dashed var(--warning-500);
}

.time {
  font-size: 9px;
  color: var(--gray-400);
}

.grid-select {
  position: absolute;
  top: 6px;
  right: 6px;
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 400px;
  gap: 16px;
  padding: 40px;
}

.empty-icon {
  color: var(--gray-300);
  margin-bottom: 8px;
}

.empty-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--gray-900);
  text-align: center;
}

.empty-subtext {
  font-size: 14px;
  color: var(--gray-600);
  text-align: center;
  max-width: 300px;
}

.upload-btn {
  background: var(--gradient-primary);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
}

.upload-btn:hover {
  background: linear-gradient(135deg, #1d4ed8 0%, #0ea5e9 100%);
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(var(--accent-rgb), 0.2);
}

/* Right-click menu */
.context-menu {
  position: fixed;
  background: var(--surface-1);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 1000;
  min-width: 180px;
  padding: 6px;
  backdrop-filter: blur(10px);
}

.context-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  border-radius: var(--radius-sm);
  font-weight: 500;
  color: var(--gray-700);
}

.context-item:hover {
  background: var(--surface-2);
  color: var(--gray-900);
}

.context-item.danger {
  color: var(--error-600);
}

.context-item.danger:hover {
  background: var(--error-50);
  color: var(--error-600);
}

.context-item .icon {
  font-size: 14px;
  width: 16px;
  text-align: center;
}

.context-divider {
  border: none;
  border-top: 1px solid var(--border-color-light);
  margin: 6px 0;
}

/* Modal dialog */

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.modal {
  width: 90%;
  max-width: 420px;
  overflow: hidden;
}

.modal.mobile {
  width: 95%;
  max-width: none;
  margin: 0 10px;
}

.close-btn:not(.app-modal-close) {
  background: var(--surface-1);
  border: var(--border-width) solid var(--border-color);
  padding: 0;
  cursor: pointer;
  color: var(--gray-600);
  transition: all var(--transition-base);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
}

.close-btn:not(.app-modal-close):hover {
  background: var(--surface-3);
  color: var(--gray-900);
}

.modal-input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 15px;
  background: var(--surface-2);
  transition: all 0.2s;
  box-sizing: border-box;
}

.modal-input:focus {
  outline: none;
  border-color: var(--primary-500);
  background: var(--surface-1);
  box-shadow: 0 0 0 3px rgba(var(--accent-rgb), 0.16);
}

.modal-input.mobile {
  padding: 16px 18px;
  font-size: 16px; /* Prevent iOS zoom */
  border-radius: 12px;
}

.btn-primary {
  background: var(--gradient-primary);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-primary:hover {
  background: linear-gradient(135deg, #1d4ed8 0%, #0ea5e9 100%);
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(var(--accent-rgb), 0.2);
}

.btn-primary.mobile {
  padding: 14px 24px;
  font-size: 16px;
  border-radius: 12px;
  min-height: 48px;
}

.btn-cancel {
  background: var(--surface-1);
  color: var(--gray-700);
  border: 1px solid var(--border-color);
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.btn-cancel:hover {
  background: var(--surface-2);
  border-color: var(--border-color-dark);
}

.btn-cancel.mobile {
  padding: 14px 24px;
  font-size: 16px;
  border-radius: 12px;
  min-height: 48px;
}

/* Loading state */
.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(241, 245, 249, 0.9);
  backdrop-filter: blur(4px);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 100;
}

.spinner {
  width: 40px;
  height: 40px;
  position: relative;
  margin-bottom: 16px;
}

.spinner::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border: 3px solid var(--border-color-light);
  border-radius: 50%;
}

.spinner::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border: 3px solid transparent;
  border-top-color: var(--primary-500);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 14px;
  color: var(--gray-600);
  font-weight: 500;
}

/* Upload progress modal */
.upload-progress-modal {
  position: fixed;
  bottom: 24px;
  right: 24px;
  background: var(--surface-1);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 360px;
  z-index: 1000;
  overflow: hidden;
}

.progress-content {
  padding: 20px;
}

.progress-content h4 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--gray-900);
}

.upload-item {
  margin-bottom: 12px;
}

.upload-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.file-name {
  font-size: 14px;
  color: var(--gray-700);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 260px;
}

.progress-text {
  font-size: 13px;
  color: var(--gray-600);
  font-weight: 500;
}

.progress-bar {
  height: 6px;
  background: var(--surface-3);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--primary-500);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.upload-error {
  color: var(--error-600);
  font-size: 13px;
  margin: 12px 0 0 0;
}

/* Mobile styles */
.mobile-menu-btn {
  background: none;
  border: none;
  padding: 8px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--gray-600);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mobile-menu-btn:hover {
  background: var(--surface-3);
  color: var(--gray-900);
}

/* Mobile menu overlay */
.mobile-menu-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  align-items: flex-end;
  z-index: 1000;
  animation: fadeIn 0.2s ease-out;
}

.mobile-menu {
  background: var(--surface-1);
  border-radius: 12px 12px 0 0;
  width: 100%;
  max-height: 70vh;
  overflow-y: auto;
  animation: slideUpIn 0.3s ease-out;
}

@keyframes slideUpIn {
  from {
    transform: translateY(100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.mobile-menu-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 20px 16px;
  border-bottom: 1px solid var(--border-color-light);
}

.mobile-menu-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--gray-900);
}

.mobile-menu-content {
  padding: 8px 0 24px;
}

.mobile-menu-item {
  width: 100%;
  padding: 16px 20px;
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  color: var(--gray-700);
  font-size: 16px;
  font-weight: 500;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 12px;
}

.mobile-menu-item:hover {
  background: var(--surface-2);
}

.mobile-menu-item.danger {
  color: var(--error-600);
}

.mobile-menu-item.danger:hover {
  background: var(--error-50);
}

.mobile-menu-divider {
  height: 1px;
  background: var(--border-color-light);
  margin: 8px 0;
}

/* Mobile file row menu button */
.mobile-menu-btn {
  background: none;
  border: none;
  padding: 4px;
  border-radius: 4px;
  cursor: pointer;
  color: var(--gray-400);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mobile-menu-btn:hover {
  background: var(--surface-3);
  color: var(--gray-600);
}

/* Mobile-specific styles */
.fm-header.mobile {
  flex-direction: column;
  gap: 12px;
  padding: 20px 16px 12px 16px;
  min-height: auto;
  position: relative;
  z-index: 10;
}

.breadcrumbs.mobile {
  flex: 1;
  min-width: 0;
}

.header-actions.mobile {
  width: 100%;
  justify-content: space-between;
}

.search-box.mobile {
  flex: 1;
  margin-right: 12px;
}

.search-input.mobile {
  width: 100%;
  padding: 12px 40px 12px 40px;
  font-size: 16px; /* Prevent iOS zoom */
}

.fm-toolbar.mobile {
  padding: 8px 16px;
  justify-content: space-between;
}

.mobile-nav-group {
  display: flex;
  gap: 4px;
  background: var(--surface-2);
  padding: 4px;
  border-radius: var(--radius-sm);
}

.mobile-actions-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.nav-btn.mobile {
  padding: 10px;
  min-width: 44px; /* Meet touch standards */
  min-height: 44px;
}

.action-btn.mobile {
  padding: 10px;
  min-width: 44px;
  min-height: 44px;
  border-radius: 8px;
}

.action-btn.mobile span {
  display: none; /* Hide text on mobile */
}

.view-toggle.mobile {
  background: var(--surface-3);
  border-radius: var(--radius-sm);
  padding: 2px;
}

.toggle-btn.mobile {
  padding: 8px;
  min-width: 40px;
  min-height: 40px;
}

/* Mobile list styles */
.list-header.mobile {
  grid-template-columns: 40px 1fr 70px 40px;
  padding: 12px 16px;
  font-size: 11px;
}

.file-list.mobile {
  padding: 4px 0 80px 0; /* Leave more space at bottom */
}

.file-row.mobile {
  grid-template-columns: 40px 1fr 70px 40px;
  padding: 12px 16px;
  min-height: 60px; /* Increase touch area */
}

.file-row.mobile .col-size {
  display: none; /* 移动端隐藏，信息在文件名下显示 */
}

.file-row.mobile .file-info {
  gap: 4px;
}

.file-row.mobile .mobile-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: #6b7280;
  margin-top: 2px;
}

.mobile-hidden {
  display: none !important;
}

/* 移动端网格样式 */
.file-grid.mobile {
  grid-template-columns: repeat(auto-fill, minmax(90px, 1fr));
  gap: 12px;
  padding: 12px 16px 80px 16px;
}

.grid-item.mobile {
  padding: 12px 8px 8px;
  min-height: 120px;
}

.grid-item.mobile .grid-icon {
  width: 40px;
  height: 40px;
  margin-bottom: 8px;
}

.grid-item.mobile .grid-name {
  font-size: 11px;
  line-height: 1.3;
  margin-bottom: 6px;
  word-break: break-all;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.grid-meta.mobile {
  font-size: 10px;
}

.grid-meta.mobile .meta-row {
  justify-content: center;
  gap: 2px;
}

/* 移动端右键菜单 */
.context-menu.mobile {
  position: fixed;
  bottom: 20px;
  left: 20px;
  right: 20px;
  top: auto;
  transform: none;
  border-radius: 12px;
  padding: 8px;
  box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
}

.context-menu.mobile .context-item {
  padding: 16px 16px;
  border-radius: 8px;
  font-size: 16px;
  min-height: 52px;
}

/* 触摸反馈 */
.file-row:active,
.grid-item:active,
.action-btn:active,
.nav-btn:active,
.toggle-btn:active {
  transform: scale(0.98);
  transition: transform 0.1s;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .list-header:not(.mobile) {
    grid-template-columns: 40px 2fr 80px 100px 120px 60px;
  }
  
  .file-row:not(.mobile) {
    grid-template-columns: 40px 2fr 80px 100px 120px 60px;
  }
  
  .col-time:last-of-type {
    display: none;
  }
}

@media (max-width: 900px) {
  .list-header:not(.mobile) {
    grid-template-columns: 40px 2fr 80px 100px 60px;
  }
  
  .file-row:not(.mobile) {
    grid-template-columns: 40px 2fr 80px 100px 60px;
  }
  
  .col-time:nth-last-child(2) {
    display: none;
  }
}

@media (max-width: 768px) {
  /* 强制移动端样式 */
  .fm-header:not(.mobile) {
    flex-direction: column;
    gap: 12px;
    padding: 16px 16px 12px 16px;
  }
  
  .fm-toolbar:not(.mobile) {
    flex-direction: column;
    gap: 8px;
    padding: 8px 16px;
  }
  
  .search-input:not(.mobile) {
    width: 200px;
  }
  
  .list-header:not(.mobile) {
    grid-template-columns: 40px 1fr 80px 60px;
  }
  
  .file-row:not(.mobile) {
    grid-template-columns: 40px 1fr 80px 60px;
  }
  
  .col-type {
    display: none;
  }
  
  .file-grid:not(.mobile) {
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
    gap: 12px;
    padding: 12px 12px 40px 12px;
  }
  
  .file-list:not(.mobile) {
    padding: 4px 0 60px 0;
  }
}

@media (max-width: 480px) {
  /* 小屏手机优化 */
  .file-grid.mobile {
    grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
    gap: 8px;
  }
  
  .grid-item.mobile {
    min-height: 100px;
    padding: 8px 4px 6px;
  }
  
  .grid-item.mobile .grid-name {
    font-size: 10px;
  }
  
  .mobile-menu {
    max-height: 80vh;
  }
}

/* 横屏模式优化 */
@media (max-height: 500px) and (orientation: landscape) {
  .mobile-menu {
    max-height: 90vh;
  }
  
  .fm-header.mobile {
    padding: 8px 16px;
  }
  
  .fm-toolbar.mobile {
    padding: 6px 16px;
  }
}
</style>
