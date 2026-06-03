/**
 * M3.2 -- Role Dashboard
 *
 * SPEC: docs/modules/M3_2_role_dashboard_SPEC.md
 * Research: [R08 SS1 SS5] [R09 SS4 SDT] [R06 SS2]
 * Risk mitigation: RISK-04, RISK-06
 */

import React, { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useCoOSStore } from "../../stores/m3_1_global_store";
import { RoleFocusCarouselDock } from "./RoleFocusCarouselDock";
import { TransitionBackground } from "./TransitionBackground";
import { ContextHeaderAggregator } from "./ContextHeaderAggregator";
import { ConsistencyHeatmap } from "./ConsistencyHeatmap";
import type { HeatmapEntry } from "./ConsistencyHeatmap";

async function fetchHeatmapData(roleId: string): Promise<HeatmapEntry[]> {
  const res = await fetch(`/api/m6_4/heatmap?role_id=${roleId}`);
  if (!res.ok) return [];
  return res.json();
}

export function RoleDashboard() {
  const { currentRole, roleCache, switchRole, setRoleTransitioning } = useCoOSStore();
  const roles = Object.values(roleCache);

  const { data: heatmapData = [] } = useQuery<HeatmapEntry[]>({
    queryKey: ["heatmap", currentRole?.id],
    queryFn: () => fetchHeatmapData(currentRole!.id),
    enabled: !!currentRole,
  });

  const handleSnap = (roleId: string) => {
    // [RISK-06] switchRole triggers M4.3 sandbox reset via isRoleTransitioning
    switchRole(roleId);
  };

  // Clear transitioning flag after animation settles
  const handleTransitionEnd = () => setRoleTransitioning(false);

  if (!currentRole) {
    return (
      <div className="flex items-center justify-center h-full text-gray-400">
        載入角色中...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full relative">
      <TransitionBackground
        roleId={currentRole.id}
        palette={currentRole.themeColorPalette}
        onTransitionEnd={handleTransitionEnd}
      />

      {/* Context Header */}
      <ContextHeaderAggregator
        roleId={currentRole.id}
        roleName={currentRole.name}
      />

      {/* Dashboard Body */}
      <div className="flex-1 overflow-y-auto px-4 py-2">
        {roles.length === 0 ? (
          <div
            data-testid="dashboard-empty-state"
            className="text-center text-gray-400 mt-16"
          >
            在 AI 幫手中描述你的目標，Dashboard 將自動填入
          </div>
        ) : (
          <ConsistencyHeatmap data={heatmapData} />
        )}
      </div>

      {/* Role Carousel Dock */}
      <div className="border-t border-white/10 pb-2">
        <RoleFocusCarouselDock
          roles={roles}
          activeRoleId={currentRole.id}
          onRoleSnap={handleSnap}
        />
      </div>
    </div>
  );
}
