/**
 * M3.2 -- Role Dashboard (Restructured)
 *
 * SPEC: docs/modules/M3_2_role_dashboard_SPEC.md
 * Research: [R08 SS1 SS5] [R09 SS4 SDT] [R06 SS2]
 * Risk mitigation: RISK-04, RISK-06
 *
 * Layout:
 *   Top 75%: TransitionBackground + ContextHeader (with Dashboard & heatmap)
 *   Bottom 25%: Coverflow Rotary Wheel Carousel
 */

import { useQuery } from "@tanstack/react-query";
import { useCoOSStore } from "../../stores/m3_1_global_store";
import { RoleFocusCarouselDock } from "./RoleFocusCarouselDock";
import { TransitionBackground } from "./TransitionBackground";
import type { ThemePalette } from "./TransitionBackground/useColorTemperature";
import { ContextHeaderAggregator } from "./ContextHeaderAggregator";
import type { HeatmapEntry } from "./ConsistencyHeatmap";

async function fetchHeatmapData(roleId: string): Promise<HeatmapEntry[]> {
  const res = await fetch(`/api/m6_4/heatmap?role_id=${roleId}`);
  if (!res.ok) return [];
  return res.json();
}

interface Props {
  onEnterChat?: (roleId: string) => void;
}

export function RoleDashboard({ onEnterChat }: Props) {
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

  const handleCenterClick = (roleId: string) => {
    onEnterChat?.(roleId);
  };

  const handleAddRole = () => {
    console.log("[M3.2] Add new role triggered — placeholder");
  };

  if (!currentRole) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          height: "100%",
          color: "var(--text-muted)",
          fontSize: 16,
        }}
      >
        載入角色中...
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", position: "relative" }}>
      <TransitionBackground
        roleId={currentRole.id}
        palette={currentRole.themeColorPalette as unknown as ThemePalette}
        onTransitionEnd={handleTransitionEnd}
      />

      {/* Top 75%: Context Header (Role title + Project/Promises/Goal + Dashboard) */}
      <div style={{ flex: 3, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {roles.length === 0 ? (
          <div
            data-testid="dashboard-empty-state"
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "var(--text-muted)",
              fontSize: 14,
            }}
          >
            在 AI 幫手中描述你的目標，Dashboard 將自動填入
          </div>
        ) : (
          <ContextHeaderAggregator
            roleId={currentRole.id}
            roleName={currentRole.name}
            heatmapData={heatmapData}
          />
        )}
      </div>

      {/* Bottom 25%: Coverflow Rotary Wheel Carousel */}
      <div
        style={{
          flex: 1,
          minHeight: 0,
          position: "relative",
          borderTop: "1px solid var(--glass-border)",
        }}
      >
        <RoleFocusCarouselDock
          roles={roles.map((r) => ({
            id: r.id,
            name: r.name,
            colorHex: r.themeColorPalette?.primary,
          }))}
          activeRoleId={currentRole.id}
          onRoleSnap={handleSnap}
          onCenterClick={handleCenterClick}
          onAddRole={handleAddRole}
        />
      </div>
    </div>
  );
}
