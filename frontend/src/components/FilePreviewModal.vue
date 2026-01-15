<!-- FilePreviewModal.vue - Enhanced file preview with editing capabilities -->
<template>
  <div v-if="showModal" class="modal-backdrop app-modal-viewport app-modal-backdrop" @click.self="closeModal">
    <div class="preview-modal app-modal">
      <div class="preview-header app-modal-header">
        <div class="header-left">
          <h4>{{ fileName }}</h4>
          <div class="file-info" v-if="previewData.mimetype">
            <span class="file-type">{{ previewData.mimetype }}</span>
            <span v-if="previewData.size" class="file-size">{{ formatSize(previewData.size) }}</span>
          </div>
        </div>
        <div class="header-right">
          <div class="header-actions">
            <button 
              v-if="previewData.editable && !editMode" 
              @click="startEdit" 
              class="action-btn edit-btn"
              title="Edit File"
            >
              ✏️ Edit
            </button>
            <button 
              v-if="editMode" 
              @click="saveFile" 
              class="action-btn save-btn"
              :disabled="!hasChanges"
              title="Save Changes"
            >
              💾 Save
            </button>
            <button 
              v-if="editMode" 
              @click="cancelEdit" 
              class="action-btn cancel-btn"
              title="Cancel Edit"
            >
              ❌ Cancel
            </button>
            <button 
              @click="downloadFile" 
              class="action-btn download-btn"
              title="Download File"
            >
              📥 Download
            </button>
            <button 
              @click="closeModal" 
              class="app-modal-close"
              title="Close"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <div class="preview-content" ref="previewContent">
        <!-- Edit Mode -->
        <div v-if="editMode" class="edit-container">
          <div class="edit-toolbar">
            <select v-model="editorLanguage" class="language-select">
              <option value="text">Plain Text</option>
              <option value="javascript">JavaScript</option>
              <option value="typescript">TypeScript</option>
              <option value="python">Python</option>
              <option value="html">HTML</option>
              <option value="css">CSS</option>
              <option value="json">JSON</option>
              <option value="markdown">Markdown</option>
              <option value="xml">XML</option>
              <option value="yaml">YAML</option>
            </select>
            <div class="edit-info">
              <span class="line-count">Lines: {{ lineCount }}</span>
              <span class="char-count">Characters: {{ charCount }}</span>
              <span v-if="hasChanges" class="unsaved-indicator">• Unsaved changes</span>
            </div>
          </div>
          <textarea 
            v-model="editContent" 
            class="code-editor"
            :placeholder="'Edit ' + fileName + '...'"
            @keydown="handleEditorKeydown"
            @input="updateEditInfo"
            ref="codeEditor"
          ></textarea>
          <div class="edit-footer">
            <span class="editor-shortcuts">
              Ctrl+S: Save | Ctrl+Z: Undo | Ctrl+Y: Redo | Ctrl+F: Find
            </span>
          </div>
        </div>

        <!-- Preview Mode -->
        <div v-else class="preview-container">
          <!-- Image preview -->
          <div v-if="previewData.type === 'image'" class="image-preview">
            <div class="image-controls">
              <button @click="zoomIn" class="zoom-btn">🔍+</button>
              <button @click="zoomOut" class="zoom-btn">🔍-</button>
              <button @click="resetZoom" class="zoom-btn">🔄</button>
              <span class="zoom-level">{{ Math.round(zoomLevel * 100) }}%</span>
            </div>
            <div class="image-container" @wheel="handleImageWheel">
              <img 
                :src="previewData.content || previewData.url" 
                class="preview-image" 
                :style="{ transform: `scale(${zoomLevel})` }"
                @load="onImageLoad"
              />
            </div>
          </div>

          <!-- HTML preview with live rendering -->
          <div v-else-if="previewData.type === 'html'" class="html-preview">
            <div class="preview-tabs">
              <button 
                :class="['tab-btn', { active: htmlTab === 'rendered' }]"
                @click="htmlTab = 'rendered'"
              >
                Rendered
              </button>
              <button 
                :class="['tab-btn', { active: htmlTab === 'source' }]"
                @click="htmlTab = 'source'"
              >
                Source
              </button>
            </div>
            <div v-if="htmlTab === 'rendered'" class="html-render-container">
              <iframe 
                :srcdoc="previewData.content" 
                class="html-iframe"
                sandbox="allow-same-origin allow-scripts"
                frameborder="0"
              ></iframe>
            </div>
            <div v-else class="html-source">
              <pre class="code-content html"><code>{{ previewData.content }}</code></pre>
            </div>
          </div>

          <!-- Markdown preview with live rendering -->
          <div v-else-if="previewData.type === 'markdown'" class="markdown-preview">
            <div class="preview-tabs">
              <button 
                :class="['tab-btn', { active: markdownTab === 'rendered' }]"
                @click="markdownTab = 'rendered'"
              >
                Rendered
              </button>
              <button 
                :class="['tab-btn', { active: markdownTab === 'source' }]"
                @click="markdownTab = 'source'"
              >
                Source
              </button>
            </div>
            <div v-if="markdownTab === 'rendered'" class="markdown-render">
              <div v-html="renderMarkdown(previewData.content)"></div>
            </div>
            <div v-else class="markdown-source">
              <pre class="code-content markdown"><code>{{ previewData.content }}</code></pre>
            </div>
          </div>

          <!-- Code preview with syntax highlighting -->
          <div v-else-if="previewData.type === 'code'" class="code-preview">
            <div class="code-header">
              <span class="language-tag">{{ previewData.language || 'text' }}</span>
              <div class="code-controls">
                <button @click="copyToClipboard" class="control-btn">📋 Copy</button>
                <button @click="toggleWordWrap" class="control-btn">
                  {{ wordWrap ? '📄' : '📜' }} {{ wordWrap ? 'Unwrap' : 'Wrap' }}
                </button>
              </div>
            </div>
            <pre class="code-content" :class="{ 'word-wrap': wordWrap }"><code>{{ previewData.content }}</code></pre>
          </div>

          <!-- JSON preview with formatting -->
          <div v-else-if="previewData.type === 'json'" class="json-preview">
            <div class="json-header">
              <span class="language-tag">JSON</span>
              <div class="json-controls">
                <button @click="formatJson" class="control-btn">🔧 Format</button>
                <button @click="compactJson" class="control-btn">📦 Compact</button>
                <button @click="validateJson" class="control-btn">✅ Validate</button>
              </div>
            </div>
            <div v-if="jsonError" class="json-error">
              ❌ Invalid JSON: {{ jsonError }}
            </div>
            <pre class="code-content json"><code>{{ formattedJson || previewData.content }}</code></pre>
          </div>

          <!-- Bioinformatics preview with enhanced analysis -->
          <div v-else-if="previewData.type === 'bioinformatics'" class="bio-preview">
            <div class="bio-header">
              <span class="language-tag">{{ previewData.file_format.toUpperCase() }}</span>
              <span class="info-tag">Bioinformatics</span>
              <span v-if="previewData.file_size" class="size-info">{{ formatSize(previewData.file_size) }}</span>
            </div>
            
            <!-- Large file warning and options -->
            <div v-if="previewData.too_large" class="large-file-warning">
              <div class="warning-content">
                <div class="warning-icon">⚠️</div>
                <div class="warning-text">
                  <h4>Large File Detected</h4>
                  <p>This file ({{ formatSize(previewData.file_size) }}) is too large for full preview. Choose an option:</p>
                </div>
              </div>
              <div class="large-file-actions">
                <button @click="loadFileHead" class="action-btn primary" :disabled="loadingHead">
                  {{ loadingHead ? 'Loading...' : '📄 Preview First 1000 Lines' }}
                </button>
                <button @click="loadFileSample" class="action-btn" :disabled="loadingSample">
                  {{ loadingSample ? 'Loading...' : '🎯 Load Sample Data' }}
                </button>
                <button @click="downloadFile" class="action-btn">
                  📥 Download Full File
                </button>
              </div>
              <div v-if="sampledData.content" class="sampled-preview">
                <div class="sample-header">
                  <span class="sample-tag">Sample Preview</span>
                  <span class="sample-info">{{ sampledData.lines_shown }} lines shown</span>
                </div>
                <pre class="code-content bio"><code>{{ sampledData.content }}</code></pre>
              </div>
            </div>
            
            <div v-else-if="previewData.bio_analysis" class="bio-analysis-panel">
              <div class="analysis-tabs">
                <button 
                  :class="['tab-btn', { active: bioTab === 'statistics' }]"
                  @click="bioTab = 'statistics'"
                >
                  📊 Statistics
                </button>
                <button 
                  :class="['tab-btn', { active: bioTab === 'sequences' }]"
                  @click="bioTab = 'sequences'"
                  v-if="previewData.file_format === 'fasta' || previewData.file_format === 'fastq'"
                >
                  🧬 Sequences
                </button>
                <button 
                  :class="['tab-btn', { active: bioTab === 'variants' }]"
                  @click="bioTab = 'variants'"
                  v-if="previewData.file_format === 'vcf'"
                >
                  🧬 Variants
                </button>
                <button 
                  :class="['tab-btn', { active: bioTab === 'annotations' }]"
                  @click="bioTab = 'annotations'"
                  v-if="previewData.file_format === 'gff' || previewData.file_format === 'gtf'"
                >
                  📝 Annotations
                </button>
                <button 
                  :class="['tab-btn', { active: bioTab === 'regions' }]"
                  @click="bioTab = 'regions'"
                  v-if="previewData.file_format === 'bed'"
                >
                  📍 Regions
                </button>
                <button 
                  :class="['tab-btn', { active: bioTab === 'alignments' }]"
                  @click="bioTab = 'alignments'"
                  v-if="previewData.file_format === 'sam' || previewData.file_format === 'bam'"
                >
                  🎯 Alignments
                </button>
                <button 
                  :class="['tab-btn', { active: bioTab === 'visualization' }]"
                  @click="bioTab = 'visualization'"
                >
                  📈 Visualization
                </button>
                <button 
                  :class="['tab-btn', { active: bioTab === 'content' }]"
                  @click="bioTab = 'content'"
                >
                  📄 Raw Content
                </button>
              </div>
              
              <!-- Statistics Tab (existing content) -->
              <div v-if="bioTab === 'statistics'" class="analysis-content">
                <div class="stats-grid">
                  <div class="stat-card">
                    <h4>Sequence Count</h4>
                    <div class="stat-value">{{ previewData.bio_analysis.sequence_count || 0 }}</div>
                  </div>
                  <div class="stat-card">
                    <h4>Total Length</h4>
                    <div class="stat-value">{{ formatNumber(previewData.bio_analysis.total_length || 0) }} bp</div>
                  </div>
                  <div class="stat-card">
                    <h4>GC Content</h4>
                    <div class="stat-value">{{ (previewData.bio_analysis.gc_content || 0).toFixed(2) }}%</div>
                  </div>
                  <div class="stat-card">
                    <h4>File Format</h4>
                    <div class="stat-value">{{ previewData.bio_analysis.sequence_type || 'Unknown' }}</div>
                  </div>
                </div>
              </div>

              <!-- Sequences Tab - Enhanced for different file formats -->
              <div v-if="bioTab === 'sequences'" class="analysis-content">
                <div class="sequences-container">
                  <div class="sequences-header">
                    <div class="sequence-info">
                      <span class="format-badge">{{ previewData.file_format.toUpperCase() }}</span>
                      <span class="count-info">{{ previewData.bio_analysis.sequence_count || 0 }} sequences</span>
                    </div>
                    <div class="sequence-controls">
                      <select v-model="selectedSequenceIndex" class="sequence-select">
                        <option v-for="(seq, index) in sequences.slice(0, 50)" :key="index" :value="index">
                          {{ seq.id || `Sequence ${index + 1}` }} ({{ seq.length || 0 }} bp)
                        </option>
                      </select>
                      <button @click="formatSequence" class="format-btn">Format</button>
                    </div>
                  </div>
                  
                  <div class="sequence-display" v-if="selectedSequence">
                    <div class="sequence-header-info">
                      <h4>{{ selectedSequence.id || 'Sequence' }}</h4>
                      <div class="sequence-meta">
                        <span v-if="selectedSequence.description">{{ selectedSequence.description }}</span>
                        <span class="length-info">Length: {{ selectedSequence.length || 0 }} bp</span>
                        <span v-if="selectedSequence.quality" class="quality-info">Avg Quality: {{ getAverageQuality(selectedSequence.quality) }}</span>
                      </div>
                    </div>
                    
                    <div class="sequence-content">
                      <div v-if="previewData.file_format === 'fastq'" class="fastq-display">
                        <div class="sequence-line">
                          <strong>Sequence:</strong>
                          <div class="sequence-text formatted">{{ formatSequenceText(selectedSequence.sequence) }}</div>
                        </div>
                        <div class="quality-line" v-if="selectedSequence.quality">
                          <strong>Quality:</strong>
                          <div class="quality-text">{{ selectedSequence.quality }}</div>
                          <div class="quality-graph">
                            <div v-for="(score, index) in parseQualityScores(selectedSequence.quality)" 
                                 :key="index" 
                                 class="quality-bar" 
                                 :style="{ height: score * 2 + 'px', backgroundColor: getQualityColor(score) }"
                                 :title="`Position ${index + 1}: Quality ${score}`">
                            </div>
                          </div>
                        </div>
                      </div>
                      
                      <div v-else-if="previewData.file_format === 'fasta'" class="fasta-display">
                        <div class="sequence-line">
                          <div class="sequence-text formatted">{{ formatSequenceText(selectedSequence.sequence) }}</div>
                        </div>
                        <div class="sequence-analysis">
                          <div class="composition-mini">
                            <span class="base-count">A: {{ countBase(selectedSequence.sequence, 'A') }}</span>
                            <span class="base-count">T: {{ countBase(selectedSequence.sequence, 'T') }}</span>
                            <span class="base-count">G: {{ countBase(selectedSequence.sequence, 'G') }}</span>
                            <span class="base-count">C: {{ countBase(selectedSequence.sequence, 'C') }}</span>
                            <span class="gc-content">GC: {{ calculateGC(selectedSequence.sequence) }}%</span>
                          </div>
                        </div>
                      </div>
                      
                      <div v-else class="generic-sequence">
                        <div class="sequence-text formatted">{{ formatSequenceText(selectedSequence.sequence) }}</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- VCF/Variant Analysis Tab -->
              <div v-if="bioTab === 'variants' && previewData.file_format === 'vcf'" class="analysis-content">
                <div class="vcf-container">
                  <div class="vcf-header">
                    <span class="format-badge">VCF</span>
                    <span class="count-info">{{ variantCount || 0 }} variants</span>
                  </div>
                  <div class="vcf-table">
                    <table class="variants-table">
                      <thead>
                        <tr>
                          <th>CHROM</th>
                          <th>POS</th>
                          <th>ID</th>
                          <th>REF</th>
                          <th>ALT</th>
                          <th>QUAL</th>
                          <th>FILTER</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(variant, index) in variants.slice(0, 100)" :key="index">
                          <td>{{ variant.chrom }}</td>
                          <td>{{ variant.pos }}</td>
                          <td>{{ variant.id || '.' }}</td>
                          <td>{{ variant.ref }}</td>
                          <td>{{ variant.alt }}</td>
                          <td>{{ variant.qual || '.' }}</td>
                          <td>{{ variant.filter || '.' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <!-- GFF/GTF Annotation Tab -->
              <div v-if="bioTab === 'annotations' && (previewData.file_format === 'gff' || previewData.file_format === 'gtf')" class="analysis-content">
                <div class="annotation-container">
                  <div class="annotation-header">
                    <span class="format-badge">{{ previewData.file_format.toUpperCase() }}</span>
                    <span class="count-info">{{ annotationCount || 0 }} features</span>
                  </div>
                  <div class="annotation-table">
                    <table class="features-table">
                      <thead>
                        <tr>
                          <th>Seqname</th>
                          <th>Source</th>
                          <th>Feature</th>
                          <th>Start</th>
                          <th>End</th>
                          <th>Score</th>
                          <th>Strand</th>
                          <th>Frame</th>
                          <th>Attributes</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(feature, index) in annotations.slice(0, 100)" :key="index">
                          <td>{{ feature.seqname }}</td>
                          <td>{{ feature.source }}</td>
                          <td>{{ feature.feature }}</td>
                          <td>{{ feature.start }}</td>
                          <td>{{ feature.end }}</td>
                          <td>{{ feature.score || '.' }}</td>
                          <td>{{ feature.strand }}</td>
                          <td>{{ feature.frame || '.' }}</td>
                          <td class="attributes-cell">{{ feature.attributes }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <!-- BED Format Tab -->
              <div v-if="bioTab === 'regions' && previewData.file_format === 'bed'" class="analysis-content">
                <div class="bed-container">
                  <div class="bed-header">
                    <span class="format-badge">BED</span>
                    <span class="count-info">{{ bedRegionCount || 0 }} regions</span>
                  </div>
                  <div class="bed-table">
                    <table class="regions-table">
                      <thead>
                        <tr>
                          <th>Chrom</th>
                          <th>Start</th>
                          <th>End</th>
                          <th>Name</th>
                          <th>Score</th>
                          <th>Strand</th>
                          <th>Length</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(region, index) in bedRegions.slice(0, 100)" :key="index">
                          <td>{{ region.chrom }}</td>
                          <td>{{ region.start }}</td>
                          <td>{{ region.end }}</td>
                          <td>{{ region.name || '.' }}</td>
                          <td>{{ region.score || '.' }}</td>
                          <td>{{ region.strand || '.' }}</td>
                          <td>{{ region.end - region.start }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <!-- SAM/BAM Alignments Tab -->
              <div v-if="bioTab === 'alignments' && (previewData.file_format === 'sam' || previewData.file_format === 'bam')" class="analysis-content">
                <div class="alignments-container">
                  <div class="alignments-header">
                    <span class="format-badge">{{ previewData.file_format.toUpperCase() }}</span>
                    <span class="count-info">{{ alignmentCount || 0 }} reads</span>
                  </div>
                  <div class="alignments-table">
                    <table class="sam-table">
                      <thead>
                        <tr>
                          <th>QNAME</th>
                          <th>FLAG</th>
                          <th>RNAME</th>
                          <th>POS</th>
                          <th>MAPQ</th>
                          <th>CIGAR</th>
                          <th>RNEXT</th>
                          <th>PNEXT</th>
                          <th>TLEN</th>
                          <th>SEQ</th>
                          <th>QUAL</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(alignment, index) in alignments.slice(0, 100)" :key="index">
                          <td>{{ alignment.qname }}</td>
                          <td>{{ alignment.flag }}</td>
                          <td>{{ alignment.rname }}</td>
                          <td>{{ alignment.pos }}</td>
                          <td>{{ alignment.mapq }}</td>
                          <td>{{ alignment.cigar }}</td>
                          <td>{{ alignment.rnext }}</td>
                          <td>{{ alignment.pnext }}</td>
                          <td>{{ alignment.tlen }}</td>
                          <td class="sequence-cell">{{ alignment.seq.slice(0, 50) }}{{ alignment.seq.length > 50 ? '...' : '' }}</td>
                          <td class="quality-cell">{{ alignment.qual.slice(0, 50) }}{{ alignment.qual.length > 50 ? '...' : '' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>

              <!-- Visualization Tab - Enhanced with ECharts -->
              <div v-if="bioTab === 'visualization'" class="analysis-content">
                <div class="visualization-container">
                  <div class="chart-controls">
                    <button @click="showCompositionChart" class="viz-btn" :class="{ active: currentChart === 'composition' }">碱基组成</button>
                    <button @click="showLengthDistribution" class="viz-btn" :class="{ active: currentChart === 'length' }">长度分布</button>
                    <button @click="showQualityScore" class="viz-btn" :class="{ active: currentChart === 'quality' }" v-if="previewData.file_format === 'fastq'">质量分数</button>
                    <button @click="showGCContent" class="viz-btn" :class="{ active: currentChart === 'gc' }" v-if="previewData.file_format === 'fasta'">GC含量</button>
                    <button @click="showVariantDistribution" class="viz-btn" :class="{ active: currentChart === 'variant' }" v-if="previewData.file_format === 'vcf'">变异分布</button>
                  </div>
                  <div ref="chartContainer" class="chart-container"></div>
                </div>
              </div>

              <!-- Content Tab -->
              <div v-if="bioTab === 'content'" class="analysis-content">
                <pre class="code-content bio"><code>{{ previewData.content }}</code></pre>
              </div>
            </div>
          </div>

          <!-- CSV/TSV preview with table view -->
          <div v-else-if="previewData.type === 'csv'" class="csv-preview">
            <div class="csv-header">
              <span class="language-tag">{{ previewData.delimiter === '\t' ? 'TSV' : 'CSV' }}</span>
              <div class="csv-controls">
                <button @click="toggleTableView" class="control-btn">
                  {{ showTableView ? '📄' : '📊' }} {{ showTableView ? 'Raw' : 'Table' }}
                </button>
              </div>
            </div>
            <div v-if="showTableView" class="csv-table-view">
              <table class="csv-table">
                <thead>
                  <tr>
                    <th v-for="(header, index) in csvHeaders" :key="index">{{ header }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, rowIndex) in csvRows.slice(0, 100)" :key="rowIndex">
                    <td v-for="(cell, cellIndex) in row" :key="cellIndex">{{ cell }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-if="csvRows.length > 100" class="table-footer">
                Showing first 100 rows of {{ csvRows.length }} total rows
              </div>
            </div>
            <div v-else class="csv-raw">
              <pre class="code-content csv"><code>{{ previewData.content }}</code></pre>
            </div>
          </div>

          <!-- Default text preview or large file handling -->
          <div v-else class="text-preview">
            <!-- Large file warning for non-bio files -->
            <div v-if="previewData.too_large || (previewData.error && previewData.error.includes('too large'))" class="large-file-warning">
              <div class="warning-content">
                <div class="warning-icon">⚠️</div>
                <div class="warning-text">
                  <h4>Large File Detected</h4>
                  <p>This file ({{ formatSize(previewData.file_size || 0) }}) is too large for full preview. Choose an option:</p>
                </div>
              </div>
              <div class="large-file-actions">
                <button @click="loadFileHead" class="action-btn primary" :disabled="loadingHead">
                  {{ loadingHead ? 'Loading...' : '📄 Preview First 1000 Lines' }}
                </button>
                <button @click="downloadFile" class="action-btn">
                  📥 Download Full File
                </button>
              </div>
              <div v-if="sampledData.content" class="sampled-preview">
                <div class="sample-header">
                  <span class="sample-tag">Preview</span>
                  <span class="sample-info">{{ sampledData.lines_shown }} lines shown</span>
                </div>
                <pre class="code-content text"><code>{{ sampledData.content }}</code></pre>
              </div>
            </div>
            <pre v-else class="code-content text"><code>{{ previewData.content }}</code></pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  showModal: {
    type: Boolean,
    default: false
  },
  fileName: {
    type: String,
    default: ''
  },
  previewData: {
    type: Object,
    default: () => ({})
  },
  projectId: {
    type: String,
    required: true
  },
  filePath: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['close', 'save', 'download'])

// Edit mode
const editMode = ref(false)
const editContent = ref('')
const originalContent = ref('')
const editorLanguage = ref('text')

// Editor info
const lineCount = ref(0)
const charCount = ref(0)

// Tab states
const htmlTab = ref('rendered')
const markdownTab = ref('rendered')
const bioTab = ref('statistics')

// Bioinformatics data
const sequences = ref([])
const selectedSequenceIndex = ref(0)
const variants = ref([])
const variantCount = ref(0)
const annotations = ref([])
const annotationCount = ref(0)
const bedRegions = ref([])
const bedRegionCount = ref(0)
const alignments = ref([])
const alignmentCount = ref(0)

// Image preview
const zoomLevel = ref(1)

// Code preview
const wordWrap = ref(false)

// JSON preview
const formattedJson = ref('')
const jsonError = ref('')

// CSV preview
const showTableView = ref(true)
const csvHeaders = ref([])
const csvRows = ref([])

// ECharts for bio visualization
const chartContainer = ref(null)
const chartInstance = ref(null)
const currentChart = ref('composition')

// Large file handling
const loadingHead = ref(false)
const loadingSample = ref(false)
const sampledData = ref({ content: '', lines_shown: 0 })

// Computed
const hasChanges = computed(() => {
  return editMode.value && editContent.value !== originalContent.value
})

const selectedSequence = computed(() => {
  return sequences.value[selectedSequenceIndex.value] || null
})

// Methods
const closeModal = () => {
  if (hasChanges.value) {
    if (confirm('You have unsaved changes. Are you sure you want to close?')) {
      resetModal()
      emit('close')
    }
  } else {
    resetModal()
    emit('close')
  }
}

const resetModal = () => {
  editMode.value = false
  editContent.value = ''
  originalContent.value = ''
  zoomLevel.value = 1
  htmlTab.value = 'rendered'
  markdownTab.value = 'rendered'
  bioTab.value = 'statistics'
  showTableView.value = true
  currentChart.value = 'composition'
  // Reset bioinformatics data
  sequences.value = []
  selectedSequenceIndex.value = 0
  variants.value = []
  annotations.value = []
  bedRegions.value = []
  alignments.value = []
  // Reset large file handling
  loadingHead.value = false
  loadingSample.value = false
  sampledData.value = { content: '', lines_shown: 0 }
  // Dispose chart instance and cleanup
  if (chartInstance.value) {
    chartInstance.value.dispose()
    chartInstance.value = null
  }
  // Clean up resize observer
  if (chartContainer.value?._resizeObserver) {
    chartContainer.value._resizeObserver.disconnect()
    delete chartContainer.value._resizeObserver
  }
}

// Large file handling methods
const loadFileHead = async () => {
  loadingHead.value = true
  try {
    const response = await fetch(`/api/filemanager/${props.projectId}/preview-head?path=${props.filePath}&lines=1000`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const data = await response.json()
    sampledData.value = {
      content: data.content,
      lines_shown: data.lines_count || 1000
    }
  } catch (error) {
    console.error('Error loading file head:', error)
    alert(`Failed to load file preview: ${error.message}`)
  } finally {
    loadingHead.value = false
  }
}

const loadFileSample = async () => {
  loadingSample.value = true
  try {
    const response = await fetch(`/api/filemanager/${props.projectId}/preview-sample?path=${props.filePath}&samples=100`)
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    const data = await response.json()
    sampledData.value = {
      content: data.content,
      lines_shown: data.lines_count || 100
    }
  } catch (error) {
    console.error('Error loading file sample:', error)
    alert(`Failed to load file sample: ${error.message}`)
  } finally {
    loadingSample.value = false
  }
}

// Bioinformatics data processing methods
const parseBioData = () => {
  if (!props.previewData || !props.previewData.content) return
  
  const content = props.previewData.content
  const format = props.previewData.file_format
  
  switch (format) {
    case 'fasta':
      parseFastaData(content)
      break
    case 'fastq':
      parseFastqData(content)
      break
    case 'vcf':
      parseVcfData(content)
      break
    case 'gff':
    case 'gtf':
      parseGffData(content)
      break
    case 'bed':
      parseBedData(content)
      break
    case 'sam':
      parseSamData(content)
      break
  }
}

const parseFastaData = (content) => {
  sequences.value = []
  const lines = content.split('\n')
  let currentSeq = null
  
  for (const line of lines) {
    if (line.startsWith('>')) {
      if (currentSeq) {
        sequences.value.push(currentSeq)
      }
      const header = line.substring(1).trim()
      const parts = header.split(' ')
      currentSeq = {
        id: parts[0],
        description: parts.slice(1).join(' '),
        sequence: '',
        length: 0
      }
    } else if (currentSeq && line.trim()) {
      currentSeq.sequence += line.trim()
      currentSeq.length = currentSeq.sequence.length
    }
  }
  
  if (currentSeq) {
    sequences.value.push(currentSeq)
  }
}

const parseFastqData = (content) => {
  sequences.value = []
  const lines = content.split('\n')
  
  for (let i = 0; i < lines.length; i += 4) {
    if (i + 3 < lines.length) {
      const header = lines[i].substring(1).trim()
      const sequence = lines[i + 1].trim()
      const quality = lines[i + 3].trim()
      
      sequences.value.push({
        id: header,
        sequence: sequence,
        quality: quality,
        length: sequence.length
      })
    }
  }
}

const parseVcfData = (content) => {
  variants.value = []
  const lines = content.split('\n')
  
  for (const line of lines) {
    if (!line.startsWith('#') && line.trim()) {
      const parts = line.split('\t')
      if (parts.length >= 8) {
        variants.value.push({
          chrom: parts[0],
          pos: parseInt(parts[1]),
          id: parts[2],
          ref: parts[3],
          alt: parts[4],
          qual: parts[5],
          filter: parts[6],
          info: parts[7]
        })
      }
    }
  }
  variantCount.value = variants.value.length
}

const parseGffData = (content) => {
  annotations.value = []
  const lines = content.split('\n')
  
  for (const line of lines) {
    if (!line.startsWith('#') && line.trim()) {
      const parts = line.split('\t')
      if (parts.length >= 9) {
        annotations.value.push({
          seqname: parts[0],
          source: parts[1],
          feature: parts[2],
          start: parseInt(parts[3]),
          end: parseInt(parts[4]),
          score: parts[5],
          strand: parts[6],
          frame: parts[7],
          attributes: parts[8]
        })
      }
    }
  }
  annotationCount.value = annotations.value.length
}

const parseBedData = (content) => {
  bedRegions.value = []
  const lines = content.split('\n')
  
  for (const line of lines) {
    if (!line.startsWith('#') && line.trim()) {
      const parts = line.split('\t')
      if (parts.length >= 3) {
        bedRegions.value.push({
          chrom: parts[0],
          start: parseInt(parts[1]),
          end: parseInt(parts[2]),
          name: parts[3] || '',
          score: parts[4] || '',
          strand: parts[5] || ''
        })
      }
    }
  }
  bedRegionCount.value = bedRegions.value.length
}

const parseSamData = (content) => {
  alignments.value = []
  const lines = content.split('\n')
  
  for (const line of lines) {
    if (!line.startsWith('@') && line.trim()) {
      const parts = line.split('\t')
      if (parts.length >= 11) {
        alignments.value.push({
          qname: parts[0],
          flag: parseInt(parts[1]),
          rname: parts[2],
          pos: parseInt(parts[3]),
          mapq: parseInt(parts[4]),
          cigar: parts[5],
          rnext: parts[6],
          pnext: parseInt(parts[7]),
          tlen: parseInt(parts[8]),
          seq: parts[9],
          qual: parts[10]
        })
      }
    }
  }
  alignmentCount.value = alignments.value.length
}

// Sequence analysis methods
const formatSequenceText = (sequence) => {
  if (!sequence) return ''
  return sequence.match(/.{1,60}/g)?.join('\n') || sequence
}

const formatSequence = () => {
  // Toggle between formatted and raw sequence display
  // This could be enhanced with more formatting options
}

const countBase = (sequence, base) => {
  if (!sequence) return 0
  return (sequence.match(new RegExp(base, 'gi')) || []).length
}

const calculateGC = (sequence) => {
  if (!sequence) return 0
  const gc = countBase(sequence, 'G') + countBase(sequence, 'C')
  return ((gc / sequence.length) * 100).toFixed(1)
}

const getAverageQuality = (qualityString) => {
  if (!qualityString) return 0
  let total = 0
  for (let i = 0; i < qualityString.length; i++) {
    total += qualityString.charCodeAt(i) - 33
  }
  return (total / qualityString.length).toFixed(1)
}

const parseQualityScores = (qualityString) => {
  if (!qualityString) return []
  return qualityString.split('').map(char => char.charCodeAt(0) - 33)
}

const getQualityColor = (score) => {
  if (score >= 30) return '#22c55e' // Green - good quality
  if (score >= 20) return '#f59e0b' // Yellow - moderate quality
  return '#ef4444' // Red - poor quality
}

const startEdit = () => {
  editMode.value = true
  editContent.value = props.previewData.content
  originalContent.value = props.previewData.content
  editorLanguage.value = detectLanguage(props.fileName)
  nextTick(() => {
    updateEditInfo()
  })
}

// Add watcher for preview data changes
watch(() => props.previewData, (newData) => {
  if (newData && newData.type === 'bioinformatics') {
    parseBioData()
  }
}, { immediate: true })

// Watch for bioTab changes to initialize chart
watch(() => props.showModal, (newVal) => {
  if (newVal) {
    nextTick(() => {
      if (bioTab.value === 'visualization' && props.previewData.type === 'bioinformatics') {
        setTimeout(() => {
          initChart()
        }, 100)
      }
    })
  }
})

watch(() => bioTab.value, (newTab) => {
  if (newTab === 'visualization' && props.previewData.type === 'bioinformatics') {
    nextTick(() => {
      setTimeout(() => {
        initChart()
      }, 100)
    })
  }
})

// Handle window resize for better responsiveness
let windowResizeTimeout = null
const handleWindowResize = () => {
  if (windowResizeTimeout) {
    clearTimeout(windowResizeTimeout)
  }
  windowResizeTimeout = setTimeout(() => {
    if (chartInstance.value && bioTab.value === 'visualization') {
      chartInstance.value.resize()
      // Re-render with new responsive settings
      switch (currentChart.value) {
        case 'composition':
          showCompositionChart()
          break
        case 'length':
          showLengthDistribution()
          break
        case 'quality':
          showQualityScore()
          break
        case 'gc':
          showGCContent()
          break
        case 'variant':
          showVariantDistribution()
          break
      }
    }
  }, 300)
}


const formatNumber = (num) => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}

const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const renderMarkdown = (content) => {
  if (!content) return ''
  
  // Basic markdown to HTML conversion
  let html = content
    // Headers
    .replace(/^### (.*$)/gim, '<h3>$1</h3>')
    .replace(/^## (.*$)/gim, '<h2>$1</h2>')
    .replace(/^# (.*$)/gim, '<h1>$1</h1>')
    // Bold
    .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
    .replace(/__(.*?)__/gim, '<strong>$1</strong>')
    // Italic
    .replace(/\*(.*)\*/gim, '<em>$1</em>')
    .replace(/_(.*?)_/gim, '<em>$1</em>')
    // Code blocks
    .replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>')
    // Inline code
    .replace(/`(.*?)`/gim, '<code>$1</code>')
    // Links
    .replace(/\[([^\]]+)\]\(([^)]+)\)/gim, '<a href="$2" target="_blank">$1</a>')
    // Line breaks
    .replace(/\n/gim, '<br>')
  
  return html
}

const cancelEdit = () => {
  if (hasChanges.value) {
    if (confirm('You have unsaved changes. Are you sure you want to cancel?')) {
      editMode.value = false
      editContent.value = originalContent.value
    }
  } else {
    editMode.value = false
  }
}

const saveEdit = () => {
  if (hasChanges.value) {
    emit('save', { path: props.filePath, content: editContent.value })
    originalContent.value = editContent.value
  }
}

const downloadFile = () => {
  emit('download', { fileName: props.fileName, filePath: props.filePath })
}

const zoomIn = () => {
  zoomLevel.value = Math.min(zoomLevel.value * 1.2, 5)
}

const zoomOut = () => {
  zoomLevel.value = Math.max(zoomLevel.value / 1.2, 0.2)
}

const resetZoom = () => {
  zoomLevel.value = 1
}

const onImageLoad = () => {
  // Reset zoom when image loads
  zoomLevel.value = 1
}

const handleImageWheel = (event) => {
  event.preventDefault()
  if (event.deltaY > 0) {
    zoomOut()
  } else {
    zoomIn()
  }
}

const toggleWordWrap = () => {
  wordWrap.value = !wordWrap.value
}



const copyToClipboard = async () => {
  try {
    await navigator.clipboard.writeText(props.previewData.content)
    alert('Content copied to clipboard!')
  } catch (error) {
    console.error('Failed to copy to clipboard:', error)
    alert('Failed to copy to clipboard')
  }
}

const formatJson = () => {
  try {
    const parsed = JSON.parse(props.previewData.content)
    formattedJson.value = JSON.stringify(parsed, null, 2)
    jsonError.value = ''
  } catch (error) {
    jsonError.value = error.message
  }
}

const compactJson = () => {
  try {
    const parsed = JSON.parse(props.previewData.content)
    formattedJson.value = JSON.stringify(parsed)
    jsonError.value = ''
  } catch (error) {
    jsonError.value = error.message
  }
}

const validateJson = () => {
  try {
    JSON.parse(props.previewData.content)
    jsonError.value = ''
    alert('JSON is valid!')
  } catch (error) {
    jsonError.value = error.message
    alert('JSON is invalid: ' + error.message)
  }
}

const parseCSV = () => {
  if (!props.previewData.content) return
  
  const lines = props.previewData.content.split('\n')
  const delimiter = props.previewData.delimiter || ','
  
  if (lines.length > 0) {
    csvHeaders.value = lines[0].split(delimiter)
    csvRows.value = lines.slice(1)
      .filter(line => line.trim())
      .map(line => line.split(delimiter))
  }
}

const toggleTableView = () => {
  showTableView.value = !showTableView.value
}

const updateEditInfo = () => {
  lineCount.value = editContent.value.split('\n').length
  charCount.value = editContent.value.length
}

const handleEditorKeydown = (event) => {
  if (event.ctrlKey && event.key === 's') {
    event.preventDefault()
    saveEdit()
  }
}

const detectLanguage = (fileName) => {
  const ext = fileName.split('.').pop().toLowerCase()
  const langMap = {
    'js': 'javascript',
    'ts': 'typescript',
    'py': 'python',
    'html': 'html',
    'css': 'css',
    'json': 'json',
    'md': 'markdown',
    'xml': 'xml',
    'yml': 'yaml',
    'yaml': 'yaml'
  }
  return langMap[ext] || 'text'
}

// ECharts initialization with responsive design
const initChart = () => {
  if (!chartContainer.value) return
  
  if (chartInstance.value) {
    chartInstance.value.dispose()
  }
  
  chartInstance.value = echarts.init(chartContainer.value)
  
  // Add window resize listener for responsive design
  const resizeObserver = new ResizeObserver(() => {
    if (chartInstance.value) {
      chartInstance.value.resize()
    }
  })
  resizeObserver.observe(chartContainer.value)
  
  // Store observer for cleanup
  chartContainer.value._resizeObserver = resizeObserver
  
  // Show default chart
  showCompositionChart()
}

// Responsive chart configuration helper
const getResponsiveConfig = () => {
  if (!chartContainer.value) return {}
  
  const containerWidth = chartContainer.value.clientWidth || 600
  const containerHeight = chartContainer.value.clientHeight || 500
  const isMobile = containerWidth < 768
  const isSmall = containerWidth < 480
  
  return {
    isMobile,
    isSmall,
    containerWidth,
    containerHeight,
    titleFontSize: isSmall ? 14 : isMobile ? 16 : 18,
    subtitleFontSize: isSmall ? 10 : isMobile ? 12 : 14,
    legendFontSize: isSmall ? 10 : isMobile ? 11 : 12,
    axisFontSize: isSmall ? 9 : isMobile ? 10 : 11,
    tooltipFontSize: isSmall ? 11 : isMobile ? 12 : 14,
    grid: isMobile ? {
      left: '5%',
      right: '5%',
      bottom: isSmall ? '15%' : '10%',
      top: '15%',
      containLabel: true
    } : {
      left: '3%',
      right: '4%',
      bottom: '8%',
      top: '12%',
      containLabel: true
    },
    legend: isMobile ? {
      orient: 'horizontal',
      left: 'center',
      bottom: '5%',
      itemWidth: 14,
      itemHeight: 14,
      textStyle: { fontSize: 10 }
    } : {
      orient: 'vertical',
      left: 'left',
      top: 'middle',
      itemWidth: 18,
      itemHeight: 18
    }
  }
}

// ECharts visualization methods
const showCompositionChart = () => {
  if (!chartInstance.value || sequences.value.length === 0) return
  
  currentChart.value = 'composition'
  const responsive = getResponsiveConfig()
  
  // Calculate overall composition
  let totalA = 0, totalT = 0, totalG = 0, totalC = 0
  sequences.value.forEach(seq => {
    totalA += countBase(seq.sequence, 'A')
    totalT += countBase(seq.sequence, 'T')
    totalG += countBase(seq.sequence, 'G')
    totalC += countBase(seq.sequence, 'C')
  })
  
  const total = totalA + totalT + totalG + totalC
  if (total === 0) return
  
  const data = [
    { value: totalA, name: 'A (腺嘌呤)', itemStyle: { color: '#ef4444' } },
    { value: totalT, name: 'T (胸腺嘧啶)', itemStyle: { color: '#3b82f6' } },
    { value: totalG, name: 'G (鸟嘌呤)', itemStyle: { color: '#10b981' } },
    { value: totalC, name: 'C (胞嘧啶)', itemStyle: { color: '#f59e0b' } }
  ]
  
  const option = {
    title: {
      text: '碱基组成分析',
      subtext: `总计 ${sequences.value.length} 条序列，${formatNumber(total)} 个碱基`,
      left: 'center',
      textStyle: {
        fontSize: responsive.titleFontSize,
        fontWeight: 'bold'
      },
      subtextStyle: {
        fontSize: responsive.subtitleFontSize
      }
    },
    tooltip: {
      trigger: 'item',
      textStyle: {
        fontSize: responsive.tooltipFontSize
      },
      formatter: function(params) {
        const percentage = ((params.value / total) * 100).toFixed(2)
        return `${params.name}<br/>数量: ${formatNumber(params.value)}<br/>比例: ${percentage}%`
      }
    },
    legend: {
      ...responsive.legend,
      textStyle: {
        fontSize: responsive.legendFontSize
      }
    },
    series: [
      {
        name: '碱基组成',
        type: 'pie',
        radius: responsive.isMobile ? ['30%', '60%'] : ['40%', '70%'],
        center: responsive.isMobile ? ['50%', '45%'] : ['60%', '50%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: responsive.isSmall ? 6 : 10,
          borderColor: '#fff',
          borderWidth: responsive.isSmall ? 1 : 2
        },
        label: {
          show: !responsive.isMobile,
          position: 'outside',
          fontSize: responsive.axisFontSize,
          formatter: '{b}: {c}\n({d}%)'
        },
        emphasis: {
          label: {
            show: true,
            fontSize: responsive.isMobile ? 14 : 18,
            fontWeight: 'bold'
          },
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        },
        labelLine: {
          show: !responsive.isMobile
        },
        data: data
      }
    ]
  }
  
  chartInstance.value.setOption(option, true)
}

const showLengthDistribution = () => {
  if (!chartInstance.value || sequences.value.length === 0) return
  
  currentChart.value = 'length'
  const responsive = getResponsiveConfig()
  
  const lengths = sequences.value.map(seq => seq.length)
  const maxLength = Math.max(...lengths)
  const minLength = Math.min(...lengths)
  
  // Create histogram - adjust bins for mobile
  const bins = Math.min(responsive.isMobile ? 12 : 20, Math.max(5, Math.floor(Math.sqrt(lengths.length))))
  const binSize = (maxLength - minLength) / bins
  const binCounts = new Array(bins).fill(0)
  const binLabels = []
  
  lengths.forEach(length => {
    const binIndex = Math.floor((length - minLength) / binSize)
    if (binIndex >= 0 && binIndex < bins) {
      binCounts[binIndex]++
    }
  })
  
  for (let i = 0; i < bins; i++) {
    const start = Math.round(minLength + i * binSize)
    const end = Math.round(minLength + (i + 1) * binSize)
    binLabels.push(responsive.isSmall ? `${start}-${end}` : `${start}-${end} bp`)
  }
  
  const option = {
    title: {
      text: '序列长度分布',
      subtext: `${sequences.value.length} 条序列，长度范围: ${minLength}-${maxLength} bp`,
      left: 'center',
      textStyle: {
        fontSize: responsive.titleFontSize,
        fontWeight: 'bold'
      },
      subtextStyle: {
        fontSize: responsive.subtitleFontSize
      }
    },
    tooltip: {
      trigger: 'axis',
      textStyle: {
        fontSize: responsive.tooltipFontSize
      },
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params) {
        const data = params[0]
        return `长度范围: ${data.axisValue}<br/>序列数量: ${data.value}`
      }
    },
    grid: responsive.grid,
    xAxis: {
      type: 'category',
      data: binLabels,
      name: responsive.isSmall ? '长度' : '长度 (bp)',
      nameLocation: 'middle',
      nameGap: responsive.isMobile ? 25 : 30,
      nameTextStyle: {
        fontSize: responsive.axisFontSize
      },
      axisLabel: {
        rotate: responsive.isMobile ? 45 : 30,
        fontSize: responsive.axisFontSize,
        interval: responsive.isSmall ? 'auto' : 0
      }
    },
    yAxis: {
      type: 'value',
      name: responsive.isSmall ? '数量' : '序列数量',
      nameLocation: 'middle',
      nameGap: responsive.isMobile ? 35 : 40,
      nameTextStyle: {
        fontSize: responsive.axisFontSize
      },
      axisLabel: {
        fontSize: responsive.axisFontSize
      }
    },
    series: [
      {
        name: '序列数量',
        type: 'bar',
        data: binCounts,
        barMaxWidth: responsive.isMobile ? 20 : 30,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#83bff6' },
            { offset: 0.5, color: '#188df0' },
            { offset: 1, color: '#188df0' }
          ]),
          borderRadius: [2, 2, 0, 0]
        },
        emphasis: {
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#2378f7' },
              { offset: 0.7, color: '#2378f7' },
              { offset: 1, color: '#83bff6' }
            ])
          }
        }
      }
    ]
  }
  
  chartInstance.value.setOption(option, true)
}

const showQualityScore = () => {
  if (!chartInstance.value || sequences.value.length === 0) return
  
  currentChart.value = 'quality'
  const responsive = getResponsiveConfig()
  
  // Calculate average quality scores
  const avgQualities = sequences.value
    .filter(seq => seq.quality)
    .map(seq => parseFloat(getAverageQuality(seq.quality)))
  
  if (avgQualities.length === 0) return
  
  const maxQuality = Math.max(...avgQualities)
  const minQuality = Math.min(...avgQualities)
  const avgOverall = (avgQualities.reduce((a, b) => a + b, 0) / avgQualities.length).toFixed(2)
  
  // Create histogram - adjust bins for mobile
  const bins = responsive.isMobile ? 12 : 20
  const binSize = (maxQuality - minQuality) / bins
  const binCounts = new Array(bins).fill(0)
  const binLabels = []
  
  avgQualities.forEach(quality => {
    const binIndex = Math.floor((quality - minQuality) / binSize)
    if (binIndex >= 0 && binIndex < bins) {
      binCounts[binIndex]++
    }
  })
  
  for (let i = 0; i < bins; i++) {
    const start = (minQuality + i * binSize).toFixed(1)
    const end = (minQuality + (i + 1) * binSize).toFixed(1)
    binLabels.push(`${start}-${end}`)
  }
  
  const option = {
    title: {
      text: 'FASTQ质量分数分布',
      subtext: responsive.isSmall ? 
        `${avgQualities.length} 条序列，平均: ${avgOverall}` :
        `${avgQualities.length} 条序列，平均质量: ${avgOverall}`,
      left: 'center',
      textStyle: {
        fontSize: responsive.titleFontSize,
        fontWeight: 'bold'
      },
      subtextStyle: {
        fontSize: responsive.subtitleFontSize
      }
    },
    tooltip: {
      trigger: 'axis',
      textStyle: {
        fontSize: responsive.tooltipFontSize
      },
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params) {
        const data = params[0]
        const quality = parseFloat(data.axisValue.split('-')[0])
        const qualityLevel = quality >= 30 ? '优秀' : quality >= 20 ? '良好' : '较差'
        return `质量范围: ${data.axisValue}<br/>序列数量: ${data.value}<br/>质量等级: ${qualityLevel}`
      }
    },
    grid: responsive.grid,
    xAxis: {
      type: 'category',
      data: binLabels,
      name: responsive.isSmall ? '质量' : '质量分数',
      nameLocation: 'middle',
      nameGap: responsive.isMobile ? 25 : 30,
      nameTextStyle: {
        fontSize: responsive.axisFontSize
      },
      axisLabel: {
        rotate: responsive.isMobile ? 45 : 30,
        fontSize: responsive.axisFontSize,
        interval: responsive.isSmall ? 'auto' : 0
      }
    },
    yAxis: {
      type: 'value',
      name: responsive.isSmall ? '数量' : '序列数量',
      nameLocation: 'middle',
      nameGap: responsive.isMobile ? 35 : 40,
      nameTextStyle: {
        fontSize: responsive.axisFontSize
      },
      axisLabel: {
        fontSize: responsive.axisFontSize
      }
    },
    series: [
      {
        name: '序列数量',
        type: 'bar',
        barMaxWidth: responsive.isMobile ? 20 : 30,
        data: binCounts.map((count, i) => {
          const avgQuality = minQuality + i * binSize + binSize / 2
          return {
            value: count,
            itemStyle: {
              color: avgQuality >= 30 ? '#22c55e' : 
                     avgQuality >= 20 ? '#f59e0b' : '#ef4444',
              borderRadius: [2, 2, 0, 0]
            }
          }
        }),
        emphasis: {
          itemStyle: {
            opacity: 0.8,
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.3)'
          }
        }
      }
    ],
    visualMap: {
      show: !responsive.isMobile,
      type: 'piecewise',
      pieces: [
        { min: 30, color: '#22c55e', label: '优秀 (≥30)' },
        { min: 20, max: 30, color: '#f59e0b', label: '良好 (20-30)' },
        { max: 20, color: '#ef4444', label: '较差 (<20)' }
      ],
      orient: 'horizontal',
      left: 'center',
      bottom: '5%',
      textStyle: {
        fontSize: responsive.legendFontSize
      }
    }
  }
  
  chartInstance.value.setOption(option, true)
}

const showGCContent = () => {
  if (!chartInstance.value || sequences.value.length === 0) return
  
  currentChart.value = 'gc'
  const responsive = getResponsiveConfig()
  
  const gcValues = sequences.value.map(seq => parseFloat(calculateGC(seq.sequence)))
  const maxGC = Math.max(...gcValues)
  const minGC = Math.min(...gcValues)
  const avgGC = (gcValues.reduce((a, b) => a + b, 0) / gcValues.length).toFixed(2)
  
  // Create histogram - adjust bins for mobile
  const bins = responsive.isMobile ? 12 : 20
  const binSize = (maxGC - minGC) / bins
  const binCounts = new Array(bins).fill(0)
  const binLabels = []
  
  gcValues.forEach(gc => {
    const binIndex = Math.floor((gc - minGC) / binSize)
    if (binIndex >= 0 && binIndex < bins) {
      binCounts[binIndex]++
    }
  })
  
  for (let i = 0; i < bins; i++) {
    const start = (minGC + i * binSize).toFixed(1)
    const end = (minGC + (i + 1) * binSize).toFixed(1)
    binLabels.push(`${start}-${end}%`)
  }
  
  const option = {
    title: {
      text: 'GC含量分布',
      subtext: responsive.isSmall ? 
        `${sequences.value.length} 条序列，平均: ${avgGC}%` :
        `${sequences.value.length} 条序列，平均GC含量: ${avgGC}%`,
      left: 'center',
      textStyle: {
        fontSize: responsive.titleFontSize,
        fontWeight: 'bold'
      },
      subtextStyle: {
        fontSize: responsive.subtitleFontSize
      }
    },
    tooltip: {
      trigger: 'axis',
      textStyle: {
        fontSize: responsive.tooltipFontSize
      },
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params) {
        const data = params[0]
        return `GC含量范围: ${data.axisValue}<br/>序列数量: ${data.value}`
      }
    },
    grid: responsive.grid,
    xAxis: {
      type: 'category',
      data: binLabels,
      name: responsive.isSmall ? 'GC (%)' : 'GC含量 (%)',
      nameLocation: 'middle',
      nameGap: responsive.isMobile ? 25 : 30,
      nameTextStyle: {
        fontSize: responsive.axisFontSize
      },
      axisLabel: {
        rotate: responsive.isMobile ? 45 : 30,
        fontSize: responsive.axisFontSize,
        interval: responsive.isSmall ? 'auto' : 0
      }
    },
    yAxis: {
      type: 'value',
      name: responsive.isSmall ? '数量' : '序列数量',
      nameLocation: 'middle',
      nameGap: responsive.isMobile ? 35 : 40,
      nameTextStyle: {
        fontSize: responsive.axisFontSize
      },
      axisLabel: {
        fontSize: responsive.axisFontSize
      }
    },
    series: [
      {
        name: '序列数量',
        type: 'bar',
        barMaxWidth: responsive.isMobile ? 20 : 30,
        data: binCounts,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#a7f3d0' },
            { offset: 0.5, color: '#10b981' },
            { offset: 1, color: '#065f46' }
          ]),
          borderRadius: [2, 2, 0, 0]
        },
        emphasis: {
          itemStyle: {
            opacity: 0.8,
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.3)'
          }
        }
      }
    ]
  }
  
  chartInstance.value.setOption(option, true)
}

const showVariantDistribution = () => {
  if (!chartInstance.value || variants.value.length === 0) return
  
  currentChart.value = 'variant'
  const responsive = getResponsiveConfig()
  
  // Count variants by chromosome
  const chromCounts = {}
  variants.value.forEach(variant => {
    chromCounts[variant.chrom] = (chromCounts[variant.chrom] || 0) + 1
  })
  
  const chroms = Object.keys(chromCounts).sort()
  const counts = chroms.map(chrom => chromCounts[chrom])
  
  // Limit chromosomes display for mobile
  const displayChroms = responsive.isMobile && chroms.length > 10 ? 
    chroms.slice(0, 10) : chroms
  const displayCounts = responsive.isMobile && chroms.length > 10 ? 
    counts.slice(0, 10) : counts
  
  const option = {
    title: {
      text: '变异染色体分布',
      subtext: responsive.isSmall ? 
        `${variants.value.length} 个变异，${chroms.length} 个染色体` :
        `总计 ${variants.value.length} 个变异，涉及 ${chroms.length} 个染色体`,
      left: 'center',
      textStyle: {
        fontSize: responsive.titleFontSize,
        fontWeight: 'bold'
      },
      subtextStyle: {
        fontSize: responsive.subtitleFontSize
      }
    },
    tooltip: {
      trigger: 'axis',
      textStyle: {
        fontSize: responsive.tooltipFontSize
      },
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params) {
        const data = params[0]
        const percentage = ((data.value / variants.value.length) * 100).toFixed(2)
        return `染色体: ${data.axisValue}<br/>变异数量: ${data.value}<br/>占比: ${percentage}%`
      }
    },
    grid: responsive.grid,
    xAxis: {
      type: 'category',
      data: displayChroms,
      name: responsive.isSmall ? '染色体' : '染色体',
      nameLocation: 'middle',
      nameGap: responsive.isMobile ? 25 : 30,
      nameTextStyle: {
        fontSize: responsive.axisFontSize
      },
      axisLabel: {
        rotate: responsive.isMobile ? 45 : 30,
        fontSize: responsive.axisFontSize,
        interval: responsive.isSmall ? 'auto' : 0
      }
    },
    yAxis: {
      type: 'value',
      name: responsive.isSmall ? '数量' : '变异数量',
      nameLocation: 'middle',
      nameGap: responsive.isMobile ? 35 : 40,
      nameTextStyle: {
        fontSize: responsive.axisFontSize
      },
      axisLabel: {
        fontSize: responsive.axisFontSize
      }
    },
    series: [
      {
        name: '变异数量',
        type: 'bar',
        barMaxWidth: responsive.isMobile ? 20 : 30,
        data: displayCounts,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#e9d5ff' },
            { offset: 0.5, color: '#8b5cf6' },
            { offset: 1, color: '#6b21a8' }
          ]),
          borderRadius: [2, 2, 0, 0]
        },
        emphasis: {
          itemStyle: {
            opacity: 0.8,
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.3)'
          }
        }
      }
    ]
  }
  
  // Add note for mobile if chromosomes are truncated
  if (responsive.isMobile && chroms.length > 10) {
    option.graphic = [{
      type: 'text',
      left: 'center',
      bottom: 10,
      style: {
        text: `显示前10个染色体（共${chroms.length}个）`,
        fontSize: responsive.axisFontSize,
        fill: '#64748b'
      }
    }]
  }
  
  chartInstance.value.setOption(option, true)
}

// Parse data when component mounts
onMounted(() => {
  if (props.previewData?.type === 'bioinformatics') {
    parseBioData()
  }
  
  if (props.previewData?.type === 'json') {
    formatJson()
  }
  
  if (props.previewData?.type === 'csv') {
    parseCSV()
  }
  
  // Add window resize listener
  window.addEventListener('resize', handleWindowResize)
  
  // Add keyboard listener
  document.addEventListener('keydown', handleKeyDown)
})

// Watch for changes in preview data
watch(() => props.previewData, (newData) => {
  if (newData?.type === 'bioinformatics') {
    parseBioData()
  } else if (newData?.type === 'json') {
    formatJson()
  } else if (newData?.type === 'csv') {
    parseCSV()
  }
}, { immediate: true })

// Watch for changes in show modal
watch(() => props.showModal, (newValue) => {
  if (!newValue) {
    resetModal()
  }
}, { immediate: true })

const saveFile = async () => {
  if (!hasChanges.value) return
  
  try {
    const response = await fetch(`/api/filemanager/${props.projectId}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        path: props.filePath, 
        content: editContent.value 
      })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    
    const result = await response.json()
    if (result.success) {
      originalContent.value = editContent.value
      editMode.value = false
      emit('save', { path: props.filePath, content: editContent.value })
      alert('File saved successfully!')
    } else {
      throw new Error(result.error || 'Failed to save file')
    }
  } catch (error) {
    console.error('Error saving file:', error)
    alert(`Failed to save file: ${error.message}`)
  }
}
// Watchers
watch(() => props.showModal, (newVal) => {
  if (newVal) {
    // Initialize based on file type
    if (props.previewData.type === 'csv') {
      parseCSV()
    }
    if (props.previewData.type === 'json') {
      formatJson()
    }
  }
})

// Handle keyboard events
const handleKeyDown = (e) => {
    if (e.key === 'Escape' && props.showModal) {
      closeModal()
    }
}

onUnmounted(() => {
  // Remove event listeners
  window.removeEventListener('resize', handleWindowResize)
  document.removeEventListener('keydown', handleKeyDown)
  
  // Clear timeout
  if (windowResizeTimeout) {
    clearTimeout(windowResizeTimeout)
    windowResizeTimeout = null
  }
  
  // Dispose chart instance
  if (chartInstance.value) {
    chartInstance.value.dispose()
    chartInstance.value = null
  }
  
  // Clean up resize observer
  if (chartContainer.value?._resizeObserver) {
    chartContainer.value._resizeObserver.disconnect()
    delete chartContainer.value._resizeObserver
  }
})
</script>

<style scoped>
.modal-backdrop {
  padding: var(--spacing-4);
}

.preview-modal {
  width: 90vw;
  height: 90vh;
  max-width: 1200px;
  overflow: hidden;
}

.file-info {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}

.file-type, .file-size {
  background: var(--surface-3);
  color: var(--gray-600);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-family: var(--font-family-mono);
}

.header-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 8px 16px;
  border: 1px solid var(--border-color);
  background: var(--surface-1);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
}

.action-btn:hover:not(:disabled) {
  background: var(--surface-3);
  border-color: var(--gray-400);
}

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.edit-btn { background: rgba(var(--accent-rgb), 0.12); color: var(--primary-500); }
.save-btn { background: var(--success-50); color: var(--success-500); }
.cancel-btn { background: var(--error-50); color: var(--error-500); }
.download-btn { background: var(--warning-50); color: var(--warning-500); }

.preview-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.edit-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.edit-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border-color-light);
}

.language-select {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 14px;
}

.edit-info {
  display: flex;
  gap: 16px;
  font-size: 14px;
  color: var(--gray-600);
}

.unsaved-indicator {
  color: var(--warning-500);
  font-weight: 500;
}

.code-editor {
  flex: 1;
  padding: 16px;
  border: none;
  outline: none;
  font-family: var(--font-family-mono);
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  background: var(--surface-2);
}

.edit-footer {
  padding: 8px 16px;
  background: var(--surface-3);
  border-top: 1px solid var(--border-color-light);
  font-size: 12px;
  color: var(--gray-600);
}

.preview-container {
  flex: 1;
  overflow: auto;
  padding: 16px;
}

.image-preview {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.image-controls {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 16px;
}

.zoom-btn {
  padding: 6px 12px;
  border: 1px solid var(--border-color);
  background: var(--surface-1);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
}

.zoom-level {
  font-weight: 500;
  color: var(--gray-700);
}

.image-container {
  flex: 1;
  overflow: auto;
  display: flex;
  justify-content: center;
  align-items: center;
  background: var(--surface-2);
  border-radius: var(--radius-sm);
}

.preview-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  cursor: grab;
  transition: transform 0.2s ease;
}

.preview-image:active {
  cursor: grabbing;
}

.preview-tabs {
  display: flex;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border-color-light);
}

.tab-btn {
  padding: 12px 24px;
  background: none;
  border: none;
  cursor: pointer;
  font-weight: 500;
  color: var(--gray-600);
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: var(--gray-700);
}

.tab-btn.active {
  color: var(--primary-500);
  border-bottom-color: var(--primary-500);
}

.code-content {
  background: var(--surface-2);
  padding: 16px;
  border-radius: var(--radius-sm);
  font-family: var(--font-family-mono);
  font-size: 14px;
  line-height: 1.5;
  overflow-x: auto;
  white-space: pre;
}

.code-content.word-wrap {
  white-space: pre-wrap;
  word-break: break-all;
}

.csv-table-view {
  overflow: auto;
  max-height: 70vh;
}

.csv-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.csv-table th,
.csv-table td {
  padding: 8px 12px;
  border: 1px solid var(--border-color-light);
  text-align: left;
}

.csv-table th {
  background: var(--surface-2);
  font-weight: 600;
  position: sticky;
  top: 0;
}

.table-footer {
  padding: 12px;
  text-align: center;
  color: var(--gray-600);
  font-size: 14px;
  background: var(--surface-2);
  border-top: 1px solid var(--border-color-light);
}

.chart-container {
  width: 100%;
  height: 500px;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-sm);
  background: var(--surface-1);
  padding: 10px;
  min-height: 400px;
  max-height: 600px;
}

.chart-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
  justify-content: center;
}

.viz-btn {
  padding: 8px 16px;
  background: var(--surface-2);
  color: var(--gray-600);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
}

.viz-btn:hover {
  background: var(--surface-3);
  border-color: var(--border-color-dark);
  color: var(--gray-700);
}

.viz-btn.active {
  background: var(--primary-500);
  color: white;
  border-color: var(--primary-500);
}

.viz-btn.active:hover {
  background: var(--primary-600);
  border-color: var(--primary-600);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chart-container {
    height: 400px;
    padding: 8px;
    min-height: 350px;
  }
  
  .chart-controls {
    gap: 6px;
    margin-bottom: 12px;
  }
  
  .viz-btn {
    padding: 6px 12px;
    font-size: 12px;
    min-width: auto;
  }
  
  .visualization-container {
    padding: 12px;
  }
}

@media (max-width: 480px) {
  .chart-container {
    height: 350px;
    padding: 6px;
    min-height: 300px;
  }
  
  .chart-controls {
    gap: 4px;
    margin-bottom: 10px;
  }
  
  .viz-btn {
    padding: 5px 10px;
    font-size: 11px;
    border-radius: var(--radius-sm);
  }
  
  .visualization-container {
    padding: 8px;
  }
}

/* 针对特别小的屏幕 */
@media (max-width: 360px) {
  .chart-container {
    height: 300px;
    padding: 4px;
    min-height: 250px;
  }
  
  .viz-btn {
    padding: 4px 8px;
    font-size: 10px;
    flex: 1;
    text-align: center;
  }
  
  .chart-controls {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 4px;
  }
}

/* 生物信息学文件预览样式 */
.bio-preview {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.bio-header {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  padding: 12px;
  background: var(--surface-2);
  border-radius: var(--radius-sm);
}

.format-badge {
  background: var(--primary-500);
  color: white;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
}

.count-info {
  background: var(--surface-3);
  color: var(--gray-600);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
}

.size-info {
  background: rgba(var(--accent-rgb), 0.12);
  color: var(--primary-700);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
}

/* 大文件警告样式 */
.large-file-warning {
  margin: 16px 0;
  padding: 20px;
  background: var(--warning-50);
  border: 1px solid var(--warning-500);
  border-radius: var(--radius-sm);
}

.warning-content {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}

.warning-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.warning-text h4 {
  margin: 0 0 8px 0;
  color: var(--warning-600);
  font-size: 16px;
}

.warning-text p {
  margin: 0;
  color: var(--warning-600);
  font-size: 14px;
  line-height: 1.5;
}

.large-file-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.large-file-actions .action-btn {
  padding: 10px 16px;
  border: 1px solid var(--border-color);
  background: var(--surface-1);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.large-file-actions .action-btn:hover:not(:disabled) {
  background: var(--surface-3);
  border-color: var(--gray-400);
}

.large-file-actions .action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.large-file-actions .action-btn.primary {
  background: var(--primary-500);
  border-color: var(--primary-500);
  color: white;
}

.large-file-actions .action-btn.primary:hover:not(:disabled) {
  background: var(--primary-600);
  border-color: var(--primary-600);
}

.sampled-preview {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.sample-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border-color-light);
}

.sample-tag {
  background: var(--success-500);
  color: white;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 600;
}

.sample-info {
  font-size: 12px;
  color: var(--gray-600);
}

.bio-analysis-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.analysis-tabs {
  display: flex;
  gap: 2px;
  margin-bottom: 16px;
  background: var(--surface-3);
  padding: 4px;
  border-radius: var(--radius-sm);
  flex-wrap: wrap;
}

.tab-btn {
  flex: 1;
  min-width: 100px;
  padding: 8px 12px;
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 14px;
  color: var(--gray-600);
  transition: all 0.2s;
}

.tab-btn:hover {
  background: var(--border-color-light);
}

.tab-btn.active {
  background: var(--surface-1);
  color: var(--primary-500);
  box-shadow: var(--shadow-xs);
}

.analysis-content {
  flex: 1;
  overflow-y: auto;
}

/* 统计信息卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.stat-card {
  background: var(--surface-2);
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-sm);
  padding: 16px;
  text-align: center;
}

.stat-card h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: var(--gray-600);
  font-weight: 500;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--gray-900);
  margin: 0;
}

/* 序列显示 */
.sequences-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.sequences-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--surface-2);
  border-radius: var(--radius-sm);
}

.sequence-info {
  display: flex;
  gap: 8px;
  align-items: center;
}

.sequence-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.sequence-select {
  padding: 4px 8px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  font-size: 12px;
  max-width: 250px;
}

.format-btn {
  padding: 4px 8px;
  background: var(--primary-500);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 12px;
}

.sequence-display {
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.sequence-header-info {
  padding: 12px;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border-color-light);
}

.sequence-header-info h4 {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: var(--gray-900);
}

.sequence-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--gray-600);
}

.sequence-content {
  padding: 12px;
}

.sequence-line {
  margin-bottom: 12px;
}

.sequence-text {
  background: var(--surface-3);
  padding: 8px;
  border-radius: var(--radius-sm);
  font-family: 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
}

.sequence-text.formatted {
  line-height: 1.6;
}

.quality-line {
  margin-top: 12px;
}

.quality-text {
  background: var(--surface-2);
  padding: 8px;
  border-radius: var(--radius-sm);
  font-family: 'Courier New', monospace;
  font-size: 12px;
  margin-bottom: 8px;
  max-height: 100px;
  overflow-y: auto;
}

.quality-graph {
  display: flex;
  gap: 1px;
  height: 60px;
  align-items: end;
  background: var(--surface-2);
  padding: 4px;
  border-radius: var(--radius-sm);
  overflow-x: auto;
}

.quality-bar {
  width: 2px;
  min-width: 2px;
  transition: all 0.2s;
}

.quality-bar:hover {
  width: 4px;
}

.composition-mini {
  display: flex;
  gap: 16px;
  margin-top: 8px;
}

.base-count {
  font-size: 12px;
  color: var(--gray-600);
}

.gc-content {
  font-size: 12px;
  color: var(--primary-500);
  font-weight: 600;
}

/* 表格样式 */
.variants-table, .features-table, .regions-table, .sam-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  background: var(--surface-1);
  border-radius: var(--radius-sm);
  overflow: hidden;
  box-shadow: var(--shadow-xs);
}

.variants-table th, .features-table th, .regions-table th, .sam-table th {
  background: var(--surface-2);
  padding: 8px;
  text-align: left;
  font-weight: 600;
  color: var(--gray-700);
  border-bottom: 1px solid var(--border-color-light);
}

.variants-table td, .features-table td, .regions-table td, .sam-table td {
  padding: 6px 8px;
  border-bottom: 1px solid var(--surface-3);
  color: var(--gray-600);
}

.variants-table tr:hover, .features-table tr:hover, .regions-table tr:hover, .sam-table tr:hover {
  background: var(--surface-2);
}

.sequence-cell, .quality-cell {
  font-family: 'Courier New', monospace;
  font-size: 11px;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attributes-cell {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 表容器 */
.vcf-table, .annotation-table, .bed-table, .alignments-table {
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--border-color-light);
  border-radius: var(--radius-sm);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  }
  
  .sequences-header {
    flex-direction: column;
    gap: 8px;
  }
  
  .sequence-meta {
    flex-direction: column;
    gap: 4px;
  }
  
  .composition-mini {
    flex-wrap: wrap;
    gap: 8px;
  }
  
  .tab-btn {
    flex: none;
    min-width: 80px;
  }
}

/* Add more specific styling for other preview types... */
</style>
