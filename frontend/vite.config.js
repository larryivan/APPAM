import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      host: env.VITE_HOST || '0.0.0.0',
      port: Number(env.VITE_PORT || 19453),
      strictPort: true,
      cors: true,
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://127.0.0.1:19454',
          changeOrigin: true,
        },
        '/socket.io': {
          target: env.VITE_WS_URL || 'ws://127.0.0.1:19454',
          ws: true,
        },
      }
    }
  }
})
