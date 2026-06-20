"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import styles from "./page.module.css";
import dashStyles from "./dashboard.module.css";

interface DashboardStats {
  total_sessions: number;
  total_questions: number;
  total_answers: number;
  total_interview_hours: number;
  active_devices: number;
}

export default function DashboardOverview() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchStats() {
      try {
        const { data } = await api.get("/api/dashboard/stats");
        setStats(data);
      } catch (err: unknown) {
        console.error(err);
        setError("Failed to load statistics.");
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, []);

  if (loading) {
    return <div className={styles.loader}>Loading your statistics...</div>;
  }

  if (error) {
    return <div className={styles.error}>{error}</div>;
  }

  return (
    <div className={`${dashStyles.card} ${dashStyles.animateFadeIn}`}>
      <h2 className={styles.sectionTitle}>Overview</h2>
      <p className={styles.sectionDesc}>Your interview performance and usage metrics at a glance.</p>
      
      <div className={styles.statsGrid}>
        <div className={styles.statBox}>
          <span className="material-symbols-outlined" style={{ color: "#a855f7" }}>bolt</span>
          <div className={styles.statValue}>{stats?.total_sessions || 0}</div>
          <div className={styles.statLabel}>Total Sessions</div>
        </div>
        <div className={styles.statBox}>
          <span className="material-symbols-outlined" style={{ color: "#3b82f6" }}>help_center</span>
          <div className={styles.statValue}>{stats?.total_questions || 0}</div>
          <div className={styles.statLabel}>Questions Asked</div>
        </div>
        <div className={styles.statBox}>
          <span className="material-symbols-outlined" style={{ color: "#10b981" }}>auto_awesome</span>
          <div className={styles.statValue}>{stats?.total_answers || 0}</div>
          <div className={styles.statLabel}>Answers Generated</div>
        </div>
        <div className={styles.statBox}>
          <span className="material-symbols-outlined" style={{ color: "#f59e0b" }}>timer</span>
          <div className={styles.statValue}>{stats?.total_interview_hours || 0}h</div>
          <div className={styles.statLabel}>Interview Hours</div>
        </div>
        <div className={styles.statBox}>
          <span className="material-symbols-outlined" style={{ color: "#ec4899" }}>devices</span>
          <div className={styles.statValue}>{stats?.active_devices || 0}</div>
          <div className={styles.statLabel}>Active Devices</div>
        </div>
      </div>
      
      <div className={styles.recentActivity}>
        <h3 className={styles.subTitle}>Recent Activity</h3>
        <p className={styles.activityEmpty}>Detailed analytics view coming soon.</p>
      </div>
    </div>
  );
}
