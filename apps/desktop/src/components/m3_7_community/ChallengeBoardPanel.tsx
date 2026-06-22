import React, { useState } from "react";
import { createPortal } from "react-dom";
import { ChallengeItem, createChallenge, generateAIChallenge, approveChallenge } from "./api";

interface ChallengeBoardPanelProps {
  challenges: ChallengeItem[];
  loading: boolean;
  communityId: string;
  isAdmin: boolean;
  onUpdate: () => void;
}

export const ChallengeBoardPanel: React.FC<ChallengeBoardPanelProps> = ({
  challenges,
  loading,
  communityId,
  isAdmin,
  onUpdate,
}) => {
  const [isCreating, setIsCreating] = useState(false);
  const [mode, setMode] = useState<"admin" | "ai_reviewed" | "member_rotation">("admin");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [period, setPeriod] = useState("weekly");
  const [submitting, setSubmitting] = useState(false);
  const [generating, setGenerating] = useState(false);

  // Edit / Approve State
  const [editingChallenge, setEditingChallenge] = useState<ChallengeItem | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editDescription, setEditDescription] = useState("");

  const activeChallenges = challenges.filter((c) => !c.is_draft);
  const draftChallenges = challenges.filter((c) => c.is_draft);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !communityId) return;

    try {
      setSubmitting(true);
      await createChallenge(communityId, {
        title: title.trim(),
        description: description.trim(),
        period,
        source: mode,
      });
      setIsCreating(false);
      setTitle("");
      setDescription("");
      onUpdate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "建立挑戰失敗");
    } finally {
      setSubmitting(false);
    }
  };

  const handleAIGenerate = async () => {
    if (!communityId) return;
    try {
      setGenerating(true);
      const res = await generateAIChallenge(communityId);
      setIsCreating(false);
      onUpdate();
      alert(`AI 已成功生成推薦挑戰草稿：\n「${res.title}」\n已加入下方待審查清單！`);
    } catch (err) {
      alert(err instanceof Error ? err.message : "AI 生成失敗");
    } finally {
      setGenerating(false);
    }
  };

  const handleDirectApprove = async (id: string) => {
    try {
      await approveChallenge(id);
      onUpdate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "核准失敗");
    }
  };

  const handleEditApprove = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingChallenge) return;
    try {
      setSubmitting(true);
      await approveChallenge(editingChallenge.id, {
        title: editTitle.trim(),
        description: editDescription.trim(),
      });
      setEditingChallenge(null);
      onUpdate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "核准失敗");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="bento-card challenge-panel skeleton-card">
        <div className="bento-card-title">
          <span className="card-icon">🎯</span> 定期挑戰
        </div>
        <div className="h-20 skeleton-line mt-4" />
        <div className="h-20 skeleton-line mt-2" />
      </div>
    );
  }

  return (
    <div className="bento-card challenge-panel" data-testid="challenge-panel">
      <div className="bento-card-title flex justify-between items-center w-full">
        <div className="flex items-center gap-1.5">
          <span className="card-icon">🎯</span> 定期挑戰
        </div>
        {communityId && communityId !== "__add__" && (
          <button
            type="button"
            className="create-challenge-btn"
            onClick={() => setIsCreating(true)}
            data-testid="create-challenge-btn"
          >
            🎯 建立挑戰
          </button>
        )}
      </div>

      <div className="challenge-content flex-1 overflow-y-auto pr-1 flex flex-col gap-4">
        {/* Pending Review Drafts (Only for Admins) */}
        {isAdmin && draftChallenges.length > 0 && (
          <div className="draft-challenges-section border-b border-dashed border-gray-200 pb-3 mb-1">
            <div className="text-2xs font-bold text-gold-accent uppercase mb-2">待審查挑戰草稿 (僅管理員可見)</div>
            <div className="flex flex-col gap-2">
              {draftChallenges.map((ch) => (
                <div key={ch.id} className="challenge-card draft-card">
                  <div className="flex justify-between items-start gap-2">
                    <span className="challenge-title text-text-primary font-bold">{ch.title}</span>
                    <span className="challenge-badge badge-draft">草稿</span>
                  </div>
                  {ch.description && (
                    <p className="text-2xs text-text-secondary mt-1">{ch.description}</p>
                  )}
                  <div className="flex gap-2 mt-2 justify-end">
                    <button
                      type="button"
                      className="validate-btn text-2xs"
                      onClick={() => {
                        setEditingChallenge(ch);
                        setEditTitle(ch.title);
                        setEditDescription(ch.description || "");
                      }}
                    >
                      ✏️ 編輯並核准
                    </button>
                    <button
                      type="button"
                      className="validate-btn text-2xs"
                      style={{ background: "var(--gold-accent)", color: "var(--bg-base)" }}
                      onClick={() => handleDirectApprove(ch.id)}
                    >
                      ✓ 核准啟動
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Active Challenges */}
        {activeChallenges.length === 0 ? (
          <div className="empty-state py-4">
            <span className="empty-state-icon">🏁</span>
            <span className="empty-state-text">目前尚無進行中的挑戰</span>
          </div>
        ) : (
          <div className="challenge-list flex flex-col gap-2.5">
            {activeChallenges.map((ch) => {
              const isWeekly = ch.period === "weekly";
              const progress = Math.min(100, Math.max(0, ch.progress || 0));

              return (
                <div key={ch.id} className="challenge-card">
                  <div className="flex justify-between items-start gap-2">
                    <span className="challenge-title">{ch.title}</span>
                    <span
                      className={`challenge-badge ${
                        isWeekly ? "badge-weekly" : "badge-monthly"
                      }`}
                    >
                      {isWeekly ? "每週" : "每月"}
                    </span>
                  </div>

                  {ch.description && (
                    <p className="text-xs text-text-secondary line-clamp-2 mt-1">
                      {ch.description}
                    </p>
                  )}

                  <div className="mt-2 flex flex-col gap-1">
                    <div className="flex justify-between text-2xs text-text-muted">
                      <span>進度</span>
                      <span>{progress}%</span>
                    </div>
                    <div className="challenge-progress">
                      <div
                        className="challenge-progress-fill"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>

                  <div className="challenge-meta mt-1 text-2xs">
                    <span>來源: {ch.source === "ai_reviewed" ? "🤖 AI 審核" : ch.source === "member_rotation" ? "👤 成員輪替" : "👤 管理員"}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Create Challenge Modal */}
      {isCreating && createPortal(
        <div className="modal-overlay" onClick={() => setIsCreating(false)}>
          <div className="modal-content glass-panel" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>🎯 建立定期挑戰</h2>
              <button className="modal-close" onClick={() => setIsCreating(false)}>×</button>
            </div>
            
            <div className="mode-tabs flex gap-2 mb-4 border-b border-gray-200 pb-2">
              <button
                type="button"
                className={`tab-btn ${mode === "admin" ? "active" : ""}`}
                onClick={() => setMode("admin")}
              >
                👤 手動配置
              </button>
              <button
                type="button"
                className={`tab-btn ${mode === "ai_reviewed" ? "active" : ""}`}
                onClick={() => setMode("ai_reviewed")}
              >
                🤖 AI 智慧推薦
              </button>
              <button
                type="button"
                className={`tab-btn ${mode === "member_rotation" ? "active" : ""}`}
                onClick={() => setMode("member_rotation")}
              >
                🔄 成員輪替
              </button>
            </div>

            {mode === "ai_reviewed" ? (
              <div className="ai-generation-box py-6 flex flex-col items-center justify-center gap-4 text-center">
                <span className="text-4xl">🤖</span>
                <div>
                  <h3 className="font-bold text-sm">AI 週期挑戰生成器</h3>
                  <p className="text-xs text-text-secondary max-w-xs mt-1">
                    系統將僅讀取社群 L3 統計數據（如完成率、質押總額等），絕不涉及私密內容，生成適合此社群目前的挑戰。
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleAIGenerate}
                  className="btn-primary"
                  style={{ width: "200px" }}
                  disabled={generating}
                >
                  {generating ? "AI 生成中..." : "🤖 生成推薦挑戰草稿"}
                </button>
              </div>
            ) : (
              <form onSubmit={handleCreate} className="modal-form">
                <div className="form-group">
                  <label>挑戰標題</label>
                  <input
                    type="text"
                    className="form-input"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="例如：每日番茄鐘 2 次"
                    required
                  />
                </div>

                <div className="form-group">
                  <label>描述</label>
                  <textarea
                    className="form-input"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="詳細說明挑戰內容及打卡規範"
                    rows={3}
                  />
                </div>

                <div className="form-group">
                  <label>週期</label>
                  <select
                    className="form-select"
                    value={period}
                    onChange={(e) => setPeriod(e.target.value)}
                  >
                    <option value="weekly">📅 每週挑戰</option>
                    <option value="monthly">📅 月度挑戰</option>
                  </select>
                </div>

                <div className="modal-actions mt-4 flex gap-2">
                  <button type="button" className="btn-secondary" onClick={() => setIsCreating(false)} disabled={submitting}>
                    取消
                  </button>
                  <button type="submit" className="btn-primary" disabled={submitting}>
                    {submitting ? "發布中..." : "🚀 發布挑戰"}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>,
        document.body
      )}

      {/* Edit & Approve Modal */}
      {editingChallenge && createPortal(
        <div className="modal-overlay" onClick={() => setEditingChallenge(null)}>
          <div className="modal-content glass-panel" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>✏️ 編輯並核准挑戰</h2>
              <button className="modal-close" onClick={() => setEditingChallenge(null)}>×</button>
            </div>
            <form onSubmit={handleEditApprove} className="modal-form">
              <div className="form-group">
                <label>挑戰標題</label>
                <input
                  type="text"
                  className="form-input"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>描述</label>
                <textarea
                  className="form-input"
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  rows={3}
                />
              </div>

              <div className="modal-actions mt-4 flex gap-2">
                <button type="button" className="btn-secondary" onClick={() => setEditingChallenge(null)} disabled={submitting}>
                  取消
                </button>
                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? "核准中..." : "✓ 核准並啟動挑戰"}
                </button>
              </div>
            </form>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};
