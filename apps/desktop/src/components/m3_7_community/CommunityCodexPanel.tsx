import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { CommunityCodex, updateCodex } from "./api";

interface CommunityCodexPanelProps {
  codex: CommunityCodex | null;
  loading: boolean;
  communityId: string;
  onUpdate: () => void;
}

export const CommunityCodexPanel: React.FC<CommunityCodexPanelProps> = ({
  codex,
  loading,
  communityId,
  onUpdate,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [goal, setGoal] = useState("");
  const [vision, setVision] = useState("");
  const [codexText, setCodexText] = useState("");
  const [rules, setRules] = useState<string[]>([]);
  const [quotes, setQuotes] = useState<string[]>([]);
  const [newRule, setNewRule] = useState("");
  const [newQuote, setNewQuote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (codex) {
      setGoal(codex.goal || "");
      setVision(codex.vision || "");
      setCodexText(codex.codex || "");
      setRules(codex.rules || []);
      setQuotes(codex.quotes || []);
    }
  }, [codex, isEditing]);

  const handleAddRule = () => {
    if (newRule.trim()) {
      setRules([...rules, newRule.trim()]);
      setNewRule("");
    }
  };

  const handleRemoveRule = (index: number) => {
    setRules(rules.filter((_, idx) => idx !== index));
  };

  const handleAddQuote = () => {
    if (newQuote.trim()) {
      setQuotes([...quotes, newQuote.trim()]);
      setNewQuote("");
    }
  };

  const handleRemoveQuote = (index: number) => {
    setQuotes(quotes.filter((_, idx) => idx !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!communityId) return;
    try {
      setSubmitting(true);
      await updateCodex(communityId, {
        goal,
        vision,
        codex: codexText,
        rules,
        quotes,
      });
      setIsEditing(false);
      onUpdate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "更新共識失敗");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="bento-card codex-panel skeleton-card">
        <div className="bento-card-title">
          <span className="card-icon">📜</span> 社群共識
        </div>
        <div className="h-4 w-1/3 skeleton-line mt-4" />
        <div className="h-3 w-3/4 skeleton-line mt-2" />
        <div className="h-4 w-1/4 skeleton-line mt-4" />
        <div className="h-3 w-5/6 skeleton-line mt-2" />
      </div>
    );
  }

  if (!codex) {
    return (
      <div className="bento-card codex-panel">
        <div className="bento-card-title">
          <span className="card-icon">📜</span> 社群共識
        </div>
        <div className="empty-state">
          <span className="empty-state-icon">❔</span>
          <span className="empty-state-text">未載入社群共識資料</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bento-card codex-panel" data-testid="codex-panel">
      <div className="bento-card-title flex justify-between items-center w-full">
        <div className="flex items-center gap-1.5">
          <span className="card-icon">📜</span> 社群共識
        </div>
        {communityId && communityId !== "__add__" && (
          <button
            type="button"
            className="edit-codex-btn"
            onClick={() => setIsEditing(true)}
            data-testid="edit-codex-btn"
          >
            ✏️ 編輯
          </button>
        )}
      </div>
      
      <div className="flex flex-col gap-4 overflow-y-auto pr-1 flex-1">
        {codex.goal && (
          <div className="codex-section">
            <div className="codex-label">Goal / 目標</div>
            <div className="codex-value">{codex.goal}</div>
          </div>
        )}

        {codex.vision && (
          <div className="codex-section">
            <div className="codex-label">Vision / 願景</div>
            <div className="codex-value">{codex.vision}</div>
          </div>
        )}

        {codex.codex && (
          <div className="codex-section">
            <div className="codex-label">Codex / 行動守則</div>
            <div className="codex-value">{codex.codex}</div>
          </div>
        )}

        {codex.rules && codex.rules.length > 0 && (
          <div className="codex-section">
            <div className="codex-label">Rules / 規範</div>
            <div className="codex-tags">
              {codex.rules.map((rule, idx) => (
                <span key={idx} className="codex-tag">
                  📌 {rule}
                </span>
              ))}
            </div>
          </div>
        )}

        {codex.quotes && codex.quotes.length > 0 && (
          <div className="codex-section">
            <div className="codex-label">Quotes / 金句</div>
            <div className="flex flex-col gap-2 mt-1">
              {codex.quotes.map((quote, idx) => (
                <div
                  key={idx}
                  className="pl-3 border-l-2 border-gold-accent italic text-xs text-text-secondary"
                >
                  「 {quote} 」
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Edit Codex Modal */}
      {isEditing && createPortal(
        <div className="modal-overlay" onClick={() => setIsEditing(false)}>
          <div className="modal-content glass-panel" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>📜 編輯社群共識</h2>
              <button className="modal-close" onClick={() => setIsEditing(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit} className="modal-form">
              <div className="form-group">
                <label>Goal / 目標</label>
                <input
                  type="text"
                  className="form-input"
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  placeholder="例如：共同度過面試難關"
                />
              </div>

              <div className="form-group">
                <label>Vision / 願景</label>
                <input
                  type="text"
                  className="form-input"
                  value={vision}
                  onChange={(e) => setVision(e.target.value)}
                  placeholder="例如：每個人都拿到心儀的 Offer"
                />
              </div>

              <div className="form-group">
                <label>Codex / 行動守則</label>
                <textarea
                  className="form-input"
                  value={codexText}
                  onChange={(e) => setCodexText(e.target.value)}
                  placeholder="例如：每日打卡、每週分享、真誠反饋"
                  rows={3}
                />
              </div>

              <div className="form-group">
                <label>Rules / 規範列表</label>
                <div className="modal-list-edit">
                  {rules.map((rule, idx) => (
                    <div key={idx} className="list-edit-item flex items-center justify-between gap-2 text-xs">
                      <span>📌 {rule}</span>
                      <button type="button" onClick={() => handleRemoveRule(idx)} className="text-red-500 hover:text-red-700">🗑️</button>
                    </div>
                  ))}
                  <div className="flex gap-2 mt-2">
                    <input
                      type="text"
                      className="form-input flex-1"
                      value={newRule}
                      onChange={(e) => setNewRule(e.target.value)}
                      placeholder="新增規範項目"
                    />
                    <button type="button" onClick={handleAddRule} className="modal-add-btn">新增</button>
                  </div>
                </div>
              </div>

              <div className="form-group">
                <label>Quotes / 金句列表</label>
                <div className="modal-list-edit">
                  {quotes.map((quote, idx) => (
                    <div key={idx} className="list-edit-item flex items-center justify-between gap-2 text-xs">
                      <span className="italic">「 {quote} 」</span>
                      <button type="button" onClick={() => handleRemoveQuote(idx)} className="text-red-500 hover:text-red-700">🗑️</button>
                    </div>
                  ))}
                  <div className="flex gap-2 mt-2">
                    <input
                      type="text"
                      className="form-input flex-1"
                      value={newQuote}
                      onChange={(e) => setNewQuote(e.target.value)}
                      placeholder="新增激勵金句"
                    />
                    <button type="button" onClick={handleAddQuote} className="modal-add-btn">新增</button>
                  </div>
                </div>
              </div>

              <div className="modal-actions mt-4 flex gap-2">
                <button type="button" className="btn-secondary" onClick={() => setIsEditing(false)} disabled={submitting}>
                  取消
                </button>
                <button type="submit" className="btn-primary" disabled={submitting}>
                  {submitting ? "儲存中..." : "儲存變更"}
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

