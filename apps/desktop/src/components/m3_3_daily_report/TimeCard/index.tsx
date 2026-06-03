/**
 * M3.3.2 -- Tolerant Time Card
 * Dual-track: AI inquiry first, telemetry fallback
 */

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { resolveTimeSpent } from "./useTimeFallback";

interface Props {
  taskId: string;
}

export function TimeCard({ taskId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["time_spent", taskId],
    queryFn: () => resolveTimeSpent(taskId),
  });

  if (isLoading) {
    return <span className="text-gray-400 text-xs">計算中...</span>;
  }

  const label = data?.source === "ai_inquiry" ? "AI 套問" : "遙測推算";
  const minutes = data?.time_spent_minutes ?? 0;

  return (
    <div className="flex items-center gap-1 text-xs">
      <span data-testid="time-value" className="font-medium">{minutes} 分</span>
      <span
        data-testid="time-source-badge"
        className="px-1.5 py-0.5 rounded text-white"
        style={{ background: data?.source === "ai_inquiry" ? "#3b82f6" : "#6b7280" }}
      >
        {label}
      </span>
    </div>
  );
}
