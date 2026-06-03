/**
 * M3.3.1 -- Daily Timeline with role grouping and date navigation
 *
 * SPEC: docs/modules/M3_3_daily_report_reflection_SPEC.md SS1.1
 */

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { TimelineDay, type TaskItem } from "./TimelineDay";

interface Props {
  currentRoleId?: string;
}

function formatDate(d: Date): string {
  return d.toISOString().split("T")[0];
}

async function fetchDayReflections(date: string, roleId?: string): Promise<TaskItem[]> {
  const params = new URLSearchParams({ date });
  if (roleId) params.set("role_id", roleId);
  const res = await fetch(`/api/m6_4/daily_timeline?${params}`);
  if (!res.ok) return [];
  return res.json();
}

export function DailyTimeline({ currentRoleId }: Props) {
  const [selectedDate, setSelectedDate] = useState(formatDate(new Date()));

  const { data: tasks = [] } = useQuery<TaskItem[]>({
    queryKey: ["daily_timeline", selectedDate, currentRoleId],
    queryFn: () => fetchDayReflections(selectedDate, currentRoleId),
  });

  const goDay = (delta: number) => {
    const d = new Date(selectedDate);
    d.setDate(d.getDate() + delta);
    setSelectedDate(formatDate(d));
  };

  return (
    <div className="flex h-full">
      {/* Left timeline nav */}
      <div className="w-20 flex-shrink-0 flex flex-col items-center pt-4 gap-2">
        <button
          data-testid="date-nav-prev"
          onClick={() => goDay(-1)}
          className="text-gray-400 hover:text-gray-700"
        >
          ▲
        </button>
        <div
          data-testid="timeline-date-label"
          className="text-xs text-center text-gray-500 leading-tight"
        >
          {selectedDate.replace(/-/g, "\n")}
        </div>
        <button
          data-testid="date-nav-next"
          onClick={() => goDay(1)}
          className="text-gray-400 hover:text-gray-700 disabled:opacity-30"
          disabled={selectedDate >= formatDate(new Date())}
        >
          ▼
        </button>
      </div>

      {/* Timeline content */}
      <div className="flex-1 overflow-y-auto px-2 py-4">
        {tasks.length === 0 ? (
          <div className="text-center text-gray-400 mt-12">今天還沒有任何記錄</div>
        ) : (
          <TimelineDay
            date={selectedDate}
            tasks={tasks}
            currentRoleId={currentRoleId}
          />
        )}
      </div>
    </div>
  );
}
