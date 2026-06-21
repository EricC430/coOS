/**
 * M3.3 -- Daily Report & Reflection Module (Global cross-role view)
 *
 * SPEC: docs/modules/M3_3_daily_report_reflection_SPEC.md
 * Research: [R08 SS4.2 SS6.1 SS6.2 SS5] [R10 MindScape]
 * Risk mitigation: RISK-01
 *
 * Design: global page — shows all roles. No role_id filter.
 * currentRole is passed down only for visual highlight, not data filtering.
 */

import React from "react";
import { useCoOSStore } from "../../stores/m3_1_global_store";
import { DailyTimeline } from "./DailyTimeline";

export function DailyReportModule() {
  const currentRole = useCoOSStore((s) => s.currentRole);

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 16px",
          borderBottom: "1px solid var(--glass-border)",
          flexShrink: 0,
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>
            Daily Report
          </h2>
          <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 1 }}>
          </div>
        </div>
        <span
          style={{
            fontSize: 12,
            fontWeight: 700,
            color: "var(--gold-accent)",
            background: "var(--glass-bg)",
            border: "1px solid var(--gold-accent)44",
            borderRadius: 8,
            padding: "3px 10px",
          }}
        >
          +XP 核准後領取
        </span>
      </div>

      {/* Timeline — fills remaining space */}
      <div style={{ flex: 1, overflow: "hidden", position: "relative" }}>
        <DailyTimeline currentRoleId={currentRole?.id} />
      </div>
    </div>
  );
}
