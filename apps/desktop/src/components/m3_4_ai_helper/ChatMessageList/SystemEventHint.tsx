/**
 * M3.4.4.1 -- System Event Hint (Invisible automation notification)
 * [R09 SS6.1 MAS] Observer events shown inline, NEVER as Modal/Toast
 * [RISK-04] L2 defer: only sidebar badge, no interruption during deep work
 */

import React, { useState } from "react";

export interface ObserverEvent {
  type: string;
  project_id?: string;
  project_name?: string;
  goal?: string;
  expert_name?: string;
  text?: string;
  title?: string;
  deadline?: string;
  source?: string; // chat | background | browser | calendar
  intention?: string;
  role_id?: string;
}

// [測試回饋] 依 source 顯示偵測來源
const SOURCE_LABEL: Record<string, string> = {
  chat: "偵測聊天內容",
  background: "偵測背景程式",
  browser: "偵測瀏覽器網頁",
  calendar: "偵測綁定行事曆",
};

function sourceLabel(source?: string): string {
  return SOURCE_LABEL[source ?? "chat"] ?? "偵測聊天內容";
}

const EVENT_MESSAGES: Record<string, (e: ObserverEvent) => string> = {
  // [測試回饋] 語意化："偵測聊天內容，已建立「X」"
  PROJECT_CREATED: (e) => `${sourceLabel(e.source)}，已建立「${e.project_name}」`,
  PROJECT_SWITCHED: (e) => `偵測切換到「${e.project_name}」專案`,
  GOAL_INFERRED: (e) => `目標「${e.goal}」已記錄`,
  GOAL_CONFIRMED: (e) => `與 ${e.expert_name ?? ""} 確立目標「${e.title}」`,
  PROMISE_RECORDED: (e) =>
    `承諾「${e.text}」已記錄${e.deadline ? `，deadline: ${e.deadline}` : ""}`,
  PROMISE_REMINDER: (e) => `承諾「${e.text}」即將到期`,
  EXPERT_POOL_EMPTY: () => `此角色已無 AI 專家，請重新配對`,
};

// 哪些事件型別可編輯/刪除（專案標籤類）
const EDITABLE_TYPES = new Set(["PROJECT_CREATED", "PROJECT_SWITCHED"]);

interface Props {
  event: ObserverEvent;
  onEditProject?: (projectId: string, newName: string) => void;
  onDeleteProject?: (projectId: string) => void;
}

// Icon per event type — keeps the marker visually distinct from timestamp dividers
const EVENT_ICONS: Record<string, string> = {
  PROJECT_CREATED: "🏷️",
  PROJECT_SWITCHED: "🔀",
  GOAL_CONFIRMED: "🎯",
  GOAL_INFERRED: "💡",
  PROMISE_RECORDED: "🤝",
  PROMISE_REMINDER: "⏰",
  EXPERT_POOL_EMPTY: "⚠️",
};

export function SystemEventHint({ event, onEditProject, onDeleteProject }: Props) {
  const message = EVENT_MESSAGES[event.type]?.(event) ?? event.type;
  const icon = EVENT_ICONS[event.type] ?? "ℹ️";
  const [editing, setEditing] = useState(false);
  const [draftName, setDraftName] = useState(event.project_name ?? "");

  const canManage =
    EDITABLE_TYPES.has(event.type) &&
    !!event.project_id &&
    (!!onEditProject || !!onDeleteProject);

  if (editing && event.project_id) {
    return (
      <div
        data-testid="system-event-hint-edit"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: 4,
          margin: "6px 16px",
          padding: "4px 10px",
          borderRadius: 8,
          background: "var(--glass-bg, rgba(255,255,255,0.06))",
          border: "1px solid var(--glass-border, rgba(255,255,255,0.12))",
          fontSize: 12,
        }}
      >
        <span>{icon}</span>
        <input
          style={{ border: "1px solid var(--glass-border)", borderRadius: 4, padding: "1px 4px", fontSize: 12, background: "transparent", color: "inherit", width: 140 }}
          value={draftName}
          onChange={(e) => setDraftName(e.target.value)}
          autoFocus
        />
        <button
          style={{ color: "var(--role-primary, #6366f1)", fontWeight: 600, fontSize: 12 }}
          onClick={() => { onEditProject?.(event.project_id!, draftName.trim()); setEditing(false); }}
        >
          存
        </button>
        <button style={{ color: "var(--text-muted, #888)", fontSize: 12 }} onClick={() => setEditing(false)}>
          取消
        </button>
      </div>
    );
  }

  return (
    // Permanent system-event separator — visually distinct from timestamp dividers.
    // [R09 SS6.1] Inline, never Modal/Toast. Persistent after history reload (stored in DB).
    <div
      data-testid="system-event-hint"
      className="group select-none"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        gap: 6,
        margin: "4px 16px",
        padding: "4px 12px",
        borderRadius: 10,
        background: "var(--glass-bg, rgba(255,255,255,0.05))",
        border: "1px solid var(--glass-border, rgba(255,255,255,0.10))",
        fontSize: 11,
        color: "var(--text-muted, #8a8a9a)",
        backdropFilter: "blur(4px)",
        cursor: "default",
      }}
    >
      <span style={{ fontSize: 13, lineHeight: 1 }}>{icon}</span>
      <span>{message}</span>
      {canManage && (
        <span className="opacity-0 group-hover:opacity-100 transition-opacity" style={{ display: "flex", gap: 2 }}>
          <button
            data-testid="event-edit-btn"
            style={{ fontSize: 11, color: "var(--text-muted)", padding: "0 3px" }}
            className="hover:text-indigo-400"
            onClick={() => { setDraftName(event.project_name ?? ""); setEditing(true); }}
            title="編輯專案名稱"
          >
            ✎
          </button>
          <button
            data-testid="event-delete-btn"
            style={{ fontSize: 11, color: "var(--text-muted)", padding: "0 3px" }}
            className="hover:text-red-400"
            onClick={() => onDeleteProject?.(event.project_id!)}
            title="刪除專案"
          >
            ✕
          </button>
        </span>
      )}
    </div>
  );
}
