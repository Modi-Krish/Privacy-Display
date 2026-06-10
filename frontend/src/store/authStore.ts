import { create } from 'zustand'
import { api } from '@/api/client'

export interface User {
  id: string
  email: string
  created_at: string
}

interface AuthState {
  user: User | null
  isLoading: boolean
  isInitialized: boolean
  error: string | null
  // Actions
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, full_name?: string) => Promise<void>
  logout: () => Promise<void>
  fetchMe: () => Promise<void>
  clearError: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  isInitialized: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null })
    try {
      const { data } = await api.post('/api/auth/login', { email, password })
      set({ user: data.user, isLoading: false })
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Login failed', isLoading: false })
      throw err
    }
  },

  register: async (email, password, full_name) => {
    set({ isLoading: true, error: null })
    try {
      const { data } = await api.post('/api/auth/register', { email, password, full_name })
      set({ user: data.user, isLoading: false })
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Registration failed', isLoading: false })
      throw err
    }
  },

  logout: async () => {
    set({ user: null, isInitialized: true })  // clear state immediately
    api.post('/api/auth/logout').catch(() => {})  // fire-and-forget
  },

  fetchMe: async () => {
    try {
      const { data } = await api.get('/api/auth/me')
      set({ user: data, isInitialized: true })
    } catch {
      set({ user: null, isInitialized: true })
    }
  },

  clearError: () => set({ error: null }),
}))
