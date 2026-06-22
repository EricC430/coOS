/**
 * M3.1 -- Global State & Layout
 *
 * SPEC: docs/modules/M3_1_global_state_layout_SPEC.md
 * Research: [R08 SS1 Cognitive Load] [R09 SS4 SDT]
 * Risk mitigation: RISK-06 (cross-role leak prevention in switchRole)
 */

import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";

export interface Role {
  id: string;
  name: string;
  themeColorPalette: Record<string, string>;
  sortOrder?: number;
  avatarUrl?: string;
  slug?: string;
}

export interface Expert {
  id: string;
  expertName: string;
  personalityPrompt?: string;
  trustLevel: number;
  title?: string;
  domain?: string;
  avatarUrl?: string;
  isActive?: boolean;
}

// [FIX-04] Lightweight type for SSE project events stored in global state
export interface ProjectTagEvent {
  type: string;
  project_id?: string;
  project_name?: string;
  goal?: string;
  expert_name?: string;
  text?: string;
  title?: string;
  deadline?: string;
  source?: string;
  intention?: string;
  role_id?: string;
}

export interface CoOSState {
  currentRole: Role | null;
  xpBalance: number;
  level: number;
  activeExpert: Expert | null;
  roleCache: Record<string, Role>;
  expertCache: Record<string, Expert>;
  isRoleTransitioning: boolean;
  // [FIX-04] Project tags: SSE project events persisted by threadId
  projectTags: Record<string, ProjectTagEvent[]>;
  activeCommunityId: string | null;

  // Actions
  switchRole: (roleId: string) => void;
  applyXPGrant: (payload: { amount: number; new_total: number }) => void;
  setActiveExpert: (expertId: string) => void;
  seedRoleCache: (roles: Role[]) => void;
  seedExpertCache: (experts: Expert[]) => void;
  setRoleTransitioning: (v: boolean) => void;
  addProjectTag: (threadId: string, event: ProjectTagEvent) => void;
  clearProjectTags: (threadId: string) => void;
  setActiveCommunity: (id: string | null) => void;
}

// [R08 SS1] Level formula: floor(sqrt(xp/100)), capped at 99
function computeLevel(xp: number): number {
  if (xp < 0) return 1;
  return Math.max(1, Math.min(99, Math.floor(Math.sqrt(xp / 100))));
}

export const useCoOSStore = create<CoOSState>()(
  subscribeWithSelector((set, get) => ({
    currentRole: null,
    xpBalance: 0,
    level: 1,
    activeExpert: null,
    roleCache: {},
    expertCache: {},
    isRoleTransitioning: false,
    projectTags: {},
    activeCommunityId: null,

    switchRole: (roleId) => {
      const { currentRole, roleCache } = get();
      // [RISK-06] Same role -- skip to avoid unnecessary M4.3 sandbox reset
      if (currentRole?.id === roleId) return;
      const role = roleCache[roleId] ?? null;
      if (!role) {
        console.warn(`[M3.1] switchRole: role ${roleId} not in cache`);
        return;
      }
      // [RISK-06] Clear expert context on role switch to prevent cross-role leakage
      set({ currentRole: role, isRoleTransitioning: true, expertCache: {}, activeExpert: null });
    },

    applyXPGrant: ({ new_total }) => {
      const level = computeLevel(new_total);
      set({ xpBalance: new_total, level });
    },

    setActiveExpert: (expertId) => {
      // __tool__ is the built-in tool AI — not stored in expertCache
      if (expertId === "__tool__") {
        set({ activeExpert: { id: "__tool__", expertName: "工具型 AI", trustLevel: 5 } });
        return;
      }
      const expert = get().expertCache[expertId.toLowerCase()] ?? null;
      if (!expert) {
        console.warn(`[M3.1] setActiveExpert: expert ${expertId} not in cache`);
        return;
      }
      set({ activeExpert: expert });
    },

    seedRoleCache: (roles) => {
      const roleCache: Record<string, Role> = {};
      for (const r of roles) roleCache[r.id] = r;
      
      // Handle empty roles state gracefully
      if (roles.length === 0) {
        set({ roleCache, currentRole: null });
        return;
      }

      const currentRole =
        roles.find((r) => r.sortOrder === 0) ?? roles[0] ?? null;
      set({ roleCache, currentRole });
    },

    seedExpertCache: (experts) => {
      const expertCache: Record<string, Expert> = {};
      for (const e of experts) expertCache[e.id.toLowerCase()] = e;
      set({ expertCache });
    },

    setRoleTransitioning: (v) => set({ isRoleTransitioning: v }),

    // [FIX-04] Add a project tag event for a given thread
    addProjectTag: (threadId, event) => {
      const prev = get().projectTags;
      const existing = prev[threadId] ?? [];
      // Deduplicate: skip if same type+project_name already recorded
      const isDupe = existing.some(
        (e) => e.type === event.type && e.project_name === event.project_name
      );
      if (isDupe) return;
      set({ projectTags: { ...prev, [threadId]: [...existing, event] } });
    },

    // [FIX-04] Clear tags for a thread (e.g. on explicit role switch)
    clearProjectTags: (threadId) => {
      const prev = get().projectTags;
      const next = { ...prev };
      delete next[threadId];
      set({ projectTags: next });
    },

    setActiveCommunity: (id) => set({ activeCommunityId: id }),
  }))
);
