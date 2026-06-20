"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import styles from "./page.module.css";
import dashStyles from "../dashboard.module.css";

interface Session {
  id: string;
  started_at: string;
  ended_at: string | null;
  questions_count: number;
}

export default function SessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchSessions() {
      try {
        const { data } = await api.get("/api/dashboard/sessions");
        setSessions(data);
      } catch (err: unknown) {
        console.error(err);
        setError("Failed to load sessions.");
      } finally {
        setLoading(false);
      }
    }
    fetchSessions();
  }, []);

  if (loading) return <div className={dashStyles.loader}>Loading sessions...</div>;
  if (error) return <div className={dashStyles.error}>{error}</div>;

  return (
    <div className={`${dashStyles.card} ${dashStyles.animateFadeIn}`}>
      <h2 className={dashStyles.sectionTitle} style={{ color: "white", fontSize: "1.25rem", marginBottom: "0.25rem" }}>Interview History</h2>
      <p className={dashStyles.sectionDesc} style={{ color: "#a1a1aa", fontSize: "0.9rem", marginBottom: "2rem" }}>
        Review your past interview sessions and analyze your answers.
      </p>

      {sessions.length === 0 ? (
        <div className={styles.emptyState}>
          <span className="material-symbols-outlined" style={{ fontSize: 48, marginBottom: "1rem", color: "#3f3f46" }}>history</span>
          <p>No interview sessions found.</p>
          <span style={{ fontSize: "0.85rem" }}>Pair your desktop app and start an interview to see it here.</span>
        </div>
      ) : (
        <div className={styles.sessionList}>
          {sessions.map((s) => {
            const startDate = new Date(s.started_at);
            let durationStr = "Ongoing";
            if (s.ended_at) {
              const endDate = new Date(s.ended_at);
              const diffMs = endDate.getTime() - startDate.getTime();
              const mins = Math.round(diffMs / 60000);
              durationStr = `${mins} min${mins !== 1 ? 's' : ''}`;
            }

            return (
              <Link key={s.id} href={`/dashboard/sessions/details?id=${s.id}`} className={styles.sessionItem}>
                <div className={styles.sessionIcon}>
                  <span className="material-symbols-outlined">forum</span>
                </div>
                <div className={styles.sessionInfo}>
                  <h3 className={styles.sessionDate}>
                    {startDate.toLocaleDateString(undefined, { weekday: 'long', year: 'numeric', month: 'short', day: 'numeric' })}
                  </h3>
                  <p className={styles.sessionMeta}>
                    {startDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} • {durationStr} • {s.questions_count} Questions
                  </p>
                </div>
                <div className={styles.sessionAction}>
                  View Details <span className="material-symbols-outlined" style={{ fontSize: 18 }}>arrow_forward</span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
