/**
 * M3.3.1 -- Daily Timeline (Global cross-role view)
 *
 * Two view modes toggled by the user:
 *   "timeline" -- chronological time-axis view (default)
 *   "topic"    -- Gemma-clustered topic groups with cumulative duration
 */

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { ClockwheelNav, type Granularity } from "../ClockwheelNav";
import { TimelineDay, type TaskItem } from "./TimelineDay";
import { TopicGroupView, type TopicGroup } from "./TopicGroupView";

interface Props {
  currentRoleId?: string;
}

type ViewMode = "timeline" | "topic";

function formatDate(d: Date): string {
  return d.toISOString().split("T")[0];
}

async function fetchDayReflections(date: string, roleId?: string): Promise<TaskItem[]> {
  const params = new URLSearchParams({ date });
  const headers: Record<string, string> = {};
  if (roleId) headers["X-Role-ID"] = roleId;
  const res = await fetch(`/api/m6_4/daily_timeline?${params}`, { headers });
  if (!res.ok) return [];
  const raw: any[] = await res.json();
  return raw.map((r) => ({
    id: r.id,
    roleId: r.roleId,
    roleName: r.roleName,
    title: r.title,
    startTime: r.startTime,
    endTime: r.endTime,
    activityMinutes: typeof r.activityMinutes === "number" ? r.activityMinutes : 0,
    status: r.status,
    reflection: r.reflection,
  }));
}

async function fetchTopicGroups(date: string, roleId?: string): Promise<TopicGroup[]> {
  const params = new URLSearchParams({ date });
  const headers: Record<string, string> = {};
  if (roleId) headers["X-Role-ID"] = roleId;
  const res = await fetch(`/api/m6_4/topic_groups?${params}`, { headers });
  if (!res.ok) return [];
  return res.json();
}

export function DailyTimeline({ currentRoleId }: Props) {
  const [selectedDate, setSelectedDate] = useState(formatDate(new Date()));
  const [granularity, setGranularity] = useState<Granularity>("day");
  const [direction, setDirection] = useState<1 | -1>(1);
  const [viewMode, setViewMode] = useState<ViewMode>("timeline");

  const { data: tasks = [] } = useQuery<TaskItem[]>({
    queryKey: ["daily_timeline", selectedDate, currentRoleId],
    queryFn: () => fetchDayReflections(selectedDate, currentRoleId),
  });

  const { data: topicGroups = [], isLoading: topicLoading } = useQuery<TopicGroup[]>({
    queryKey: ["topic_groups", selectedDate, currentRoleId],
    queryFn: () => fetchTopicGroups(selectedDate, currentRoleId),
    enabled: viewMode === "topic",  // only fetch when user switches to topic mode
  });

  const handleDateChange = (next: string) => {
    setDirection(next > selectedDate ? 1 : -1);
    setSelectedDate(next);
  };

  const isEmpty = tasks.length === 0;

  return (
    <div
      className="clockwheel-host"
      style={{ display: "flex", height: "100%", position: "relative" }}
    >
      {/* ── Left: clock-wheel navigator ── */}
      <ClockwheelNav
        date={selectedDate}
        granularity={granularity}
        onDateChange={handleDateChange}
        onGranularityChange={setGranularity}
      />

      {/* ── Right: scrollable content ── */}
      <div style={{ flex: 1, overflowY: "auto", padding: "12px 16px 16px 8px", minWidth: 0, background: "var(--bg-base)" }}>

        {/* View mode toggle */}
        {!isEmpty && (
          <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
            <ViewToggleBtn
              active={viewMode === "timeline"}
              onClick={() => setViewMode("timeline")}
              label="時間軸"
              icon="⏱"
            />
            <ViewToggleBtn
              active={viewMode === "topic"}
              onClick={() => setViewMode("topic")}
              label="主題分組"
              icon="🗂"
            />
          </div>
        )}

        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={`${selectedDate}-${viewMode}`}
            initial={{ opacity: 0, x: direction * 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -direction * 20 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
          >
            {isEmpty ? (
              <div
                style={{
                  textAlign: "center",
                  color: "var(--text-muted)",
                  marginTop: 60,
                  fontSize: 13,
                }}
              >
                <div style={{ fontSize: 32, marginBottom: 8 }}>📋</div>
                <div>這一天還沒有任何記錄</div>
                <div style={{ fontSize: 11, marginTop: 4, opacity: 0.7 }}>
                  使用底部對話框與 AI 互動，系統會自動記錄
                </div>
              </div>
            ) : viewMode === "timeline" ? (
              <TimelineDay
                date={selectedDate}
                tasks={tasks}
                currentRoleId={currentRoleId}
              />
            ) : (
              <TopicGroupView
                groups={topicGroups}
                isLoading={topicLoading}
                currentRoleId={currentRoleId}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

function ViewToggleBtn({
  active,
  onClick,
  label,
  icon,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  icon: string;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 4,
        padding: "4px 10px",
        borderRadius: 8,
        border: active ? "1px solid #6366f1" : "1px solid var(--glass-border)",
        background: active ? "#6366f118" : "transparent",
        color: active ? "#818cf8" : "var(--text-muted)",
        fontSize: 11,
        fontWeight: active ? 700 : 400,
        cursor: "pointer",
        transition: "all 0.15s",
      }}
    >
      <span>{icon}</span>
      <span>{label}</span>
    </button>
  );
}
