"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import styles from "./page.module.css";
import dashStyles from "../dashboard.module.css";

interface Device {
  id: string;
  device_id: string;
  device_name: string | null;
  last_seen: string | null;
  created_at: string;
  session_count: number;
}

export default function DevicesPage() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function fetchDevices() {
      try {
        setLoading(true);
        const { data } = await api.get("/api/dashboard/devices");
        setDevices(data);
      } catch (err: unknown) {
        console.error(err);
        setError("Failed to load paired devices.");
      } finally {
        setLoading(false);
      }
    }
    fetchDevices();
  }, []);

  const handleRevoke = async (deviceId: string) => {
    if (!confirm("Are you sure you want to revoke access for this device? It will be logged out immediately.")) return;
    
    try {
      await api.delete(`/api/auth/devices/${deviceId}`);
      setDevices(devices.filter(d => d.device_id !== deviceId));
    } catch (err) {
      console.error("Failed to revoke device", err);
      alert("Failed to revoke device.");
    }
  };

  if (loading && devices.length === 0) return <div className={dashStyles.loader}>Loading devices...</div>;
  if (error) return <div className={dashStyles.error}>{error}</div>;

  return (
    <div className={`${dashStyles.card} ${dashStyles.animateFadeIn}`}>
      <h2 className={dashStyles.sectionTitle}>Paired Devices</h2>
      <p className={dashStyles.sectionDesc}>
        Manage the desktop applications connected to your REAI account.
      </p>

      {devices.length === 0 ? (
        <div className={styles.emptyState}>
          <span className="material-symbols-outlined" style={{ fontSize: 48, marginBottom: "1rem", color: "#3f3f46" }}>devices</span>
          <p>No paired devices found.</p>
          <span style={{ fontSize: "0.85rem" }}>Login via the REAI desktop app to pair a new device.</span>
        </div>
      ) : (
        <div className={styles.deviceList}>
          {devices.map(device => (
            <div key={device.id} className={styles.deviceItem}>
              <div className={styles.deviceIcon}>
                <span className="material-symbols-outlined">desktop_windows</span>
              </div>
              <div className={styles.deviceInfo}>
                <h3 className={styles.deviceName}>{device.device_name || "Unknown Device"}</h3>
                <p className={styles.deviceMeta}>
                  ID: {device.device_id.substring(0, 8)}... • Paired on {new Date(device.created_at).toLocaleDateString()}
                </p>
                {device.last_seen && (
                  <p className={styles.deviceMeta}>
                    Last active: {new Date(device.last_seen).toLocaleString()}
                  </p>
                )}
              </div>
              <button className={styles.revokeBtn} onClick={() => handleRevoke(device.device_id)}>
                Revoke Access
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
