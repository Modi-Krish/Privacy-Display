import { contextBridge, ipcRenderer } from 'electron'

/**
 * Expose a minimal, typed API surface to the renderer process.
 * contextBridge ensures no Node.js APIs leak into the renderer (Risk R-08).
 */
contextBridge.exposeInMainWorld('electronAPI', {
  platform: process.platform,
  setContentProtection: (enable: boolean) => ipcRenderer.send('set-content-protection', enable),
  setSkipTaskbar: (skip: boolean) => ipcRenderer.send('set-skip-taskbar', skip),
  minimizeWindow: () => ipcRenderer.send('window-minimize'),
  maximizeWindow: () => ipcRenderer.send('window-maximize'),
  closeWindow: () => ipcRenderer.send('window-close'),
  
  createTab: (id: string, url: string) => ipcRenderer.send('browser-create-tab', id, url),
  switchTab: (id: string) => ipcRenderer.send('browser-switch-tab', id),
  closeTab: (id: string) => ipcRenderer.send('browser-close-tab', id),
  resizeBrowser: (bounds: { x: number, y: number, width: number, height: number }) => ipcRenderer.send('browser-resize', bounds),
  navigate: (id: string, url: string) => ipcRenderer.send('browser-navigate', id, url),
  goBack: (id: string) => ipcRenderer.send('browser-go-back', id),
  goForward: (id: string) => ipcRenderer.send('browser-go-forward', id),
  reload: (id: string) => ipcRenderer.send('browser-reload', id),
  onBrowserNavigate: (callback: (id: string, url: string) => void) => {
    ipcRenderer.removeAllListeners('browser-did-navigate')
    ipcRenderer.on('browser-did-navigate', (_event, id, url) => callback(id, url))
  },
  onBrowserTitleUpdated: (callback: (id: string, title: string) => void) => {
    ipcRenderer.removeAllListeners('browser-title-updated')
    ipcRenderer.on('browser-title-updated', (_event, id, title) => callback(id, title))
  },

  // ── Overlay APIs ─────────────────────────────────────────────────────
  toggleOverlayClickThrough: () => ipcRenderer.send('overlay-toggle-click-through'),
  onOverlayModeChanged: (callback: (isClickThrough: boolean) => void) => {
    ipcRenderer.removeAllListeners('overlay-mode-changed')
    ipcRenderer.on('overlay-mode-changed', (_event, isClickThrough) => callback(isClickThrough))
  },
  
  // ── Auth APIs ────────────────────────────────────────────────────────
  auth: {
    setTokens: (tokens: { access_token: string, refresh_token: string, user_id: string }) => ipcRenderer.invoke('auth-set-tokens', tokens),
    getTokens: () => ipcRenderer.invoke('auth-get-tokens'),
    clearTokens: () => ipcRenderer.invoke('auth-clear-tokens'),
  },
})

export type ElectronAPI = {
  platform: NodeJS.Platform
  setContentProtection: (enable: boolean) => void
  setSkipTaskbar: (skip: boolean) => void
  minimizeWindow: () => void
  maximizeWindow: () => void
  closeWindow: () => void
  
  createTab: (id: string, url: string) => void
  switchTab: (id: string) => void
  closeTab: (id: string) => void
  resizeBrowser: (bounds: { x: number, y: number, width: number, height: number }) => void
  navigate: (id: string, url: string) => void
  goBack: (id: string) => void
  goForward: (id: string) => void
  reload: (id: string) => void
  onBrowserNavigate: (callback: (id: string, url: string) => void) => void
  onBrowserTitleUpdated: (callback: (id: string, title: string) => void) => void

  // Overlay
  toggleOverlayClickThrough: () => void
  onOverlayModeChanged: (callback: (isClickThrough: boolean) => void) => void

  // Auth
  auth: {
    setTokens: (tokens: { access_token: string, refresh_token: string, user_id: string }) => Promise<boolean>
    getTokens: () => Promise<{ access_token: string, refresh_token: string, user_id: string } | null>
    clearTokens: () => Promise<boolean>
  }
}
