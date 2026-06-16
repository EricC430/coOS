/**
 * M3.4.2 -- Match State Modal with Preview Confirmation
 * [R05 §therapy alliance] Match flow: user describes state -> system recommends persona -> user confirms (SDT)
 * This is the entry ritual for persona engagement
 */

import React, { useState } from "react";
import { useCoOSStore } from "../../../stores/m3_1_global_store";

interface ExpertPreview {
  id: string;
  name: string;
  backstory: string;
  tone_default: string;
  personality_summary: string;
}

interface Props {
  onSuccess: (personaId: string, greetingMessage: string, expertName: string) => Promise<void>;
  onClose: () => void;
  excludePersonaId?: string;
}

export function MatchStateModal({ onSuccess, onClose, excludePersonaId }: Props) {
  const [step, setStep] = useState<"input" | "preview">("input");
  const [stateInput, setStateInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewData, setPreviewData] = useState<ExpertPreview | null>(null);

  const { currentRole } = useCoOSStore();

  const handleRequestMatch = async () => {
    if (!stateInput.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/m4_1/match_persona", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_state_description: stateInput.trim(),
          current_role_id: currentRole?.id,
          exclude_persona_id: excludePersonaId,
        }),
      });

      if (!res.ok) throw new Error("match_failed");
      const data = await res.json();
      const { matched, persona_id, expert_preview } = data;

      if (!matched || !persona_id || !expert_preview) {
        setError("抱歉，目前無法配對到合適的專家，請調整描述後再試一次。");
        return;
      }

      setPreviewData(expert_preview);
      setStep("preview");
    } catch (err) {
      setError("配對請求失敗，請稍後重試。");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmMatch = async () => {
    if (!previewData) return;
    setLoading(true);
    setError(null);
    try {
      const confirmRes = await fetch("/api/m4_1/confirm_match", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          persona_id: previewData.id,
          role_id: currentRole?.id,
          original_message: stateInput.trim(),
        }),
      });

      if (!confirmRes.ok) throw new Error("confirm_failed");
      const confirmData = await confirmRes.json();
      const { greeting_message, expert_name } = confirmData;

      await onSuccess(previewData.id, greeting_message || "", expert_name || previewData.name);
      onClose();
    } catch (err) {
      setError("確認配對失敗，請稍後重試。");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div
        data-testid="match-state-modal"
        className="bg-[var(--bg-surface)] text-[var(--text-primary)] rounded-xl shadow-2xl w-full max-w-md mx-4 border border-[var(--glass-border)] overflow-hidden transition-all duration-300"
      >
        {/* Header */}
        <div className="px-6 pt-5 pb-3 border-b border-[var(--glass-border)]">
          <h3 className="font-semibold text-lg flex items-center gap-2">
            {step === "input" ? (
              <>
                {excludePersonaId ? "🔄 重新配對專家" : "✨ 配對你的 AI 專家"}
              </>
            ) : (
              <>🎯 推薦的專家人選</>
            )}
          </h3>
        </div>

        {/* Body */}
        <div className="px-6 py-5 space-y-4">
          {step === "input" ? (
            <>
              <p className="text-sm text-[var(--text-secondary)]">
                請用一句話或一段話描述你目前的學習、工作情境或面臨的挑戰，系統會為你媒合最契合人設的專家。
              </p>
              <textarea
                data-testid="state-input"
                className="w-full bg-[var(--bg-base)] border border-[var(--glass-border)] rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--gold-accent)] text-[var(--text-primary)] resize-none"
                rows={4}
                value={stateInput}
                onChange={(e) => setStateInput(e.target.value)}
                placeholder="例：我最近要準備微積分期末考，可是極限跟導數的觀念一直搞不懂，覺得很焦慮..."
                autoFocus
              />
            </>
          ) : (
            previewData && (
              <div className="space-y-4">
                <p className="text-sm text-[var(--text-secondary)]">
                  根據你的情境，系統特別推薦以下專家為你指引：
                </p>

                {/* Expert Card */}
                <div className="p-4 rounded-xl bg-[var(--bg-base)] border border-[var(--glass-border)] space-y-3 relative overflow-hidden">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-[var(--gold-accent)] text-white flex items-center justify-center font-bold text-lg shadow-sm">
                      {previewData.name.charAt(0)}
                    </div>
                    <div>
                      <h4 className="font-bold text-[var(--text-primary)] text-base">{previewData.name}</h4>
                      <span className="inline-block text-xs bg-[var(--edge-trigger-bg)] border border-[var(--edge-trigger-border)] text-[var(--gold-accent)] px-2 py-0.5 rounded-full font-medium mt-0.5">
                        風格：{previewData.tone_default}
                      </span>
                    </div>
                  </div>

                  <div className="space-y-2 text-sm">
                    {previewData.backstory && (
                      <div>
                        <span className="text-xs font-semibold text-[var(--text-muted)] block">專家背景</span>
                        <p className="text-[var(--text-secondary)] leading-relaxed">{previewData.backstory}</p>
                      </div>
                    )}
                    {previewData.personality_summary && (
                      <div>
                        <span className="text-xs font-semibold text-[var(--text-muted)] block">性格特點</span>
                        <p className="text-[var(--text-secondary)] leading-relaxed italic">
                          「{previewData.personality_summary}」
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          )}

          {error && <p className="text-xs text-red-500 font-medium">{error}</p>}
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 px-6 pb-5 border-t border-transparent">
          {step === "input" ? (
            <>
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
              >
                取消
              </button>
              <button
                data-testid="confirm-match-btn"
                onClick={handleRequestMatch}
                disabled={!stateInput.trim() || loading}
                className="px-5 py-2 text-sm bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg disabled:opacity-40 disabled:hover:bg-indigo-600 transition-all font-medium shadow-md"
              >
                {loading ? "分析配對中..." : "送出配對請求"}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setStep("input")}
                disabled={loading}
                className="px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-50 transition-colors"
              >
                返回修改
              </button>
              <button
                data-testid="confirm-match-btn"
                onClick={handleConfirmMatch}
                disabled={loading}
                className="px-5 py-2 text-sm bg-[var(--gold-accent)] hover:opacity-90 text-white rounded-lg disabled:opacity-50 transition-all font-semibold shadow-md"
              >
                {loading ? "建立連線中..." : "確認選擇此專家"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
