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
    host: '0.0.0.0', // 监听所有网络接口
    port: 8080,      // 使用开启的防火墙端口
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://127.0.0.1:5001',
        changeOrigin: true,
      },
      '/socket.io': {
        target: process.env.VITE_WS_URL || 'ws://127.0.0.1:5001',
        ws: true,
      },
    }
  }
})
