import { create } from 'zustand'
import { api } from '@/api/client'

export interface Resume {
  id: string
  file_name: string
  extracted_text: string | null
}

export interface Project {
  id: string
  title: string
  description: string | null
  technologies: string | null
}

export interface Skill {
  id: string
  skill_name: string
}

export interface Profile {
  id: string
  user_id: string
  full_name: string | null
  summary: string | null
}

export interface IndexingProgress {
  status: string
  progress_pct: number
  current_file: string
  completed_items: number
  total_items: number
  time_remaining_sec: number | null
  error: string | null
}

interface ProfileState {
  profile: Profile | null
  resume: Resume | null
  projects: Project[]
  skills: Skill[]
  isIndexing: boolean
  indexingProgress: IndexingProgress | null
  error: string | null

  fetchProfile: () => Promise<void>
  fetchIndexingProgress: () => Promise<void>
  updateProfile: (data: Partial<Pick<Profile, 'full_name' | 'summary'>>) => Promise<void>

  uploadResume: (file: File) => Promise<void>
  deleteResume: () => Promise<void>

  fetchProjects: () => Promise<void>
  addProject: (p: Omit<Project, 'id'>) => Promise<void>
  updateProject: (id: string, p: Partial<Omit<Project, 'id'>>) => Promise<void>
  deleteProject: (id: string) => Promise<void>

  fetchSkills: () => Promise<void>
  addSkill: (name: string) => Promise<void>
  deleteSkill: (id: string) => Promise<void>

  clearError: () => void
  setIndexingState: (isIndexing: boolean, progress: IndexingProgress | null) => void
}

export const useProfileStore = create<ProfileState>((set, get) => ({
  profile: null,
  resume: null,
  projects: [],
  skills: [],
  isIndexing: false,
  indexingProgress: null,
  error: null,

  fetchProfile: async () => {
    try {
      const { data } = await api.get('/api/profile')
      set({ profile: data })
    } catch { /* profile may not exist yet */ }
  },

  fetchIndexingProgress: async () => {
    try {
      const { data } = await api.get('/api/resume/progress')
      if (data.status === 'completed' || data.status === 'idle' || data.status === 'failed') {
        set({ isIndexing: false, indexingProgress: data })
      } else {
        set({ isIndexing: true, indexingProgress: data })
      }
    } catch (err) {
      set({ isIndexing: false })
    }
  },

  updateProfile: async (body) => {
    const { data } = await api.put('/api/profile', body)
    set({ profile: data })
  },

  uploadResume: async (file) => {
    set({ isIndexing: true, error: null, indexingProgress: null })
    try {
      const form = new FormData()
      form.append('file', file)
      const { data } = await api.post('/api/resume/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      set({ resume: data }) // Keep isIndexing true to trigger polling
    } catch (err: any) {
      set({ error: err.response?.data?.detail || 'Upload failed', isIndexing: false })
      throw err
    }
  },

  deleteResume: async () => {
    set({ isIndexing: true, indexingProgress: null })
    await api.delete('/api/resume')
    set({ resume: null })
  },

  fetchProjects: async () => {
    const { data } = await api.get('/api/projects')
    set({ projects: data })
  },

  addProject: async (p) => {
    set({ isIndexing: true, indexingProgress: null })
    const { data } = await api.post('/api/projects', p)
    set((s) => ({ projects: [...s.projects, data] }))
  },

  updateProject: async (id, p) => {
    set({ isIndexing: true, indexingProgress: null })
    const { data } = await api.put(`/api/projects/${id}`, p)
    set((s) => ({
      projects: s.projects.map((pr) => (pr.id === id ? data : pr)),
    }))
  },

  deleteProject: async (id) => {
    set({ isIndexing: true, indexingProgress: null })
    await api.delete(`/api/projects/${id}`)
    set((s) => ({ projects: s.projects.filter((p) => p.id !== id) }))
  },

  fetchSkills: async () => {
    const { data } = await api.get('/api/skills')
    set({ skills: data })
  },

  addSkill: async (name) => {
    set({ isIndexing: true, indexingProgress: null })
    const { data } = await api.post('/api/skills', { skill_name: name })
    set((s) => ({ skills: [...s.skills, data] }))
  },

  deleteSkill: async (id) => {
    set({ isIndexing: true, indexingProgress: null })
    await api.delete(`/api/skills/${id}`)
    set((s) => ({ skills: s.skills.filter((sk) => sk.id !== id) }))
  },

  clearError: () => set({ error: null }),
  setIndexingState: (isIndexing, progress) => set({ isIndexing, indexingProgress: progress }),
}))
