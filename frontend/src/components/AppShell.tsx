import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { Mic2, User, Settings, Globe, Shield, ShieldOff } from 'lucide-react'
import toast from 'react-hot-toast'
import BrowserPage from '@/pages/BrowserPage'
import styles from './AppShell.module.css'
import { useSettingsStore } from '@/store/settingsStore'

const NAV = [
  { to: '/interview', icon: Mic2,    label: 'Interview' },
  { to: '/profile',   icon: User,    label: 'Profile'   },
  { to: '/browser',   icon: Globe,   label: 'Browser'   },
  { to: '/settings',  icon: Settings, label: 'Settings' },
]

export default function AppShell() {
  const navigate = useNavigate()
  const location = useLocation()
  const isBrowserTab = location.pathname === '/browser'
  const isElectron = window.electronAPI !== undefined

  const { stealthActive, toggleStealth } = useSettingsStore()

  const handleToggleStealth = () => {
    const nextState = !stealthActive
    toggleStealth(nextState)
    toast.success(nextState ? 'Stealth Mouse Enabled!' : 'Normal Mouse Enabled!')
  }

  return (
    <div className={styles.shell}>
      {/* Dock Navigation */}
      {!isBrowserTab && (
        <div className={styles.dock}>
        <nav className={styles.nav}>
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              id={`nav-${label.toLowerCase()}`}
              role="tab"
              aria-label={`Navigate to ${label}`}
              className={({ isActive }) =>
                `${styles.navItem} ${isActive ? styles.navActive : ''}`
              }
            >
              <Icon size={18} strokeWidth={2.5} />
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
              <Shield size={18} strokeWidth={2.5} />
            ) : (
              <ShieldOff size={18} strokeWidth={2.5} />
            )}
            <span>{stealthActive ? 'Stealth Active' : 'Stealth Off'}</span>
          </button>
        )}
      </div>
      )}

      {/* Main content */}
      <main className={styles.main}>
        <div style={{ display: isBrowserTab ? 'block' : 'none', height: '100%', width: '100%' }}>
          <BrowserPage />
        </div>
        {!isBrowserTab && <Outlet />}
      </main>
    </div>
  )
}
