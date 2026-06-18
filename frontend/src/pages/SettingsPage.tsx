import { useState } from 'react'
import toast from 'react-hot-toast'
import styles from './SettingsPage.module.css'
import { useSettingsStore } from '@/store/settingsStore'

const MODELS = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro']
const WHISPER_SIZES = ['tiny', 'base', 'small', 'medium']

export default function SettingsPage() {
  const [apiKey,      setApiKey]      = useState(localStorage.getItem('gemini_api_key') || '')
  const [showKey,     setShowKey]     = useState(false)
  const [model,       setModel]       = useState(localStorage.getItem('gemini_model') || 'gemini-2.5-flash')
  const [whisperSize, setWhisperSize] = useState(localStorage.getItem('whisper_size') || 'base')
  const [saved,       setSaved]       = useState(false)

  const isElectron = window.electronAPI !== undefined
  const { 
    stealthActive, skipTaskbar, toggleStealth, toggleSkipTaskbar,
    theme, typography, setTheme, setTypography 
  } = useSettingsStore()

  const handleToggleScreenProtect = (checked: boolean) => {
    toggleStealth(checked)
    if (isElectron) {
      toast.success(checked ? 'Screen protection enabled!' : 'Screen protection disabled.')
    }
  }

  const handleToggleSkipTaskbar = (checked: boolean) => {
    toggleSkipTaskbar(checked)
    if (isElectron) {
      toast.success(checked ? 'Application icon hidden from taskbar.' : 'Application icon visible on taskbar.')
    }
  }

  const handleSave = () => {
    localStorage.setItem('gemini_api_key', apiKey)
    localStorage.setItem('gemini_model', model)
    localStorage.setItem('whisper_size', whisperSize)
    setSaved(true)
    toast.success('Settings saved')
    setTimeout(() => setSaved(false), 2500)
  }

  return (
    <div className={styles.page}>
      {/* Header */}
      <div className={styles.header}>
        <h1 className={styles.headerTitle}>Settings</h1>
        <p className={styles.headerDesc}>Manage your AI integrations and privacy preferences.</p>
      </div>

      <div className={styles.gridContainer}>
        {/* Gemini API Card */}
        <section className={styles.md3Card}>
          <div className={styles.cardHeader}>
            <span className={`material-symbols-outlined ${styles.cardHeaderIcon}`}>smart_toy</span>
            <h3 className={styles.cardHeaderTitle}>Gemini API</h3>
          </div>

          {/* M3 Filled Text Field: API Key */}
          <div className={styles.textField}>
            <input
              id="api-key"
              type={showKey ? 'text' : 'password'}
              className={styles.textFieldInput}
              placeholder=" "
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              spellCheck={false}
            />
            <label className={styles.textFieldLabel} htmlFor="api-key">API Key</label>
            <button
              type="button"
              className={styles.textFieldIconBtn}
              onClick={() => setShowKey(!showKey)}
            >
              <span className="material-symbols-outlined">
                {showKey ? 'visibility_off' : 'visibility'}
              </span>
            </button>
          </div>

          {/* M3 Filled Select: Model */}
          <div className={styles.textField}>
            <select
              id="model-select"
              className={styles.textFieldSelect}
              value={model}
              onChange={(e) => setModel(e.target.value)}
            >
              {MODELS.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
            <label className={styles.textFieldLabel} htmlFor="model-select">Model</label>
            <span className={`material-symbols-outlined ${styles.selectIcon}`}>arrow_drop_down</span>
          </div>
        </section>

        {/* Configuration Column */}
        <div className={styles.column}>
          {/* Speech Recognition Card */}
          <section className={styles.md3Card}>
            <div className={styles.cardHeader}>
              <span className={`material-symbols-outlined ${styles.cardHeaderIcon}`}>mic</span>
              <h3 className={styles.cardHeaderTitle}>Speech Recognition</h3>
            </div>

            <div className={styles.textField}>
              <select
                id="whisper-size"
                className={styles.textFieldSelect}
                value={whisperSize}
                onChange={(e) => setWhisperSize(e.target.value)}
              >
                {WHISPER_SIZES.map((s) => (
                  <option key={s} value={s}>
                    {s.charAt(0).toUpperCase() + s.slice(1)}
                    {s === 'tiny'  ? ' (Fastest, low accuracy)' : ''}
                    {s === 'base'  ? ' (Balanced)' : ''}
                    {s === 'small' ? ' (High accuracy, slower)' : ''}
                    {s === 'medium' ? ' (Best accuracy, slowest)' : ''}
                  </option>
                ))}
              </select>
              <label className={styles.textFieldLabel} htmlFor="whisper-size">Whisper Model Size</label>
              <span className={`material-symbols-outlined ${styles.selectIcon}`}>arrow_drop_down</span>
            </div>
          </section>

          {/* Appearance & Accessibility Card */}
          <section className={styles.md3Card} style={{ marginBottom: '24px' }}>
            <div className={styles.cardHeader}>
              <span className={`material-symbols-outlined ${styles.cardHeaderIcon}`}>palette</span>
              <h3 className={styles.cardHeaderTitle}>Appearance & Accessibility</h3>
            </div>

            {/* Toggle: Dark Mode */}
            <label className={styles.switchItem}>
              <div className={styles.switchText}>
                <span className={styles.switchTitle}>Dark Mode</span>
                <span className={styles.switchDesc}>Easier on the eyes in low light.</span>
              </div>
              <div className={styles.m3SwitchWrap}>
                <input
                  type="checkbox"
                  className={styles.m3SwitchInput}
                  checked={theme === 'dark'}
                  onChange={(e) => setTheme(e.target.checked ? 'dark' : 'light')}
                />
                <div className={styles.switchTrack}>
                  <div className={styles.switchThumb}></div>
                </div>
              </div>
            </label>

            {/* Toggle: Standard Typography */}
            <label className={styles.switchItem}>
              <div className={styles.switchText}>
                <span className={styles.switchTitle}>Standard Typography</span>
                <span className={styles.switchDesc}>Use standard fonts for better readability.</span>
              </div>
              <div className={styles.m3SwitchWrap}>
                <input
                  type="checkbox"
                  className={styles.m3SwitchInput}
                  checked={typography === 'standard'}
                  onChange={(e) => setTypography(e.target.checked ? 'standard' : 'handwritten')}
                />
                <div className={styles.switchTrack}>
                  <div className={styles.switchThumb}></div>
                </div>
              </div>
            </label>
          </section>

          {/* Privacy & Security Card */}
          <section className={styles.md3Card}>
            <div className={styles.cardHeader}>
              <span className={`material-symbols-outlined ${styles.cardHeaderIcon}`}>shield_lock</span>
              <h3 className={styles.cardHeaderTitle}>Privacy & Security</h3>
            </div>

            {/* Toggle 1: Screen Protect */}
            <label className={styles.switchItem}>
              <div className={styles.switchText}>
                <span className={styles.switchTitle}>
                  Anti-Screen Share
                </span>
                <span className={styles.switchDesc}>
                  {isElectron 
                    ? 'Obscures sensitive info during presentations.' 
                    : 'Requires running in the desktop app wrapper.'}
                </span>
              </div>
              <div className={styles.m3SwitchWrap}>
                <input
                  type="checkbox"
                  className={styles.m3SwitchInput}
                  checked={stealthActive}
                  disabled={!isElectron}
                  onChange={(e) => handleToggleScreenProtect(e.target.checked)}
                />
                <div className={styles.switchTrack}>
                  <div className={styles.switchThumb}></div>
                </div>
              </div>
            </label>

            {/* Toggle 2: Hide Taskbar */}
            <label className={styles.switchItem}>
              <div className={styles.switchText}>
                <span className={styles.switchTitle}>Hide from Taskbar</span>
                <span className={styles.switchDesc}>
                  {isElectron 
                    ? 'Run stealthily in the system tray.' 
                    : 'Requires running in the desktop app wrapper.'}
                </span>
              </div>
              <div className={styles.m3SwitchWrap}>
                <input
                  type="checkbox"
                  className={styles.m3SwitchInput}
                  checked={skipTaskbar}
                  disabled={!isElectron}
                  onChange={(e) => handleToggleSkipTaskbar(e.target.checked)}
                />
                <div className={styles.switchTrack}>
                  <div className={styles.switchThumb}></div>
                </div>
              </div>
            </label>

            {!isElectron && (
              <div className={styles.privacyAlert}>
                <span className={`material-symbols-outlined ${styles.alertIcon}`}>warning</span>
                <div>
                  <strong>Web Browser Sandbox Active:</strong> Web browsers cannot block system-level screen capture or customize taskbar items. 
                  <div style={{ marginTop: 4 }}>
                    To hide the app during an interview:
                    <ul style={{ paddingLeft: 14, marginTop: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
                      <li>Launch via the desktop app (Electron).</li>
                      <li>Or share only your specific window rather than your Entire Screen.</li>
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>

      {/* Floating Action Button (FAB) for Save */}
      <div className={styles.fabContainer}>
        <button
          className={styles.fab}
          onClick={handleSave}
          disabled={saved}
        >
          <span className="material-symbols-outlined">
            {saved ? 'check_circle' : 'save'}
          </span>
          {saved ? 'Saved' : 'Save Settings'}
        </button>
      </div>
    </div>
  )
}
