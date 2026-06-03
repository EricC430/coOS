/**
 * coOS App Shell
 *
 * Phase 5 UI layout: 5-tab navigation wrapping M3.1~M3.7 modules
 * [M3.1] Zustand store bootstrapped here; Tauri bridge initialised on mount
 */

import React, { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useCoOSStore } from "./stores/m3_1_global_store";
import { initTauriBridge } from "./stores/m3_1_tauri_bridge";
import { RoleDashboard } from "./components/m3_2_dashboard";
import { DailyReportModule } from "./components/m3_3_daily_report";
import { MultiAgentHelper } from "./components/m3_4_ai_helper";
import { AchievementDisplay } from "./components/m3_5_achievements";
import { CommunityUI } from "./components/m3_7_community";
import { WorkflowModal } from "./components/m3_6_workflow_modal";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
});

type Tab = "dashboard" | "report" | "helper" | "achievements" | "community";

const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "dashboard", label: "儀表板", icon: "🏠" },
  { id: "report", label: "日報", icon: "📋" },
  { id: "helper", label: "AI 幫手", icon: "🤖" },
  { id: "achievements", label: "成就", icon: "🎖" },
  { id: "community", label: "社群", icon: "🌐" },
];

// Bootstrap role cache with default roles (replaced by real API in production)
const DEFAULT_ROLES = [
  { id: "uni_001", name: "UNI", themeColorPalette: { primary: "#6366f1" }, sortOrder: 0 },
  { id: "csie_001", name: "CSIE", themeColorPalette: { primary: "#3b82f6" }, sortOrder: 1 },
  { id: "family_001", name: "FAMILY", themeColorPalette: { primary: "#f59e0b" }, sortOrder: 2 },
  { id: "counseling_001", name: "諮商", themeColorPalette: { primary: "#10b981" }, sortOrder: 3 },
  { id: "scholar_001", name: "學者", themeColorPalette: { primary: "#8b5cf6" }, sortOrder: 4 },
];

function AppContent() {
  const [activeTab, setActiveTab] = useState<Tab>("dashboard");
  const [workflowOpen, setWorkflowOpen] = useState(false);
  const { seedRoleCache } = useCoOSStore();

  useEffect(() => {
    // Seed default roles until real API is wired
    seedRoleCache(DEFAULT_ROLES);
    // Connect Tauri event bridge
    initTauriBridge();
  }, []);

  return (
    <div className="flex flex-col h-screen bg-gray-50 text-gray-800 font-sans">
      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        {activeTab === "dashboard" && <RoleDashboard />}
        {activeTab === "report" && <DailyReportModule />}
        {activeTab === "helper" && (
          <MultiAgentHelper onWorkflowOpen={() => setWorkflowOpen(true)} />
        )}
        {activeTab === "achievements" && <AchievementDisplay />}
        {activeTab === "community" && <CommunityUI stubMode />}
      </main>

      {/* Bottom tab bar */}
      <nav className="flex border-t bg-white">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            data-testid={`tab-${tab.id}`}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex flex-col items-center py-2 text-xs transition-colors ${
              activeTab === tab.id
                ? "text-indigo-600 font-semibold"
                : "text-gray-400 hover:text-gray-600"
            }`}
          >
            <span className="text-lg">{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </nav>

      {/* M3.6 Workflow Modal -- in-context, no page navigation */}
      <WorkflowModal open={workflowOpen} onClose={() => setWorkflowOpen(false)} />
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
