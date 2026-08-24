import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// Local standalone Vite configuration (Port 3000 with Caching & Pre-bundling)
export default defineConfig(({ mode }) => {
  const emitSourcemaps = mode === 'development'

  return {
    base: './',
    build: {
      sourcemap: emitSourcemaps ? 'inline' : false,
      minify: !emitSourcemaps,
      cssMinify: true,
      modulePreload: { polyfill: true },
    },
    optimizeDeps: {
      include: ['react', 'react-dom', 'recharts'],
      holdUntilCrawlEnd: false,
    },
    plugins: [
      react(),
      tailwindcss(),
      {
        name: 'dev-cache-headers',
        configureServer(server) {
          server.middlewares.use((req, res, next) => {
            // Cache pre-bundled dependencies and node_modules for instant reload
            if (req.url && (req.url.includes('/@vite/') || req.url.includes('/node_modules/'))) {
              res.setHeader('Cache-Control', 'public, max-age=31536000, immutable')
            }
            next()
          })
        },
      },
    ],
    resolve: {
      alias: {
        '@': path.resolve(import.meta.dirname, './src'),
      },
    },
    server: {
      host: '0.0.0.0',
      port: parseInt(process.env.PORT || '3000'),
      strictPort: false,
      hmr: {
        host: 'localhost',
        clientPort: 3000,
      },
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
        '/ws': {
          target: 'ws://127.0.0.1:8000',
          ws: true,
        },
      },
      warmup: {
        clientFiles: ['./src/main.tsx', './src/App.tsx', './src/index.css'],
      },
      watch: {
        ignored: [
          '**/ble-indoor-positioning/**',
          '**/Unity_BLE_Simulator/**',
          '**/build/**',
          '**/dist/**',
          '**/.git/**',
        ],
      },
    },
    preview: {
      host: '0.0.0.0',
      port: parseInt(process.env.PORT || '3000'),
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/setupTests.ts'],
    },
  }
})
