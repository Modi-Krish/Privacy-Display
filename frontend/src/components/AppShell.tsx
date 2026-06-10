import { useState, useEffect } from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { Mic2, User, Settings, LogOut, Brain, Globe, Shield, ShieldOff } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import toast from 'react-hot-toast'
import styles from './AppShell.module.css'

const NAV = [
  { to: '/interview', icon: Mic2,    label: 'Interview' },
  { to: '/profile',   icon: User,    label: 'Profile'   },
  { to: '/browser',   icon: Globe,   label: 'Browser'   },
  { to: '/settings',  icon: Settings, label: 'Settings' },
]

export default function AppShell() {
  const logout   = useAuthStore((s) => s.logout)
  const navigate = useNavigate()
  const isElectron = window.electronAPI !== undefined

  const [stealthActive, setStealthActive] = useState(() => {
    return localStorage.getItem('screen_protection') === 'true'
  })

  // Sync state if changed via Ctrl+Shift+A+S hotkey or SettingsPage
  useEffect(() => {
    const handleSync = () => {
      setStealthActive(localStorage.getItem('screen_protection') === 'true')
    }
    window.addEventListener('screen-protection-changed', handleSync)
    return () => {
      window.removeEventListener('screen-protection-changed', handleSync)
    }
  }, [])

  const handleToggleStealth = () => {
    const nextState = !stealthActive
    setStealthActive(nextState)
    localStorage.setItem('screen_protection', nextState ? 'true' : 'false')

    if (isElectron && window.electronAPI) {
      window.electronAPI.setContentProtection(nextState)
    }

    // Sync settings page and custom cursor
    window.dispatchEvent(new Event('screen-protection-changed'))

    toast.success(nextState ? 'Stealth Mouse Enabled!' : 'Normal Mouse Enabled!')
  }

  const handleLogout = async () => {
    await logout()
    toast.success('Logged out')
    navigate('/login')
  }

  return (
    <div className={styles.shell}>
      {/* Sidebar */}
      <aside className={styles.sidebar}>
        <div className={styles.logo}>
          <Brain size={22} strokeWidth={1.5} style={{ color: 'var(--accent)' }} />
          <span>Copilot</span>
        </div>

        <nav className={styles.nav}>
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              id={`nav-${label.toLowerCase()}`}
              className={({ isActive }) =>
                `${styles.navItem} ${isActive ? styles.navActive : ''}`
              }
            >
              <Icon size={18} strokeWidth={1.5} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        {isElectron && (
          <button
            id="btn-toggle-stealth"
            className={`${styles.navItem} ${styles.stealthBtn} ${stealthActive ? styles.stealthActive : ''}`}
            onClick={handleToggleStealth}
            title="Toggle Stealth Mode (Ctrl+Shift+A+S)"
          >
            {stealthActive ? (
              <Shield size={18} strokeWidth={1.5} />
            ) : (
              <ShieldOff size={18} strokeWidth={1.5} />
            )}
            <span>{stealthActive ? 'Stealth Active' : 'Stealth Off'}</span>
          </button>
        )}

        <button
          id="btn-logout"
          className={`${styles.navItem} ${styles.logoutBtn}`}
          onClick={handleLogout}
        >
          <LogOut size={18} strokeWidth={1.5} />
          <span>Logout</span>
        </button>
      </aside>

      {/* Main content */}
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  )
}
