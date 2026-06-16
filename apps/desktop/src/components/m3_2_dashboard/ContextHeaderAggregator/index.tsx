/**
 * M3.2.3 -- Context Header Aggregator (Restructured 2-Row Layout)
 *
 * SPEC: docs/modules/M3_2_role_dashboard_SPEC.md SS1.1
 * 
 * Layout:
 *   - Top: Role name as large title (no "Role" prefix)
 *   - Row 1: Project | Promises | Goal (equal-width 3 columns)
 *   - Row 2: Dashboard (with heatmap + title)
 *   - Both rows are equal height
 *
 * [R08 SS1] Skeleton UI prevents layout shift during load
 * [RISK-06] Waits for ROLE_CONTEXT_SYNCED before showing real data
 */

import { useQuery } from "@tanstack/react-query";
import { fetchRoleContext } from "./useRoleContextCache";
import { ConsistencyHeatmap } from "../ConsistencyHeatmap";
import type { HeatmapEntry } from "../ConsistencyHeatmap";

interface ContextData {
  project?: { name: string };
  promises?: string[];
  goals?: string[];
  role?: { name: string };
}

interface Props {
  roleId: string;
  roleName?: string;
  heatmapData: HeatmapEntry[];
}

function SkeletonSlot() {
  return (
    <div
      data-testid="skeleton-loader"
      className="glass-card"
      style={{
        height: "100%",
        minHeight: 60,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          width: "60%",
          height: 16,
          borderRadius: 8,
          background: "var(--glass-border)",
          animation: "pulse 1.5s ease-in-out infinite",
        }}
      />
    </div>
  );
}

export function ContextHeaderAggregator({ roleId, roleName, heatmapData }: Props) {
  const { data, isLoading } = useQuery<ContextData>({
    queryKey: ["role_context", roleId],
    queryFn: () => fetchRoleContext(roleId),
    staleTime: 8_000,
    refetchInterval: 15_000,
    retry: 2,
    enabled: !!roleId,
  });

  if (isLoading) {
    return (
      <div className="context-header" data-testid="context-header">
        <div
          style={{
            width: 120,
            height: 28,
            borderRadius: 8,
            background: "var(--glass-border)",
            animation: "pulse 1.5s ease-in-out infinite",
          }}
        />
        <div className="context-grid">
          <div className="context-row-top">
            <SkeletonSlot />
            <SkeletonSlot />
            <SkeletonSlot />
          </div>
          <SkeletonSlot />
        </div>
      </div>
    );
  }

  return (
    <div className="context-header" data-testid="context-header" style={{ flex: 1, minHeight: 0 }}>
      {/* Role name as top-level title — only name, no "Role" prefix */}
      <h1 className="context-role-title" data-testid="role-title">
        {roleName ?? data?.role?.name ?? "—"}
      </h1>

      {/* 2-row equal-height grid */}
      <div className="context-grid" style={{ flex: 1, minHeight: 0 }}>
        {/* Row 1: Project | Promises | Goal — equal width */}
        <div className="context-row-top">
          <div className="glass-card context-slot" data-testid="project-slot">
            <span className="context-slot-label">Project</span>
            <span className="context-slot-value">
              {data?.project?.name ?? "—"}
            </span>
          </div>

          <div className="glass-card context-slot" data-testid="promises-slot">
            <span className="context-slot-label">Promises</span>
            <span className="context-slot-value">
              {data?.promises?.[0] ?? "—"}
            </span>
          </div>

          <div className="glass-card context-slot" data-testid="goal-slot">
            <span className="context-slot-label">Goal</span>
            <span className="context-slot-value">
              {data?.goals?.[0] ?? "—"}
            </span>
          </div>
        </div>

        {/* Row 2: Dashboard with heatmap */}
        <div className="glass-card dashboard-block" data-testid="dashboard-block">
          <span className="dashboard-title">Dashboard</span>
          <div>
            <span className="heatmap-title">365 天一致性紀錄</span>
            <ConsistencyHeatmap data={heatmapData} />
          </div>
        </div>
      </div>
    </div>
  );
}
