import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useCoOSStore } from "../../stores/m3_1_global_store";
import { RoleFocusCarouselDock } from "./RoleFocusCarouselDock";
import { ContextHeaderAggregator } from "./ContextHeaderAggregator";
import { TransitionBackground } from "./TransitionBackground";
import { RoleCreationModal } from "./RoleCreationModal";

interface HeatmapEntry {
  date: string;
  count: number;
}

interface Props {
  onEnterChat?: (roleId: string) => void;
}

type ThemePalette = { primary: string };

async function fetchHeatmapData(roleId: string): Promise<HeatmapEntry[]> {
  const res = await fetch(`/api/m6_4/heatmap?role_id=${roleId}`);
  if (!res.ok) return [];
  return res.json();
}

export function RoleDashboard({ onEnterChat }: Props) {
  const { currentRole, roleCache, switchRole, setRoleTransitioning, seedRoleCache } = useCoOSStore();
  const [creationOpen, setCreationOpen] = useState(false);
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
    setCreationOpen(true);
  };

  const handleCreated = async () => {
    try {
        const res = await fetch("/api/m6_2/roles");
        if (res.ok) {
            const roles = await res.json();
            seedRoleCache(roles);
        }
    } catch (err) {
        console.error("Failed to refresh roles:", err);
    }
  };

  if (!currentRole && roles.length > 0) {
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
        roleId={currentRole?.id || "none"}
        palette={(currentRole?.themeColorPalette as unknown as ThemePalette) || { primary: "#333" }}
        onTransitionEnd={handleTransitionEnd}
      />

      {/* Top 75%: Context Header (Role title + Project/Promises/Goal + Dashboard) */}
      <div style={{ flex: 3, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        {roles.length === 0 ? (
          <div
            data-testid="dashboard-empty-state"
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "var(--text-muted)",
              gap: '24px'
            }}
          >
            <div style={{ fontSize: '4rem', opacity: 0.2 }}>🌿</div>
            <div style={{ fontSize: 18, textAlign: 'center' }}>
                歡迎來到 coOS。<br/>首先，建立一個你的生活角色吧。
            </div>
            <button className="settings-save-btn" onClick={handleAddRole} style={{ height: 'auto', padding: '12px 32px', fontSize: '1.1rem' }}>
              + 建立第一個角色
            </button>
          </div>
        ) : currentRole ? (
          <ContextHeaderAggregator
            roleId={currentRole.id}
            roleName={currentRole.name}
            heatmapData={heatmapData}
          />
        ) : null}
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
          activeRoleId={currentRole?.id || ""}
          onRoleSnap={handleSnap}
          onCenterClick={handleCenterClick}
          onAddRole={handleAddRole}
        />
      </div>

      <RoleCreationModal 
        isOpen={creationOpen} 
        onClose={() => setCreationOpen(false)} 
        onCreated={handleCreated} 
      />
    </div>
  );
}
