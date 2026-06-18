import { useState, useEffect } from 'react'
import OverlayAnswerCard from '@/components/OverlayAnswerCard'
import styles from './OverlayPage.module.css'

export default function OverlayPage() {
  const [isClickThrough, setIsClickThrough] = useState(false)

  useEffect(() => {
    // Listen for click-through mode changes from the Electron main process
    if (window.electronAPI?.onOverlayModeChanged) {
      window.electronAPI?.onOverlayModeChanged((clickThrough: boolean) => {
        setIsClickThrough(clickThrough)
      })
    }
  }, [])

  useEffect(() => {
    document.body.classList.add('is-overlay')
    return () => document.body.classList.remove('is-overlay')
  }, [])

  return (
    <div className={styles.page}>
      {/* Drag handle for repositioning */}
      <div className={styles.dragHandle}>
        <div className={styles.dragPill} />
      </div>

      {/* Main card */}
      <div className={styles.cardContainer}>
        <OverlayAnswerCard isClickThrough={isClickThrough} />
      </div>

      {/* Hotkey hint */}
      <div className={styles.hotkeyHint}>
        <span className={styles.hotkeyText}>
          <span className={styles.kbd}>Ctrl+Space</span> toggle
        </span>
        <span className={styles.hotkeyText}>
          <span className={styles.kbd}>Ctrl+Shift+Space</span> click-through
        </span>
      </div>
    </div>
  )
}
