import { app, BrowserWindow, ipcMain, Menu, globalShortcut, screen, BrowserView } from 'electron'
import path from 'path'
import fs from 'fs'
import { spawn, ChildProcess } from 'child_process'

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged
let backendProcess: ChildProcess | null = null

// ── Overlay state ───────────────────────────────────────────────────────────
let overlayWin: BrowserWindow | null = null
let overlayClickThrough = false
const OVERLAY_BOUNDS_FILE = path.join(app.getPath('userData'), 'overlay-bounds.json')

// ── Backend sidecar ─────────────────────────────────────────────────────────

function startBackend() {
  if (isDev) {
    console.log('Running in development mode. Assuming backend is started separately.')
    return
  }

  const isWin = process.platform === 'win32'
  const backendBinName = isWin ? 'reai-backend.exe' : 'reai-backend'

  // Path to the PyInstaller folder inside Resources directory:
  // resources/backend/reai-backend/reai-backend.exe (or reai-backend on macOS)
  const backendPath = path.join(
    process.resourcesPath,
    'backend',
    'reai-backend',
    backendBinName
  )

  console.log(`Spawning backend sidecar at: ${backendPath}`)
  const backendDir = path.dirname(backendPath)

  backendProcess = spawn(backendPath, [], {
    stdio: 'ignore',
    cwd: backendDir,
    env: {
      ...process.env,
      PORT: '8000',
      HOST: '127.0.0.1'
    }
  })

  backendProcess.on('error', (err) => {
    console.error('Failed to start backend process:', err)
  })

  backendProcess.on('exit', (code, signal) => {
    console.log(`Backend process exited with code ${code} and signal ${signal}`)
  })
}

function stopBackend() {
  if (backendProcess) {
    console.log('Terminating backend process...')
    if (process.platform === 'win32') {
      try {
        spawn('taskkill', ['/pid', backendProcess.pid!.toString(), '/f', '/t'])
      } catch (err) {
        console.error('Failed to taskkill backend on Windows:', err)
      }
    } else {
      backendProcess.kill('SIGKILL')
    }
    backendProcess = null
  }
}

// ── Main Window ─────────────────────────────────────────────────────────────

function createWindow() {
  // Remove the native menu bar entirely
  Menu.setApplicationMenu(null)

  const win = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 960,
    minHeight: 640,
    titleBarStyle: 'hidden',
    backgroundColor: '#fdfbf7',
    icon: path.join(__dirname, '../icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webviewTag: true,
    },
  })

  if (isDev) {
    win.loadURL('http://localhost:3000')
    win.webContents.openDevTools()
  } else {
    win.loadFile(path.join(__dirname, '../dist/index.html'))
  }
}

// ── Overlay Window ──────────────────────────────────────────────────────────

function loadOverlayBounds(): { x?: number; y?: number; width: number; height: number } {
  try {
    if (fs.existsSync(OVERLAY_BOUNDS_FILE)) {
      const data = JSON.parse(fs.readFileSync(OVERLAY_BOUNDS_FILE, 'utf-8'))
      return {
        x: data.x,
        y: data.y,
        width: data.width || 420,
        height: data.height || 600,
      }
    }
  } catch (err) {
    console.warn('Failed to load overlay bounds:', err)
  }
  return { width: 420, height: 600 }
}

function saveOverlayBounds() {
  if (!overlayWin || overlayWin.isDestroyed()) return
  try {
    const bounds = overlayWin.getBounds()
    fs.writeFileSync(OVERLAY_BOUNDS_FILE, JSON.stringify(bounds), 'utf-8')
  } catch (err) {
    console.warn('Failed to save overlay bounds:', err)
  }
}

function createOverlayWindow() {
  if (overlayWin && !overlayWin.isDestroyed()) {
    overlayWin.focus()
    return
  }

  const savedBounds = loadOverlayBounds()

  // Position on the active monitor if no saved position
  let x = savedBounds.x
  let y = savedBounds.y

  if (x === undefined || y === undefined) {
    const cursorPoint = screen.getCursorScreenPoint()
    const activeDisplay = screen.getDisplayNearestPoint(cursorPoint)
    const workArea = activeDisplay.workArea

    // Bottom-right corner of active monitor, with padding
    x = workArea.x + workArea.width - savedBounds.width - 24
    y = workArea.y + workArea.height - savedBounds.height - 24
  }

  overlayWin = new BrowserWindow({
    x,
    y,
    width: savedBounds.width,
    height: savedBounds.height,
    minWidth: 320,
    minHeight: 400,
    maxWidth: 800,
    maxHeight: 1000,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    resizable: true,
    skipTaskbar: true,
    hasShadow: false,
    focusable: true,
    icon: path.join(__dirname, '../icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  })

  // Enable screen-sharing protection by default
  overlayWin.setContentProtection(true)

  // Load the overlay route
  if (isDev) {
    overlayWin.loadURL('http://localhost:3000/#/overlay')
  } else {
    overlayWin.loadFile(path.join(__dirname, '../dist/index.html'), {
      hash: '/overlay',
    })
  }

  // Persist position on move/resize
  overlayWin.on('moved', () => saveOverlayBounds())
  overlayWin.on('resized', () => saveOverlayBounds())

  overlayWin.on('closed', () => {
    overlayWin = null
    overlayClickThrough = false
  })
}

function toggleOverlayVisibility() {
  if (!overlayWin || overlayWin.isDestroyed()) {
    createOverlayWindow()
    return
  }

  if (overlayWin.isVisible()) {
    overlayWin.hide()
  } else {
    overlayWin.show()
    // Restore click-through state
    if (overlayClickThrough) {
      overlayWin.setIgnoreMouseEvents(true, { forward: true })
    }
  }
}

function toggleOverlayClickThrough() {
  if (!overlayWin || overlayWin.isDestroyed()) return

  overlayClickThrough = !overlayClickThrough

  if (overlayClickThrough) {
    overlayWin.setIgnoreMouseEvents(true, { forward: true })
  } else {
    overlayWin.setIgnoreMouseEvents(false)
  }

  // Notify the renderer about the mode change
  overlayWin.webContents.send('overlay-mode-changed', overlayClickThrough)
}

// ── Global Hotkeys ──────────────────────────────────────────────────────────

function registerGlobalShortcuts() {
  // Ctrl+Space — Toggle overlay visibility
  globalShortcut.register('CommandOrControl+Space', () => {
    toggleOverlayVisibility()
  })

  // Ctrl+Shift+Space — Toggle click-through mode
  globalShortcut.register('CommandOrControl+Shift+Space', () => {
    toggleOverlayClickThrough()
  })
}

// ── App Lifecycle ───────────────────────────────────────────────────────────

app.whenReady().then(() => {
  const { session, desktopCapturer } = require('electron')
  session.defaultSession.setDisplayMediaRequestHandler((request: any, callback: any) => {
    desktopCapturer.getSources({ types: ['screen'] }).then((sources: any[]) => {
      // Auto-select the first screen and enable system audio loopback
      callback({ video: sources[0], audio: 'loopback' })
    }).catch((err: any) => {
      console.error('Error getting sources for display media:', err)
      // Call with null to reject if there's an error
      callback(null as any)
    })
  })

  startBackend()
  createWindow()
  createOverlayWindow()
  registerGlobalShortcuts()
})

app.on('will-quit', () => {
  globalShortcut.unregisterAll()
  stopBackend()
})

app.on('window-all-closed', () => {
  stopBackend()
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

// ── IPC Handlers ────────────────────────────────────────────────────────────

ipcMain.on('set-content-protection', (event, enable: boolean) => {
  const win = BrowserWindow.fromWebContents(event.sender)
  if (win) {
    win.setContentProtection(enable)
  }
  // Also update overlay protection if it exists
  if (overlayWin && !overlayWin.isDestroyed()) {
    overlayWin.setContentProtection(enable)
  }
})

ipcMain.on('set-skip-taskbar', (event, skip: boolean) => {
  const win = BrowserWindow.fromWebContents(event.sender)
  if (win) {
    win.setSkipTaskbar(skip)
    
    // On Windows, dynamically changing skipTaskbar requires a quick hide/show cycle 
    // to force Windows Shell to refresh and immediately hide/show the taskbar icon.
    if (process.platform === 'win32') {
      win.hide()
      win.show()
    }
  }
})

ipcMain.on('window-minimize', (event) => {
  BrowserWindow.fromWebContents(event.sender)?.minimize()
})

ipcMain.on('window-maximize', (event) => {
  const win = BrowserWindow.fromWebContents(event.sender)
  if (!win) return
  win.isMaximized() ? win.unmaximize() : win.maximize()
})

ipcMain.on('window-close', (event) => {
  BrowserWindow.fromWebContents(event.sender)?.close()
})

// Overlay-specific IPC
ipcMain.on('overlay-toggle-click-through', () => {
  toggleOverlayClickThrough()
})

// --- BrowserView Management ---
const browserViews = new Map<string, BrowserView>()
let activeBrowserId: string | null = null

ipcMain.on('browser-create-tab', (event, id: string, url: string) => {
  const win = BrowserWindow.fromWebContents(event.sender)
  if (!win) return

  const view = new BrowserView({
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    }
  })
  browserViews.set(id, view)
  win.addBrowserView(view)
  view.webContents.loadURL(url)

  // Send navigation and title events back to React
  view.webContents.on('did-navigate', (_, navUrl) => {
    win.webContents.send('browser-did-navigate', id, navUrl)
  })
  view.webContents.on('did-navigate-in-page', (_, navUrl) => {
    win.webContents.send('browser-did-navigate', id, navUrl)
  })
  view.webContents.on('page-title-updated', (_, title) => {
    win.webContents.send('browser-title-updated', id, title)
  })
})

ipcMain.on('browser-switch-tab', (event, id: string) => {
  const win = BrowserWindow.fromWebContents(event.sender)
  if (!win) return
  const view = browserViews.get(id)
  if (view) {
    win.setTopBrowserView(view)
    activeBrowserId = id
  }
})

ipcMain.on('browser-close-tab', (event, id: string) => {
  const win = BrowserWindow.fromWebContents(event.sender)
  if (!win) return
  const view = browserViews.get(id)
  if (view) {
    win.removeBrowserView(view)
    browserViews.delete(id)
    if (activeBrowserId === id) activeBrowserId = null
  }
})

ipcMain.on('browser-resize', (event, bounds: { x: number, y: number, width: number, height: number }) => {
  const win = BrowserWindow.fromWebContents(event.sender)
  if (!win) return
  // Resize all views so they are ready when switched to
  for (const view of browserViews.values()) {
    view.setBounds(bounds)
  }
})

ipcMain.on('browser-navigate', (event, id: string, url: string) => {
  const view = browserViews.get(id)
  if (view) view.webContents.loadURL(url)
})

ipcMain.on('browser-go-back', (event, id: string) => {
  const view = browserViews.get(id)
  if (view && view.webContents.canGoBack()) view.webContents.goBack()
})

ipcMain.on('browser-go-forward', (event, id: string) => {
  const view = browserViews.get(id)
  if (view && view.webContents.canGoForward()) view.webContents.goForward()
})

ipcMain.on('browser-reload', (event, id: string) => {
  const view = browserViews.get(id)
  if (view) view.webContents.reload()
})
