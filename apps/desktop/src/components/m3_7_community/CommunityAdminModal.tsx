import React, { useState, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import {
  fetchMembers,
  updateMemberRole,
  kickMember,
  leaveCommunity,
  fetchJoinRequests,
  handleJoinRequest,
  updateCommunitySettings,
  MemberRead,
  JoinRequestRead,
  CommunityRead,
} from "./api";

interface CommunityAdminModalProps {
  isOpen: boolean;
  onClose: () => void;
  communityId: string;
  communityName: string;
  isAdmin: boolean;
  memberCap: number;
  challengeMode: string;
  onUpdate: () => void;
}

type TabType = "members" | "requests" | "settings";

export const CommunityAdminModal: React.FC<CommunityAdminModalProps> = ({
  isOpen,
  onClose,
  communityId,
  communityName,
  isAdmin: initialIsAdmin,
  memberCap: initialMemberCap,
  challengeMode: initialChallengeMode,
  onUpdate,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>("members");
  
  // Members State
  const [members, setMembers] = useState<MemberRead[]>([]);
  const [loadingMembers, setLoadingMembers] = useState(false);
  
  // Requests State
  const [requests, setRequests] = useState<JoinRequestRead[]>([]);
  const [loadingRequests, setLoadingRequests] = useState(false);
  
  // Settings State
  const [memberCap, setMemberCap] = useState(initialMemberCap);
  const [challengeMode, setChallengeMode] = useState(initialChallengeMode);
  const [savingSettings, setSavingSettings] = useState(false);
  const [settingsError, setSettingsError] = useState("");
  const [settingsSuccess, setSettingsSuccess] = useState(false);

  const [currentUserRole, setCurrentUserRole] = useState<string>("member");

  // Determine current user ID:
  // In our desktop frontend, we can fetch role context or settings. For mock mode, the current user is "00000000-0000-0000-0000-000000000000"
  const currentUserId = "00000000-0000-0000-0000-000000000000";

  // Fetch Members
  const loadMembers = useCallback(async () => {
    if (!communityId) return;
    try {
      setLoadingMembers(true);
      const list = await fetchMembers(communityId);
      setMembers(list);
      
      // Determine user's role in this community dynamically
      const me = list.find(m => m.user_id === currentUserId);
      if (me) {
        setCurrentUserRole(me.role);
      }
    } catch (err) {
      console.error("Failed to load members:", err);
    } finally {
      setLoadingMembers(false);
    }
  }, [communityId]);

  // Fetch Join Requests
  const loadRequests = useCallback(async () => {
    if (!communityId || !initialIsAdmin) return;
    try {
      setLoadingRequests(true);
      const list = await fetchJoinRequests(communityId);
      setRequests(list);
    } catch (err) {
      console.error("Failed to load join requests:", err);
    } finally {
      setLoadingRequests(false);
    }
  }, [communityId, initialIsAdmin]);

  // Load initial data
  useEffect(() => {
    if (isOpen) {
      loadMembers();
      if (initialIsAdmin) {
        loadRequests();
      }
      setMemberCap(initialMemberCap);
      setChallengeMode(initialChallengeMode);
      setSettingsSuccess(false);
      setSettingsError("");
    }
  }, [isOpen, loadMembers, loadRequests, initialMemberCap, initialChallengeMode, initialIsAdmin]);

  if (!isOpen) return null;

  const userIsAdmin = currentUserRole === "admin" || initialIsAdmin;

  // Handle Role Toggle
  const handleToggleRole = async (userId: string, currentRole: string) => {
    const newRole = currentRole === "admin" ? "member" : "admin";
    
    // Safety check: last admin demotion
    if (currentRole === "admin") {
      const adminCount = members.filter(m => m.role === "admin").length;
      if (adminCount <= 1) {
        alert("無法取消管理員權限，因為該成員是此社群的唯一管理員！");
        return;
      }
    }

    try {
      await updateMemberRole(communityId, userId, newRole);
      await loadMembers();
      onUpdate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "修改角色失敗");
    }
  };

  // Handle Kick Member
  const handleKick = async (userId: string, userName: string, userRole: string) => {
    if (userRole === "admin") {
      const adminCount = members.filter(m => m.role === "admin").length;
      if (adminCount <= 1) {
        alert("無法踢除管理員，因為該成員是此社群的唯一管理員！");
        return;
      }
    }

    if (!confirm(`確定要將成員「${userName}」移出社群嗎？`)) return;

    try {
      await kickMember(communityId, userId);
      await loadMembers();
      onUpdate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "踢除成員失敗");
    }
  };

  // Handle Leave Community
  const handleLeave = async () => {
    const isActiveAdmin = currentUserRole === "admin";
    if (isActiveAdmin) {
      const adminCount = members.filter(m => m.role === "admin").length;
      if (adminCount <= 1 && members.length > 1) {
        alert("無法退出社群，因為您是此社群唯一的管理員。請先指派其他成員為管理員再退出！");
        return;
      }
    }

    if (!confirm("確定要退出此社群嗎？退出後您將無法查看此社群內部的承諾與貼文。")) return;

    try {
      await leaveCommunity(communityId);
      onUpdate();
      onClose();
    } catch (err) {
      alert(err instanceof Error ? err.message : "退出社群失敗");
    }
  };

  // Handle Join Request action
  const handleActionRequest = async (requestId: string, action: "approve" | "reject") => {
    try {
      const res = await handleJoinRequest(communityId, requestId, action);
      if (res.status === "approved") {
        alert("已成功同意該成員加入！");
      } else {
        alert("已拒絕該成員的加入申請。");
      }
      await loadRequests();
      await loadMembers();
      onUpdate();
    } catch (err) {
      alert(err instanceof Error ? err.message : "處理申請失敗");
    }
  };

  // Handle Settings Submit
  const handleSaveSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSettingsError("");
    setSettingsSuccess(false);
    
    if (memberCap < members.length) {
      setSettingsError(`人數上限不能少於當前社群成員數 (${members.length} 人)`);
      return;
    }

    try {
      setSavingSettings(true);
      await updateCommunitySettings(communityId, {
        challenge_mode: challengeMode,
        member_cap: memberCap,
      });
      setSettingsSuccess(true);
      onUpdate();
    } catch (err) {
      setSettingsError(err instanceof Error ? err.message : "更新設定失敗");
    } finally {
      setSavingSettings(false);
    }
  };

  const activeMembersCount = members.length;

  return createPortal(
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content glass-panel community-admin-modal" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div className="flex items-center gap-2">
            <h2>⚙️ 社群管理：{communityName}</h2>
            <span className="members-badge">
              {activeMembersCount} / {memberCap} 人
            </span>
          </div>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        {/* Tab Headers */}
        <div className="admin-tabs">
          <button
            type="button"
            className={`admin-tab-btn ${activeTab === "members" ? "active" : ""}`}
            onClick={() => setActiveTab("members")}
          >
            👥 成員名單
          </button>
          <button
            type="button"
            className={`admin-tab-btn ${activeTab === "requests" ? "active" : ""}`}
            onClick={() => setActiveTab("requests")}
          >
            📥 待加入審核 {requests.length > 0 && <span className="req-count-badge">{requests.length}</span>}
          </button>
          <button
            type="button"
            className={`admin-tab-btn ${activeTab === "settings" ? "active" : ""}`}
            onClick={() => setActiveTab("settings")}
          >
            🔧 偏好設定
          </button>
        </div>

        {/* Tab Content */}
        <div className="admin-tab-content flex-1 overflow-y-auto pr-1">
          {/* TAB 1: MEMBERS */}
          {activeTab === "members" && (
            <div className="tab-pane members-pane">
              <div className="section-desc">本社群的現有成員名單。管理員可以管理其他成員的角色或進行踢除。</div>
              {loadingMembers ? (
                <div className="text-center py-8 text-sm text-text-muted">載入中...</div>
              ) : members.length === 0 ? (
                <div className="text-center py-8 text-sm text-text-muted">尚無成員</div>
              ) : (
                <div className="members-list">
                  {members.map((member) => {
                    const isSelf = member.user_id === currentUserId;
                    return (
                      <div key={member.user_id} className={`member-item ${isSelf ? "is-self" : ""}`}>
                        <div className="member-info">
                          <span className="member-avatar">👤</span>
                          <div className="member-details">
                            <div className="member-name flex items-center gap-1.5">
                              {member.display_name} {isSelf && <span className="self-tag">(我)</span>}
                            </div>
                            <div className="member-joined">加入時間：{new Date(member.joined_at).toLocaleDateString()}</div>
                          </div>
                        </div>
                        <div className="member-actions">
                          {/* Role tag / toggle */}
                          {userIsAdmin && !isSelf ? (
                            <button
                              type="button"
                              className={`role-btn-toggle ${member.role === "admin" ? "is-admin" : "is-member"}`}
                              onClick={() => handleToggleRole(member.user_id, member.role)}
                              title={member.role === "admin" ? "點擊降為一般成員" : "點擊升為管理員"}
                            >
                              {member.role === "admin" ? "管理員" : "成員"}
                            </button>
                          ) : (
                            <span className={`role-badge ${member.role === "admin" ? "is-admin" : "is-member"}`}>
                              {member.role === "admin" ? "管理員" : "成員"}
                            </span>
                          )}

                          {/* Kick Action */}
                          {userIsAdmin && !isSelf && (
                            <button
                              type="button"
                              className="kick-btn"
                              onClick={() => handleKick(member.user_id, member.display_name, member.role)}
                            >
                              🗑️ 踢除
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Leave Button */}
              <div className="leave-section mt-6 border-t border-glass-border pt-4 flex justify-end">
                <button
                  type="button"
                  className="leave-btn"
                  onClick={handleLeave}
                >
                  🚪 退出此社群
                </button>
              </div>
            </div>
          )}

          {/* TAB 2: REQUESTS (APPROVALS) */}
          {activeTab === "requests" && (
            <div className="tab-pane requests-pane">
              {!userIsAdmin ? (
                <div className="empty-state">
                  <span className="empty-state-icon">🔒</span>
                  <span className="empty-state-text">非管理員無權限審核成員申請</span>
                </div>
              ) : loadingRequests ? (
                <div className="text-center py-8 text-sm text-text-muted">載入中...</div>
              ) : requests.length === 0 ? (
                <div className="empty-state">
                  <span className="empty-state-icon">✅</span>
                  <span className="empty-state-text">目前沒有待審核的加入申請</span>
                </div>
              ) : (
                <div className="requests-list">
                  <div className="section-desc mb-3">審核使用者申請加入此社群的請求。</div>
                  {requests.map((req) => (
                    <div key={req.id} className="request-item">
                      <div className="request-info">
                        <span className="request-avatar">👤</span>
                        <div className="request-details">
                          <div className="request-name">{req.display_name}</div>
                          <div className="request-time">申請時間：{new Date(req.created_at).toLocaleDateString()}</div>
                        </div>
                      </div>
                      <div className="request-actions">
                        <button
                          type="button"
                          className="action-btn approve"
                          onClick={() => handleActionRequest(req.id, "approve")}
                        >
                          ✓ 同意
                        </button>
                        <button
                          type="button"
                          className="action-btn reject"
                          onClick={() => handleActionRequest(req.id, "reject")}
                        >
                          × 拒絕
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: SETTINGS */}
          {activeTab === "settings" && (
            <div className="tab-pane settings-pane">
              <form onSubmit={handleSaveSettings} className="modal-form">
                <div className="form-group">
                  <label htmlFor="settings-cap">成員人數上限 (鄧巴數 2~8 人)</label>
                  <select
                    id="settings-cap"
                    className="form-select"
                    value={memberCap}
                    onChange={(e) => setMemberCap(parseInt(e.target.value))}
                    disabled={!userIsAdmin || savingSettings}
                  >
                    <option value={2}>2 人</option>
                    <option value={3}>3 人</option>
                    <option value={4}>4 人</option>
                    <option value={5}>5 人</option>
                    <option value={6}>6 人</option>
                    <option value={7}>7 人</option>
                    <option value={8}>8 人</option>
                  </select>
                  <small className="form-help text-text-muted mt-1 display-block">
                    當前成員數為 {activeMembersCount} 人。上限不可少於當前成員數。
                  </small>
                </div>

                <div className="form-group">
                  <label htmlFor="settings-mode">挑戰建立模式 (Challenge Creation Mode)</label>
                  <select
                    id="settings-mode"
                    className="form-select"
                    value={challengeMode}
                    onChange={(e) => setChallengeMode(e.target.value)}
                    disabled={!userIsAdmin || savingSettings}
                  >
                    <option value="manual">✍️ 手動建立 (管理員自行出題)</option>
                    <option value="ai_reviewed">🤖 AI 推薦審核 (AI 自動生成挑戰，待管理員審查後公開)</option>
                    <option value="member_rotation">🔄 成員輪替 (每週由不同社群成員出題)</option>
                  </select>
                </div>

                {settingsError && (
                  <div className="settings-error-alert text-red-500 text-xs mt-2">
                    ⚠️ {settingsError}
                  </div>
                )}

                {settingsSuccess && (
                  <div className="settings-success-alert text-green-500 text-xs mt-2">
                    🎉 設定儲存成功！
                  </div>
                )}

                {userIsAdmin ? (
                  <button
                    type="submit"
                    className="btn-primary mt-4"
                    disabled={savingSettings}
                  >
                    {savingSettings ? "儲存中..." : "儲存設定變更"}
                  </button>
                ) : (
                  <div className="text-xs text-text-muted mt-4 border-t border-glass-border pt-3">
                    ℹ️ 唯有管理員可修改此社群的偏好設定。
                  </div>
                )}
              </form>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};
