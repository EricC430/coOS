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
import { ExpertItem } from "./ExpertItem";

const TOOL_AI: Expert & { isToolType: boolean } = {
  id: "__tool__",
  expertName: "工具型 AI",
  trustLevel: 5,
  isToolType: true,
};

interface Props {
  activeExperts: Expert[];
  allExperts?: Expert[];
  activeExpertId?: string;
  onSelectTool: () => void;
  onSelectPersona: (expert: Expert) => void;
}

export function ExpertSidebar({
  activeExperts,
  activeExpertId,
  onSelectTool,
  onSelectPersona,
}: Props) {
  const [matchHint, setMatchHint] = useState<string | null>(null);

  const handlePersonaClick = (expert: Expert) => {
    // [R05 §therapy alliance] Cannot start chat by clicking -- must match
    setMatchHint(expert.id);
    setTimeout(() => setMatchHint(null), 3000);
  };

  return (
    <div className="flex flex-col w-48 border-r bg-gray-50 h-full overflow-y-auto">
      <div className="px-3 py-3 font-semibold text-sm text-gray-600">🤖 AI 幫手</div>

      {/* Tool AI -- always first, not deletable */}
      <ExpertItem
        expert={TOOL_AI}
        isActive={!activeExpertId || activeExpertId === "__tool__"}
        onClick={onSelectTool}
      />

      <div className="mx-3 my-1 border-t" />

      {/* Unlocked personas only */}
      {activeExperts.map((expert) => (
        <div key={expert.id} className="relative">
          <ExpertItem
            expert={expert}
            isActive={activeExpertId === expert.id}
            onClick={() => handlePersonaClick(expert)}
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

      <div className="flex-1" />
      <div className="px-3 py-2 border-t">
        <div className="text-xs text-gray-400 text-center">配對更多專家</div>
      </div>
    </div>
  );
}
