import { contextBridge, ipcRenderer } from 'electron'

/**
 * Expose a minimal, typed API surface to the renderer process.
 * contextBridge ensures no Node.js APIs leak into the renderer (Risk R-08).
 */
contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  setContentProtection: (enable: boolean) => ipcRenderer.send('set-content-protection', enable),
  setSkipTaskbar: (skip: boolean) => ipcRenderer.send('set-skip-taskbar', skip),
})

export type ElectronAPI = {
  platform: NodeJS.Platform
  setContentProtection: (enable: boolean) => void
  setSkipTaskbar: (skip: boolean) => void
}

