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

  const handleMatchSuccess = async (personaId: string, _greetingMessage: string, _expertName: string) => {
    // Reload expert sidebar so newly auto-generated expert appears
    if (currentRole?.id) {
      try {
        const { seedExpertCache } = useCoOSStore.getState();
        const expRes = await fetch(`/api/m6_2/roles/${currentRole.id}/experts`);
        if (expRes.ok) seedExpertCache(await expRes.json());
      } catch { /* non-fatal */ }
    }

    // [FIX-05] Switch expert — this triggers loadHistory which fetches greeting from DB.
    // DO NOT manually inject greeting here: confirm_match already saved it to chat_transcripts.
    setActiveExpert(personaId);
    onMatch?.(personaId);
  };

  return (
    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
      <button
        data-testid="match-btn"
        onClick={() => setShowModal(true)}
        style={{
          flex: 1,
          padding: "8px 12px",
          fontSize: 13,
          fontWeight: 600,
          background: "var(--glass-bg)",
          color: "var(--role-primary, #6366f1)",
          border: "1px solid var(--glass-border)",
          borderRadius: 10,
          cursor: "pointer",
          transition: "background 0.15s",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--glass-border)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "var(--glass-bg)")}
      >
        + 配對
      </button>

      {currentPersonaId && (
        <button
          data-testid="rematch-btn"
          onClick={() => setShowRematch(true)}
          style={{
            padding: "8px",
            fontSize: 14,
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "var(--text-muted)",
            borderRadius: 8,
            transition: "color 0.15s",
          }}
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
