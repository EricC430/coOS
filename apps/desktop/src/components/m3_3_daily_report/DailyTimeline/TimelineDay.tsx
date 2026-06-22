/**
 * M3.3.1 -- Single day timeline group
 *
 * Layout: role sections sorted by first card start_time.
 * Within each role: vertical timeline axis (node + line) with time label on the left,
 * card on the right.
 * Status pill: "已完成" only when is_reviewed=true; "草稿" otherwise (it's always a draft).
 */

import React, { useState } from "react";
import { motion } from "framer-motion";
import { DraftApproveModal } from "../DraftApproveModal";
import type { DailyReflection } from "../DraftApproveModal/useApprovalGuard";

export interface TaskItem {
  id: string;
  roleId: string;
  roleName: string;
  title: string;
  startTime?: string;
  endTime?: string;
  activityMinutes?: number;
  status: "in_progress" | "completed";
  reflection?: DailyReflection;
}

interface Props {
  date: string;
  tasks: TaskItem[];
  currentRoleId?: string;
}

function roleColor(roleId: string): string {
  const palette = [
    "#f4a261", "#e76f51", "#6a89a7", "#6366f1", "#10b981", "#f59e0b", "#8b5cf6",
  ];
  let h = 0;
  for (let i = 0; i < roleId.length; i++) h = (h * 31 + roleId.charCodeAt(i)) & 0xffffffff;
  return palette[Math.abs(h) % palette.length];
}

function roleInitials(name: string): string {
  return name.slice(0, 2).toUpperCase();
}

/** Sort tasks within a role by start_time string (HH:MM). */
function sortByTime(tasks: TaskItem[]): TaskItem[] {
  return [...tasks].sort((a, b) => (a.startTime ?? "00:00").localeCompare(b.startTime ?? "00:00"));
}

export function TimelineDay({ date, tasks, currentRoleId }: Props) {
  const [approveTarget, setApproveTarget] = useState<DailyReflection | null>(null);

  // Group by role, preserving first-appearance order
  const byRole: Record<string, TaskItem[]> = {};
  const roleOrder: string[] = [];
  for (const t of tasks) {
    if (!byRole[t.roleId]) {
      byRole[t.roleId] = [];
      roleOrder.push(t.roleId);
    }
    byRole[t.roleId].push(t);
  }

  // Sort role order by the earliest card start_time in each group
  roleOrder.sort((a, b) => {
    const aFirst = sortByTime(byRole[a])[0]?.startTime ?? "00:00";
    const bFirst = sortByTime(byRole[b])[0]?.startTime ?? "00:00";
    return aFirst.localeCompare(bFirst);
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
      {roleOrder.map((roleId, groupIdx) => {
        const roleTasks = sortByTime(byRole[roleId]);
        const roleName = roleTasks[0]?.roleName ?? roleId;
        const color = roleColor(roleId);
        const isCurrentRole = roleId === currentRoleId;

        return (
          <motion.div
            key={roleId}
            data-testid={`role-group-${roleId}`}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: groupIdx * 0.06, duration: 0.22 }}
          >
            {/* Role header */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 10 }}>
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: "50%",
                  background: `linear-gradient(135deg, ${color}, ${color}bb)`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 11,
                  fontWeight: 700,
                  color: "#fff",
                  boxShadow: isCurrentRole ? `0 0 0 3px ${color}44` : "none",
                  border: isCurrentRole ? `2px solid ${color}` : "2px solid transparent",
                  flexShrink: 0,
                }}
              >
                {roleInitials(roleName)}
              </div>
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  color: isCurrentRole ? color : "var(--text-secondary)",
                }}
              >
                {roleName}
              </span>
            </div>

            {/* Timeline cards */}
            <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
              {roleTasks.map((task, idx) => (
                <TimelineRow
                  key={task.id}
                  task={task}
                  accentColor={color}
                  isLast={idx === roleTasks.length - 1}
                  onReviewClick={(r) => setApproveTarget(r)}
                />
              ))}
            </div>
          </motion.div>
        );
      })}

      {approveTarget && (
        <DraftApproveModal
          reflection={approveTarget}
          onApproved={() => setApproveTarget(null)}
          onClose={() => setApproveTarget(null)}
        />
      )}
    </div>
  );
}

// ── Timeline row: [time label] [node+line] [card] ──────────────────────────

interface RowProps {
  task: TaskItem;
  accentColor: string;
  isLast: boolean;
  onReviewClick: (r: DailyReflection) => void;
}

function TimelineRow({ task, accentColor, isLast, onReviewClick }: RowProps) {
  const isReviewed = task.reflection?.is_reviewed ?? false;
  const mins = task.activityMinutes ?? 0;
  const timeLabel = task.startTime ?? "";

  return (
    <div style={{ display: "flex", gap: 0, alignItems: "flex-start" }}>
      {/* Left column: time label (fixed width) */}
      <div
        style={{
          width: 44,
          flexShrink: 0,
          paddingTop: 10,
          textAlign: "right",
          paddingRight: 8,
          fontSize: 10,
          color: "var(--text-muted)",
          fontVariantNumeric: "tabular-nums",
          lineHeight: 1,
        }}
      >
        {timeLabel}
      </div>

      {/* Center column: node + vertical line */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          flexShrink: 0,
          width: 16,
        }}
      >
        {/* Node circle */}
        <div
          style={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            background: isReviewed ? "#10b981" : accentColor,
            border: `2px solid ${isReviewed ? "#10b98155" : `${accentColor}55`}`,
            marginTop: 11,
            flexShrink: 0,
            zIndex: 1,
          }}
        />
        {/* Vertical connecting line (hidden for last item) */}
        {!isLast && (
          <div
            style={{
              width: 2,
              flex: 1,
              minHeight: 12,
              background: `linear-gradient(to bottom, ${accentColor}44, ${accentColor}11)`,
              marginTop: 2,
            }}
          />
        )}
      </div>

      {/* Right column: card */}
      <div style={{ flex: 1, minWidth: 0, paddingLeft: 8, paddingBottom: isLast ? 0 : 10 }}>
        <motion.div
          data-testid="task-card"
          data-role-id={task.roleId}
          whileHover={{ scale: 1.003 }}
          style={{
            background: "var(--glass-bg)",
            border: "1px solid var(--glass-border)",
            borderLeft: `3px solid ${accentColor}`,
            borderRadius: 10,
            padding: "9px 11px",
            display: "flex",
            flexDirection: "column",
            gap: 5,
            backdropFilter: "blur(8px)",
            boxShadow: "var(--glass-shadow)",
          }}
        >
          {/* Row 1: title + reviewed CTA */}
          <div style={{ display: "flex", alignItems: "flex-start", gap: 6 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: 13,
                  fontWeight: 600,
                  color: "var(--text-primary)",
                  lineHeight: 1.35,
                  wordBreak: "break-word",
                }}
              >
                {task.title}
              </div>
            </div>
            <button
              data-testid={`review-btn-${task.id}`}
              onClick={() => {
                if (!isReviewed && task.reflection) onReviewClick(task.reflection);
              }}
              style={{
                fontSize: 10,
                padding: "2px 7px",
                borderRadius: 6,
                border: isReviewed
                  ? "1px solid #10b98155"
                  : `1px solid ${accentColor}55`,
                background: isReviewed ? "#10b98111" : `${accentColor}15`,
                color: isReviewed ? "#10b981" : accentColor,
                cursor: isReviewed ? "default" : "pointer",
                fontWeight: 600,
                flexShrink: 0,
                whiteSpace: "nowrap",
                transition: "background 0.15s",
              }}
            >
              {isReviewed ? "reviewed ✓" : "reviewed?"}
            </button>
          </div>

          {/* Row 2: status pill + duration */}
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <StatusPill reviewed={isReviewed} />
            {mins > 0 && (
              <span
                style={{
                  fontSize: 10,
                  color: "var(--text-muted)",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {mins < 1 ? `< 1 分鐘` : `${Math.round(mins)} 分鐘`}
              </span>
            )}
            {task.endTime && task.startTime && (
              <span style={{ fontSize: 10, color: "var(--text-muted)", opacity: 0.7 }}>
                {task.startTime}–{task.endTime}
              </span>
            )}
          </div>

          {/* Row 3: ai_description (draft preview) */}
          {task.reflection?.ai_description && (
            <div
              style={{
                fontSize: 11,
                color: "var(--text-muted)",
                borderTop: "1px solid var(--glass-border)",
                paddingTop: 5,
                lineHeight: 1.5,
                whiteSpace: "pre-line",
                overflow: "hidden",
                display: "-webkit-box",
                WebkitLineClamp: 4,
                WebkitBoxOrient: "vertical",
              }}
            >
              {task.reflection.ai_description}
            </div>
          )}

          {/* Row 4: user feeling after review */}
          {task.reflection?.user_feeling && (
            <div
              style={{
                fontSize: 11,
                color: "var(--text-secondary)",
                borderTop: "1px solid var(--glass-border)",
                paddingTop: 5,
                display: "flex",
                gap: 4,
                alignItems: "flex-start",
              }}
            >
              <span style={{ flexShrink: 0, opacity: 0.7 }}>學到了～</span>
              <span
                style={{
                  overflow: "hidden",
                  display: "-webkit-box",
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: "vertical",
                }}
              >
                {task.reflection.user_feeling}
              </span>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}

function StatusPill({ reviewed }: { reviewed: boolean }) {
  return (
    <span
      style={{
        fontSize: 10,
        fontWeight: 600,
        padding: "2px 7px",
        borderRadius: 99,
        background: reviewed ? "#10b98120" : "#6366f118",
        color: reviewed ? "#10b981" : "#818cf8",
        border: reviewed ? "1px solid #10b98140" : "1px solid #6366f140",
        flexShrink: 0,
      }}
    >
      {reviewed ? "已完成" : "草稿"}
    </span>
  );
}
