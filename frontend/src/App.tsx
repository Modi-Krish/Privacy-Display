import { useEffect } from 'react'
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import ProfilePage from '@/pages/ProfilePage'
import InterviewPage from '@/pages/InterviewPage'
import SettingsPage from '@/pages/SettingsPage'
import BrowserPage  from '@/pages/BrowserPage'
import AppShell    from '@/components/AppShell'
import CustomCursor from '@/components/CustomCursor'
import TitleBar from '@/components/TitleBar'

import AuthPage from '@/pages/AuthPage'
import OverlayPage from '@/pages/OverlayPage'
import ProtectedRoute from '@/components/ProtectedRoute'

export default function App() {
  useEffect(() => {
    // Apply screen protection and taskbar settings on startup if in Electron
    const isElectron = window.electronAPI !== undefined
    if (isElectron && window.electronAPI) {
      const screenProtect = localStorage.getItem('screen_protection') === 'true'
      if (screenProtect) {
        window.electronAPI?.setContentProtection(true)
      }
      const skipTaskbar = localStorage.getItem('skip_taskbar') === 'true'
      if (skipTaskbar) {
        window.electronAPI?.setSkipTaskbar(true)
      }
    }
    // Update dynamic privacy settings listeners
    window.dispatchEvent(new Event('screen-protection-changed'))
  }, [])

  const isElectron = window.electronAPI !== undefined

  // Detect if we're in the overlay window (loaded with #/overlay hash)
  const isOverlay = window.location.hash.startsWith('#/overlay')

  useEffect(() => {
    if (isOverlay) {
      document.body.classList.add('is-overlay')
    } else {
      document.body.classList.remove('is-overlay')
    }
  }, [isOverlay])

  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#fff',
            color: '#2d2d2d',
            border: '2px solid #2d2d2d',
            fontFamily: "'Patrick Hand', cursive",
            fontSize: '0.95rem',
            boxShadow: '4px 4px 0px 0px #2d2d2d',
            borderRadius: '8px 24px 10px 20px / 20px 10px 24px 8px',
          },
        }}
      />
      {!isOverlay && <CustomCursor />}
      {isElectron && !isOverlay && <TitleBar />}
      <HashRouter>
        <Routes>
          {/* Overlay route — no AppShell wrapper */}
          <Route path="/overlay" element={<OverlayPage />} />

          {/* Main app routes */}
          <Route path="/auth" element={<AuthPage />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<AppShell />}>
              <Route index element={<Navigate to="/interview" replace />} />
              <Route path="/interview" element={<InterviewPage />} />
              <Route path="/profile"   element={<ProfilePage />} />
              <Route path="/browser"   element={<></>} />
              <Route path="/settings"  element={<SettingsPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </HashRouter>
    </>
  )
}
