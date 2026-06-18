import styles from './TitleBar.module.css'

export default function TitleBar() {
  const api = window.electronAPI

  return (
    <div className={styles.titleBar}>
      {/* Draggable region fills the whole bar */}
      <div className={styles.dragRegion} />

      {/* App name — left side */}
      <div className={styles.appName}>
        Real-Time AI Privacy Display
      </div>

      {/* Window controls — right side */}
      <div className={styles.controls}>
        <button
          className={`${styles.btn} ${styles.minimize}`}
          onClick={() => api?.minimizeWindow()}
          title="Minimize"
          aria-label="Minimize"
        >
          <span className={styles.line} />
        </button>

        <button
          className={`${styles.btn} ${styles.maximize}`}
          onClick={() => api?.maximizeWindow()}
          title="Maximize / Restore"
          aria-label="Maximize"
        >
          <span className={styles.square} />
        </button>

        <button
          className={`${styles.btn} ${styles.close}`}
          onClick={() => api?.closeWindow()}
          title="Close"
          aria-label="Close"
        >
          <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
            <line x1="1" y1="1" x2="9" y2="9" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
            <line x1="9" y1="1" x2="1" y2="9" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"/>
          </svg>
        </button>
      </div>
    </div>
  )
}
