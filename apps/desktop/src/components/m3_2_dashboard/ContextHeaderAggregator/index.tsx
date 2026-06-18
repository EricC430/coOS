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
import { WidgetGridManager } from "../WidgetGridManager";
import type { HeatmapEntry } from "../ConsistencyHeatmap";

interface ProjectEntry {
  name: string;
  description?: string;
  created_at?: string;
}

interface ContextData {
  project?: { name: string };
  projects?: ProjectEntry[];
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
          <div className="glass-card context-slot" data-testid="project-slot" style={{ overflowY: "auto" }}>
            <span className="context-slot-label">Projects</span>
            {data?.projects && data.projects.length > 0 ? (
              <ul style={{ margin: 0, padding: 0, listStyle: "none", width: "100%" }}>
                {data.projects.map((p, i) => (
                  <li
                    key={i}
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      paddingBottom: 4,
                      borderBottom: i < data.projects!.length - 1 ? "1px solid var(--glass-border)" : "none",
                      marginBottom: 4,
                    }}
                  >
                    <span className="context-slot-value" style={{ fontSize: 12 }}>{p.name}</span>
                    {p.description && (
                      <span style={{ fontSize: 10, color: "var(--text-muted)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {p.description}
                      </span>
                    )}
                    {p.created_at && (
                      <span style={{ fontSize: 9, color: "var(--text-muted)" }}>
                        {p.created_at.slice(0, 10)}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <span className="context-slot-value">{data?.project?.name ?? "—"}</span>
            )}
          </div>

          <div className="glass-card context-slot" data-testid="promises-slot"
            style={{ overflowY: "auto" }}>
            <span className="context-slot-label">Promises</span>
            {data?.promises && data.promises.length > 0 ? (
              <ul style={{ margin: 0, padding: 0, listStyle: "none", width: "100%" }}>
                {data.promises.map((p, i) => (
                  <li key={i} style={{
                    paddingBottom: 4,
                    borderBottom: i < data.promises!.length - 1 ? "1px solid var(--glass-border)" : "none",
                    marginBottom: 4,
                    fontSize: 12,
                    color: "var(--text-primary)",
                  }}>
                    {p}
                  </li>
                ))}
              </ul>
            ) : (
              <span className="context-slot-value">—</span>
            )}
          </div>

          <div className="glass-card context-slot" data-testid="goal-slot"
            style={{ overflowY: "auto" }}>
            <span className="context-slot-label">Goal</span>
            {data?.goals && data.goals.length > 0 ? (
              <ul style={{ margin: 0, padding: 0, listStyle: "none", width: "100%" }}>
                {data.goals.map((g, i) => (
                  <li key={i} style={{
                    paddingBottom: 4,
                    borderBottom: i < data.goals!.length - 1 ? "1px solid var(--glass-border)" : "none",
                    marginBottom: 4,
                    fontSize: 12,
                    color: "var(--text-primary)",
                  }}>
                    {g}
                  </li>
                ))}
              </ul>
            ) : (
              <span className="context-slot-value">—</span>
            )}
          </div>
        </div>

        {/* Row 2: Dashboard with reorderable widget cards */}
        <div className="glass-card dashboard-block" data-testid="dashboard-block"
          style={{ overflow: "auto" }}>
          <span className="dashboard-title">Dashboard</span>
          <WidgetGridManager roleId={roleId} heatmapData={heatmapData} />
        </div>
      </div>
    </div>
  );
}
