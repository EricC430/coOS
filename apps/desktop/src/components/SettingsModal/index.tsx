import { useEffect, useRef, useState, useCallback } from "react";
import { open } from "@tauri-apps/plugin-dialog";
import { open as openUrl } from "@tauri-apps/plugin-shell";
import { apiCall } from "../../lib/ipc";
import { useCoOSStore } from "../../stores/m3_1_global_store";

interface SettingsState {
  content_capture: string;
  voice_cloud: boolean;
  cloud_sync: boolean;
  theme: string;
  notification_enabled: boolean;
  daily_report_time: string;
  focus_hours_start: string;
  focus_hours_end: string;
  gemma_model: string;
  ai_local_host: string;
  ipad_ai_local_host: string;
}

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: Props) {
  const { currentRole } = useCoOSStore();
  const [activeTab, setActiveTab] = useState<"privacy" | "role" | "system" | "git" | "accounts">("privacy");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [gitSources, setGitSources] = useState<any[]>([]);
  const [isGithubConnected, setIsGithubConnected] = useState(false);
  const [newGitPath, setNewGitPath] = useState("");
  const [newGithubRepo, setNewGithubRepo] = useState("");
  const [whitelist, setWhitelist] = useState<string[]>([]);
  const [newApp, setNewApp] = useState("");
  const [settings, setSettings] = useState<SettingsState>({
    content_capture: "off",
    voice_cloud: false,
    cloud_sync: false,
    theme: "default",
    notification_enabled: true,
    daily_report_time: "22:00",
    focus_hours_start: "09:00",
    focus_hours_end: "18:00",
    gemma_model: "",
    ai_local_host: "",
    ipad_ai_local_host: "",
  });

  useEffect(() => {
    if (!isOpen || !currentRole?.id) return;
    const roleId = currentRole.id;

    async function loadSettings() {
      setLoading(true);
      try {
        const data = await apiCall<SettingsState>(`/api/settings?role_id=${roleId}`);
        setSettings(data);
      } catch (err) {
        console.error("Failed to load settings:", err);
      } finally {
        setLoading(false);
      }
    }

    loadSettings();
    if (isOpen) {
        loadGitSources();
        loadWhitelist();
    }
  }, [isOpen, currentRole?.id]);

  async function loadGitSources() {
    try {
      const data = await apiCall<any[]>("/api/m1_4/connected_sources");
      setGitSources(data);
      // Check if GitHub OAuth account is in the sources
      setIsGithubConnected(data.some(s => s.type === 'github_oauth'));
    } catch (err) {
      console.error("Failed to load git sources:", err);
    }
  }

  async function loadWhitelist() {
    try {
      const data = await apiCall<string[]>("/api/settings/whitelist");
      setWhitelist(data);
    } catch (err) {
      console.error("Failed to load whitelist:", err);
    }
  }

  async function handleAddWhitelist() {
    if (!newApp) return;
    const next = [...whitelist, newApp];
    try {
      await apiCall("/api/settings/whitelist", {
        method: "POST",
        body: JSON.stringify(next),
      });
      setWhitelist(next);
      setNewApp("");
    } catch (err) {
      alert("新增失敗");
    }
  }

  async function handleRemoveWhitelist(app: string) {
    const next = whitelist.filter(a => a !== app);
    try {
      await apiCall("/api/settings/whitelist", {
        method: "POST",
        body: JSON.stringify(next),
      });
      setWhitelist(next);
    } catch (err) {
      alert("移除失敗");
    }
  }

  async function handleSelectFolder() {
    try {
      const selected = await open({
        directory: true,
        multiple: false,
        title: "選擇 Git 專案資料夾",
      });
      if (selected && typeof selected === "string") {
        setNewGitPath(selected);
      }
    } catch (err) {
      console.error("Failed to open dialog:", err);
    }
  }

  async function handleAddGitSource() {
    if (!newGitPath) return;
    try {
      await apiCall("/api/m1_4/bind_source", {
        method: "POST",
        body: JSON.stringify({
          source_type: "local_git",
          repo_path: newGitPath,
          github_repo: newGithubRepo || undefined,
        }),
      });
      setNewGitPath("");
      setNewGithubRepo("");
      loadGitSources();
      alert("已成功連接 Git 來源，重啟 Sidecar 後將開始監控。");
    } catch (err: any) {
      alert("連接失敗: " + (err.message || "未知錯誤"));
    }
  }

  async function handleDisconnectSource(path: string) {
    if (!confirm("確定要停止監控此 Git 專案嗎？")) return;
    try {
      await apiCall("/api/m1_4/disconnect_source", {
        method: "POST",
        body: JSON.stringify({ repo_path: path }),
      });
      loadGitSources();
    } catch (err) {
      alert("移除失敗");
    }
  }

  async function handleLinkGithub() {
    try {
      const resp = await apiCall<any>("/api/m1_4/github_auth_url");
      if (resp.error) {
        alert("GitHub 設定錯誤: " + resp.error);
        return;
      }
      if (resp.url) {
        await openUrl(resp.url);
        // Prompt user to refresh after auth
        setTimeout(() => {
            if (confirm("已在瀏覽器開啟授權頁面，完成授權後請點擊確定以刷新狀態。")) {
                loadGitSources();
            }
        }, 1000);
      }
    } catch (err) {
      console.error("Failed to get auth url:", err);
    }
  }

  async function handleDisconnectGithub() {
    if (!confirm("確定要解除 GitHub 帳號連結嗎？這將停止雲端 Webhook 同步。")) return;
    try {
      await apiCall("/api/v1/auth/github/disconnect", { method: "POST" });
      loadGitSources();
    } catch (err) {
      alert("解除連結失敗");
    }
  }

  const handleSave = async () => {
    if (!currentRole?.id) return;
    const roleId = currentRole.id;
    setSaving(true);
    try {
      await apiCall(`/api/settings?role_id=${roleId}`, {
        method: "POST",
        body: JSON.stringify(settings),
      });
      
      const resolvedTheme =
        settings.theme === "dark" || settings.theme === "light"
          ? settings.theme
          : document.documentElement.getAttribute("data-theme") || 
            (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
      
      if (settings.theme !== "default") {
          document.documentElement.setAttribute("data-theme", resolvedTheme);
      }
      window.dispatchEvent(new CustomEvent("coos:theme-changed", { detail: resolvedTheme }));
      
      onClose();
    } catch (err) {
      console.error("Failed to save settings:", err);
      alert("儲存設定失敗");
    } finally {
      setSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="settings-backdrop" onClick={onClose}>
      <div className="settings-dialog glass-card" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>系統設定 / Preferences</h2>
          <button className="settings-close-btn" onClick={onClose}>&times;</button>
        </div>

        {loading ? (
          <div className="settings-loading">
            <div className="settings-spinner"></div>
            <span>載入設定中...</span>
          </div>
        ) : (
          <div className="settings-body">
            <div className="settings-tabs">
              <button
                className={`settings-tab-btn ${activeTab === "privacy" ? "active" : ""}`}
                onClick={() => setActiveTab("privacy")}
              >
                🔒 隱私與安全
              </button>
              <button
                className={`settings-tab-btn ${activeTab === "role" ? "active" : ""}`}
                onClick={() => setActiveTab("role")}
              >
                👤 角色偏好 ({currentRole?.name})
              </button>
              <button
                className={`settings-tab-btn ${activeTab === "system" ? "active" : ""}`}
                onClick={() => setActiveTab("system")}
              >
                ⚙️ 系統與 AI
              </button>
              <button
                className={`settings-tab-btn ${activeTab === "git" ? "active" : ""}`}
                onClick={() => setActiveTab("git")}
              >
                🌿 Git 與工作流
              </button>
              <button
                className={`settings-tab-btn ${activeTab === "accounts" ? "active" : ""}`}
                onClick={() => setActiveTab("accounts")}
              >
                🔗 帳號連結
              </button>
              </div>

              <div className="settings-content">
              {activeTab === "privacy" && (
                <div className="settings-section">
                  <h3>隱私授權選項</h3>
                  
                  <div className="settings-field">
                    <label>
                      <strong>遙測內文採集模式</strong>
                      <span className="field-desc">設定是否允許背景採集視窗標題與文字做本地意圖分析。</span>
                    </label>
                    <select
                      value={settings.content_capture}
                      onChange={(e) => setSettings({ ...settings, content_capture: e.target.value })}
                    >
                      <option value="off">完全關閉 (Off)</option>
                      <option value="all">採集所有應用程式 (All)</option>
                      <option value="selected">僅採集白名單應用 (Selected)</option>
                    </select>
                  </div>

                  {settings.content_capture === "selected" && (
                    <div className="settings-field" style={{ marginTop: '16px', background: 'rgba(0,0,0,0.1)', padding: '12px', borderRadius: '8px' }}>
                      <label><strong>軟體監測白名單</strong></label>
                      <div style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                        <input 
                          type="text" 
                          placeholder="例如: Code.exe" 
                          value={newApp} 
                          onChange={(e) => setNewApp(e.target.value)}
                          style={{ flex: 1, padding: '4px 8px', borderRadius: '4px', border: '1px solid #444', background: '#222', color: '#fff' }}
                        />
                        <button className="settings-save-btn" style={{ height: 'auto', padding: '4px 12px' }} onClick={handleAddWhitelist}>新增</button>
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                        {whitelist.map(app => (
                          <div key={app} style={{ display: 'inline-flex', alignItems: 'center', background: 'rgba(255,255,255,0.1)', padding: '2px 8px', borderRadius: '4px', fontSize: '0.8rem' }}>
                            {app}
                            <button onClick={() => handleRemoveWhitelist(app)} style={{ background: 'none', border: 'none', color: '#ef4444', marginLeft: '6px', cursor: 'pointer', fontSize: '1rem' }}>&times;</button>
                          </div>
                        ))}
                        {whitelist.length === 0 && <span style={{ opacity: 0.5, fontSize: '0.8rem' }}>尚未設定白名單</span>}
                      </div>
                    </div>
                  )}

                  <div className="settings-field row">
                    <label>
                      <strong>語音雲端推論同意</strong>
                      <span className="field-desc">是否允許將語音輸入發送至雲端 Whisper 進行高精準度辨識。</span>
                    </label>
                    <input
                      type="checkbox"
                      className="settings-toggle-checkbox"
                      checked={settings.voice_cloud}
                      onChange={(e) => setSettings({ ...settings, voice_cloud: e.target.checked })}
                    />
                  </div>

                  <div className="settings-field row">
                    <label>
                      <strong>雲端同步服務</strong>
                      <span className="field-desc">是否允許與雲端資料庫進行非對稱資料同步與備份。</span>
                    </label>
                    <input
                      type="checkbox"
                      className="settings-toggle-checkbox"
                      checked={settings.cloud_sync}
                      onChange={(e) => setSettings({ ...settings, cloud_sync: e.target.checked })}
                    />
                  </div>
                </div>
              )}

              {activeTab === "role" && (
                <div className="settings-section">
                  <h3>角色與通知偏好 ({currentRole?.name})</h3>
                  <div className="settings-field">
                    <label><strong>主題風格</strong></label>
                    <select value={settings.theme} onChange={(e) => setSettings({ ...settings, theme: e.target.value })}>
                      <option value="default">跟隨系統</option>
                      <option value="light">淺色模式</option>
                      <option value="dark">深色模式</option>
                    </select>
                  </div>
                  <div className="settings-field">
                    <label><strong>每日日報生成時間</strong></label>
                    <input type="time" value={settings.daily_report_time} onChange={(e) => setSettings({ ...settings, daily_report_time: e.target.value })} />
                  </div>
                </div>
              )}

              {activeTab === "system" && (
                <div className="settings-section">
                  <h3>系統與本地 AI 配置</h3>
                  <div className="settings-field">
                    <label><strong>Ollama 本地連接位址</strong></label>
                    <input type="text" value={settings.ai_local_host} onChange={(e) => setSettings({ ...settings, ai_local_host: e.target.value })} />
                  </div>
                  <div className="settings-field">
                    <label><strong>Gemma 邊緣模型名稱</strong></label>
                    <input type="text" value={settings.gemma_model} onChange={(e) => setSettings({ ...settings, gemma_model: e.target.value })} />
                  </div>
                  <div className="settings-field">
                    <label><strong>iPad M1 ai.local 位址</strong></label>
                    <input type="text" value={settings.ipad_ai_local_host} onChange={(e) => setSettings({ ...settings, ipad_ai_local_host: e.target.value })} />
                  </div>
                </div>
              )}

              {activeTab === "git" && (
                <div className="settings-section">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <h3 style={{ margin: 0 }}>Git 遙測與工作流整合</h3>
                    <div style={{ fontSize: '0.8rem', padding: '4px 8px', borderRadius: '4px', background: isGithubConnected ? 'rgba(52, 211, 153, 0.2)' : 'rgba(239, 68, 68, 0.1)', color: isGithubConnected ? '#10b981' : '#ef4444' }}>
                        {isGithubConnected ? '● GitHub 已連結' : '○ GitHub 未連結'}
                    </div>
                  </div>

                  <div className="settings-field">
                    <label><strong>新增本地 Git 監控</strong></label>
                    <div className="git-input-group" style={{ display: 'flex', gap: '8px', marginBottom: '8px' }}>
                      <input type="text" style={{ flex: 1, padding: '4px 8px', borderRadius: '4px', border: '1px solid #444', background: '#222', color: '#fff' }} value={newGitPath} readOnly placeholder="選擇資料夾..." />
                      <button className="settings-tab-btn" onClick={handleSelectFolder}>瀏覽...</button>
                      <button className="settings-save-btn" onClick={handleAddGitSource}>連接</button>
                    </div>
                    <div style={{ position: 'relative' }}>
                        <input 
                            type="text" 
                            style={{ width: '100%', opacity: isGithubConnected ? 1 : 0.5, padding: '4px 8px', borderRadius: '4px', border: '1px solid #444', background: '#222', color: '#fff' }} 
                            placeholder={isGithubConnected ? "GitHub Repo (選填，如 owner/repo)" : "需先連結 GitHub 帳號方可輸入雲端 Repo"} 
                            value={newGithubRepo} 
                            disabled={!isGithubConnected}
                            onChange={(e) => setNewGithubRepo(e.target.value)} 
                        />
                        {!isGithubConnected && <div style={{ fontSize: '0.7rem', color: '#ef4444', marginTop: '4px' }}>⚠ 請先完成下方的 GitHub OAuth 授權</div>}
                    </div>
                  </div>

                  <div className="settings-field">
                    <label><strong>已連接的來源</strong></label>
                    <div style={{ maxHeight: '150px', overflowY: 'auto', background: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>
                      {gitSources.filter(s => s.type === 'local_git').map(s => (
                        <div key={s.id} style={{ padding: '8px', borderBottom: '1px solid #333', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div style={{ flex: 1, minWidth: 0 }}>
                            <div style={{ fontWeight: 'bold', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.name}</div>
                            <div style={{ fontSize: '0.7rem', opacity: 0.5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.path}</div>
                          </div>
                          <button 
                            style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '1.2rem', padding: '0 8px' }}
                            onClick={() => handleDisconnectSource(s.path)}
                            title="移除此來源"
                          >
                            &times;
                          </button>
                        </div>
                      ))}
                      {gitSources.filter(s => s.type === 'local_git').length === 0 && (
                        <div style={{ padding: '20px', textAlign: 'center', opacity: 0.5, fontSize: '0.9rem' }}>尚無監控中的本地專案</div>
                      )}
                    </div>
                  </div>

                  <div className="settings-field" style={{ marginTop: '24px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '16px' }}>
                    {isGithubConnected ? (
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <div style={{ fontWeight: 'bold' }}>GitHub 帳號已連結</div>
                                <div style={{ fontSize: '0.8rem', opacity: 0.6 }}>已啟用雲端 Webhook 同步功能</div>
                            </div>
                            <button className="settings-cancel-btn" style={{ borderColor: '#ef4444', color: '#ef4444' }} onClick={handleDisconnectGithub}>解除連結</button>
                        </div>
                    ) : (
                        <button className="settings-save-btn" style={{ width: '100%' }} onClick={handleLinkGithub}>透過 OAuth 連結 GitHub</button>
                    )}
                  </div>
                </div>
              )}
              {activeTab === "accounts" && (
                <div className="settings-section">
                  <h3>帳號與跨裝置同步</h3>
                  <div className="settings-field">
                    <label><strong>Google 帳號</strong></label>
                    <p className="field-desc" style={{ marginBottom: "12px" }}>
                      連結 Google 帳號後，您可以在其他裝置上登入相同的帳號以同步資料。<br/>
                      目前連線需要後端設定 GCP Client ID，若未設定則處於展示 (Stub) 狀態。
                    </p>
                    <button 
                        className="primary-btn" 
                        onClick={async () => {
                            try {
                                const res = await fetch("/api/m1_4/github_auth_url");
                                const data = await res.json();
                                if (data.error) alert(data.error);
                                else alert("開發中: 此處將引導至 OAuth 授權頁面");
                            } catch (e) {
                                alert("網路錯誤");
                            }
                        }}
                    >
                      連結 Google 帳號
                    </button>
                    <div style={{ marginTop: "1rem", fontSize: "0.85rem", opacity: 0.6 }}>
                      當前設備身分 ID: {useCoOSStore.getState().currentRole === null ? "尚未載入" : "已啟用持久化本地識別"}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="settings-footer">
          <button className="settings-cancel-btn" onClick={onClose} disabled={saving}>取消</button>
          <button className="settings-save-btn" onClick={handleSave} disabled={loading || saving}>{saving ? "儲存中..." : "儲存設定"}</button>
        </div>
      </div>
    </div>
  );
}
