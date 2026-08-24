import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'
import fs from 'node:fs'
import net from 'node:net'
import { spawn, type ChildProcess } from 'node:child_process'

let backendProcess: ChildProcess | null = null
let isLaunchingBackend = false

function checkPort8000(): Promise<boolean> {
  return new Promise((resolve) => {
    const socket = new net.Socket()
    socket.setTimeout(400)
    socket.on('connect', () => {
      socket.destroy()
      resolve(true)
    })
    socket.on('timeout', () => {
      socket.destroy()
      resolve(false)
    })
    socket.on('error', () => {
      socket.destroy()
      resolve(false)
    })
    socket.connect(8000, '127.0.0.1')
  })
}

async function autoStartBackendService() {
  if (isLaunchingBackend) return
  const isUp = await checkPort8000()
  if (isUp) return

  isLaunchingBackend = true
  console.log('[Auto-Healing] ⚡ Location Engine (Port 8000) is offline. Auto-starting backend in background...')

  const rootDir = process.cwd()
  const projDir = path.join(rootDir, 'ble-indoor-positioning')
  const venvPy = path.join(projDir, '.venv', 'Scripts', 'python.exe')
  const pyCmd = fs.existsSync(venvPy) ? venvPy : 'python'
  const scriptPath = path.join(projDir, 'server', 'app.py')

  try {
    backendProcess = spawn(pyCmd, [scriptPath], {
      cwd: path.join(projDir, 'server'),
      detached: false,
      stdio: 'ignore',
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
    })

    backendProcess.on('error', (err) => {
      console.error('[Auto-Healing] Failed to spawn backend process:', err)
      isLaunchingBackend = false
    })

    backendProcess.on('exit', (code) => {
      console.log(`[Auto-Healing] Backend process exited with code ${code}`)
      backendProcess = null
      isLaunchingBackend = false
    })

    // Give it a brief moment to bind to 8000
    for (let i = 0; i < 15; i++) {
      await new Promise((r) => setTimeout(r, 200))
      if (await checkPort8000()) {
        console.log('[Auto-Healing] ✅ Location Engine API (Port 8000) is now ONLINE!')
        break
      }
    }
  } catch (err) {
    console.error('[Auto-Healing] Error starting background backend:', err)
  } finally {
    isLaunchingBackend = false
  }
}

// Cleanup spawned process when Vite exits
const cleanupBackendProcess = () => {
  if (backendProcess && !backendProcess.killed) {
    console.log('[Auto-Healing] Terminating background Location Engine process...')
    try {
      backendProcess.kill('SIGTERM')
    } catch {
      // Ignore cleanup errors
    }
  }
}

process.on('exit', cleanupBackendProcess)
process.on('SIGINT', () => {
  cleanupBackendProcess()
  process.exit(0)
})
process.on('SIGTERM', () => {
  cleanupBackendProcess()
  process.exit(0)
})

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
        name: 'dev-cache-headers-and-auto-heal',
        configureServer(server) {
          server.middlewares.use((req, res, next) => {
            // Cache pre-bundled dependencies and node_modules for instant reload
            if (req.url && (req.url.includes('/@vite/') || req.url.includes('/node_modules/'))) {
              res.setHeader('Cache-Control', 'public, max-age=31536000, immutable')
            }

            // Auto-start backend handler
            if (req.url === '/api/service/autostart') {
              autoStartBackendService().then(() => {
                res.setHeader('Content-Type', 'application/json')
                res.end(JSON.stringify({ status: 'ok', message: 'Location Engine background auto-start triggered.' }))
              })
              return
            }

            // Proactively auto-heal backend if an API request is made
            if (req.url && req.url.startsWith('/api/')) {
              checkPort8000().then((isUp) => {
                if (!isUp) {
                  autoStartBackendService()
                }
              })
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

