<template>
  <component
    :is="iconComponent"
    :size="size"
    :stroke-width="strokeWidth"
    :class="['app-icon', { spin }]"
    aria-hidden="true"
  />
</template>

<script setup>
import { computed } from 'vue'
import {
  Activity, AlignJustify, ArrowDown, ArrowLeft, ArrowUp, BookOpen, Box, ChartBar, ChartLine, ChartNoAxesCombined, ChartPie, ChartScatter, Check,
  ChevronDown, ChevronRight, ChevronUp, Circle, CircleCheck, CircleX, ClipboardList, ClipboardPaste,
  Copy, Cpu, Dna, Download, ExternalLink, Eye, EyeOff, File, FileArchive, FileCode, FileImage, FileMusic,
  FilePen, FileSpreadsheet, FileText, FileVideo, Folder, FolderOpen, FolderUp,
  FolderPlus, Globe, HardDrive, Home, Image, Images, Info, Keyboard, LayoutDashboard, LayoutGrid, Lightbulb, List, LogIn, LogOut, MapPin,
  KeyRound, Maximize2, MemoryStick, MessageCircle, Minimize2, Minus, MoreHorizontal, PanelLeftClose,
  PanelLeftOpen, Pause, Pencil, Play, Plus, RotateCcw, Save,
  Scissors, Search, ShieldCheck, SlidersHorizontal, Table, Target, Trash2, TriangleAlert, UserRound, Users, WandSparkles,
  SquareTerminal, Upload, Wrench, WrapText, X, Zap, ZoomIn, ZoomOut,
} from '@lucide/vue'

/**
 * 统一图标封装,基于 @lucide/vue。
 * 用法:<Icon name="folder" /> 或 <Icon name="Folder" />,接受 kebab-case 或 PascalCase。
 * 仅显式引入实际用到的图标以便 tree-shaking;新增图标时在下方 registry 注册即可。
 * 替代散落的 emoji 与 inline SVG,不改动任何业务逻辑。
 */
const registry = {
  Activity, AlignJustify, ArrowDown, ArrowLeft, ArrowUp, BookOpen, Box, ChartBar, ChartLine, ChartNoAxesCombined, ChartPie, ChartScatter, Check,
  ChevronDown, ChevronRight, ChevronUp, Circle, CircleCheck, CircleX, ClipboardList, ClipboardPaste,
  Copy, Cpu, Dna, Download, ExternalLink, Eye, EyeOff, File, FileArchive, FileCode, FileImage, FileMusic,
  FilePen, FileSpreadsheet, FileText, FileVideo, Folder, FolderOpen, FolderUp,
  FolderPlus, Globe, HardDrive, Home, Image, Images, Info, Keyboard, LayoutDashboard, LayoutGrid, Lightbulb, List, LogIn, LogOut, MapPin,
  KeyRound, Maximize2, MemoryStick, MessageCircle, Minimize2, Minus, MoreHorizontal, PanelLeftClose,
  PanelLeftOpen, Pause, Pencil, Play, Plus, RotateCcw, Save,
  Scissors, Search, ShieldCheck, SlidersHorizontal, Table, Target, Trash2, TriangleAlert, UserRound, Users, WandSparkles,
  SquareTerminal, Upload, Wrench, WrapText, X, Zap, ZoomIn, ZoomOut,
}

const props = defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 18 },
  strokeWidth: { type: [Number, String], default: 2 },
  spin: { type: Boolean, default: false },
})

const toPascal = (s) =>
  String(s).replace(/(^|-|_)([a-z0-9])/g, (_, __, c) => c.toUpperCase())

const iconComponent = computed(() => {
  const resolved = registry[toPascal(props.name)]
  if (!resolved && import.meta.env.DEV) {
    console.warn(`[Icon] "${props.name}" is not registered; falling back to Circle.`)
  }
  return resolved || Circle
})
</script>

<style scoped>
.app-icon {
  display: inline-block;
  vertical-align: middle;
  flex-shrink: 0;
}
.app-icon.spin {
  animation: app-icon-spin 0.9s linear infinite;
}
@keyframes app-icon-spin {
  to { transform: rotate(360deg); }
}
</style>
