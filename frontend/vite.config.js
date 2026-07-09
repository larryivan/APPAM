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
    build: {
      chunkSizeWarningLimit: 650,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) return undefined
            if (id.includes('/echarts/') || id.includes('/zrender/')) return 'vendor-charts'
            if (id.includes('/xterm')) return 'vendor-terminal'
            if (id.includes('/@vue-flow/') || id.includes('/@dagrejs/')) return 'vendor-workflow'
            if (id.includes('/marked/') || id.includes('/highlight.js/')) return 'vendor-docs'
            if (
              id.includes('/vue/')
              || id.includes('/vue-router/')
              || id.includes('/pinia/')
              || id.includes('/axios/')
              || id.includes('/socket.io-client/')
            ) return 'vendor-core'
            return undefined
          }
        }
      }
    },
    server: {
      host: env.VITE_HOST || '0.0.0.0',
      port: Number(env.VITE_PORT || 25078),
      strictPort: true,
      cors: true,
      proxy: {
        '/api': {
          target: env.VITE_API_URL || 'http://127.0.0.1:25079',
          changeOrigin: true,
        },
        '/socket.io': {
          target: env.VITE_WS_URL || 'ws://127.0.0.1:25079',
          ws: true,
        },
      }
    }
  }
})
