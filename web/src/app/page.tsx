"use client";

import { useState, useEffect } from "react";
import { signInWithPopup, GoogleAuthProvider, onAuthStateChanged, User } from "firebase/auth";
import { auth } from "@/lib/firebase";
import axios from "axios";

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [pairingCode, setPairingCode] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (currentUser) => {
      setUser(currentUser);
      if (currentUser) {
        await handleBackendLogin(currentUser);
      }
    });
    return () => unsubscribe();
  }, []);

  const handleBackendLogin = async (currentUser: User) => {
    setLoading(true);
    setError(null);
    try {
      const token = await currentUser.getIdToken();
      // Ensure user exists in backend
      await axios.post(`${API_URL}/api/auth/web/login`, {
        firebase_token: token,
      });
      // Generate pairing code
      const { data } = await axios.post(`${API_URL}/api/auth/web/pair/generate`, {
        firebase_token: token,
      });
      setPairingCode(data.code);
      setExpiresAt(new Date(data.expires_at).toLocaleTimeString());
    } catch (err: any) {
      console.error(err);
      setError("Failed to communicate with backend. Make sure it is running.");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    try {
      const provider = new GoogleAuthProvider();
      await signInWithPopup(auth, provider);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleSignOut = () => {
    auth.signOut();
    setUser(null);
    setPairingCode(null);
    setExpiresAt(null);
  };

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100 flex flex-col items-center justify-center p-6 font-sans">
      <div className="max-w-md w-full bg-neutral-900 border border-neutral-800 rounded-2xl p-8 shadow-2xl text-center">
        <h1 className="text-3xl font-bold mb-2 tracking-tight">REAI Portal</h1>
        <p className="text-neutral-400 mb-8">Authenticate your desktop device</p>

        {error && (
          <div className="bg-red-900/50 border border-red-500 text-red-200 p-3 rounded-lg mb-6 text-sm">
            {error}
          </div>
        )}

        {!user ? (
          <button
            onClick={handleGoogleSignIn}
            className="w-full flex items-center justify-center gap-3 bg-white text-black py-3 px-4 rounded-xl font-medium hover:bg-neutral-200 transition-colors"
          >
            <svg viewBox="0 0 24 24" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
            </svg>
            Continue with Google
          </button>
        ) : (
          <div className="flex flex-col items-center">
            {loading ? (
              <div className="animate-pulse flex flex-col items-center">
                <div className="h-8 w-8 border-4 border-neutral-600 border-t-white rounded-full animate-spin mb-4"></div>
                <p>Generating pairing code...</p>
              </div>
            ) : pairingCode ? (
              <>
                <p className="text-sm text-neutral-400 mb-2">Your Pairing Code</p>
                <div className="bg-neutral-950 border border-neutral-800 rounded-xl px-8 py-6 mb-4 w-full">
                  <span className="text-5xl font-mono tracking-widest text-white">{pairingCode}</span>
                </div>
                <p className="text-sm text-orange-400 mb-8">
                  Expires at {expiresAt}
                </p>
                <button
                  onClick={handleSignOut}
                  className="text-sm text-neutral-500 hover:text-white transition-colors"
                >
                  Sign out
                </button>
              </>
            ) : null}
          </div>
        )}
      </div>
    </main>
  );
}
