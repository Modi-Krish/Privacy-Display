import { useState, useEffect } from 'react'
import { Key, Cpu, Mic2, Save, Eye, EyeOff, CheckCircle, Shield, AlertTriangle } from 'lucide-react'
import toast from 'react-hot-toast'
import styles from './SettingsPage.module.css'

const MODELS = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-1.5-pro']
const WHISPER_SIZES = ['tiny', 'base', 'small', 'medium']

export default function SettingsPage() {
  const [apiKey,      setApiKey]      = useState(localStorage.getItem('gemini_api_key') || '')
  const [showKey,     setShowKey]     = useState(false)
  const [model,       setModel]       = useState(localStorage.getItem('gemini_model') || 'gemini-2.5-flash')
  const [whisperSize, setWhisperSize] = useState(localStorage.getItem('whisper_size') || 'base')
  const [saved,       setSaved]       = useState(false)

  const isElectron = window.electronAPI !== undefined
  const [screenProtect, setScreenProtect] = useState(() => {
    return localStorage.getItem('screen_protection') === 'true'
  })
  const [skipTaskbar, setSkipTaskbar] = useState(() => {
    return localStorage.getItem('skip_taskbar') === 'true'
  })

  // Sync state if changed via F9 global hotkey
  useEffect(() => {
    const handleSync = () => {
      setScreenProtect(localStorage.getItem('screen_protection') === 'true')
    }
    window.addEventListener('screen-protection-changed', handleSync)
    return () => {
      window.removeEventListener('screen-protection-changed', handleSync)
    }
  }, [])

  const handleToggleScreenProtect = (checked: boolean) => {
    setScreenProtect(checked)
    localStorage.setItem('screen_protection', checked ? 'true' : 'false')
    if (isElectron && window.electronAPI) {
      window.electronAPI.setContentProtection(checked)
      toast.success(checked ? 'Screen protection enabled!' : 'Screen protection disabled.')
    }
    // Dispatch a custom event to update other components dynamically
    window.dispatchEvent(new Event('screen-protection-changed'))
  }

  const handleToggleSkipTaskbar = (checked: boolean) => {
    setSkipTaskbar(checked)
    localStorage.setItem('skip_taskbar', checked ? 'true' : 'false')
    if (isElectron && window.electronAPI) {
      window.electronAPI.setSkipTaskbar(checked)
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
      <div className={styles.header}>
        <h1>Settings</h1>
        <p>Configure your API key, model selection, and audio preferences.</p>
      </div>

      <div className={styles.sections}>
        {/* Gemini API */}
        <section className={`card ${styles.section}`}>
          <div className={styles.sectionHead}>
            <Key size={16} style={{ color: 'var(--accent)' }} />
            <h2>Gemini API</h2>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="input-api-key">API Key</label>
            <div className={styles.inputWrap}>
              <input
                id="input-api-key"
                type={showKey ? 'text' : 'password'}
                className={`input ${styles.inputPadded}`}
                placeholder="AIza…"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                spellCheck={false}
              />
              <button
                id="btn-toggle-key"
                type="button"
                className={styles.eyeBtn}
                onClick={() => setShowKey(!showKey)}
              >
                {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
            <p className="form-error" style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginTop: 4 }}>
              Stored locally only. Get yours at{' '}
              <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer"
                style={{ color: 'var(--accent)' }}>
                aistudio.google.com
              </a>
            </p>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="select-model">Model</label>
            <select
              id="select-model"
              className="input"
              value={model}
              onChange={(e) => setModel(e.target.value)}
              style={{ cursor: 'pointer' }}
            >
              {MODELS.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
        </section>

        {/* Audio */}
        <section className={`card ${styles.section}`}>
          <div className={styles.sectionHead}>
            <Mic2 size={16} style={{ color: 'var(--accent)' }} />
            <h2>Speech Recognition</h2>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="select-whisper">Whisper Model Size</label>
            <select
              id="select-whisper"
              className="input"
              value={whisperSize}
              onChange={(e) => setWhisperSize(e.target.value)}
              style={{ cursor: 'pointer' }}
            >
              {WHISPER_SIZES.map((s) => (
                <option key={s} value={s}>
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                  {s === 'tiny'  ? ' — fastest, lower accuracy' : ''}
                  {s === 'base'  ? ' — recommended (default)' : ''}
                  {s === 'small' ? ' — better accuracy' : ''}
                  {s === 'medium' ? ' — best accuracy, slower' : ''}
                </option>
              ))}
            </select>
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 4 }}>
              Larger models are more accurate but slower. Requires backend restart to apply.
            </p>
          </div>

          <div className={styles.modelInfo}>
            <Cpu size={14} />
            <span>Processing device: CPU (configure GPU via backend <code>.env</code>)</span>
          </div>
        </section>

        {/* Privacy & Screen Protection */}
        <section className={`card ${styles.section}`}>
          <div className={styles.sectionHead}>
            <Shield size={16} style={{ color: 'var(--accent)' }} />
            <h2>Privacy & Security</h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div className={styles.toggleGroup}>
              <div className={styles.toggleLabel}>
                <span className={styles.toggleTitle}>
                  Anti-Screen Share
                  <kbd style={{
                    background: 'var(--bg-base)',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontSize: '0.75rem',
                    marginLeft: '8px',
                    border: '1px solid var(--border)',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--accent)'
                  }}>Ctrl + Shift + A + S</kbd>
                </span>
                <span className={styles.toggleDesc}>
                  {isElectron 
                    ? 'Hide this application and mouse cursor from screen sharing and recordings.' 
                    : 'Requires running in the desktop app wrapper.'}
                </span>
              </div>
              <label className={styles.switch}>
                <input
                  type="checkbox"
                  checked={screenProtect}
                  disabled={!isElectron}
                  onChange={(e) => handleToggleScreenProtect(e.target.checked)}
                />
                <span className={styles.slider}></span>
              </label>
            </div>

            <div className={styles.toggleGroup}>
              <div className={styles.toggleLabel}>
                <span className={styles.toggleTitle}>Hide from Taskbar</span>
                <span className={styles.toggleDesc}>
                  {isElectron 
                    ? 'Remove the application icon from your OS taskbar (use Alt+Tab to switch back).' 
                    : 'Requires running in the desktop app wrapper.'}
                </span>
              </div>
              <label className={styles.switch}>
                <input
                  type="checkbox"
                  checked={skipTaskbar}
                  disabled={!isElectron}
                  onChange={(e) => handleToggleSkipTaskbar(e.target.checked)}
                />
                <span className={styles.slider}></span>
              </label>
            </div>
          </div>

          {!isElectron ? (
            <div className={styles.privacyAlert}>
              <AlertTriangle size={16} style={{ color: 'var(--warning)', flexShrink: 0, marginTop: 2 }} />
              <div>
                <strong>Web Browser Sandbox Active:</strong> Web browsers cannot block system-level screen capture or customize taskbar items. 
                <div style={{ marginTop: 4 }}>
                  To hide the app during an interview:
                  <ul style={{ paddingLeft: 14, marginTop: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <li>Launch via the desktop app (Electron).</li>
                    <li>Or, when sharing your screen, select <strong>only your specific window</strong> (e.g. VS Code or browser tab under test) rather than sharing your <strong>Entire Screen</strong>.</li>
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              Status: {screenProtect ? '🛡️ Screen Protected' : '👁️ Visible'} | {skipTaskbar ? '🙈 Hidden from taskbar' : '🐵 Visible on taskbar'}
            </p>
          )}
        </section>
      </div>

      <div className={styles.footer}>
        <button
          id="btn-save-settings"
          className="btn btn-primary"
          onClick={handleSave}
          disabled={saved}
        >
          {saved ? <><CheckCircle size={16} /> Saved</> : <><Save size={16} /> Save Settings</>}
        </button>
      </div>
    </div>
  )
}
