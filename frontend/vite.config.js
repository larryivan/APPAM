import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const apiTarget = env.VITE_API_URL || 'http://127.0.0.1:25079'
  const wsTarget = env.VITE_WS_URL || 'ws://127.0.0.1:25079'
  const apiOrigin = new URL(apiTarget).origin
  // Engine.IO compares Origin with http(s) origins, so present the socket
  // target in that form; a ws:// origin is never accepted.
  const wsOrigin = new URL(wsTarget.replace(/^ws/, 'http')).origin

  // Build for a URL prefix, e.g. VITE_BASE_PATH=/proxy/relative/<host>/<port>
  // behind a gateway that strips it; see src/lib/basePath.js.
  const base = (env.VITE_BASE_PATH || env.APPAM_PUBLIC_BASE_PATH || '/').replace(/\/*$/, '/')

  return {
    base,
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
            if (id.includes('/marked/')) return 'vendor-docs'
            if (
              id.includes('/vue/')
              || id.includes('/vue-router/')
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
          target: apiTarget,
          changeOrigin: true,
          headers: {
            Origin: apiOrigin,
          },
        },
        '/socket.io': {
          target: wsTarget,
          ws: true,
          changeOrigin: true,
          headers: {
            Origin: wsOrigin,
          },
        },
      }
    }
  }
})
