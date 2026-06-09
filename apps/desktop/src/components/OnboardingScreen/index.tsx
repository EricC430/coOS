/**
 * Onboarding screen — shown only when no roles exist.
 *
 * Step 1 (welcome):  Google OAuth prompt (can be skipped)
 * Step 2 (create):   RoleDashboard with the carousel so the user creates first role via "+"
 *
 * While on the welcome step all other chrome (nav triggers, settings, theme toggle) is hidden.
 * After the first role is created `onRolesCreated()` is called to exit onboarding.
 */

import { useState, useEffect } from "react";
import { RoleDashboard } from "../m3_2_dashboard";

interface Props {
  onRolesCreated: () => Promise<void>;
}

interface GoogleStatus {
  linked: boolean;
  google_email?: string;
  display_name?: string;
}

type Step = "welcome" | "create";

export function OnboardingScreen({ onRolesCreated }: Props) {
  const [step, setStep] = useState<Step>("welcome");
  const [googleStatus, setGoogleStatus] = useState<GoogleStatus>({ linked: false });
  const [googleOAuthUrl, setGoogleOAuthUrl] = useState<string | null>(null);
  const [oauthStub, setOauthStub] = useState(false);
  const [linking, setLinking] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const [statusRes, urlRes] = await Promise.all([
          fetch("/api/auth/google/status"),
          fetch("/api/auth/google/url"),
        ]);
        if (statusRes.ok) setGoogleStatus(await statusRes.json());
        if (urlRes.ok) {
          const urlData = await urlRes.json();
          setGoogleOAuthUrl(urlData.url ?? null);
          setOauthStub(!!urlData.stub);
        }
      } catch {
        // non-fatal
      }
    }
    load();
  }, []);

  async function handleLinkGoogle() {
    if (!googleOAuthUrl) return;
    setLinking(true);
    try {
      // Open URL in system browser (Tauri shell plugin)
      const { open } = await import("@tauri-apps/plugin-shell");
      await open(googleOAuthUrl);
      // Poll status after a short delay — user completes OAuth in browser
      await new Promise((r) => setTimeout(r, 3000));
      const res = await fetch("/api/auth/google/status");
      if (res.ok) setGoogleStatus(await res.json());
    } catch {
      // Fallback: try window.open for web preview
      window.open(googleOAuthUrl, "_blank");
    } finally {
      setLinking(false);
    }
  }

  function handleSkip() {
    setStep("create");
  }

  // Called from RoleDashboard once user creates a role via the carousel "+"
  async function handleRoleCreated() {
    await onRolesCreated();
  }

  if (step === "create") {
    return (
      <div style={{ width: "100vw", height: "100vh", position: "relative", overflow: "hidden" }}>
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            padding: "16px 24px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 20,
            pointerEvents: "none",
          }}
        >
          <span style={{ fontSize: "0.85rem", opacity: 0.5 }}>
            點擊下方轉盤的「+」來建立你的第一個角色
          </span>
        </div>
        <RoleDashboard onEnterChat={() => {}} onFirstRoleCreated={handleRoleCreated} />
      </div>
    );
  }

  return (
    <div
      className="onboarding-screen"
      style={{
        width: "100vw",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg-main, #1a1a2e)",
        gap: "24px",
        padding: "40px",
      }}
    >
      {/* Logo / Title */}
      <div style={{ textAlign: "center", marginBottom: "8px" }}>
        <div style={{ fontSize: "3rem", marginBottom: "8px" }}>🌿</div>
        <h1 style={{ margin: 0, fontSize: "2rem", fontWeight: 700, letterSpacing: "-0.5px" }}>
          歡迎來到 coOS
        </h1>
        <p style={{ margin: "8px 0 0", opacity: 0.6, fontSize: "0.95rem" }}>
          個人目標管理系統 — 你的多角色生活助理
        </p>
      </div>

      {/* Google OAuth card */}
      <div
        className="glass-card"
        style={{
          maxWidth: 400,
          width: "100%",
          padding: "28px",
          borderRadius: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        <div>
          <h3 style={{ margin: "0 0 6px", fontSize: "1rem" }}>連結 Google 帳號</h3>
          <p style={{ margin: 0, opacity: 0.6, fontSize: "0.85rem", lineHeight: 1.5 }}>
            連結後可跨裝置同步進度、參與真人社群功能。<br />
            所有個人資料僅儲存你的 Google ID 與 Email，原始 Token 不被保存。
          </p>
        </div>

        {googleStatus.linked ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "10px",
              background: "rgba(52, 211, 153, 0.15)",
              border: "1px solid rgba(52, 211, 153, 0.3)",
              borderRadius: "8px",
              padding: "12px",
            }}
          >
            <span style={{ fontSize: "1.2rem" }}>✓</span>
            <div>
              <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>已連結 Google 帳號</div>
              <div style={{ opacity: 0.7, fontSize: "0.8rem" }}>
                {googleStatus.display_name} · {googleStatus.google_email}
              </div>
            </div>
          </div>
        ) : (
          <button
            className="primary-btn"
            onClick={handleLinkGoogle}
            disabled={oauthStub || linking}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "10px",
              padding: "12px 20px",
              borderRadius: "10px",
              fontSize: "0.95rem",
              opacity: oauthStub ? 0.5 : 1,
              cursor: oauthStub || linking ? "not-allowed" : "pointer",
            }}
          >
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844c-.209 1.125-.843 2.078-1.796 2.717v2.258h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
              <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332C2.438 15.983 5.482 18 9 18z" fill="#34A853"/>
              <path d="M3.964 10.71c-.18-.54-.282-1.117-.282-1.71s.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
              <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0 5.482 0 2.438 2.017.957 4.958L3.964 6.29C4.672 4.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
            </svg>
            {linking ? "等待授權中..." : "使用 Google 帳號連結"}
            {oauthStub && <span style={{ fontSize: "0.75rem", marginLeft: 4 }}>(未設定)</span>}
          </button>
        )}
      </div>

      {/* Skip / continue */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "10px" }}>
        <button
          className="settings-save-btn"
          onClick={() => setStep("create")}
          style={{ padding: "12px 40px", fontSize: "1rem", borderRadius: "10px" }}
        >
          {googleStatus.linked ? "開始使用 →" : "稍後再說，直接開始 →"}
        </button>
        {!googleStatus.linked && (
          <span
            onClick={handleSkip}
            style={{ fontSize: "0.8rem", opacity: 0.45, cursor: "pointer", textDecoration: "underline" }}
          >
            略過連結
          </span>
        )}
      </div>
    </div>
  );
}
