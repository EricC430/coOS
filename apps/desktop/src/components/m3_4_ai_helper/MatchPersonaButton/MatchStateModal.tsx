/**
 * M3.4.2 -- Match State Modal
 * [R05 §therapy alliance] Match flow: user describes state -> system recommends persona
 * This is the entry ritual for persona engagement
 */

import React, { useState } from "react";
import { useCoOSStore } from "../../../stores/m3_1_global_store";

interface Props {
  onMatch: (stateDescription: string, excludePersonaId?: string) => Promise<void>;
  onClose: () => void;
  excludePersonaId?: string;
}

export function MatchStateModal({ onMatch, onClose, excludePersonaId }: Props) {
  const [stateInput, setStateInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleConfirm = async () => {
    if (!stateInput.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await onMatch(stateInput.trim(), excludePersonaId);
      onClose();
    } catch {
      setError("配對失敗，請稍後重試");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div
        data-testid="match-state-modal"
        className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4"
      >
        <div className="px-6 pt-5 pb-3 border-b">
          <h3 className="font-semibold">
            {excludePersonaId ? "🔄 重新配對專家" : "配對你的 AI 專家"}
          </h3>
        </div>
        <div className="px-6 py-4 space-y-3">
          <p className="text-sm text-gray-500">描述你目前的情境或需求，系統將推薦最合適的專家</p>
          <textarea
            data-testid="state-input"
            className="w-full border rounded-lg p-3 text-sm resize-none"
            rows={4}
            value={stateInput}
            onChange={(e) => setStateInput(e.target.value)}
            placeholder="例：我最近在準備期末考，微積分還沒搞懂..."
            autoFocus
          />
          {error && <p className="text-sm text-red-500">{error}</p>}
        </div>
        <div className="flex justify-end gap-3 px-6 pb-5">
          <button onClick={onClose} className="text-sm text-gray-500 hover:text-gray-700">
            取消
          </button>
          <button
            data-testid="confirm-match-btn"
            onClick={handleConfirm}
            disabled={!stateInput.trim() || loading}
            className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg disabled:opacity-40"
          >
            {loading ? "配對中..." : "送出配對請求"}
          </button>
        </div>
      </div>
    </div>
  );
}
