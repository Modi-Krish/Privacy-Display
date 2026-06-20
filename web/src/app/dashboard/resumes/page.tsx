"use client";

import { useEffect, useState, useRef } from "react";
import { api } from "@/lib/api";
import styles from "./page.module.css";
import dashStyles from "../dashboard.module.css";

interface Resume {
  id: string;
  file_name: string;
  uploaded_at: string;
}

export default function ResumesPage() {
  const [resume, setResume] = useState<Resume | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    async function fetchResume() {
      try {
        setLoading(true);
        setError("");
        const { data } = await api.get("/api/resume");
        setResume(data);
      } catch (err: unknown) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        if ((err as any).response?.status !== 404) {
          setError("Failed to load resume.");
        }
      } finally {
        setLoading(false);
      }
    }
    fetchResume();
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.type !== "application/pdf") {
      alert("Only PDF files are supported.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    try {
      setUploading(true);
      setError("");
      const { data } = await api.post("/api/resume/upload", formData);
      setResume(data);
    } catch (err: unknown) {
      console.error(err);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((err as any).response?.data?.detail || "Failed to upload resume.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDelete = async () => {
    if (!confirm("Delete your current resume? This cannot be undone.")) return;
    try {
      setLoading(true);
      await api.delete("/api/resume");
      setResume(null);
    } catch {
      setError("Failed to delete resume.");
    } finally {
      setLoading(false);
    }
  };

  if (loading && !resume) return <div className={dashStyles.loader}>Loading resume...</div>;

  return (
    <div className={`${dashStyles.card} ${dashStyles.animateFadeIn}`}>
      <h2 className={dashStyles.sectionTitle}>Resume Management</h2>
      <p className={dashStyles.sectionDesc}>
        Upload your resume (PDF only) to personalize your interview questions and AI-generated answers.
      </p>

      {error && <div className={dashStyles.error} style={{ marginBottom: "1rem" }}>{error}</div>}

      <div className={styles.uploadSection}>
        <input 
          type="file" 
          accept="application/pdf" 
          style={{ display: 'none' }} 
          ref={fileInputRef}
          onChange={handleFileUpload}
        />
        <button 
          className={styles.uploadBtn} 
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          <span className="material-symbols-outlined">upload_file</span>
          {uploading ? "Uploading..." : resume ? "Upload New Resume" : "Upload Resume (PDF)"}
        </button>
      </div>

      {resume ? (
        <div className={styles.resumeCard}>
          <div className={styles.resumeIcon}>
            <span className="material-symbols-outlined">picture_as_pdf</span>
          </div>
          <div className={styles.resumeInfo}>
            <h3 className={styles.resumeName}>{resume.file_name}</h3>
            <p className={styles.resumeMeta}>
              Uploaded on {new Date(resume.uploaded_at).toLocaleString()}
            </p>
          </div>
          <button className={styles.deleteBtn} onClick={handleDelete}>
            <span className="material-symbols-outlined">delete</span>
          </button>
        </div>
      ) : (
        <div className={styles.emptyState}>
          <span className="material-symbols-outlined" style={{ fontSize: 48, marginBottom: "1rem", color: "#3f3f46" }}>find_in_page</span>
          <p>No resume uploaded.</p>
          <span style={{ fontSize: "0.85rem" }}>Upload a PDF to get personalized interviews.</span>
        </div>
      )}
    </div>
  );
}
