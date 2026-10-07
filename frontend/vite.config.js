import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// When VITE_API_BASE_URL is left blank the client calls a relative /api path,
// which the dev server forwards to the FastAPI app below. Keeping requests
// same-origin means the browser never sends a cross-origin request to an API
// that does not enable CORS.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.VITE_PROXY_TARGET || 'http://localhost:8000'

  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: false,
    },
  }
})
