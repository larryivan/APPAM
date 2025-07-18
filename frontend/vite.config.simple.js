import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 最简单的配置
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 8083
  }
}) 