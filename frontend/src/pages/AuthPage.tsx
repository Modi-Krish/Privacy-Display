import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'react-hot-toast'
import axios from 'axios'
import styles from './AuthPage.module.css'
import { getApiUrl } from '@/api/client'

export default function AuthPage() {
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    // Check if we already have valid tokens on load
    const checkAuth = async () => {
      if (window.electronAPI?.auth) {
        const tokens = await window.electronAPI.auth.getTokens()
        if (tokens?.access_token) {
          navigate('/interview', { replace: true })
        }
      }
    }
    checkAuth()
  }, [navigate])

  const handlePair = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!code || code.length < 6) return

    setLoading(true)
    try {
      // 1. Generate a somewhat unique device ID locally if we don't have one
      let deviceId = localStorage.getItem('device_id')
      if (!deviceId) {
        deviceId = crypto.randomUUID()
        localStorage.setItem('device_id', deviceId)
      }

      // 2. Call backend pair/verify
      const { data } = await axios.post(`${getApiUrl()}/api/auth/desktop/pair/verify`, {
        code,
        device_id: deviceId,
        device_name: window.electronAPI ? `REAI Desktop (${window.electronAPI.platform})` : 'REAI Desktop'
      })

      // 3. Save tokens securely
      if (window.electronAPI?.auth) {
        await window.electronAPI.auth.setTokens({
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          user_id: data.user_id
        })
      }

      toast.success('Device paired successfully!')
      navigate('/interview', { replace: true })

    } catch (error: any) {
      console.error(error)
      const msg = error.response?.data?.detail || 'Failed to verify pairing code.'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>Connect Your Device</h1>
        <p className={styles.subtitle}>
          Please visit <a href="https://app.reai.ai" target="_blank" rel="noreferrer" className={styles.link}>app.reai.ai</a> to sign in with Google and generate a pairing code.
        </p>

        <form onSubmit={handlePair} className={styles.form}>
          <div className={styles.inputGroup}>
            <input
              type="text"
              placeholder="Enter 6-digit code"
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              maxLength={6}
              className={styles.input}
              autoFocus
            />
          </div>
          
          <button 
            type="submit" 
            disabled={loading || code.length < 6}
            className={`${styles.button} ${loading ? styles.loading : ''}`}
          >
            {loading ? 'Pairing...' : 'Connect'}
          </button>
        </form>
      </div>
    </div>
  )
}
