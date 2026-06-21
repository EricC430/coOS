/**
 * M3.3.1 -- Single day timeline group
 * Groups tasks by role_id; role avatar on left, cards on right.
 * Matches sketch: status pill, time spent, 學到了, expert tag, reviewed? CTA.
 */

import React, { useState } from "react";
import { motion } from "framer-motion";
import { TimeCard } from "../TimeCard";
import { DraftApproveModal } from "../DraftApproveModal";
import type { DailyReflection } from "../DraftApproveModal/useApprovalGuard";

export interface TaskItem {
  id: string;
  roleId: string;
  roleName: string;
  title: string;
  status: "in_progress" | "completed";
  reflection?: DailyReflection;
}

interface Props {
  date: string;
  tasks: TaskItem[];
  currentRoleId?: string;
}

// Derive a deterministic warm accent from roleId
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

export function TimelineDay({ date, tasks, currentRoleId }: Props) {
  const [approveTarget, setApproveTarget] = useState<DailyReflection | null>(null);

  // Group by role
  const byRole: Record<string, TaskItem[]> = {};
  const roleOrder: string[] = [];
  for (const t of tasks) {
    if (!byRole[t.roleId]) {
      byRole[t.roleId] = [];
      roleOrder.push(t.roleId);
    }
    byRole[t.roleId].push(t);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {roleOrder.map((roleId, groupIdx) => {
        const roleTasks = byRole[roleId];
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
            style={{ display: "flex", gap: 12, alignItems: "flex-start" }}
          >
            {/* Role avatar — left column */}
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4, width: 52, flexShrink: 0 }}>
              <div
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: "50%",
                  background: `linear-gradient(135deg, ${color}, ${color}bb)`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: 13,
                  fontWeight: 700,
                  color: "#fff",
                  boxShadow: isCurrentRole ? `0 0 0 3px ${color}55, 0 2px 8px ${color}44` : "none",
                  border: isCurrentRole ? `2px solid ${color}` : "2px solid transparent",
                  transition: "box-shadow 0.2s",
                }}
              >
                {roleInitials(roleName)}
              </div>
              <span
                style={{
                  fontSize: 9,
                  color: "var(--text-muted)",
                  textAlign: "center",
                  maxWidth: 52,
                  lineHeight: 1.2,
                  wordBreak: "keep-all",
                }}
              >
                {roleName}
              </span>
            </div>

            {/* Task cards — right column */}
            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8, minWidth: 0 }}>
              {roleTasks.map((task) => (
                <TaskCard
                  key={task.id}
                  task={task}
                  accentColor={color}
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

// ── Individual task card ────────────────────────────────────────────────────

interface TaskCardProps {
  task: TaskItem;
  accentColor: string;
  onReviewClick: (r: DailyReflection) => void;
}

function TaskCard({ task, accentColor, onReviewClick }: TaskCardProps) {
  const isReviewed = task.reflection?.is_reviewed ?? false;
  const isDone = task.status === "completed";

  return (
    <motion.div
      data-testid="task-card"
      data-role-id={task.roleId}
      whileHover={{ scale: 1.005 }}
      style={{
        background: "var(--glass-bg)",
        border: "1px solid var(--glass-border)",
        borderLeft: `3px solid ${accentColor}`,
        borderRadius: 10,
        padding: "10px 12px",
        display: "flex",
        flexDirection: "column",
        gap: 6,
        backdropFilter: "blur(8px)",
        boxShadow: "var(--glass-shadow)",
      }}
    >
      {/* Row 1: title + expert tag + reviewed CTA */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
        {/* Task icon */}
        <span style={{ fontSize: 14, lineHeight: 1, marginTop: 1, flexShrink: 0 }}>📋</span>

        {/* Title */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--text-primary)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {task.title}
          </div>
        </div>

        {/* Reviewed CTA — right side */}
        <button
          data-testid={`review-btn-${task.id}`}
          onClick={() => {
            if (!isReviewed && task.reflection) {
              onReviewClick(task.reflection);
            }
          }}
          style={{
            fontSize: 11,
            padding: "2px 8px",
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

      {/* Row 2: status pill + time */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <StatusPill done={isDone} />
        {task.id && <TimeCard taskId={task.id} />}
      </div>

      {/* Row 3: 學到了 (user feeling from reflection) */}
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

      {/* Row 4: ai_description snippet if not yet reviewed */}
      {!isReviewed && task.reflection?.ai_description && (
        <div
          style={{
            fontSize: 11,
            color: "var(--text-muted)",
            fontStyle: "italic",
            borderTop: "1px solid var(--glass-border)",
            paddingTop: 5,
            overflow: "hidden",
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
          }}
        >
          {task.reflection.ai_description}
        </div>
      )}
    </motion.div>
  );
}

function StatusPill({ done }: { done: boolean }) {
  return (
    <span
      style={{
        fontSize: 10,
        fontWeight: 600,
        padding: "2px 7px",
        borderRadius: 99,
        background: done ? "#10b98120" : "#f59e0b18",
        color: done ? "#10b981" : "#d97706",
        border: done ? "1px solid #10b98140" : "1px solid #f59e0b40",
        flexShrink: 0,
      }}
    >
      {done ? "已完成" : "正在進行中"}
    </span>
  );
}
