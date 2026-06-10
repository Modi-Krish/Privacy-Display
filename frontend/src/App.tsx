import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import AuthPage    from '@/pages/AuthPage'
import ProfilePage from '@/pages/ProfilePage'
import InterviewPage from '@/pages/InterviewPage'
import SettingsPage from '@/pages/SettingsPage'
import BrowserPage  from '@/pages/BrowserPage'
import AppShell    from '@/components/AppShell'
import CustomCursor from '@/components/CustomCursor'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user)
  const isInitialized = useAuthStore((s) => s.isInitialized)

  // Don't redirect until we've checked the session
  if (!isInitialized) return null

  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  const fetchMe = useAuthStore((s) => s.fetchMe)

  useEffect(() => {
    fetchMe()
    
    // Apply screen protection and taskbar settings on startup if in Electron
    const isElectron = window.electronAPI !== undefined
    if (isElectron && window.electronAPI) {
      const screenProtect = localStorage.getItem('screen_protection') === 'true'
      if (screenProtect) {
        window.electronAPI.setContentProtection(true)
      }
      const skipTaskbar = localStorage.getItem('skip_taskbar') === 'true'
      if (skipTaskbar) {
        window.electronAPI.setSkipTaskbar(true)
      }
    }
    // Update dynamic privacy settings listeners
    window.dispatchEvent(new Event('screen-protection-changed'))
  }, [])

  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--bg-elevated)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
            fontFamily: 'var(--font-sans)',
            fontSize: '0.875rem',
          },
        }}
      />
      <CustomCursor />
      <BrowserRouter>
        <Routes>
          <Route path="/login"    element={<AuthPage />} />
          <Route path="/register" element={<AuthPage mode="register" />} />
          <Route element={<RequireAuth><AppShell /></RequireAuth>}>
            <Route index element={<Navigate to="/interview" replace />} />
            <Route path="/interview" element={<InterviewPage />} />
            <Route path="/profile"   element={<ProfilePage />} />
            <Route path="/browser"   element={<BrowserPage />} />
            <Route path="/settings"  element={<SettingsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </>
  )
}
