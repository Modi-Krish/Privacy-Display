import { useEffect, useRef, useState } from 'react'
import { Upload, Trash2, Plus, X, FileText, Briefcase, Code2, CheckCircle, Loader } from 'lucide-react'
import { useProfileStore } from '@/store/profileStore'
import toast from 'react-hot-toast'
import styles from './ProfilePage.module.css'

export default function ProfilePage() {
  const {
    profile, resume, projects, skills, isIndexing,
    fetchProfile, fetchProjects, fetchSkills,
    uploadResume, deleteResume,
    addProject, deleteProject,
    addSkill, deleteSkill,
    updateProfile,
  } = useProfileStore()

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [newSkill,  setNewSkill]  = useState('')
  const [showAddProj, setShowAddProj] = useState(false)
  const [projForm, setProjForm]   = useState({ title: '', description: '', technologies: '' })

  useEffect(() => {
    fetchProfile()
    fetchProjects()
    fetchSkills()
  }, [])

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      await uploadResume(file)
      toast.success('Resume uploaded and indexed!')
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Upload failed')
    }
    e.target.value = ''
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

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1>Profile</h1>
        <p>Your resume, projects and skills power the RAG retrieval during interviews.</p>
        {isIndexing && (
          <div className={styles.indexingBadge}>
            <Loader size={13} className={styles.spin} />
            <span>Updating knowledge base…</span>
          </div>
        )}
      </div>

      <div className={styles.grid}>
        {/* ── Resume ────────────────────────────────── */}
        <section className={`card ${styles.section}`}>
          <div className={styles.sectionHead}>
            <div className="flex items-center gap-2">
              <FileText size={16} style={{ color: 'var(--accent)' }} />
              <h2>Resume</h2>
            </div>
            {resume && <span className="badge badge-success"><CheckCircle size={11} /> Indexed</span>}
          </div>

          {resume ? (
            <div className={styles.resumeCard}>
              <div className={styles.resumeInfo}>
                <FileText size={20} style={{ color: 'var(--text-muted)' }} />
                <div>
                  <p className={styles.resumeName}>{resume.file_name}</p>
                  <p className={styles.resumeMeta}>
                    {resume.extracted_text
                      ? `${resume.extracted_text.split(' ').length.toLocaleString()} words extracted`
                      : 'Text extraction pending'}
                  </p>
                </div>
              </div>
              <button id="btn-delete-resume" className="btn btn-danger btn-sm" onClick={handleDeleteResume}>
                <Trash2 size={14} /> Remove
              </button>
            </div>
          ) : (
            <div
              className={styles.dropzone}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault()
                const f = e.dataTransfer.files[0]
                if (f) { const dt = new DataTransfer(); dt.items.add(f); if (fileInputRef.current) { fileInputRef.current.files = dt.files; handleResumeUpload({ target: fileInputRef.current } as any) } }
              }}
            >
              <Upload size={24} style={{ color: 'var(--text-muted)' }} />
              <p>Click or drag PDF here</p>
              <span className={styles.dropzoneHint}>Max 10 MB · PDF only</span>
            </div>
          )}
          <input
            ref={fileInputRef}
            id="input-resume-file"
            type="file"
            accept="application/pdf"
            style={{ display: 'none' }}
            onChange={handleResumeUpload}
          />
        </section>

        {/* ── Skills ────────────────────────────────── */}
        <section className={`card ${styles.section}`}>
          <div className={styles.sectionHead}>
            <div className="flex items-center gap-2">
              <Code2 size={16} style={{ color: 'var(--accent)' }} />
              <h2>Skills</h2>
            </div>
            <span className={styles.count}>{skills.length}</span>
          </div>

          <form onSubmit={handleAddSkill} className={styles.addSkillForm}>
            <input
              id="input-new-skill"
              className="input"
              placeholder="Python, React, Docker…"
              value={newSkill}
              onChange={(e) => setNewSkill(e.target.value)}
            />
            <button id="btn-add-skill" type="submit" className="btn btn-primary btn-sm" disabled={!newSkill.trim()}>
              <Plus size={14} /> Add
            </button>
          </form>

          <div className={styles.skillCloud}>
            {skills.map((s) => (
              <div key={s.id} className={styles.skillTag}>
                <span>{s.skill_name}</span>
                <button
                  id={`btn-del-skill-${s.id}`}
                  className={styles.skillDel}
                  onClick={() => deleteSkill(s.id).then(() => toast.success('Skill removed'))}
                  title="Remove"
                >
                  <X size={11} />
                </button>
              </div>
            ))}
            {skills.length === 0 && (
              <p className={styles.emptyHint}>Add your technical and soft skills</p>
            )}
          </div>
        </section>

        {/* ── Projects ──────────────────────────────── */}
        <section className={`card ${styles.section} ${styles.fullWidth}`}>
          <div className={styles.sectionHead}>
            <div className="flex items-center gap-2">
              <Briefcase size={16} style={{ color: 'var(--accent)' }} />
              <h2>Projects</h2>
            </div>
            <button
              id="btn-show-add-project"
              className="btn btn-secondary btn-sm"
              onClick={() => setShowAddProj(!showAddProj)}
            >
              <Plus size={14} /> Add Project
            </button>
          </div>

          {showAddProj && (
            <form onSubmit={handleAddProject} className={`${styles.projForm} fade-in`}>
              <div className="form-group">
                <label className="form-label" htmlFor="proj-title">Project Title *</label>
                <input id="proj-title" className="input" placeholder="Interview Copilot" required
                  value={projForm.title} onChange={(e) => setProjForm({ ...projForm, title: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="proj-desc">Description</label>
                <textarea id="proj-desc" className="input" placeholder="What does this project do?"
                  value={projForm.description} onChange={(e) => setProjForm({ ...projForm, description: e.target.value })} />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="proj-tech">Technologies</label>
                <input id="proj-tech" className="input" placeholder="Python, FastAPI, FAISS"
                  value={projForm.technologies} onChange={(e) => setProjForm({ ...projForm, technologies: e.target.value })} />
              </div>
              <div className="flex gap-2">
                <button id="btn-save-project" type="submit" className="btn btn-primary">Save Project</button>
                <button type="button" className="btn btn-ghost" onClick={() => setShowAddProj(false)}>Cancel</button>
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
                  id={`btn-del-project-${p.id}`}
                  className="btn btn-ghost btn-icon btn-sm"
                  onClick={() => deleteProject(p.id).then(() => toast.success('Project removed'))}
                  title="Delete project"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
            {projects.length === 0 && !showAddProj && (
              <p className={styles.emptyHint}>Add projects to improve retrieval quality</p>
            )}
          </div>
        </section>
      </div>
    </div>
  )
}
