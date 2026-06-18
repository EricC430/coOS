/**
 * M3.4.1 -- Expert Sidebar (Dual-Track)
 *
 * SPEC: docs/modules/M3_4_multi_agent_helper_SPEC.md SS7.1
 * [R03 SS1] Tool AI + persona AI dual-track architecture
 * [R05 §therapy alliance] Persona unlocked only via match flow, not direct click
 * Anti-pattern: do NOT allow direct click on persona to start chat -- requires match ritual
 *
 * [FIX-02] No self-managed width — fills parent container (width is controlled by parent resize)
 * [FIX-06] All colours use CSS variables for dark mode support
 */

import React, { useState } from "react";
import type { Expert } from "../../../stores/m3_1_global_store";
import { useCoOSStore } from "../../../stores/m3_1_global_store";
import { ExpertItem } from "./ExpertItem";

interface Props {
  activeExperts: Expert[];
  allExperts?: Expert[];
  activeExpertId?: string;
  onSelectTool: () => void;
  onSelectPersona: (expert: Expert) => void;
  onDeleteExpert?: (expertId: string) => Promise<void>;
}

export function ExpertSidebar({
  activeExperts,
  activeExpertId,
  onSelectTool,
  onSelectPersona,
  onDeleteExpert,
}: Props) {
  const [matchHint, setMatchHint] = useState<string | null>(null);
  // [GAP-A4][RISK-17] last-expert deletion confirmation state
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const { currentRole } = useCoOSStore();

  const handlePersonaClick = (expert: Expert) => {
    // [R05 §therapy alliance] Direct click switches to that expert's chat room
    onSelectPersona(expert);
  };

  const handleDeleteClick = (expertId: string) => {
    if (activeExperts.length === 1) {
      // [RISK-17] Last expert: require confirmation
      setDeleteConfirmId(expertId);
    } else if (onDeleteExpert) {
      onDeleteExpert(expertId);
    }
  };

  const handleConfirmLastDelete = () => {
    if (deleteConfirmId && onDeleteExpert) {
      onDeleteExpert(deleteConfirmId);
    }
    setDeleteConfirmId(null);
  };

  const roleName = currentRole?.name ?? "AI 幫手";

  const TOOL_AI: Expert & { isToolType: boolean } = {
    id: "__tool__",
    expertName: "工具型 AI",
    trustLevel: 5,
    isToolType: true,
  };

  return (
    // [FIX-02] width: 100% fills the parent resizable container; [FIX-06] CSS vars for dark mode
    <div
      className="expert-sidebar"
      style={{
        display: "flex",
        flexDirection: "column",
        width: "100%",
        height: "100%",
        overflowY: "auto",
        background: "var(--bg-surface)",
        borderRight: "1px solid var(--glass-border)",
      }}
    >
      <div style={{
        padding: "12px 12px 8px",
        fontWeight: 600,
        fontSize: 13,
        color: "var(--text-secondary)",
        borderBottom: "1px solid var(--glass-border)",
      }}>
        💬 {roleName}聊天室
      </div>

      {/* Tool AI -- always first */}
      <ExpertItem
        expert={TOOL_AI}
        isActive={!activeExpertId || activeExpertId === "__tool__"}
        onClick={onSelectTool}
        icon="🤖"
      />

      {activeExperts.length > 0 && (
        <div style={{ margin: "4px 12px", borderTop: "1px solid var(--glass-border)" }} />
      )}

      {/* Unlocked personas -- each is an independent chat room */}
      {activeExperts.map((expert) => (
        <div key={expert.id} style={{ position: "relative" }}>
          <ExpertItem
            expert={expert}
            isActive={activeExpertId === expert.id}
            onClick={() => handlePersonaClick(expert)}
            onDelete={onDeleteExpert ? handleDeleteClick : undefined}
          />
          {matchHint === expert.id && (
            <div
              data-testid="match-required-hint"
              style={{
                position: "absolute",
                left: 0, right: 0,
                bottom: "100%",
                marginBottom: 4,
                background: "var(--bg-base)",
                border: "1px solid var(--glass-border)",
                color: "var(--text-primary)",
                fontSize: 11,
                borderRadius: 6,
                padding: "4px 8px",
                textAlign: "center",
                pointerEvents: "none",
              }}
            >
              請透過「配對」按鈕開始對話
            </div>
          )}
        </div>
      ))}

      {/* [RISK-17] Last-expert deletion confirmation modal */}
      {deleteConfirmId && (
        <div
          data-testid="last-expert-confirm-modal"
          style={{
            margin: "8px",
            padding: "8px",
            background: "rgba(239,68,68,0.08)",
            border: "1px solid rgba(239,68,68,0.3)",
            borderRadius: 8,
            fontSize: 12,
          }}
        >
          <p style={{ color: "#ef4444", fontWeight: 600, marginBottom: 4 }}>刪除最後一位專家？</p>
          <p style={{ color: "var(--text-secondary)", marginBottom: 8 }}>刪除後此角色將無 AI 專家可對話，需重新配對。</p>
          <div style={{ display: "flex", gap: 4 }}>
            <button
              data-testid="confirm-last-delete"
              style={{
                flex: 1, background: "#ef4444", color: "white",
                border: "none", borderRadius: 6, padding: "4px 8px",
                fontSize: 12, cursor: "pointer",
              }}
              onClick={handleConfirmLastDelete}
            >
              確認刪除
            </button>
            <button
              style={{
                flex: 1, background: "var(--glass-bg)",
                color: "var(--text-secondary)",
                border: "1px solid var(--glass-border)",
                borderRadius: 6, padding: "4px 8px",
                fontSize: 12, cursor: "pointer",
              }}
              onClick={() => setDeleteConfirmId(null)}
            >
              取消
            </button>
          </div>
        </div>
      )}

      <div style={{ flex: 1 }} />
      <div style={{
        padding: "8px 12px",
        borderTop: "1px solid var(--glass-border)",
        fontSize: 11,
        color: "var(--text-muted)",
        textAlign: "center",
      }}>
        配對更多專家
      </div>
    </div>
  );
}
