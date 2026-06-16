/**
 * coOS App Shell (Redesigned)
 *
 * Phase 5 UI layout — No bottom tab bar.
 * Navigation:
 *   - Left edge hover / ← key → Daily Report (slides from left)
 *   - Right edge hover / → key → Community (slides from right)
 *   - Top edge hover / ↑ key → Achievements (slides from top)
 *   - Click center carousel role → Chat Room (slides from bottom)
 *   - ESC / back button → return to home (slides back out)
 *
 * [M3.1] Zustand store bootstrapped here; Tauri bridge initialised on mount
 */

import { useEffect, useState, useCallback } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useCoOSStore } from "./stores/m3_1_global_store";
import { initTauriBridge } from "./stores/m3_1_tauri_bridge";
import { RoleDashboard } from "./components/m3_2_dashboard";
import { DailyReportModule } from "./components/m3_3_daily_report";
import { MultiAgentHelper } from "./components/m3_4_ai_helper";
import { AchievementDisplay } from "./components/m3_5_achievements";
import { CommunityUI } from "./components/m3_7_community";
import { WorkflowModal } from "./components/m3_6_workflow_modal";
import { EdgeNavigationTrigger } from "./components/EdgeNavigationTrigger";
import { PageTransition } from "./components/PageTransition";
import { SettingsModal } from "./components/SettingsModal";
import { OnboardingScreen } from "./components/OnboardingScreen";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

type ActiveView = "home" | "report" | "achievements" | "community" | "chat";

function ThemeToggle() {
  const [dark, setDark] = useState(() =>
    document.documentElement.getAttribute("data-theme") === "dark"
  );

  // Stay in sync when settings modal changes the theme
  useEffect(() => {
    const handler = (e: Event) => {
      setDark((e as CustomEvent<string>).detail === "dark");
    };
    window.addEventListener("coos:theme-changed", handler);
    return () => window.removeEventListener("coos:theme-changed", handler);
  }, []);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.setAttribute("data-theme", next ? "dark" : "light");
    window.dispatchEvent(new CustomEvent("coos:theme-changed", { detail: next ? "dark" : "light" }));
  };

  return (
    <button
      className="theme-toggle"
      onClick={toggle}
      data-testid="theme-toggle"
      aria-label="Toggle theme"
      title={dark ? "切換淺色模式" : "切換深色模式"}
    >
      {dark ? "☀" : "🌙"}
    </button>
  );
}

function AppContent() {
  const [activeView, setActiveView] = useState<ActiveView>("home");
  const [workflowOpen, setWorkflowOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [_chatRoleId, setChatRoleId] = useState<string | null>(null);
  const { currentRole, seedRoleCache, roleCache } = useCoOSStore();
  const [loading, setLoading] = useState(true);

  // isOnboarding = true while there are no roles at all
  const hasRoles = Object.keys(roleCache).length > 0;
  const isOnboarding = !loading && !hasRoles;

  const refreshRoles = useCallback(async () => {
    try {
      const res = await fetch("/api/m6_2/roles");
      if (res.ok) {
        const roles = await res.json();
        seedRoleCache(roles);
      }
    } catch (err) {
      console.error("Failed to load roles:", err);
    }
  }, [seedRoleCache]);

  useEffect(() => {
    async function init() {
      await refreshRoles();
      setLoading(false);
    }
    init();
    initTauriBridge();
  }, [refreshRoles]);

  const goHome = useCallback(() => setActiveView("home"), []);

  const handleEnterChat = useCallback((roleId: string) => {
    setChatRoleId(roleId);
    setActiveView("chat");
  }, []);

  // Keyboard navigation — disabled during onboarding
  useEffect(() => {
    if (isOnboarding) return;
    const handler = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      )
        return;

      if (activeView === "home") {
        if (e.key === "ArrowLeft") { e.preventDefault(); setActiveView("report"); }
        else if (e.key === "ArrowRight") { e.preventDefault(); setActiveView("community"); }
        else if (e.key === "ArrowUp") { e.preventDefault(); setActiveView("achievements"); }
      } else {
        if (e.key === "Escape") { e.preventDefault(); goHome(); }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [activeView, goHome, isOnboarding]);

  if (loading) {
    return <div className="loading-screen">coOS Loading...</div>;
  }

  // Onboarding: full-screen lock — no nav, no settings, no theme toggle
  if (isOnboarding) {
    return (
      <OnboardingScreen
        onRolesCreated={async () => {
          await refreshRoles();
        }}
      />
    );
  }

  return (
    <div style={{ width: "100vw", height: "100vh", position: "relative", overflow: "hidden" }}>
      {/* Theme toggle */}
      <ThemeToggle />

      {/* Settings toggle */}
      <button
        className="settings-toggle"
        onClick={() => setSettingsOpen(true)}
        aria-label="Open settings"
        title="系統與隱私設定"
      >
        ⚙️
      </button>

      {/* Main content */}
      <main style={{ width: "100%", height: "100%", position: "relative" }}>
        <RoleDashboard
          onEnterChat={handleEnterChat}
          onFirstRoleCreated={refreshRoles}
        />
      </main>

      {/* Edge triggers — only shown when on home view */}
      {activeView === "home" && (
        <>
          <EdgeNavigationTrigger side="left" label="日報" arrowIcon="‹" onClick={() => setActiveView("report")} />
          <EdgeNavigationTrigger side="right" label="社群" arrowIcon="›" onClick={() => setActiveView("community")} />
          <EdgeNavigationTrigger side="top" label="成就" arrowIcon="▲" onClick={() => setActiveView("achievements")} />
        </>
      )}

      {/* Overlay pages with directional transitions */}
      <PageTransition isOpen={activeView === "report"} direction="left" onBack={goHome}>
        <DailyReportModule />
      </PageTransition>

      <PageTransition isOpen={activeView === "community"} direction="right" onBack={goHome}>
        <CommunityUI stubMode />
      </PageTransition>

      <PageTransition isOpen={activeView === "achievements"} direction="top" onBack={goHome}>
        <AchievementDisplay />
      </PageTransition>

      <PageTransition isOpen={activeView === "chat"} direction="bottom" onBack={goHome}>
        <MultiAgentHelper onWorkflowOpen={() => setWorkflowOpen(true)} />
      </PageTransition>

      <WorkflowModal open={workflowOpen} onClose={() => setWorkflowOpen(false)} />
      <SettingsModal isOpen={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppContent />
    </QueryClientProvider>
  );
}
