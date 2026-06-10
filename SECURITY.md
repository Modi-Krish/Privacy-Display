# Security Policy

We take the security of the **Real-Time AI Interview Copilot (REAI)** seriously. This document outlines our supported versions, reporting processes, and threat model guidelines to protect user data and systems.

---

## 🛡️ Supported Versions

We actively maintain and provide security updates for the following versions:

| Version | Supported | Security Hotfixes |
| ------- | :---: | :---: |
| **v1.x.x** (Latest) | :white_check_mark: | Active |
| **v0.x.x** (Beta)   | :x: | None |

---

## 🕵️ Threat Model & Security Controls

REAI is built with a **security-first local design** to minimize threat exposure:
1. **Local Model execution**: Speech-to-Text (`faster-whisper`) and text embedding (`sentence-transformers`) run entirely locally. No audio recordings or raw resume contents are sent to external speech-transcription APIs.
2. **Dynamic Header Injection**: User keys (e.g., Gemini API keys) are stored locally in the frontend browser context (`localStorage`) and injected into requests at the protocol layer via transient HTTP headers rather than being stored statically in backend configuration files.
3. **Electron IPC Sandbox**: The desktop app runs with `contextIsolation: true`, `nodeIntegration: false`, and `sandbox: true`. No Node.js APIs are directly exposed to the renderer context. All window parameters (anti-screen share, skip taskbar) are bridged using a strictly typed, minimal `contextBridge` layer to mitigate Remote Code Execution (RCE) risks.
4. **Cookie Protection**: Authentication is managed using HTTP-only, secure session cookies to prevent Cross-Site Scripting (XSS) token interception.

---

## 🚨 Reporting a Vulnerability

If you identify a security vulnerability in this project, **please do not open a public issue or pull request**. Public disclosure risks exposing active systems before they can be secured.

### Reporting Channels
Please submit all security disclosures by emailing **`security@reai-copilot.org`** (or contact the lead maintainer directly). 

To help us triage the issue quickly, please include:
- **Impact Description**: A summary of what an attacker could accomplish (e.g. CSRF, token leaks, local privilege escalation).
- **Reproduction Steps**: A detailed step-by-step guide or proof-of-concept (PoC) script.
- **Environment**: Details on OS version, Node/Python runtime versions, and active configurations (Docker vs. local dev).

---

## 🤝 Responsible Disclosure & Response Timeline

We adhere to standard responsible disclosure principles. Upon receiving a report:
1. **Acknowledgment**: We will acknowledge receipt of your vulnerability report within **24 hours**.
2. **Validation**: We will investigate and validate the report within **48 hours**, sharing a status update and preliminary fix timeline with you.
3. **Remediation**: We aim to release a patched release version within **7 days** of verification, unless complexity warrants a coordinated release schedule.
4. **Attribution**: Once patched, we will gladly credit you in our changelog and release notes (unless you request anonymity).
