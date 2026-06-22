/**
 * M3.3.1 -- Topic Group View
 *
 * Gemma scans all day's segments and clusters them into semantic themes.
 * Each theme card shows: group name, cumulative time, member segment cards.
 * Collapsed by default; click to expand.
 */

import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { DraftApproveModal } from "../DraftApproveModal";
import type { DailyReflection } from "../DraftApproveModal/useApprovalGuard";
import type { TaskItem } from "./TimelineDay";

export interface TopicGroup {
  groupName: string;
  totalMinutes: number;
  segments: TaskItem[];
}

interface Props {
  groups: TopicGroup[];
  isLoading: boolean;
  currentRoleId?: string;
}

// Stable colour from group name
function groupColor(name: string): string {
  const palette = ["#6366f1", "#10b981", "#f59e0b", "#e76f51", "#6a89a7", "#8b5cf6", "#f4a261"];
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) & 0xffffffff;
  return palette[Math.abs(h) % palette.length];
}

function fmtMins(m: number): string {
  if (m < 1) return "< 1 分鐘";
  if (m < 60) return `${Math.round(m)} 分鐘`;
  const h = Math.floor(m / 60);
  const rem = Math.round(m % 60);
  return rem > 0 ? `${h} 時 ${rem} 分` : `${h} 小時`;
}

export function TopicGroupView({ groups, isLoading, currentRoleId }: Props) {
  const [approveTarget, setApproveTarget] = useState<DailyReflection | null>(null);

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", color: "var(--text-muted)", marginTop: 40, fontSize: 13 }}>
        <div style={{ marginBottom: 8, fontSize: 20 }}>🗂</div>
        <div>Gemma 正在分析主題...</div>
        <div style={{ fontSize: 11, marginTop: 4, opacity: 0.6 }}>本地推論中，稍等片刻</div>
      </div>
    );
  }

  if (groups.length === 0) {
    return (
      <div style={{ textAlign: "center", color: "var(--text-muted)", marginTop: 40, fontSize: 13 }}>
        <div style={{ fontSize: 20, marginBottom: 8 }}>📭</div>
        <div>沒有可分組的活動</div>
      </div>
    );
  }

  // Sort groups by totalMinutes descending (most time first)
  const sorted = [...groups].sort((a, b) => b.totalMinutes - a.totalMinutes);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      {sorted.map((group, idx) => (
        <TopicGroupCard
          key={group.groupName}
          group={group}
          index={idx}
          onReviewClick={(r) => setApproveTarget(r)}
        />
      ))}

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

// ── Individual topic group card ─────────────────────────────────────────────

interface GroupCardProps {
  group: TopicGroup;
  index: number;
  onReviewClick: (r: DailyReflection) => void;
}

function TopicGroupCard({ group, index, onReviewClick }: GroupCardProps) {
  const [expanded, setExpanded] = useState(index === 0); // first group open by default
  const color = groupColor(group.groupName);
  const reviewedCount = group.segments.filter((s) => s.reflection?.is_reviewed).length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.2 }}
      style={{
        border: "1px solid var(--glass-border)",
        borderLeft: `3px solid ${color}`,
        borderRadius: 12,
        background: "var(--glass-bg)",
        backdropFilter: "blur(8px)",
        overflow: "hidden",
      }}
    >
      {/* Group header — always visible, clickable to expand */}
      <button
        onClick={() => setExpanded((v) => !v)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "11px 14px",
          background: "transparent",
          border: "none",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        {/* Colour dot */}
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: color,
            flexShrink: 0,
          }}
        />

        {/* Group name */}
        <span
          style={{
            flex: 1,
            fontSize: 13,
            fontWeight: 700,
            color: "var(--text-primary)",
          }}
        >
          {group.groupName}
        </span>

        {/* Cumulative time badge */}
        <span
          style={{
            fontSize: 11,
            fontWeight: 600,
            color: color,
            background: `${color}18`,
            border: `1px solid ${color}44`,
            borderRadius: 20,
            padding: "2px 8px",
            whiteSpace: "nowrap",
          }}
        >
          {fmtMins(group.totalMinutes)}
        </span>

        {/* Segment count + reviewed */}
        <span style={{ fontSize: 10, color: "var(--text-muted)", whiteSpace: "nowrap" }}>
          {group.segments.length} 張{reviewedCount > 0 ? ` · ${reviewedCount} 已完成` : ""}
        </span>

        {/* Expand chevron */}
        <span
          style={{
            fontSize: 10,
            color: "var(--text-muted)",
            transition: "transform 0.2s",
            transform: expanded ? "rotate(180deg)" : "rotate(0deg)",
            flexShrink: 0,
          }}
        >
          ▼
        </span>
      </button>

      {/* Expandable segment list */}
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="content"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            style={{ overflow: "hidden" }}
          >
            <div
              style={{
                borderTop: "1px solid var(--glass-border)",
                padding: "8px 12px 12px",
                display: "flex",
                flexDirection: "column",
                gap: 6,
              }}
            >
              {group.segments.map((seg) => (
                <SegmentMiniCard
                  key={seg.id}
                  seg={seg}
                  accentColor={color}
                  onReviewClick={onReviewClick}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// ── Compact segment card inside a group ────────────────────────────────────

interface MiniCardProps {
  seg: TaskItem;
  accentColor: string;
  onReviewClick: (r: DailyReflection) => void;
}

function SegmentMiniCard({ seg, accentColor, onReviewClick }: MiniCardProps) {
  const isReviewed = seg.reflection?.is_reviewed ?? false;
  const mins = seg.activityMinutes ?? 0;

  return (
    <div
      style={{
        display: "flex",
        gap: 8,
        alignItems: "flex-start",
        padding: "7px 10px",
        borderRadius: 8,
        background: "var(--bg-base)",
        border: "1px solid var(--glass-border)",
      }}
    >
      {/* Time range column */}
      <div
        style={{
          width: 42,
          flexShrink: 0,
          fontSize: 10,
          color: "var(--text-muted)",
          lineHeight: 1.4,
          paddingTop: 1,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        <div>{seg.startTime ?? ""}</div>
        <div style={{ opacity: 0.6 }}>{seg.endTime ?? ""}</div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 12,
            fontWeight: 600,
            color: "var(--text-primary)",
            lineHeight: 1.3,
            wordBreak: "break-word",
          }}
        >
          {seg.title}
        </div>
        {seg.reflection?.ai_description && (
          <div
            style={{
              fontSize: 11,
              color: "var(--text-muted)",
              marginTop: 3,
              lineHeight: 1.45,
              overflow: "hidden",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              whiteSpace: "pre-line",
            }}
          >
            {seg.reflection.ai_description}
          </div>
        )}
      </div>

      {/* Right: duration + review btn */}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-end",
          gap: 4,
          flexShrink: 0,
        }}
      >
        {mins > 0 && (
          <span style={{ fontSize: 10, color: "var(--text-muted)", whiteSpace: "nowrap" }}>
            {mins < 1 ? "< 1 分" : `${Math.round(mins)} 分`}
          </span>
        )}
        <button
          onClick={() => {
            if (!isReviewed && seg.reflection) onReviewClick(seg.reflection);
          }}
          style={{
            fontSize: 10,
            padding: "1px 6px",
            borderRadius: 5,
            border: isReviewed ? "1px solid #10b98155" : `1px solid ${accentColor}55`,
            background: isReviewed ? "#10b98111" : `${accentColor}15`,
            color: isReviewed ? "#10b981" : accentColor,
            cursor: isReviewed ? "default" : "pointer",
            fontWeight: 600,
            whiteSpace: "nowrap",
          }}
        >
          {isReviewed ? "✓" : "review?"}
        </button>
      </div>
    </div>
  );
}
