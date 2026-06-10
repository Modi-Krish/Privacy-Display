import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Brain, Mail, Lock, User, ArrowRight, Eye, EyeOff } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import toast from 'react-hot-toast'
import styles from './AuthPage.module.css'

interface Props { mode?: 'login' | 'register' }

export default function AuthPage({ mode = 'login' }: Props) {
  const [isLogin, setIsLogin]       = useState(mode === 'login')
  const [email, setEmail]           = useState('')
  const [password, setPassword]     = useState('')
  const [fullName, setFullName]     = useState('')
  const [showPass, setShowPass]     = useState(false)
  const { login, register, isLoading, error, clearError } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    try {
      if (isLogin) {
        await login(email, password)
        toast.success('Welcome back!')
      } else {
        await register(email, password, fullName || undefined)
        toast.success('Account created!')
      }
      navigate('/interview')
    } catch { /* error shown from store */ }
  }

  return (
    <div className={styles.page}>
      {/* Background glow */}
      <div className={styles.glow} />

      <div className={styles.card}>
        {/* Logo */}
        <div className={styles.logo}>
          <div className={styles.logoIcon}>
            <Brain size={28} strokeWidth={1.5} />
          </div>
          <h1 className={styles.logoText}>Interview <span className="gradient-text">Copilot</span></h1>
          <p className={styles.logoSub}>AI-powered interview assistance</p>
        </div>

        {/* Tabs */}
        <div className={styles.tabs}>
          <button
            id="tab-login"
            className={`${styles.tab} ${isLogin ? styles.tabActive : ''}`}
            onClick={() => { setIsLogin(true); clearError() }}
          >Sign In</button>
          <button
            id="tab-register"
            className={`${styles.tab} ${!isLogin ? styles.tabActive : ''}`}
            onClick={() => { setIsLogin(false); clearError() }}
          >Create Account</button>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          {!isLogin && (
            <div className="form-group">
              <label className="form-label" htmlFor="input-name">Full Name (optional)</label>
              <div className={styles.inputWrap}>
                <User size={16} className={styles.inputIcon} />
                <input
                  id="input-name"
                  type="text"
                  className={`input ${styles.inputPadded}`}
                  placeholder="Jane Smith"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>
            </div>
          )}

          <div className="form-group">
            <label className="form-label" htmlFor="input-email">Email</label>
            <div className={styles.inputWrap}>
              <Mail size={16} className={styles.inputIcon} />
              <input
                id="input-email"
                type="email"
                className={`input ${styles.inputPadded}`}
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="input-password">Password</label>
            <div className={styles.inputWrap}>
              <Lock size={16} className={styles.inputIcon} />
              <input
                id="input-password"
                type={showPass ? 'text' : 'password'}
                className={`input ${styles.inputPadded} ${styles.inputPaddedRight}`}
                placeholder={isLogin ? '••••••••' : 'Min. 8 characters'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete={isLogin ? 'current-password' : 'new-password'}
              />
              <button
                type="button"
                id="btn-toggle-password"
                className={styles.eyeBtn}
                onClick={() => setShowPass(!showPass)}
                tabIndex={-1}
              >
                {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {error && <p className={styles.errorMsg}>{error}</p>}

          <button
            id="btn-auth-submit"
            type="submit"
            className="btn btn-primary w-full btn-lg"
            disabled={isLoading}
          >
            {isLoading ? <span className="spinner" /> : <ArrowRight size={18} />}
            {isLogin ? 'Sign In' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  )
}
