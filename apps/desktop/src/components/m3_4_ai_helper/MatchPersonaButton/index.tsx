/**
 * M3.4.2 -- Dynamic Persona Matching Controller
 * [R05 §therapy alliance] Match is the entry ritual -- user describes state, not picks persona
 * [R09 SS4 SDT] "My choice" feeling maintained through state description flow
 */

import React, { useState } from "react";
import { useCoOSStore } from "../../../stores/m3_1_global_store";
import { MatchStateModal } from "./MatchStateModal";
import type { ChatMessage } from "../ChatMessageList";

let _greetId = 0;

interface Props {
  currentPersonaId?: string;
  onMatch?: (personaId: string) => void;
  onGreeting?: (msg: ChatMessage) => void;
}

export function MatchPersonaButton({ currentPersonaId, onMatch, onGreeting }: Props) {
  const [showModal, setShowModal] = useState(false);
  const [showRematch, setShowRematch] = useState(false);
  const { setActiveExpert, currentRole } = useCoOSStore();

  const handleMatchSuccess = async (personaId: string, greetingMessage: string, expertName: string) => {
    // Reload expert sidebar so newly auto-generated expert appears
    if (currentRole?.id) {
      try {
        const { seedExpertCache } = useCoOSStore.getState();
        const expRes = await fetch(`/api/m6_2/roles/${currentRole.id}/experts`);
        if (expRes.ok) seedExpertCache(await expRes.json());
      } catch { /* non-fatal */ }
    }

    setActiveExpert(personaId);
    onMatch?.(personaId);

    // [M4.2] Expert initiates the conversation with a greeting
    if (greetingMessage && onGreeting) {
      // Short delay so the sidebar transition finishes before the bubble appears
      await new Promise((r) => setTimeout(r, 600));
      onGreeting({
        id: `greet_${++_greetId}`,
        role: "assistant",
        content: greetingMessage,
        expertName: expertName ?? undefined,
      });
    }
  };

  return (
    <div className="flex gap-2 items-center">
      <button
        data-testid="match-btn"
        onClick={() => setShowModal(true)}
        className="flex-1 py-2 text-sm bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100 font-medium"
      >
        + 配對
      </button>

      {currentPersonaId && (
        <button
          data-testid="rematch-btn"
          onClick={() => setShowRematch(true)}
          className="py-2 px-3 text-sm text-gray-500 hover:text-gray-700"
          title="重新配對"
        >
          🔄
        </button>
      )}

      {showModal && (
        <MatchStateModal
          onSuccess={handleMatchSuccess}
          onClose={() => setShowModal(false)}
        />
      )}

      {showRematch && (
        <MatchStateModal
          onSuccess={handleMatchSuccess}
          onClose={() => setShowRematch(false)}
          excludePersonaId={currentPersonaId}
        />
      )}
    </div>
  );
}
