"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { onAuthStateChanged, User } from "firebase/auth";
import { auth } from "@/lib/firebase";
import GlobalSearch from "@/components/GlobalSearch";
import styles from "./dashboard.module.css";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      if (!currentUser) {
        router.push("/");
      } else {
        setUser(currentUser);
      }
      setLoading(false);
    });
    return () => unsubscribe();
  }, [router]);

  if (loading) {
    return (
      <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", background: "#0f0f13", color: "white" }}>
        Loading REAI Workspace...
      </div>
    );
  }

  if (!user) return null;

  const navItems = [
    { name: "Overview", path: "/dashboard", icon: "grid_view" },
    { name: "Sessions", path: "/dashboard/sessions", icon: "history" },
    { name: "Resumes", path: "/dashboard/resumes", icon: "description" },
    { name: "Devices", path: "/dashboard/devices", icon: "devices" },
    { name: "Settings", path: "/dashboard/settings", icon: "settings" },
  ];

  const pageTitle = navItems.find((item) => item.path === pathname)?.name || "Dashboard";

  return (
    <div className={styles.dashboardContainer}>
      <aside className={styles.sidebar}>
        <Link href="/dashboard" className={styles.brand}>
          <div className={styles.brandLogo}>R</div>
          <span className={styles.brandText}>REAI Workspace</span>
        </Link>

        <nav className={styles.navGroup}>
          <div className={styles.navGroupTitle}>Menu</div>
          {navItems.map((item) => {
            const isActive = pathname === item.path;
            return (
              <Link
                key={item.path}
                href={item.path}
                className={`${styles.navLink} ${isActive ? styles.navLinkActive : ""}`}
              >
                {/* Material Symbols placeholder - we'll add the link in layout or globals */}
                <span className="material-symbols-outlined" style={{ fontSize: "20px" }}>{item.icon}</span>
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className={styles.userProfile} onClick={() => auth.signOut()}>
          <img src={user.photoURL || `https://ui-avatars.com/api/?name=${user.email}`} alt="Avatar" className={styles.userAvatar} />
          <div className={styles.userInfo}>
            <span className={styles.userName}>{user.displayName || "User"}</span>
            <span className={styles.userEmail}>{user.email}</span>
          </div>
        </div>
      </aside>

      <main className={styles.mainContent}>
        <header className={styles.topBar}>
          <h1 className={styles.pageTitle}>{pageTitle}</h1>
          <div className={styles.topActions}>
             <GlobalSearch />
          </div>
        </header>
        
        <div className={styles.contentBody}>
          {children}
        </div>
      </main>
    </div>
  );
}
