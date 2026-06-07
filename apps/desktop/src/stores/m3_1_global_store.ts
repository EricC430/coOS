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

export interface CoOSState {
  currentRole: Role | null;
  xpBalance: number;
  level: number;
  activeExpert: Expert | null;
  roleCache: Record<string, Role>;
  expertCache: Record<string, Expert>;
  isRoleTransitioning: boolean;

  // Actions
  switchRole: (roleId: string) => void;
  applyXPGrant: (payload: { amount: number; new_total: number }) => void;
  setActiveExpert: (expertId: string) => void;
  seedRoleCache: (roles: Role[]) => void;
  seedExpertCache: (experts: Expert[]) => void;
  setRoleTransitioning: (v: boolean) => void;
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

    switchRole: (roleId) => {
      const { currentRole, roleCache } = get();
      // [RISK-06] Same role -- skip to avoid unnecessary M4.3 sandbox reset
      if (currentRole?.id === roleId) return;
      const role = roleCache[roleId] ?? null;
      if (!role) {
        console.warn(`[M3.1] switchRole: role ${roleId} not in cache`);
        return;
      }
      set({ currentRole: role, isRoleTransitioning: true });
    },

    applyXPGrant: ({ new_total }) => {
      const level = computeLevel(new_total);
      set({ xpBalance: new_total, level });
    },

    setActiveExpert: (expertId) => {
      const expert = get().expertCache[expertId] ?? null;
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
      for (const e of experts) expertCache[e.id] = e;
      set({ expertCache });
    },

    setRoleTransitioning: (v) => set({ isRoleTransitioning: v }),
  }))
);
