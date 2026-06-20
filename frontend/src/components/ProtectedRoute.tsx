import { useEffect, useState } from 'react'
import { Navigate, Outlet } from 'react-router-dom'

export default function ProtectedRoute() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)

  useEffect(() => {
    const checkAuth = async () => {
      if (window.electronAPI?.auth) {
        const tokens = await window.electronAPI.auth.getTokens()
        if (tokens?.access_token) {
          setIsAuthenticated(true)
        } else {
          setIsAuthenticated(false)
        }
      } else {
        // If not running in Electron, we might not have a way to check securely here,
        // but since the app relies on Electron for auth, we will default to false.
        setIsAuthenticated(false)
      }
    }
    checkAuth()
  }, [])

  if (isAuthenticated === null) {
    return (
      <div style={{ display: 'flex', height: '100vh', justifyContent: 'center', alignItems: 'center', backgroundColor: '#fdfbf7', color: '#2d2d2d', fontFamily: "'Patrick Hand', cursive" }}>
        Checking connection...
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />
  }

  return <Outlet />
}
