import React, { useState } from "react";
import { createPortal } from "react-dom";
import { CommitmentItem, TaskToValidate, ActiveStake, createPostDraft, publishPost } from "./api";

interface CommitmentClosedLoopProps {
  commitments: CommitmentItem[];
  toValidate: TaskToValidate[];
  activeStakes: ActiveStake[];
  promises: string[];
  onStakeClick: (taskTitle: string) => void;
  onValidate: (postId: string, evidenceUrl?: string) => void;
  loading: boolean;
  communityId: string;
  onRefresh: () => void;
}

export const CommitmentClosedLoop: React.FC<CommitmentClosedLoopProps> = ({
  commitments,
  toValidate,
  activeStakes,
  promises,
  onStakeClick,
  onValidate,
  loading,
  communityId,
  onRefresh,
}) => {
  // Commitment Creation States
  const [isCreating, setIsCreating] = useState(false);
  const [stage, setStage] = useState<1 | 2>(1); // 1: Input/Draft, 2: Confirm/Publish
  const [content, setContent] = useState("");
  const [kind, setKind] = useState("achievement"); // achievement | milestone
  const [draftId, setDraftId] = useState<string | null>(null);
  const [warning, setWarning] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Validation States
  const [validatingTask, setValidatingTask] = useState<TaskToValidate | null>(null);
  const [attachEvidence, setAttachEvidence] = useState(false);
  const [evidenceUrl, setEvidenceUrl] = useState("");

  const handleCreateDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim() || !communityId) return;

    try {
      setSubmitting(true);
      const res = await createPostDraft({
        community_id: communityId,
        content: content.trim(),
        kind,
      });
      setDraftId(res.id);
      setWarning(res.privacy_warning || "此貼文將公開，請確認不包含個人敏感資訊。");
      setStage(2);
    } catch (err) {
      alert(err instanceof Error ? err.message : "建立草稿失敗");
    } finally {
      setSubmitting(false);
    }
  };

  const handlePublish = async () => {
    if (!draftId) return;
    try {
      setSubmitting(true);
      await publishPost(draftId);
      setIsCreating(false);
      setContent("");
      setStage(1);
      setDraftId(null);
      onRefresh();
    } catch (err) {
      alert(err instanceof Error ? err.message : "發布失敗");
    } finally {
      setSubmitting(false);
    }
  };

  const handleValidationSubmit = () => {
    if (!validatingTask) return;
    onValidate(validatingTask.id, attachEvidence ? evidenceUrl.trim() : undefined);
    setValidatingTask(null);
    setAttachEvidence(false);
    setEvidenceUrl("");
  };

  if (loading) {
    return (
      <div className="bento-card commitment-panel skeleton-card">
        <div className="bento-card-title">
          <span className="card-icon">🔄</span> 行動與承諾閉環
        </div>
        <div className="h-24 skeleton-line mt-4" />
        <div className="h-24 skeleton-line mt-2" />
      </div>
    );
  }

  return (
    <div className="bento-card commitment-panel" data-testid="commitment-panel">
      <div className="bento-card-title">
        <span className="card-icon">🔄</span> 行動與承諾閉環
      </div>

      <div className="commitment-sections flex-1 overflow-y-auto pr-1 my-2">
        {/* Section 1: Tasks (to claim) */}
        <div className="flex flex-col gap-2">
          <div className="commitment-section-title">任務對賭 / Tasks (to claim)</div>
          {promises.length === 0 ? (
            <div className="text-2xs text-text-muted pl-1">目前沒有可進行對賭的任務</div>
          ) : (
            <div className="flex flex-col gap-1.5">
              {promises.map((promise, idx) => (
                <div
                  key={idx}
                  className="commitment-item flex justify-between items-center hover:border-gold-accent transition-colors"
                >
                  <span className="font-medium text-xs text-text-primary">{promise}</span>
                  <button
                    onClick={() => onStakeClick(promise)}
                    className="validate-btn"
                    style={{ fontSize: "10px", padding: "2px 8px" }}
                  >
                    🎲 質押
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Section 2: Commitments & Active Stakes */}
        <div className="flex flex-col gap-2 mt-4">
          <div className="flex justify-between items-center w-full">
            <div className="commitment-section-title">公開承諾 / Commitments</div>
            {communityId && communityId !== "__add__" && (
              <button
                type="button"
                className="create-commitment-btn"
                onClick={() => {
                  setIsCreating(true);
                  setStage(1);
                }}
                data-testid="create-commitment-btn"
              >
                ✨ 建立公開承諾
              </button>
            )}
          </div>
          
          {/* Active Stakes */}
          {activeStakes.length > 0 && (
            <div className="flex flex-col gap-1.5 mb-2">
              {activeStakes.map((stake) => (
                <div key={stake.id} className="commitment-item">
                  <div className="flex justify-between items-center">
                    <span className="font-semibold text-xs text-text-primary">XP 質押對賭</span>
                    <span className="stake-pill">💰 {stake.xp_amount} XP</span>
                  </div>
                  {stake.deadline && (
                    <div className="commitment-meta">
                      ⏱️ 截止: {new Date(stake.deadline).toLocaleString()}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Commitments */}
          {commitments.length === 0 && activeStakes.length === 0 ? (
            <div className="text-2xs text-text-muted pl-1">無作用中的公開承諾</div>
          ) : (
            <div className="flex flex-col gap-1.5">
              {commitments.map((c) => (
                <div key={c.id} className="commitment-item">
                  <span className="font-medium text-xs text-text-primary">{c.content}</span>
                  <div className="commitment-meta">
                    <span>型別: {c.kind === "achievement" ? "🏆 成就" : c.kind === "milestone" ? "🚩 里程碑" : "✨ 鼓勵"}</span>
                    <span>•</span>
                    <span>同儕驗證: {c.validation_count} 次</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Section 3: Peer Validation */}
        <div className="flex flex-col gap-2 mt-4">
          <div className="commitment-section-title">同儕驗證 / Validation</div>
          {toValidate.length === 0 ? (
            <div className="text-2xs text-text-muted pl-1">沒有需要您驗證的他人承諾</div>
          ) : (
            <div className="flex flex-col gap-1.5">
              {toValidate.map((tv) => (
                <div key={tv.id} className="commitment-item flex justify-between items-center">
                  <div className="flex flex-col gap-1">
                    <span className="font-medium text-xs text-text-primary">{tv.content}</span>
                    <span className="text-3xs text-text-muted">來自成員: {tv.author_id.substring(0, 8)}...</span>
                  </div>
                  <button
                    onClick={() => setValidatingTask(tv)}
                    className="validate-btn"
                  >
                    ✓ 驗證
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {isCreating && createPortal(
        <div className="modal-overlay" onClick={() => setIsCreating(false)}>
          <div className="modal-content glass-panel" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>✨ 建立公開承諾</h2>
              <button className="modal-close" onClick={() => setIsCreating(false)}>×</button>
            </div>

            {stage === 1 ? (
              <form onSubmit={handleCreateDraft} className="modal-form">
                <div className="form-group">
                  <label>承諾類型</label>
                  <select
                    className="form-select"
                    value={kind}
                    onChange={(e) => setKind(e.target.value)}
                  >
                    <option value="achievement">🏆 挑戰成就</option>
                    <option value="milestone">🚀 里程碑進度</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>承諾內容</label>
                  <textarea
                    className="form-input"
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="請輸入您的公開承諾內容..."
                    rows={4}
                    required
                  />
                </div>

                <div className="privacy-warning-card p-3 border border-yellow-500/20 bg-yellow-500/10 rounded-lg text-2xs text-text-secondary leading-normal mb-4">
                  ⚠️ 注意：公開承諾將對此社群中的所有成員公開，請確保內容不包含您或他人的敏感個人隱私資訊。
                </div>

                <div className="modal-actions flex gap-2">
                  <button type="button" className="btn-secondary" onClick={() => setIsCreating(false)} disabled={submitting}>
                    取消
                  </button>
                  <button type="submit" className="btn-primary" disabled={submitting || !content.trim()}>
                    {submitting ? "準備中..." : "下一步 (隱私檢核)"}
                  </button>
                </div>
              </form>
            ) : (
              <div className="modal-form flex flex-col gap-4">
                <div className="privacy-warning-box p-4 border border-gold-accent bg-gold-accent/10 rounded-lg">
                  <h3 className="font-bold text-xs text-text-primary mb-1">🔒 前端隱私檢核提示</h3>
                  <p className="text-xs text-text-secondary leading-normal">{warning}</p>
                </div>

                <p className="text-2xs text-text-muted leading-normal">
                  此貼文發布後，社群成員將可以點擊「✓ 驗證」對此承諾進行同儕背書。
                </p>

                <div className="modal-actions flex gap-2">
                  <button type="button" className="btn-secondary" onClick={() => setStage(1)} disabled={submitting}>
                    上一步修改
                  </button>
                  <button type="button" className="btn-primary" onClick={handlePublish} disabled={submitting}>
                    {submitting ? "發布中..." : "✓ 確認發布公開承諾"}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>,
        document.body
      )}

      {validatingTask && createPortal(
        <div className="modal-overlay" onClick={() => setValidatingTask(null)}>
          <div className="modal-content glass-panel" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>✓ 同儕承諾驗證</h2>
              <button className="modal-close" onClick={() => setValidatingTask(null)}>×</button>
            </div>
            
            <div className="modal-form flex flex-col gap-3">
              <div className="validation-target-box p-3 bg-white/5 border border-white/10 rounded-lg mb-2">
                <span className="text-3xs text-text-muted">驗證對象承諾：</span>
                <p className="text-xs font-semibold mt-1 text-text-primary">{validatingTask.content}</p>
              </div>

              <div className="form-group flex items-center gap-2 py-2">
                <input
                  id="attach-evidence-chk"
                  type="checkbox"
                  checked={attachEvidence}
                  onChange={(e) => setAttachEvidence(e.target.checked)}
                  className="w-4 h-4 rounded accent-gold-accent"
                />
                <label htmlFor="attach-evidence-chk" className="cursor-pointer text-xs font-semibold">附上驗證證據 (可選)</label>
              </div>

              {attachEvidence && (
                <div className="form-group">
                  <label>證據連結 / 網址</label>
                  <input
                    type="url"
                    className="form-input"
                    value={evidenceUrl}
                    onChange={(e) => setEvidenceUrl(e.target.value)}
                    placeholder="https://example.com/screenshot.jpg"
                    required={attachEvidence}
                  />
                  <div className="evidence-warning-card p-3 border border-red-500/20 bg-red-500/10 rounded-lg text-3xs text-text-secondary leading-normal mt-2">
                    ⚠️ 提醒：如果提供證據網址，該連結不會經過隱私過濾，且社群內的所有成員皆可直接點開此連結。請確保不包含私密個人資訊。
                  </div>
                </div>
              )}

              <p className="text-3xs text-text-muted leading-normal">
                點擊確認後，您將為此成員的承諾進行同儕背書，將計入其驗證次數中。
              </p>

              <div className="modal-actions mt-3 flex gap-2">
                <button type="button" className="btn-secondary" onClick={() => setValidatingTask(null)}>
                  取消
                </button>
                <button type="button" className="btn-primary" onClick={handleValidationSubmit}>
                  確認送出驗證
                </button>
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};
