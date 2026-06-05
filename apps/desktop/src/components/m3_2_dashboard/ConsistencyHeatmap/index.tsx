/**
 * M3.2.4 -- Consistency Heatmap (365-day activity grid)
 *
 * SPEC: docs/modules/M3_2_role_dashboard_SPEC.md SS7.1
 * [R06 SS2] Digital phenotype from behaviour records
 * Anti-pattern: NEVER render raw raw_tracking_logs; expects pre-aggregated {date, count}[]
 */

import { useState } from "react";
import { HeatmapCell } from "./HeatmapCell";

export interface HeatmapEntry {
  date: string; // ISO yyyy-MM-dd
  count: number;
}

interface Props {
  data: HeatmapEntry[];
}

function buildGrid(data: HeatmapEntry[]): HeatmapEntry[] {
  const map: Record<string, number> = {};
  for (const e of data) map[e.date] = e.count;

  const days: HeatmapEntry[] = [];
  const today = new Date();
  for (let i = 364; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(today.getDate() - i);
    const iso = d.toISOString().split("T")[0];
    days.push({ date: iso, count: map[iso] ?? 0 });
  }
  return days;
}

export function ConsistencyHeatmap({ data }: Props) {
  const [tooltip, setTooltip] = useState<{ date: string; count: number } | null>(null);
  const grid = buildGrid(data);

  return (
    <div style={{ position: "relative" }}>
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 2,
          maxWidth: 728,
        }}
      >
        {grid.map((entry) => (
          <HeatmapCell
            key={entry.date}
            date={entry.date}
            count={entry.count}
            onHover={(date, count) => setTooltip({ date, count })}
            onLeave={() => setTooltip(null)}
          />
        ))}
      </div>
      {tooltip && (
        <div
          data-testid="heatmap-tooltip"
          className="glass-card"
          style={{
            position: "absolute",
            bottom: "100%",
            left: 0,
            marginBottom: 4,
            fontSize: 12,
            padding: "6px 10px",
            pointerEvents: "none",
            color: "var(--text-primary)",
            whiteSpace: "nowrap",
            zIndex: 20,
          }}
        >
          {tooltip.date}: {tooltip.count} 項
        </div>
      )}
    </div>
  );
}
