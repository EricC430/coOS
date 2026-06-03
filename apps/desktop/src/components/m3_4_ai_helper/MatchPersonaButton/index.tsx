/**
 * M3.4.2 -- Dynamic Persona Matching Controller
 * [R05 §therapy alliance] Match is the entry ritual -- user describes state, not picks persona
 * [R09 SS4 SDT] "My choice" feeling maintained through state description flow
 */

import React, { useState } from "react";
import { useCoOSStore } from "../../../stores/m3_1_global_store";
import { MatchStateModal } from "./MatchStateModal";

interface Props {
  currentPersonaId?: string;
  onMatch?: (personaId: string) => void;
}

export function MatchPersonaButton({ currentPersonaId, onMatch }: Props) {
  const [showModal, setShowModal] = useState(false);
  const [showRematch, setShowRematch] = useState(false);
  const { setActiveExpert, currentRole } = useCoOSStore();

  const handleMatch = async (stateDescription: string, excludePersonaId?: string) => {
    const res = await fetch("/api/m4_1/match_persona", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        current_state_description: stateDescription,
        current_role_id: currentRole?.id,
        exclude_persona_id: excludePersonaId,
      }),
    });
    if (!res.ok) throw new Error("match_failed");
    const { persona_id } = await res.json();
    setActiveExpert(persona_id);
    onMatch?.(persona_id);
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
          onMatch={handleMatch}
          onClose={() => setShowModal(false)}
        />
      )}

      {showRematch && (
        <MatchStateModal
          onMatch={handleMatch}
          onClose={() => setShowRematch(false)}
          excludePersonaId={currentPersonaId}
        />
      )}
    </div>
  );
}
