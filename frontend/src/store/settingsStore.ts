import { create } from 'zustand'

interface SettingsState {
  stealthActive: boolean
  skipTaskbar: boolean
  theme: 'light' | 'dark'
  typography: 'handwritten' | 'standard'
  toggleStealth: (active: boolean) => void
  toggleSkipTaskbar: (skip: boolean) => void
  setTheme: (theme: 'light' | 'dark') => void
  setTypography: (typography: 'handwritten' | 'standard') => void
}

const isElectron = window.electronAPI !== undefined

export const useSettingsStore = create<SettingsState>((set) => ({
  stealthActive: localStorage.getItem('screen_protection') === 'true',
  skipTaskbar: localStorage.getItem('skip_taskbar') === 'true',
  theme: (localStorage.getItem('theme') as 'light' | 'dark') || 'light',
  typography: (localStorage.getItem('typography') as 'handwritten' | 'standard') || 'handwritten',

  toggleStealth: (active) => {
    localStorage.setItem('screen_protection', active ? 'true' : 'false')
    if (isElectron && window.electronAPI) {
      window.electronAPI?.setContentProtection(active)
    }
    set({ stealthActive: active })
  },

  toggleSkipTaskbar: (skip) => {
    localStorage.setItem('skip_taskbar', skip ? 'true' : 'false')
    if (isElectron && window.electronAPI) {
      window.electronAPI?.setSkipTaskbar(skip)
    }
    set({ skipTaskbar: skip })
  },

  setTheme: (theme) => {
    localStorage.setItem('theme', theme)
    document.documentElement.dataset.theme = theme
    set({ theme })
  },

  setTypography: (typography) => {
    localStorage.setItem('typography', typography)
    document.documentElement.dataset.typography = typography
    set({ typography })
  }
}))
