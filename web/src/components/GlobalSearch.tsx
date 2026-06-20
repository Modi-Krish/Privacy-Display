"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import styles from "./GlobalSearch.module.css";

interface SearchResults {
  questions: Array<{ id: string; text: string; session_id: string }>;
  answers: Array<{ id: string; text: string; session_id: string }>;
  resumes: Array<{ id: string; file_name: string }>;
}

export default function GlobalSearch() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    const performSearch = async (q: string) => {
      setLoading(true);
      try {
        const { data } = await api.get(`/api/dashboard/search?q=${encodeURIComponent(q)}`);
        setResults(data);
        setOpen(true);
      } catch (err) {
        console.error("Search failed", err);
      } finally {
        setLoading(false);
      }
    };

    const delayDebounceFn = setTimeout(() => {
      if (query.trim().length >= 2) {
        performSearch(query);
      } else {
        setResults(null);
      }
    }, 400);

    return () => clearTimeout(delayDebounceFn);
  }, [query]);



  const hasResults = results && (
    results.questions.length > 0 ||
    results.answers.length > 0 ||
    results.resumes.length > 0
  );

  return (
    <div className={styles.searchContainer} ref={containerRef}>
      <div className={styles.inputWrapper}>
        <span className="material-symbols-outlined">search</span>
        <input
          type="text"
          placeholder="Search questions, answers, resumes..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => {
            if (query.trim().length >= 2) setOpen(true);
          }}
          className={styles.searchInput}
        />
        {loading && <div className={styles.spinner}></div>}
      </div>

      {open && query.trim().length >= 2 && (
        <div className={styles.dropdown}>
          {!loading && !hasResults ? (
            <div className={styles.noResults}>No results found for &quot;{query}&quot;</div>
          ) : null}

          {results?.questions.length ? (
            <div className={styles.resultGroup}>
              <div className={styles.groupHeader}>Questions</div>
              {results.questions.map(q => (
                <Link 
                  href={`/dashboard/sessions/details?id=${q.session_id}`} 
                  key={`q-${q.id}`} 
                  className={styles.resultItem}
                  onClick={() => setOpen(false)}
                >
                  <span className="material-symbols-outlined text-sm">help</span>
                  <div className={styles.resultText}>{q.text}</div>
                </Link>
              ))}
            </div>
          ) : null}

          {results?.answers.length ? (
            <div className={styles.resultGroup}>
              <div className={styles.groupHeader}>Answers</div>
              {results.answers.map(a => (
                <Link 
                  href={`/dashboard/sessions/details?id=${a.session_id}`} 
                  key={`a-${a.id}`} 
                  className={styles.resultItem}
                  onClick={() => setOpen(false)}
                >
                  <span className="material-symbols-outlined text-sm">auto_awesome</span>
                  <div className={styles.resultText}>{a.text}</div>
                </Link>
              ))}
            </div>
          ) : null}

          {results?.resumes.length ? (
            <div className={styles.resultGroup}>
              <div className={styles.groupHeader}>Resumes</div>
              {results.resumes.map(r => (
                <Link 
                  href={`/dashboard/resumes`} 
                  key={`r-${r.id}`} 
                  className={styles.resultItem}
                  onClick={() => setOpen(false)}
                >
                  <span className="material-symbols-outlined text-sm">description</span>
                  <div className={styles.resultText}>{r.file_name}</div>
                </Link>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
