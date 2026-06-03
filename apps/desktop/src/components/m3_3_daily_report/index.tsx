/**
 * M3.3 -- Daily Report & Reflection Module
 *
 * SPEC: docs/modules/M3_3_daily_report_reflection_SPEC.md
 * Research: [R08 SS4.2 SS6.1 SS6.2 SS5] [R10 MindScape]
 * Risk mitigation: RISK-01
 */

import React from "react";
import { useCoOSStore } from "../../stores/m3_1_global_store";
import { DailyTimeline } from "./DailyTimeline";

export function DailyReportModule() {
  const currentRole = useCoOSStore((s) => s.currentRole);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h2 className="font-semibold text-gray-700">Daily Report</h2>
        <span className="text-xs text-indigo-600 font-medium">+XP 核准後領取</span>
      </div>
      <div className="flex-1 overflow-hidden">
        <DailyTimeline currentRoleId={currentRole?.id} />
      </div>
    </div>
  );
}
