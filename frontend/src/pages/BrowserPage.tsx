import { useState, useEffect, useRef } from 'react'
import { NavLink } from 'react-router-dom'
import { Mic2, User, Settings, Globe, Shield, ShieldOff } from 'lucide-react'
import toast from 'react-hot-toast'
import styles from './BrowserPage.module.css'
import { useSettingsStore } from '@/store/settingsStore'

const NAV = [
  { to: '/interview', icon: Mic2,    label: 'Interview' },
  { to: '/profile',   icon: User,    label: 'Profile'   },
  { to: '/browser',   icon: Globe,   label: 'Browser'   },
  { to: '/settings',  icon: Settings, label: 'Settings' },
]

type TabInfo = {
  id: string;
  title: string;
  url: string;
}

export default function BrowserPage({ isOverlay = false }: { isOverlay?: boolean }) {
  const generateId = () => Math.random().toString(36).substr(2, 9)

  const [tabs, setTabs] = useState<TabInfo[]>([
    { id: '1', title: 'New Tab', url: 'https://www.google.com' }
  ])
  const [activeTabId, setActiveTabId] = useState('1')
  const [inputVal, setInputVal] = useState('https://www.google.com')
  const containerRef = useRef<HTMLDivElement>(null)

  const isElectron = window.electronAPI !== undefined

  const { stealthActive, toggleStealth } = useSettingsStore()

  useEffect(() => {
    if (!isElectron) return

    // Initialize the first tab in the main process
    window.electronAPI?.createTab(tabs[0].id, tabs[0].url)
    window.electronAPI?.switchTab(tabs[0].id)

    // Setup IPC listeners for native navigation events
    window.electronAPI?.onBrowserNavigate((id: string, url: string) => {
      setTabs(prev => prev.map(t => t.id === id ? { ...t, url } : t))
      setActiveTabId(curr => {
        if (curr === id) setInputVal(url)
        return curr
      })
    })

    window.electronAPI?.onBrowserTitleUpdated((id: string, title: string) => {
      setTabs(prev => prev.map(t => t.id === id ? { ...t, title } : t))
    })

    // Setup ResizeObserver to sync native BrowserView bounds with our React layout
    if (containerRef.current) {
      const ro = new ResizeObserver((entries) => {
        for (let entry of entries) {
          const rect = entry.target.getBoundingClientRect()
          window.electronAPI?.resizeBrowser({
            x: Math.round(rect.left),
            y: Math.round(rect.top),
            width: Math.round(rect.width),
            height: Math.round(rect.height)
          })
        }
      })
      ro.observe(containerRef.current)
      return () => ro.disconnect()
    }
  }, []) // Empty dependency array means this runs once on mount

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    let targetUrl = inputVal.trim()
    if (!targetUrl.startsWith('http://') && !targetUrl.startsWith('https://')) {
      if (targetUrl.includes('.') && !targetUrl.includes(' ')) {
        targetUrl = 'https://' + targetUrl
      } else {
        targetUrl = 'https://www.google.com/search?q=' + encodeURIComponent(targetUrl)
      }
    }
    setTabs(prev => prev.map(t => t.id === activeTabId ? { ...t, url: targetUrl } : t))
    setInputVal(targetUrl)
    if (isElectron) window.electronAPI?.navigate(activeTabId, targetUrl)
  }

  const handleAddTab = () => {
    const newTab = { id: generateId(), title: 'New Tab', url: 'https://www.google.com' }
    setTabs([...tabs, newTab])
    setActiveTabId(newTab.id)
    setInputVal(newTab.url)
    if (isElectron) {
      window.electronAPI?.createTab(newTab.id, newTab.url)
      window.electronAPI?.switchTab(newTab.id)
    }
  }

  const handleCloseTab = (e: React.MouseEvent, tabId: string) => {
    e.stopPropagation()
    if (isElectron) window.electronAPI?.closeTab(tabId)

    if (tabs.length === 1) {
      const newTab = { id: generateId(), title: 'New Tab', url: 'https://www.google.com' }
      setTabs([newTab])
      setActiveTabId(newTab.id)
      setInputVal(newTab.url)
      if (isElectron) {
        window.electronAPI?.createTab(newTab.id, newTab.url)
        window.electronAPI?.switchTab(newTab.id)
      }
      return
    }

    const index = tabs.findIndex(t => t.id === tabId)
    const newTabs = tabs.filter(t => t.id !== tabId)
    setTabs(newTabs)

    if (activeTabId === tabId) {
      const nextTab = newTabs[Math.max(0, index - 1)]
      setActiveTabId(nextTab.id)
      setInputVal(nextTab.url)
      if (isElectron) window.electronAPI?.switchTab(nextTab.id)
    }
  }

  const handleSwitchTab = (tabId: string) => {
    const tab = tabs.find(t => t.id === tabId)
    if (tab) {
      setActiveTabId(tab.id)
      setInputVal(tab.url)
      if (isElectron) window.electronAPI?.switchTab(tab.id)
    }
  }

  const handleBack = () => {
    if (isElectron) window.electronAPI?.goBack(activeTabId)
  }

  const handleForward = () => {
    if (isElectron) window.electronAPI?.goForward(activeTabId)
  }

  const handleReload = () => {
    if (isElectron) window.electronAPI?.reload(activeTabId)
  }

  const handleToggleStealth = () => {
    const nextState = !stealthActive
    toggleStealth(nextState)
    toast.success(nextState ? 'Stealth Mouse Enabled!' : 'Normal Mouse Enabled!')
  }

  return (
    <div className={styles.page}>
      {/* Atmospheric Glow Effect */}
      <div className={styles.blurOrb1}></div>
      <div className={styles.blurOrb2}></div>

      {/* Custom Browser Interface Frame */}
      <div className={styles.browserFrame}>
        
        {/* Browser Header */}
        <div className={styles.browserHeader}>
          
          {/* Top Row: Navigation and Address Bar */}
          <div className={styles.topRow}>
            {/* Left: App Name & Navigation Controls */}
            <div className={styles.leftSection}>
              {!isOverlay && <h2 className={styles.appName}>ReAI Browser</h2>}
              <div className={styles.navControls}>
                <button className={styles.navButton} onClick={handleBack} title="Back">
                  <span className="material-symbols-outlined">arrow_back</span>
                </button>
                <button className={styles.navButton} onClick={handleForward} title="Forward">
                  <span className="material-symbols-outlined">arrow_forward</span>
                </button>
                <button className={styles.navButton} onClick={handleReload} title="Reload">
                  <span className="material-symbols-outlined">refresh</span>
                </button>
              </div>
            </div>

            {/* Center: Omnibox / Search Bar */}
            <div className={styles.centerSection}>
              <form onSubmit={handleSubmit} className={styles.addressForm}>
                <div className={styles.omnibox}>
                  <span className={`material-symbols-outlined ${styles.omniboxIcon}`}>security</span>
                  <input
                    type="text"
                    className={styles.addressInput}
                    value={inputVal}
                    onChange={(e) => setInputVal(e.target.value)}
                    placeholder="Search or type URL"
                    spellCheck={false}
                  />
                  <span className={`material-symbols-outlined ${styles.starIcon}`}>star_border</span>
                </div>
              </form>
            </div>

            {/* Right: Navigation / Menu */}
            {!isOverlay && (
              <div className={styles.rightSection}>
                <nav className={styles.topNav}>
                  {NAV.map(({ to, icon: Icon, label }) => (
                    <NavLink
                      key={to}
                      to={to}
                      role="tab"
                      aria-label={`Navigate to ${label}`}
                      className={({ isActive }) =>
                        `${styles.topNavItem} ${isActive ? styles.topNavActive : ''}`
                      }
                    >
                      <Icon size={16} strokeWidth={2.5} />
                      <span>{label}</span>
                    </NavLink>
                  ))}
                  
                  {isElectron && (
                    <button
                      className={`${styles.topNavItem} ${styles.stealthBtn} ${stealthActive ? styles.stealthActive : ''}`}
                      onClick={handleToggleStealth}
                      title="Toggle Stealth Mode (Ctrl+Shift+A+S)"
                    >
                      {stealthActive ? (
                        <Shield size={16} strokeWidth={2.5} />
                      ) : (
                        <ShieldOff size={16} strokeWidth={2.5} />
                      )}
                      <span>{stealthActive ? 'Stealth Active' : 'Stealth Off'}</span>
                    </button>
                  )}
                  
                  <button className={`${styles.navButton} ${styles.moreBtn}`}>
                    <span className="material-symbols-outlined">more_vert</span>
                  </button>
                </nav>
              </div>
            )}
          </div>

          {/* Tab Row */}
          <div className={styles.tabRow}>
            {tabs.map((tab) => {
              const isActive = activeTabId === tab.id
              return (
                <div
                  key={tab.id}
                  className={`${styles.tab} ${isActive ? styles.activeTab : ''}`}
                  onClick={() => handleSwitchTab(tab.id)}
                >
                  <span className={`material-symbols-outlined ${styles.tabIcon}`}>public</span>
                  <span className={styles.tabTitle}>{tab.title}</span>
                  <button 
                    className={styles.closeTabBtn} 
                    onClick={(e) => handleCloseTab(e, tab.id)}
                    title="Close Tab"
                  >
                    <span className="material-symbols-outlined">close</span>
                  </button>
                </div>
              )
            })}
            <button className={styles.addTabBtn} onClick={handleAddTab} title="New Tab">
              <span className="material-symbols-outlined">add</span>
            </button>
          </div>
        </div>

        {/* Browser Viewport Placeholder */}
        <div className={styles.webviewWrapper} ref={containerRef}>
          {!isElectron && (
            <div className={styles.sandboxWarning}>
              <span className={`material-symbols-outlined ${styles.sandboxWarningIcon}`}>language</span>
              <h3 className={styles.sandboxWarningTitle}>Desktop App Wrapper Required</h3>
              <p className={styles.sandboxWarningDesc}>
                Due to modern security constraints (CORS and X-Frame-Options headers), major web applications cannot be embedded in standard browser tabs. Please launch this project via the desktop application to access the workspace browser.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
