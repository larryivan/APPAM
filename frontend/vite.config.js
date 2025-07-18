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
    host: true, // 或者使用 '0.0.0.0'，true 会监听所有地址
    port: 8081,
    strictPort: true, // 如果端口被占用则报错
    cors: true, // 启用CORS
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
