import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import electron from 'vite-plugin-electron'
import { resolve } from 'path'

export default defineConfig({
  envDir: '../',
  plugins: [
    react(),
    electron([
      {
        // Main-Process entry point of the Electron App.
        entry: 'src/electron/main.ts',
      },
      {
        entry: 'src/electron/preload.ts',
        onstart(options) {
          // Notify the Renderer-Process to reload the page when the Preload-Scripts build is complete,
          // instead of restarting the entire Electron App.
          options.reload()
        },
      },
    ]),
  ],
  base: './',
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: process.env.VITE_API_URL || 'http://localhost:8000',
        changeOrigin: true,
        ws: true,  // enable WebSocket proxying for /api/ws/realtime
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
