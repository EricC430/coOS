import React, { useState } from "react";
import { SocialPost, createPostDraft, publishPost, likePost } from "./api";
import { useCoOSStore } from "../../stores/m3_1_global_store";

interface PostsFeedProps {
  posts: SocialPost[];
  communityId: string;
  onRefresh: () => void;
}

export const PostsFeed: React.FC<PostsFeedProps> = ({
  posts,
  communityId,
  onRefresh,
}) => {
  const { xpBalance } = useCoOSStore();
  const [content, setContent] = useState("");
  const [kind, setKind] = useState("achievement");
  const [loading, setLoading] = useState(false);

  // Draft workflow
  const [activeDraft, setActiveDraft] = useState<{ id: string; warning: string } | null>(null);
  const [submittingPublish, setSubmittingPublish] = useState(false);

  // Social Pressure Toggle state
  const [pressureMode, setPressureMode] = useState<"friends" | "stranger">("friends");

  // Read implicit state for anxiety detection (from Zustand or mock safe default if not fully integrated)
  const implicitState = { label: "normal", confidence: 0.5 }; // Fallback or can read from store if exists

  const handleCreateDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim() || loading) return;

    setLoading(true);
    try {
      const res = await createPostDraft({
        community_id: communityId,
        content: content.trim(),
        kind,
      });
      setActiveDraft({
        id: res.id,
        warning: res.privacy_warning || "此貼文將對所有社群成員公開，請確認無敏感個人隱私資訊。",
      });
    } catch (err) {
      alert(err instanceof Error ? err.message : "建立草稿失敗");
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmPublish = async () => {
    if (!activeDraft || submittingPublish) return;
    setSubmittingPublish(true);
    try {
      const res = await publishPost(activeDraft.id);
      if (res.published) {
        setContent("");
        setActiveDraft(null);
        onRefresh();
      } else {
        alert("發布失敗，可能未通過隱私審查");
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "發布貼文失敗");
    } finally {
      setSubmittingPublish(false);
    }
  };

  const handleLike = async (postId: string) => {
    try {
      await likePost(postId);
      onRefresh();
    } catch (err) {
      console.error("Like failed:", err);
    }
  };

  // Determine display author
  const getAuthorDisplay = (post: SocialPost) => {
    if (pressureMode === "stranger") {
      return "匿名成員";
    }
    return post.author_display || "成員";
  };

  return (
    <div className="bento-card posts-panel" data-testid="posts-feed" data-community-id={communityId}>
      <div className="flex justify-between items-center pb-2 border-b border-glass-border">
        <div className="bento-card-title">
          <span className="card-icon">💬</span> 動態與成就
        </div>

        {/* Social Pressure Mode Selector */}
        <div className="flex items-center gap-2">
          <label className="text-2xs text-text-muted">社交模式:</label>
          <select
            className="bg-bg-card border border-glass-border rounded px-2 py-1 text-2xs text-text-primary outline-none"
            value={pressureMode}
            onChange={(e) => setPressureMode(e.target.value as "friends" | "stranger")}
            data-testid="pressure-select"
          >
            <option value="friends">朋友圈模式</option>
            <option value="stranger">陌生人匿名模式</option>
          </select>
        </div>
      </div>

      {/* Anxiety Warning Suggestion */}
      {implicitState.label === "anxiety" && implicitState.confidence > 0.7 && (
        <div
          className="privacy-warning-banner flex items-center justify-between"
          data-testid="destress-suggestion"
        >
          <span>💡 偵測到您目前焦慮感較高，建議切換為「陌生人匿名模式」以減輕社交壓力。</span>
          <button
            onClick={() => setPressureMode("stranger")}
            className="text-2xs underline hover:text-white"
          >
            切換
          </button>
        </div>
      )}

      {/* Posts list */}
      <div className="posts-feed flex-1 overflow-y-auto pr-1 my-2">
        {posts.length === 0 ? (
          <div className="empty-state">
            <span className="empty-state-icon">📭</span>
            <span className="empty-state-text">尚無任何動態，發布第一條吧！</span>
          </div>
        ) : (
          posts.map((post) => (
            <div key={post.id} className="post-card" data-testid="achievement-post">
              <div className="post-avatar">
                {getAuthorDisplay(post).substring(0, 1)}
              </div>
              <div className="post-body">
                <div className="flex justify-between items-baseline">
                  <span className="post-author" data-testid="post-author">
                    {getAuthorDisplay(post)}
                  </span>
                  <span className="post-kind-badge">
                    {post.kind === "achievement" ? "🏆 成就" : post.kind === "milestone" ? "🚩 里程碑" : "✨ 鼓勵"}
                  </span>
                </div>
                <p className="post-content">{post.content}</p>
                <div className="post-actions">
                  <button
                    className="post-action-btn"
                    onClick={() => handleLike(post.id)}
                    title="按讚"
                  >
                    👍 {post.likes_count}
                  </button>
                  <span className="text-2xs text-text-muted">
                    驗證次數: {post.validation_count}
                  </span>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Compose bar */}
      <form onSubmit={handleCreateDraft} className="compose-bar">
        <select
          className="bg-transparent text-xs text-text-secondary outline-none border-r border-glass-border pr-2 cursor-pointer"
          value={kind}
          onChange={(e) => setKind(e.target.value)}
        >
          <option value="achievement">🏆 成就</option>
          <option value="encouragement">✨ 鼓勵</option>
          <option value="milestone">🚩 里程碑</option>
        </select>
        <input
          type="text"
          className="compose-input"
          placeholder="分享你的成就或鼓勵..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
          required
        />
        <button
          type="submit"
          className="compose-submit"
          disabled={loading || !content.trim()}
        >
          {loading ? "處理中..." : "傳送"}
        </button>
      </form>

      {/* Privacy Approval Alert Modal */}
      {activeDraft && (
        <div className="stake-modal-backdrop" data-testid="privacy-warning-modal">
          <div className="stake-modal">
            <h3>🔒 隱私與公開確認</h3>
            <p className="text-xs text-text-secondary mb-4 leading-relaxed" data-testid="privacy-warning">
              {activeDraft.warning}
            </p>
            <div className="stake-actions">
              <button
                className="stake-confirm-btn"
                onClick={handleConfirmPublish}
                disabled={submittingPublish}
                data-testid="publish-btn"
              >
                {submittingPublish ? "發布中..." : "確認公開發布"}
              </button>
              <button
                className="stake-cancel-btn"
                onClick={() => setActiveDraft(null)}
                disabled={submittingPublish}
              >
                取消
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
