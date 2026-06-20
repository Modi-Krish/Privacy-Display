import { useEffect, useRef, useState } from 'react'
import { useProfileStore } from '@/store/profileStore'
import toast from 'react-hot-toast'
import axios from 'axios'
import { getApiUrl } from '@/api/client'
import { useNavigate } from 'react-router-dom'
import styles from './ProfilePage.module.css'

export default function ProfilePage() {
  const {
    resume, projects, skills, isIndexing, indexingProgress,
    fetchProfile, fetchProjects, fetchSkills, fetchIndexingProgress,
    uploadResume, deleteResume,
    addProject, deleteProject,
    addSkill, deleteSkill,
  } = useProfileStore()

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [newSkill,  setNewSkill]  = useState('')
  const [showAddProj, setShowAddProj] = useState(false)
  const [projForm, setProjForm]   = useState({ title: '', description: '', technologies: '' })
  const [isDragActive, setIsDragActive] = useState(false)
  const [authCode, setAuthCode] = useState('')
  const [authLoading, setAuthLoading] = useState(false)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    fetchProfile()
    fetchProjects()
    fetchSkills()
    const checkAuth = async () => {
      if (window.electronAPI?.auth) {
        const tokens = await window.electronAPI.auth.getTokens()
        if (tokens?.access_token) {
          setIsAuthenticated(true)
        }
      }
    }
    checkAuth()
  }, [])

  useEffect(() => {
    let interval: NodeJS.Timeout
    if (isIndexing) {
      interval = setInterval(() => {
        fetchIndexingProgress()
      }, 1000)
    }
    return () => clearInterval(interval)
  }, [isIndexing, fetchIndexingProgress])

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      await uploadResume(file)
      toast.success('Resume uploaded and indexed!')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Upload failed')
    }
    if (e.target) {
        e.target.value = ''
    }
  }

  const handleDeleteResume = async () => {
    await deleteResume()
    toast.success('Resume removed')
  }

  const handleAddSkill = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newSkill.trim()) return
    try {
      await addSkill(newSkill.trim())
      setNewSkill('')
      toast.success('Skill added')
    } catch { toast.error('Could not add skill') }
  }

  const handleAddProject = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!projForm.title.trim()) return
    try {
      await addProject(projForm)
      setProjForm({ title: '', description: '', technologies: '' })
      setShowAddProj(false)
      toast.success('Project added and indexed')
    } catch { toast.error('Could not add project') }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragActive(true)
    } else if (e.type === 'dragleave') {
      setIsDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const f = e.dataTransfer.files[0]
      const dt = new DataTransfer()
      dt.items.add(f)
      if (fileInputRef.current) {
        fileInputRef.current.files = dt.files
        handleResumeUpload({ target: fileInputRef.current } as any)
      }
    }
  }

  const handlePair = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!authCode || authCode.trim().length === 0) return

    setAuthLoading(true)
    try {
      let deviceId = localStorage.getItem('device_id')
      if (!deviceId) {
        deviceId = crypto.randomUUID()
        localStorage.setItem('device_id', deviceId)
      }

      const { data } = await axios.post(`${getApiUrl()}/api/auth/desktop/pair/verify`, {
        code: authCode,
        device_id: deviceId,
        device_name: window.electronAPI ? `REAI Desktop (${window.electronAPI.platform})` : 'REAI Desktop'
      })

      if (window.electronAPI?.auth) {
        await window.electronAPI.auth.setTokens({
          access_token: data.access_token,
          refresh_token: data.refresh_token,
          user_id: data.user_id
        })
      }

      toast.success('Device paired successfully!')
      setIsAuthenticated(true)
      setAuthCode('')
    } catch (error: any) {
      console.error(error)
      const msg = error.response?.data?.detail || 'Failed to verify pairing code.'
      toast.error(msg)
    } finally {
      setAuthLoading(false)
    }
  }

  const handleLogout = async () => {
    if (window.electronAPI?.auth) {
      await window.electronAPI.auth.clearTokens()
    }
    setIsAuthenticated(false)
    toast.success('Logged out successfully')
    navigate('/auth')
  }

  return (
    <div className={styles.page}>

      {isIndexing && (
        <div className={styles.indexingBadge} style={{ flexDirection: 'column', alignItems: 'flex-start', padding: '16px', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className={`material-symbols-outlined ${styles.spin}`}>sync</span>
            <span>Updating knowledge base…</span>
          </div>
          {indexingProgress && (
            <div style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px', opacity: 0.8 }}>
                <span>{indexingProgress.current_file || 'Initializing...'}</span>
                <span>{indexingProgress.progress_pct}%</span>
              </div>
              <div style={{ width: '100%', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{ height: '100%', width: `${indexingProgress.progress_pct}%`, background: 'var(--primary)', transition: 'width 0.3s ease' }} />
              </div>
              {indexingProgress.time_remaining_sec !== null && indexingProgress.time_remaining_sec > 0 && (
                <div style={{ fontSize: '11px', marginTop: '4px', opacity: 0.6, textAlign: 'right' }}>
                  ~{indexingProgress.time_remaining_sec}s remaining
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <div className={styles.bentoGrid}>
        {/* ── Account Section ────────────────────────────────── */}
        <section className={`${styles.md3Card} ${styles.accountSection}`}>
          <h2 className={styles.cardHeader}>
            <span className={`material-symbols-outlined ${styles.cardHeaderIcon}`}>account_circle</span>
            Account Connection
            {isAuthenticated && (
              <div className={styles.cardHeaderRight}>
                <span className={styles.indexedBadge} style={{ background: '#d4edda', borderColor: '#28a745', color: '#155724' }}>
                  <span className={`material-symbols-outlined ${styles.indexedBadgeIcon}`}>check_circle</span>
                  Connected
                </span>
              </div>
            )}
          </h2>

          {isAuthenticated ? (
            <div className={styles.accountActive}>
              <div className={styles.accountInfoWrap}>
                <span className={`material-symbols-outlined ${styles.accountIcon}`}>verified_user</span>
                <div>
                  <p className={styles.accountStatus}>Your device is linked to REAI</p>
                  <p className={styles.accountMeta}>You can access your cloud data.</p>
                </div>
              </div>
              <button className={styles.removeBtn} onClick={handleLogout}>
                <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>logout</span>
                Disconnect
              </button>
            </div>
          ) : (
            <div className={styles.accountInactive}>
              <p className={styles.accountDesc}>
                Please visit <a href="https://app.reai.ai" target="_blank" rel="noreferrer" style={{ color: '#2d5da1', textDecoration: 'underline' }}>app.reai.ai</a> to sign in and generate a pairing code.
              </p>
              <form onSubmit={handlePair} className={styles.accountForm}>
                <input
                  className={styles.skillInput}
                  type="text"
                  placeholder="Enter pairing code"
                  value={authCode}
                  onChange={(e) => setAuthCode(e.target.value.trim())}
                />
                <button 
                  type="submit" 
                  className={`${styles.pillButton} ${styles.skillAddBtn}`}
                  disabled={authLoading || authCode.trim().length === 0}
                  style={{ width: 'auto' }}
                >
                  {authLoading ? 'Pairing...' : 'Connect'}
                </button>
              </form>
            </div>
          )}
        </section>

        {/* ── Resume Section ────────────────────────────────── */}
        <section className={`${styles.md3Card} ${styles.resumeSection}`}>
          <h2 className={styles.cardHeader}>
            <span className={`material-symbols-outlined ${styles.cardHeaderIcon}`}>description</span>
            Resume
            {resume && (
              <div className={styles.cardHeaderRight}>
                <span className={styles.indexedBadge}>
                  <span className={`material-symbols-outlined ${styles.indexedBadgeIcon}`}>check_circle</span>
                  Indexed
                </span>
              </div>
            )}
          </h2>

          {resume ? (
            <div className={styles.resumeActive}>
              <div className={styles.resumeInfoWrap}>
                <span className={`material-symbols-outlined ${styles.resumeIcon}`}>file_present</span>
                <div>
                  <p className={styles.resumeName}>{resume.file_name}</p>
                  <p className={styles.resumeMeta}>
                    {resume.extracted_text
                      ? `${resume.extracted_text.split(' ').length.toLocaleString()} words extracted`
                      : 'Text extraction pending'}
                  </p>
                </div>
              </div>
              <button className={styles.removeBtn} onClick={handleDeleteResume}>
                <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>delete</span>
                Remove
              </button>
            </div>
          ) : (
            <div
              className={`${styles.dashedArea} ${isDragActive ? styles.dashedAreaActive : ''}`}
              onClick={() => fileInputRef.current?.click()}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <div className={styles.uploadIconWrap}>
                <span className={`material-symbols-outlined ${styles.uploadIcon}`}>upload_file</span>
              </div>
              <p className={styles.uploadTitle}>Click or drag PDF here</p>
              <span className={styles.uploadHint}>Max 10 MB · PDF only</span>
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            style={{ display: 'none' }}
            onChange={handleResumeUpload}
          />
        </section>

        {/* ── Skills Section ────────────────────────────────── */}
        <section className={`${styles.md3Card} ${styles.skillsSection}`}>
          <h2 className={styles.cardHeader}>
            <span className={`material-symbols-outlined ${styles.cardHeaderIcon}`}>psychology</span>
            Skills
          </h2>
          
          <div className={styles.skillsContainer}>
            <form onSubmit={handleAddSkill} className="flex flex-col gap-3 w-full">
              <div className={styles.skillInputWrap}>
                <input
                  className={styles.skillInput}
                  placeholder="Python, React, Docker..."
                  value={newSkill}
                  onChange={(e) => setNewSkill(e.target.value)}
                  type="text"
                />
              </div>
              <button 
                type="submit" 
                className={`${styles.pillButton} ${styles.skillAddBtn}`} 
                disabled={!newSkill.trim()}
              >
                <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>add</span>
                Add
              </button>
            </form>

            <div className={styles.skillTags}>
              {skills.map((s) => (
                <div key={s.id} className={styles.skillTag}>
                  <span>{s.skill_name}</span>
                  <span 
                    className={`material-symbols-outlined ${styles.skillTagClose}`}
                    onClick={() => deleteSkill(s.id).then(() => toast.success('Skill removed'))}
                    title="Remove"
                  >
                    close
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Projects Section ──────────────────────────────── */}
        <section className={`${styles.md3Card} ${styles.projectsSection}`}>
          <div className={styles.projectsHeader}>
            <h2 className={styles.cardHeader}>
              <span className={`material-symbols-outlined ${styles.cardHeaderIcon}`}>folder_open</span>
              Projects
            </h2>
            <button 
              className={`${styles.pillButton} ${styles.addProjectBtn}`}
              onClick={() => setShowAddProj(!showAddProj)}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '18px' }}>add</span>
              Add Project
            </button>
          </div>

          {showAddProj && (
            <form onSubmit={handleAddProject} className={styles.projectForm}>
              <div className={styles.formGroup}>
                <label className={styles.formLabel} htmlFor="proj-title">Project Title *</label>
                <input 
                  id="proj-title" 
                  className={styles.skillInput} 
                  placeholder="Privacy Display" 
                  required
                  value={projForm.title} 
                  onChange={(e) => setProjForm({ ...projForm, title: e.target.value })} 
                />
              </div>
              <div className={styles.formGroup}>
                <label className={styles.formLabel} htmlFor="proj-desc">Description</label>
                <textarea 
                  id="proj-desc" 
                  className={styles.skillInput} 
                  style={{ minHeight: '80px', borderRadius: '16px' }}
                  placeholder="What does this project do?"
                  value={projForm.description} 
                  onChange={(e) => setProjForm({ ...projForm, description: e.target.value })} 
                />
              </div>
              <div className={styles.formGroup}>
                <label className={styles.formLabel} htmlFor="proj-tech">Technologies</label>
                <input 
                  id="proj-tech" 
                  className={styles.skillInput} 
                  placeholder="Python, FastAPI, FAISS"
                  value={projForm.technologies} 
                  onChange={(e) => setProjForm({ ...projForm, technologies: e.target.value })} 
                />
              </div>
              <div className={styles.formActions}>
                <button type="submit" className={`${styles.pillButton} ${styles.addProjectBtn}`}>
                  Save Project
                </button>
                <button type="button" className={`${styles.pillButton} ${styles.cancelBtn}`} onClick={() => setShowAddProj(false)}>
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className={styles.projectList}>
            {projects.map((p) => (
              <div key={p.id} className={styles.projectCard}>
                <div className={styles.projInfo}>
                  <p className={styles.projTitle}>{p.title}</p>
                  {p.description && <p className={styles.projDesc}>{p.description}</p>}
                  {p.technologies && (
                    <p className={styles.projTech}>{p.technologies}</p>
                  )}
                </div>
                <button 
                  className={styles.removeBtn} 
                  style={{ padding: '8px', border: 'none' }}
                  onClick={() => deleteProject(p.id).then(() => toast.success('Project removed'))}
                  title="Delete project"
                >
                  <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>delete</span>
                </button>
              </div>
            ))}
            {projects.length === 0 && !showAddProj && (
              <div className={styles.projectsEmpty}>
                <span className={`material-symbols-outlined ${styles.projectsEmptyIcon}`}>auto_awesome</span>
                <p className={styles.projectsEmptyText}>
                  Add projects to improve retrieval quality. The AI will use these details to provide more accurate context during interviews.
                </p>
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
