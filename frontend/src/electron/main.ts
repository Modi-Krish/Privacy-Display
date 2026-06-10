import { app, BrowserWindow, ipcMain } from 'electron'
import path from 'path'

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 960,
    minHeight: 640,
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#0d1117',
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

app.whenReady().then(createWindow)

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow()
})

ipcMain.on('set-content-protection', (event, enable: boolean) => {
  const win = BrowserWindow.fromWebContents(event.sender)
  if (win) {
    win.setContentProtection(enable)
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

