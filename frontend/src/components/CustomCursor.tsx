import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'

export default function CustomCursor() {
  const isElectron = window.electronAPI !== undefined
  const [active, setActive] = useState(() => {
    return isElectron && localStorage.getItem('screen_protection') === 'true'
  })
  const [position, setPosition] = useState({ x: -100, y: -100 })
  const [visible, setVisible] = useState(false)

  // Sync settings when modified from outside (e.g. SettingsPage or AppShell)
  useEffect(() => {
    const checkActive = () => {
      const isProtected = localStorage.getItem('screen_protection') === 'true'
      setActive(isElectron && isProtected)
    }

    window.addEventListener('screen-protection-changed', checkActive)
    return () => {
      window.removeEventListener('screen-protection-changed', checkActive)
    }
  }, [isElectron])

  // Key listener for Ctrl + Shift + A + S combo
  useEffect(() => {
    const pressedKeys = new Set<string>()

    const handleKeyDown = (e: KeyboardEvent) => {
      pressedKeys.add(e.key.toLowerCase())

      const hasCtrl = e.ctrlKey || pressedKeys.has('control')
      const hasShift = e.shiftKey || pressedKeys.has('shift')
      const hasA = pressedKeys.has('a')
      const hasS = pressedKeys.has('s')

      if (hasCtrl && hasShift && hasA && hasS) {
        // Clear set to prevent immediate repeated triggers
        pressedKeys.clear()

        const currentProtect = localStorage.getItem('screen_protection') === 'true'
        const nextProtect = !currentProtect

        localStorage.setItem('screen_protection', nextProtect ? 'true' : 'false')
        setActive(isElectron && nextProtect)

        if (isElectron && window.electronAPI) {
          window.electronAPI?.setContentProtection(nextProtect)
        }

        // Notify other components and sync settings UI
        window.dispatchEvent(new Event('screen-protection-changed'))

        // User feedback toast
        if (nextProtect) {
          toast.success('Privacy mode active (Ctrl+Shift+A+S)', { id: 'privacy-toast' })
        } else {
          toast.success('Privacy mode disabled (Ctrl+Shift+A+S)', { id: 'privacy-toast' })
        }
      }
    }

    const handleKeyUp = (e: KeyboardEvent) => {
      pressedKeys.delete(e.key.toLowerCase())
    }

    // Clear set if the window loses focus to avoid stuck key states
    const handleBlur = () => {
      pressedKeys.clear()
    }

    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    window.addEventListener('blur', handleBlur)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
      window.removeEventListener('blur', handleBlur)
    }
  }, [isElectron])

  useEffect(() => {
    if (!active) {
      document.body.classList.remove('hide-system-cursor')
      return
    }

    const handleMouseMove = (e: MouseEvent) => {
      setPosition({ x: e.clientX, y: e.clientY })
      setVisible(true)
    }

    const handleMouseLeave = () => {
      setVisible(false)
    }

    const handleMouseEnter = () => {
      setVisible(true)
    }

    window.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseleave', handleMouseLeave)
    document.addEventListener('mouseenter', handleMouseEnter)
    document.body.classList.add('hide-system-cursor')

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseleave', handleMouseLeave)
      document.removeEventListener('mouseenter', handleMouseEnter)
      document.body.classList.remove('hide-system-cursor')
    }
  }, [active])

  if (!active || !visible) return null

  return (
    <div
      style={{
        position: 'fixed',
        left: position.x,
        top: position.y,
        width: '10px',
        height: '10px',
        borderRadius: '50%',
        backgroundColor: '#fff',
        border: '2px solid var(--accent)',
        boxShadow: '0 0 8px var(--accent-glow)',
        pointerEvents: 'none',
        transform: 'translate(-50%, -50%)',
        zIndex: 99999,
      }}
    />
  )
}
