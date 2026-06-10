import { useState, useEffect, useRef } from 'react'
import { ArrowLeft, ArrowRight, RotateCw, Globe, Search } from 'lucide-react'
import styles from './BrowserPage.module.css'

const PRESETS = [
  { name: 'Google', url: 'https://www.google.com' },
  { name: 'LeetCode', url: 'https://leetcode.com' },
  { name: 'HackerRank', url: 'https://www.hackerrank.com' },
  { name: 'GitHub', url: 'https://github.com' },
  { name: 'StackOverflow', url: 'https://stackoverflow.com' },
]

export default function BrowserPage() {
  const [url, setUrl] = useState('https://www.google.com')
  const [inputVal, setInputVal] = useState('https://www.google.com')
  const webviewRef = useRef<any>(null)

  useEffect(() => {
    const webview = webviewRef.current
    if (!webview) return

    const handleNavigate = (e: any) => {
      setUrl(e.url)
      setInputVal(e.url)
    }

    // Add listeners to sync the address bar URL on navigation
    webview.addEventListener('did-navigate', handleNavigate)
    webview.addEventListener('did-navigate-in-page', handleNavigate)

    return () => {
      webview.removeEventListener('did-navigate', handleNavigate)
      webview.removeEventListener('did-navigate-in-page', handleNavigate)
    }
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    let targetUrl = inputVal.trim()
    if (!targetUrl.startsWith('http://') && !targetUrl.startsWith('https://')) {
      // If it looks like a domain, prepend https
      if (targetUrl.includes('.') && !targetUrl.includes(' ')) {
        targetUrl = 'https://' + targetUrl
      } else {
        // Otherwise search via Google
        targetUrl = 'https://www.google.com/search?q=' + encodeURIComponent(targetUrl)
      }
    }
    setUrl(targetUrl)
    setInputVal(targetUrl)
  }

  const handleBack = () => {
    if (webviewRef.current) {
      try {
        webviewRef.current.goBack()
      } catch (err) {
        console.error('Webview goBack failed', err)
      }
    }
  }

  const handleForward = () => {
    if (webviewRef.current) {
      try {
        webviewRef.current.goForward()
      } catch (err) {
        console.error('Webview goForward failed', err)
      }
    }
  }

  const handleReload = () => {
    if (webviewRef.current) {
      try {
        webviewRef.current.reload()
      } catch (err) {
        console.error('Webview reload failed', err)
      }
    }
  }

  const handlePreset = (presetUrl: string) => {
    setUrl(presetUrl)
    setInputVal(presetUrl)
  }

  const isElectron = window.electronAPI !== undefined

  return (
    <div className={styles.page}>
      {/* Control bar */}
      <div className={styles.controlBar}>
        <button
          className={styles.navButton}
          onClick={handleBack}
          title="Back"
        >
          <ArrowLeft size={16} />
        </button>
        <button
          className={styles.navButton}
          onClick={handleForward}
          title="Forward"
        >
          <ArrowRight size={16} />
        </button>
        <button
          className={styles.navButton}
          onClick={handleReload}
          title="Reload"
        >
          <RotateCw size={15} />
        </button>

        <form onSubmit={handleSubmit} className={styles.addressForm}>
          <input
            type="text"
            className={styles.addressInput}
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="Search Google or enter web address..."
            spellCheck={false}
          />
          <button type="submit" className="btn btn-secondary btn-sm" style={{ padding: '6px 12px' }}>
            <Search size={14} />
          </button>
        </form>
      </div>

      {/* Preset shortcuts bar */}
      <div className={styles.presets}>
        <span className={styles.presetTitle}>Presets:</span>
        {PRESETS.map((p) => (
          <button
            key={p.name}
            className={styles.presetBtn}
            onClick={() => handlePreset(p.url)}
          >
            {p.name}
          </button>
        ))}
      </div>

      {/* Embedded Web View */}
      <div className={styles.webviewContainer}>
        {isElectron ? (
          <webview
            ref={webviewRef}
            src={url}
            className={styles.webview}
            allowpopups="true"
          />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12, padding: 20, textAlign: 'center' }}>
            <Globe size={48} style={{ color: 'var(--accent)', opacity: 0.8 }} />
            <h3>Desktop App Wrapper Required</h3>
            <p style={{ maxWidth: 420, fontSize: '0.875rem' }}>
              Due to modern security constraints (CORS and X-Frame-Options headers), major web applications cannot be embedded in standard browser tabs. Please launch this project via the desktop application to access the workspace browser.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
