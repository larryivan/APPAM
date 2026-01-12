import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0', // 明确使用字符串而不是true
    port: 8082,      // 临时换端口测试
    strictPort: true,
    cors: true,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://127.0.0.1:5000',
        changeOrigin: true,
      },
      '/socket.io': {
        target: process.env.VITE_WS_URL || 'ws://127.0.0.1:5000',
        ws: true,
      },
    }
  }
})
