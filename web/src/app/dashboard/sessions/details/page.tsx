"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import styles from "./page.module.css";
import dashStyles from "../../dashboard.module.css";

interface QAPair {
  id: string;
  question_text: string;
  category: string;
  created_at: string;
  answer: string | null;
  confidence_score: number | null;
}

interface TimelineEvent {
  id: string;
  type: string;
  content: string;
  created_at: string;
}

interface SessionData {
  session: {
    id: string;
    started_at: string;
    ended_at: string | null;
  };
  timeline: TimelineEvent[];
  qa_pairs: QAPair[];
}

function SessionDetailsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [data, setData] = useState<SessionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const sessionId = searchParams.get("id");

  useEffect(() => {
    async function fetchSessionDetails() {
      try {
        const res = await api.get(`/api/dashboard/sessions/${sessionId}`);
        setData(res.data);
      } catch (err: unknown) {
        console.error(err);
        setError("Failed to load session details.");
      } finally {
        setLoading(false);
      }
    }
    if (sessionId) fetchSessionDetails();
  }, [sessionId]);

  if (loading) return <div className={dashStyles.loader}>Loading timeline...</div>;
  if (error) return <div className={dashStyles.error}>{error}</div>;
  if (!data) return null;

  const { session, qa_pairs } = data;
  const startDate = new Date(session.started_at);

  return (
    <div className={dashStyles.animateFadeIn}>
      <button className={styles.backBtn} onClick={() => router.push('/dashboard/sessions')}>
        <span className="material-symbols-outlined">arrow_back</span> Back to Sessions
      </button>

      <div className={dashStyles.card} style={{ marginBottom: "2rem" }}>
        <h2 className={dashStyles.sectionTitle}>Session Timeline</h2>
        <p className={dashStyles.sectionDesc}>
          {startDate.toLocaleDateString()} at {startDate.toLocaleTimeString()}
        </p>

        {qa_pairs.length === 0 ? (
          <p style={{ color: "#a1a1aa" }}>No questions recorded in this session.</p>
        ) : (
          <div className={styles.timelineContainer}>
            {qa_pairs.map((qa, index) => (
              <div key={qa.id} className={styles.timelineItem}>
                <div className={styles.timelineMarker}>
                  <div className={styles.timelineDot}></div>
                  {index !== qa_pairs.length - 1 && <div className={styles.timelineLine}></div>}
                </div>
                
                <div className={styles.timelineContent}>
                  <div className={styles.qaCard}>
                    <div className={styles.qHeader}>
                      <span className={styles.categoryBadge}>{qa.category || "General"}</span>
                      <span className={styles.timeLabel}>
                        {new Date(qa.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                    <h3 className={styles.questionText}>{qa.question_text}</h3>
                    
                    {qa.answer ? (
                      <div className={styles.answerSection}>
                        <div className={styles.answerHeader}>
                          <span className="material-symbols-outlined text-sm">auto_awesome</span> Suggested Answer
                          {qa.confidence_score && (
                            <span className={styles.confidenceLabel}>
                              {Math.round(qa.confidence_score * 100)}% Confidence
                            </span>
                          )}
                        </div>
                        <p className={styles.answerText}>{qa.answer}</p>
                      </div>
                    ) : (
                      <div className={styles.noAnswer}>No answer generated.</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function SessionDetailsPage() {
  return (
    <Suspense fallback={<div className={dashStyles.loader}>Loading...</div>}>
      <SessionDetailsContent />
    </Suspense>
  );
}
