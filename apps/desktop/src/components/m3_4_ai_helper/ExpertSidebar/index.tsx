/**
 * M3.4.1 -- Expert Sidebar (Dual-Track)
 *
 * SPEC: docs/modules/M3_4_multi_agent_helper_SPEC.md SS7.1
 * [R03 SS1] Tool AI + persona AI dual-track architecture
 * [R05 §therapy alliance] Persona unlocked only via match flow, not direct click
 * Anti-pattern: do NOT allow direct click on persona to start chat -- requires match ritual
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
    <div className="flex flex-col w-48 border-r bg-gray-50 h-full overflow-y-auto">
      <div className="px-3 py-3 font-semibold text-sm text-gray-600">💬 {roleName}聊天室</div>

      {/* Tool AI -- always first */}
      <ExpertItem
        expert={TOOL_AI}
        isActive={!activeExpertId || activeExpertId === "__tool__"}
        onClick={onSelectTool}
        icon="🤖"
      />

      {activeExperts.length > 0 && <div className="mx-3 my-1 border-t" />}

      {/* Unlocked personas -- each is an independent chat room */}
      {activeExperts.map((expert) => (
        <div key={expert.id} className="relative">
          <ExpertItem
            expert={expert}
            isActive={activeExpertId === expert.id}
            onClick={() => handlePersonaClick(expert)}
            onDelete={onDeleteExpert ? handleDeleteClick : undefined}
          />
          {matchHint === expert.id && (
            <div
              data-testid="match-required-hint"
              className="absolute left-0 right-0 bottom-full mb-1 bg-black text-white text-xs rounded px-2 py-1 text-center pointer-events-none"
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
          className="mx-2 my-2 p-2 bg-red-50 border border-red-200 rounded text-xs"
        >
          <p className="text-red-700 font-medium mb-1">刪除最後一位專家？</p>
          <p className="text-red-600 mb-2">刪除後此角色將無 AI 專家可對話，需重新配對。</p>
          <div className="flex gap-1">
            <button
              data-testid="confirm-last-delete"
              className="flex-1 bg-red-500 text-white rounded px-2 py-1 text-xs"
              onClick={handleConfirmLastDelete}
            >
              確認刪除
            </button>
            <button
              className="flex-1 bg-gray-200 rounded px-2 py-1 text-xs"
              onClick={() => setDeleteConfirmId(null)}
            >
              取消
            </button>
          </div>
        </div>
      )}

      <div className="flex-1" />
      <div className="px-3 py-2 border-t">
        <div className="text-xs text-gray-400 text-center">配對更多專家</div>
      </div>
    </div>
  );
}
