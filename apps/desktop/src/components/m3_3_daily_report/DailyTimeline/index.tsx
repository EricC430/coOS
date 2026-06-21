/**
 * M3.3.1 -- Daily Timeline (Global cross-role view)
 *
 * Layout:
 *   [ ClockwheelNav (left, peeks right arc) ]  [ task cards (right, scrollable) ]
 *
 * The ClockwheelNav disc is huge (R=260) but the parent clockwheel-host clips it
 * so only the rightmost ~60 px arc peeks into the panel — analogous to how the
 * homepage carousel arc peeks up from the bottom edge.
 */

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { ClockwheelNav, type Granularity } from "../ClockwheelNav";
import { TimelineDay, type TaskItem } from "./TimelineDay";

interface Props {
  currentRoleId?: string;
}

function formatDate(d: Date): string {
  return d.toISOString().split("T")[0];
}

async function fetchDayReflections(date: string): Promise<TaskItem[]> {
  const params = new URLSearchParams({ date });
  const res = await fetch(`/api/m6_4/daily_timeline?${params}`);
  if (!res.ok) return [];
  return res.json();
}

export function DailyTimeline({ currentRoleId }: Props) {
  const [selectedDate, setSelectedDate] = useState(formatDate(new Date()));
  const [granularity, setGranularity] = useState<Granularity>("day");
  const [direction, setDirection] = useState<1 | -1>(1);

  const { data: tasks = [] } = useQuery<TaskItem[]>({
    queryKey: ["daily_timeline", selectedDate],
    queryFn: () => fetchDayReflections(selectedDate),
  });

  const handleDateChange = (next: string) => {
    setDirection(next > selectedDate ? 1 : -1);
    setSelectedDate(next);
  };

  return (
    /*
     * clockwheel-host: overflow:hidden clips the large disc of ClockwheelNav.
     * The disc extends leftward outside this box; only the right-edge arc peeks in.
     */
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

      {/* ── Right: scrollable task list ── */}
      <div style={{ flex: 1, overflowY: "auto", padding: "16px 16px 16px 8px", minWidth: 0 }}>
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={selectedDate}
            initial={{ opacity: 0, x: direction * 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -direction * 20 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
          >
            {tasks.length === 0 ? (
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
            ) : (
              <TimelineDay
                date={selectedDate}
                tasks={tasks}
                currentRoleId={currentRoleId}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
