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

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

type ActiveView = "home" | "report" | "achievements" | "community" | "chat";

// Bootstrap role cache with default roles (replaced by real API in production)
const DEFAULT_ROLES = [
  { id: "uni_001", name: "UNI", themeColorPalette: { primary: "#d4915e" }, sortOrder: 0 },
  { id: "csie_001", name: "CSIE", themeColorPalette: { primary: "#c47830" }, sortOrder: 1 },
  { id: "family_001", name: "FAMILY", themeColorPalette: { primary: "#e8a556" }, sortOrder: 2 },
  { id: "counseling_001", name: "諮商", themeColorPalette: { primary: "#8fbc8f" }, sortOrder: 3 },
  { id: "scholar_001", name: "學者", themeColorPalette: { primary: "#b08d6e" }, sortOrder: 4 },
];

function ThemeToggle() {
  const [dark, setDark] = useState(false);

  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.setAttribute("data-theme", next ? "dark" : "light");
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
  const { seedRoleCache } = useCoOSStore();

  useEffect(() => {
    // Seed default roles until real API is wired
    seedRoleCache(DEFAULT_ROLES);
    // Connect Tauri event bridge
    initTauriBridge();
  }, []);

  const goHome = useCallback(() => setActiveView("home"), []);

  const handleEnterChat = useCallback((roleId: string) => {
    setChatRoleId(roleId);
    setActiveView("chat");
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Don't intercept when typing in inputs
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement
      )
        return;

      if (activeView === "home") {
        if (e.key === "ArrowLeft") {
          e.preventDefault();
          setActiveView("report");
        } else if (e.key === "ArrowRight") {
          e.preventDefault();
          setActiveView("community");
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          setActiveView("achievements");
        }
      } else {
        if (e.key === "Escape") {
          e.preventDefault();
          goHome();
        }
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [activeView, goHome]);

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

      {/* Main content — always rendered underneath */}
      <main style={{ width: "100%", height: "100%", position: "relative" }}>
        <RoleDashboard onEnterChat={handleEnterChat} />
      </main>

      {/* Edge triggers — only shown when on home view */}
      {activeView === "home" && (
        <>
          <EdgeNavigationTrigger
            side="left"
            label="日報"
            arrowIcon="‹"
            onClick={() => setActiveView("report")}
          />
          <EdgeNavigationTrigger
            side="right"
            label="社群"
            arrowIcon="›"
            onClick={() => setActiveView("community")}
          />
          <EdgeNavigationTrigger
            side="top"
            label="成就"
            arrowIcon="▲"
            onClick={() => setActiveView("achievements")}
          />
        </>
      )}

      {/* Overlay pages with directional transitions */}
      <PageTransition
        isOpen={activeView === "report"}
        direction="left"
        onBack={goHome}
      >
        <DailyReportModule />
      </PageTransition>

      <PageTransition
        isOpen={activeView === "community"}
        direction="right"
        onBack={goHome}
      >
        <CommunityUI stubMode />
      </PageTransition>

      <PageTransition
        isOpen={activeView === "achievements"}
        direction="top"
        onBack={goHome}
      >
        <AchievementDisplay />
      </PageTransition>

      <PageTransition
        isOpen={activeView === "chat"}
        direction="bottom"
        onBack={goHome}
      >
        <MultiAgentHelper onWorkflowOpen={() => setWorkflowOpen(true)} />
      </PageTransition>

      {/* M3.6 Workflow Modal -- in-context, no page navigation */}
      <WorkflowModal open={workflowOpen} onClose={() => setWorkflowOpen(false)} />

      {/* Settings Modal */}
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
