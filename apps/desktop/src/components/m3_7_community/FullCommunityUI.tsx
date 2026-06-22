import React, { useEffect, useState, useCallback } from "react";
import {
  fetchCommunities,
  fetchCodex,
  fetchPosts,
  fetchChallenges,
  fetchCommitments,
  createValidation,
  createCommunity,
  joinCommunity,
  fetchExploreCommunities,
  applyJoinCommunity,
  CommunityRead,
  CommunityCodex,
  SocialPost,
  ChallengeItem,
  CommitmentsView,
  useCommunityStream,
} from "./api";
import { useCoOSStore } from "../../stores/m3_1_global_store";
import { CommunityCarousel } from "./CommunityCarousel";
import { CommunityCodexPanel } from "./CommunityCodexPanel";
import { ChallengeBoardPanel } from "./ChallengeBoardPanel";
import { PostsFeed } from "./PostsFeed";
import { CommitmentClosedLoop } from "./CommitmentClosedLoop";
import { StakeXPInterface } from "./StakeXPInterface";
import { CommunityAdminModal } from "./CommunityAdminModal";
import "./community.css";

export const FullCommunityUI: React.FC = () => {
  const { currentRole, activeCommunityId, setActiveCommunity } = useCoOSStore();
  const [communities, setCommunities] = useState<CommunityRead[]>([]);
  const [codex, setCodex] = useState<CommunityCodex | null>(null);
  const [posts, setPosts] = useState<SocialPost[]>([]);
  const [challenges, setChallenges] = useState<ChallengeItem[]>([]);
  const [commitmentsView, setCommitmentsView] = useState<CommitmentsView>({
    commitments: [],
    to_validate: [],
    active_stakes: [],
  });

  const [promises, setPromises] = useState<string[]>([
    "完成本日的學習目標",
    "進行 15 分鐘的每日反思",
    "完成一個專案里程碑成果",
  ]);

  const [loadingList, setLoadingList] = useState(true);
  const [loadingData, setLoadingData] = useState(false);

  // Staking Modal State
  const [stakingTask, setStakingTask] = useState<string | null>(null);

  // Join/Create State
  const [joining, setJoining] = useState(false);
  const [newCommName, setNewCommName] = useState("");
  const [newCommTheme, setNewCommTheme] = useState("study");
  const [newCommCap, setNewCommCap] = useState(5);

  // Explore Communities State
  const [exploreCommunities, setExploreCommunities] = useState<CommunityRead[]>([]);
  const [loadingExplore, setLoadingExplore] = useState(false);

  // Admin Modal State
  const [managingCommunityId, setManagingCommunityId] = useState<string | null>(null);

  // SSE hook
  const { events, connected } = useCommunityStream(activeCommunityId);


  // Fetch communities list
  const loadCommunities = useCallback(async () => {
    try {
      setLoadingList(true);
      const list = await fetchCommunities();
      setCommunities(list);
      if (list.length > 0 && !activeCommunityId) {
        setActiveCommunity(list[0].id);
      }
    } catch (err) {
      console.error("Failed to fetch communities:", err);
    } finally {
      setLoadingList(false);
    }
  }, [activeCommunityId, setActiveCommunity]);

  // Fetch all data for the active community
  const loadActiveCommunityData = useCallback(async (communityId: string) => {
    if (!communityId || communityId === "__add__") return;
    setLoadingData(true);
    try {
      const [cCodex, cPosts, cChallenges, cCommitments] = await Promise.all([
        fetchCodex(communityId),
        fetchPosts(communityId),
        fetchChallenges(communityId),
        fetchCommitments(communityId),
      ]);
      setCodex(cCodex);
      setPosts(cPosts);
      setChallenges(cChallenges);
      setCommitmentsView(cCommitments);
    } catch (err) {
      console.error("Failed to load community details:", err);
    } finally {
      setLoadingData(false);
    }
  }, []);

  // Fetch promises from current role context
  const loadPromises = useCallback(async () => {
    if (!currentRole) return;
    try {
      const res = await fetch(`/api/m6_3/role_context?role_id=${currentRole.id}`);
      if (res.ok) {
        const data = await res.json();
        if (data.promises && data.promises.length > 0) {
          setPromises(data.promises);
        }
      }
    } catch (err) {
      console.error("Failed to fetch role context for promises:", err);
    }
  }, [currentRole]);

  // Fetch explore communities
  const loadExploreCommunities = useCallback(async () => {
    try {
      setLoadingExplore(true);
      const list = await fetchExploreCommunities();
      setExploreCommunities(list);
    } catch (err) {
      console.error("Failed to fetch explore communities:", err);
    } finally {
      setLoadingExplore(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadCommunities();
  }, [loadCommunities]);

  // Load explore communities on screen switch
  useEffect(() => {
    if (activeCommunityId === "__add__" || communities.length === 0) {
      loadExploreCommunities();
    }
  }, [activeCommunityId, communities.length, loadExploreCommunities]);

  // Load community details on community switch
  useEffect(() => {
    if (activeCommunityId) {
      loadActiveCommunityData(activeCommunityId);
    }
  }, [activeCommunityId, loadActiveCommunityData]);

  // Load user promises
  useEffect(() => {
    loadPromises();
  }, [loadPromises]);

  // SSE event listener to trigger data refresh
  useEffect(() => {
    if (events.length > 0 && activeCommunityId) {
      console.log("[M3.7] SSE Event received, refreshing details...", events[0]);
      loadActiveCommunityData(activeCommunityId);
    }
  }, [events, activeCommunityId, loadActiveCommunityData]);

  // Peer validation action
  const handleValidate = async (postId: string, evidenceUrl?: string) => {
    try {
      await createValidation({ post_id: postId, evidence_url: evidenceUrl });
      if (activeCommunityId) {
        loadActiveCommunityData(activeCommunityId);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "驗證失敗");
    }
  };

  const handleStakeSuccess = () => {
    if (activeCommunityId) {
      loadActiveCommunityData(activeCommunityId);
    }
  };

  const handleJoin = async (mode: string, theme?: string) => {
    try {
      setJoining(true);
      const res = await joinCommunity({ mode, theme });
      if (res.id) {
        await loadCommunities();
        setActiveCommunity(res.id);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "加入社群失敗");
    } finally {
      setJoining(false);
    }
  };

  const handleApplyJoin = async (communityId: string) => {
    try {
      setJoining(true);
      await applyJoinCommunity(communityId);
      alert("申請已送出，請等待社群管理員審核！");
      await loadExploreCommunities();
    } catch (err) {
      alert(err instanceof Error ? err.message : "申請加入失敗");
    } finally {
      setJoining(false);
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCommName.trim()) return;
    try {
      setJoining(true);
      const res = await createCommunity({
        name: newCommName.trim(),
        theme: newCommTheme,
        member_cap: newCommCap,
      });
      if (res.id) {
        await loadCommunities();
        setActiveCommunity(res.id);
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "建立社群失敗");
    } finally {
      setJoining(false);
    }
  };

  const activeCommunity = communities.find((c) => c.id === activeCommunityId);
  const activeCommName = activeCommunityId && activeCommunityId !== "__add__" 
    ? (activeCommunity?.name || "社群空間") 
    : "探索/建立社群";
  const isAdmin = activeCommunity?.role === "admin";

  return (
    <div className="community-page">
      <div className="flex flex-col min-h-0 overflow-hidden">
        {/* Page Header */}
        <header className="community-header px-5 pt-4">
          <div className="flex items-center gap-2">
            <h1>🌐 {activeCommName}</h1>
            <span
              className={`sse-indicator ${connected ? "connected" : "disconnected"}`}
              title={connected ? "已連線即時更新" : "即時連線已中斷，降級為輪詢模式"}
            />
          </div>
        </header>

        {communities.length === 0 || !activeCommunityId || activeCommunityId === "__add__" ? (
          /* Join or Create Community Interface */
          <div className="join-community-container" data-testid="join-community-interface">
            {/* Join Theme Card */}
            <div className="join-community-card">
              <h2>🎲 隨機加入社群</h2>
              <p className="subtitle">選擇一個你感興趣的主題，系統將為你分派到適合的子社群：</p>
              <div className="theme-options">
                <button
                  type="button"
                  className="theme-btn"
                  onClick={() => handleJoin("theme_random", "study")}
                  disabled={joining}
                  data-testid="join-study-btn"
                >
                  <span className="theme-btn-emoji">📚</span>
                  <span className="theme-btn-label">學習成長</span>
                </button>
                <button
                  type="button"
                  className="theme-btn"
                  onClick={() => handleJoin("theme_random", "career")}
                  disabled={joining}
                  data-testid="join-career-btn"
                >
                  <span className="theme-btn-emoji">💼</span>
                  <span className="theme-btn-label">職涯準備</span>
                </button>
                <button
                  type="button"
                  className="theme-btn"
                  onClick={() => handleJoin("theme_random", "cooking")}
                  disabled={joining}
                  data-testid="join-cooking-btn"
                >
                  <span className="theme-btn-emoji">🍳</span>
                  <span className="theme-btn-label">生活廚藝</span>
                </button>
                <button
                  type="button"
                  className="theme-btn"
                  onClick={() => handleJoin("theme_random", "social")}
                  disabled={joining}
                  data-testid="join-social-btn"
                >
                  <span className="theme-btn-emoji">🤝</span>
                  <span className="theme-btn-label">社交互動</span>
                </button>
              </div>
              <button
                type="button"
                className="system-random-btn"
                onClick={() => handleJoin("system_random")}
                disabled={joining}
                data-testid="join-system-btn"
              >
                🌐 系統隨機分派加入
              </button>
            </div>

            {/* Create Community Card */}
            <div className="join-community-card">
              <h2>✨ 建立新社群</h2>
              <p className="subtitle">建立一個新的社群空間，邀請其他成員一起加入！</p>
              <form onSubmit={handleCreate} className="create-comm-form" data-testid="create-community-form">
                <div className="form-group">
                  <label htmlFor="comm-name">社群名稱</label>
                  <input
                    id="comm-name"
                    type="text"
                    className="form-input"
                    placeholder="例如：自律學習小組"
                    value={newCommName}
                    onChange={(e) => setNewCommName(e.target.value)}
                    required
                    disabled={joining}
                    data-testid="comm-name-input"
                  />
                </div>
                <div className="form-group">
                  <label htmlFor="comm-theme">社群主題</label>
                  <select
                    id="comm-theme"
                    className="form-select"
                    value={newCommTheme}
                    onChange={(e) => setNewCommTheme(e.target.value)}
                    disabled={joining}
                    data-testid="comm-theme-select"
                  >
                    <option value="study">📚 學習成長</option>
                    <option value="career">💼 職涯準備</option>
                    <option value="cooking">🍳 生活廚藝</option>
                    <option value="social">🤝 社交互動</option>
                  </select>
                </div>
                <div className="form-group">
                  <label htmlFor="comm-cap">人數上限 (鄧巴數 2~8 人)</label>
                  <select
                    id="comm-cap"
                    className="form-select"
                    value={newCommCap}
                    onChange={(e) => setNewCommCap(parseInt(e.target.value))}
                    disabled={joining}
                    data-testid="comm-cap-select"
                  >
                    <option value={2}>2 人</option>
                    <option value={3}>3 人</option>
                    <option value={4}>4 人</option>
                    <option value={5}>5 人</option>
                    <option value={6}>6 人</option>
                    <option value={7}>7 人</option>
                    <option value={8}>8 人</option>
                  </select>
                </div>
                <button
                  type="submit"
                  className="create-submit-btn"
                  disabled={joining || !newCommName.trim()}
                  data-testid="create-comm-btn"
                >
                  {joining ? "處理中..." : "🚀 建立社群空間"}
                </button>
              </form>
            </div>
            {/* Explore Communities Card */}
            <div className="join-community-card explore-communities-card" style={{ gridColumn: "span 2", maxHeight: "400px", overflowY: "auto" }}>
              <h2>🔍 申請加入公開社群</h2>
              <p className="subtitle">您可以瀏覽並申請加入現有的社群，共同完成日常反思與質押挑戰：</p>
              {loadingExplore ? (
                <div className="text-center py-4 text-sm text-text-muted">載入中...</div>
              ) : exploreCommunities.length === 0 ? (
                <div className="empty-explore text-sm text-text-muted py-4">目前沒有其他公開社群可供申請。</div>
              ) : (
                <div className="explore-list flex flex-col gap-3">
                  {exploreCommunities.map((c) => (
                    <div key={c.id} className="explore-item flex items-center justify-between p-3 rounded-lg border border-glass-border bg-card">
                      <div className="explore-info">
                        <div className="explore-name font-semibold text-sm flex items-center gap-1.5">
                          {c.name}
                          <span className="theme-tag text-xs px-2 py-0.5 rounded-full bg-role-primary-faint text-text-muted">
                            {c.theme === "study" ? "📚 學習" : c.theme === "career" ? "💼 職涯" : c.theme === "cooking" ? "🍳 廚藝" : "🤝 社交"}
                          </span>
                        </div>
                        <div className="explore-meta text-xs text-text-muted mt-1">
                          成員容量：{c.member_count} / {c.member_cap} 人
                        </div>
                      </div>
                      <button
                        type="button"
                        className={`apply-join-btn text-xs px-3 py-1.5 rounded-lg ${c.goal === "申請審核中..." ? "bg-role-primary-faint text-text-muted cursor-not-allowed" : "btn-primary"}`}
                        onClick={() => c.goal !== "申請審核中..." && handleApplyJoin(c.id)}
                        disabled={joining || c.goal === "申請審核中..." || c.member_count >= c.member_cap}
                      >
                        {c.goal === "申請審核中..." ? "申請審核中" : c.member_count >= c.member_cap ? "已滿額" : "申請加入"}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Bento Grid */
          <div className="community-bento flex-1">
            <CommunityCodexPanel
              codex={codex}
              loading={loadingData}
              communityId={activeCommunityId || ""}
              onUpdate={() => activeCommunityId && loadActiveCommunityData(activeCommunityId)}
            />

            <ChallengeBoardPanel
              challenges={challenges}
              loading={loadingData}
              communityId={activeCommunityId || ""}
              isAdmin={isAdmin}
              onUpdate={() => activeCommunityId && loadActiveCommunityData(activeCommunityId)}
            />

            <PostsFeed
              posts={posts}
              communityId={activeCommunityId || ""}
              onRefresh={() => activeCommunityId && loadActiveCommunityData(activeCommunityId)}
            />

            <CommitmentClosedLoop
              commitments={commitmentsView.commitments}
              toValidate={commitmentsView.to_validate}
              activeStakes={commitmentsView.active_stakes}
              promises={promises}
              onStakeClick={(title) => setStakingTask(title)}
              onValidate={handleValidate}
              loading={loadingData}
              communityId={activeCommunityId || ""}
              onRefresh={() => activeCommunityId && loadActiveCommunityData(activeCommunityId)}
            />
          </div>
        )}
      </div>

      {/* Right Sidebar Carousel */}
      <CommunityCarousel
        communities={communities}
        loading={loadingList}
        onManageCommunity={(id) => setManagingCommunityId(id)}
      />

      {/* Stake Modal */}
      {stakingTask && activeCommunityId && (
        <StakeXPInterface
          isOpen={true}
          onClose={() => setStakingTask(null)}
          taskTitle={stakingTask}
          communityId={activeCommunityId}
          onSuccess={handleStakeSuccess}
        />
      )}

      {/* Community Admin/Management Modal */}
      {managingCommunityId && (
        <CommunityAdminModal
          isOpen={true}
          onClose={() => setManagingCommunityId(null)}
          communityId={managingCommunityId}
          communityName={communities.find((c) => c.id === managingCommunityId)?.name || ""}
          isAdmin={communities.find((c) => c.id === managingCommunityId)?.role === "admin"}
          memberCap={communities.find((c) => c.id === managingCommunityId)?.member_cap || 5}
          challengeMode={communities.find((c) => c.id === managingCommunityId)?.challenge_mode || "manual"}
          onUpdate={async () => {
            await loadCommunities();
            if (activeCommunityId && activeCommunityId !== "__add__") {
              await loadActiveCommunityData(activeCommunityId);
            }
          }}
        />
      )}
    </div>
  );
};

