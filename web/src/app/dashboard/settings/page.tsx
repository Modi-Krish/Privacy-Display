"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import styles from "./page.module.css";
import dashStyles from "../dashboard.module.css";

interface UserSetting {
  theme: string;
  overlay_mode: string;
}

interface BrowserState {
  pinned_tabs: string | null;
  allowed_domains: string | null;
  blocked_domains: string | null;
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSetting | null>(null);
  const [browserState, setBrowserState] = useState<BrowserState | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  useEffect(() => {
    async function fetchData() {
      try {
        const [settingsRes, browserRes] = await Promise.all([
          api.get("/api/dashboard/settings"),
          api.get("/api/dashboard/browser_state")
        ]);
        setSettings(settingsRes.data);
        setBrowserState(browserRes.data);
      } catch (err) {
        console.error(err);
        setError("Failed to load settings.");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!settings || !browserState) return;

    try {
      setSaving(true);
      setError("");
      setSuccessMsg("");

      await Promise.all([
        api.post("/api/dashboard/settings", settings),
        api.post("/api/dashboard/browser_state", browserState)
      ]);

      setSuccessMsg("Settings saved successfully.");
      setTimeout(() => setSuccessMsg(""), 3000);
    } catch (err) {
      console.error(err);
      setError("Failed to save settings.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className={dashStyles.loader}>Loading settings...</div>;

  return (
    <div className={`${dashStyles.card} ${dashStyles.animateFadeIn}`}>
      <h2 className={dashStyles.sectionTitle}>Account Settings</h2>
      <p className={dashStyles.sectionDesc}>
        Configure your REAI desktop application preferences. Changes sync instantly to your paired devices.
      </p>

      {error && <div className={dashStyles.error} style={{ marginBottom: "1rem" }}>{error}</div>}
      {successMsg && <div className={styles.successAlert}>{successMsg}</div>}

      <form onSubmit={handleSave} className={styles.formContainer}>
        {/* User Settings */}
        <div className={styles.formSection}>
          <h3 className={styles.sectionHeading}>Appearance & Behavior</h3>
          
          <div className={styles.inputGroup}>
            <label>Theme</label>
            <select 
              value={settings?.theme || "dark"}
              onChange={e => setSettings(s => s ? {...s, theme: e.target.value} : null)}
            >
              <option value="dark">Dark</option>
              <option value="light">Light</option>
              <option value="system">System Default</option>
            </select>
          </div>

          <div className={styles.inputGroup}>
            <label>Overlay Mode</label>
            <select 
              value={settings?.overlay_mode || "default"}
              onChange={e => setSettings(s => s ? {...s, overlay_mode: e.target.value} : null)}
            >
              <option value="default">Default</option>
              <option value="minimal">Minimal</option>
              <option value="stealth">Stealth Mode</option>
            </select>
          </div>
        </div>

        {/* Browser State */}
        <div className={styles.formSection}>
          <h3 className={styles.sectionHeading}>Browser State sync</h3>
          
          <div className={styles.inputGroup}>
            <label>Allowed Domains (comma separated)</label>
            <input 
              type="text" 
              placeholder="e.g., github.com, stackoverflow.com"
              value={browserState?.allowed_domains || ""}
              onChange={e => setBrowserState(b => b ? {...b, allowed_domains: e.target.value} : null)}
            />
          </div>

          <div className={styles.inputGroup}>
            <label>Blocked Domains (comma separated)</label>
            <input 
              type="text" 
              placeholder="e.g., reddit.com, twitter.com"
              value={browserState?.blocked_domains || ""}
              onChange={e => setBrowserState(b => b ? {...b, blocked_domains: e.target.value} : null)}
            />
          </div>
        </div>

        <div className={styles.formActions}>
          <button type="submit" className={styles.saveBtn} disabled={saving}>
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </form>
    </div>
  );
}
