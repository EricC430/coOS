import React, { useState, useEffect } from "react";
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
  const [activeTab, setActiveTab] = useState<"privacy" | "role" | "system">("privacy");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
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
  }, [isOpen, currentRole?.id]);

  if (!isOpen) return null;

  const handleSave = async () => {
    if (!currentRole?.id) return;
    const roleId = currentRole.id;
    setSaving(true);
    try {
      await apiCall(`/api/settings?role_id=${roleId}`, {
        method: "POST",
        body: JSON.stringify(settings),
      });
      
      // Update local storage/DOM attributes for instant feedback
      if (settings.theme === "dark" || settings.theme === "light") {
        document.documentElement.setAttribute("data-theme", settings.theme);
      } else {
        // Fall back to system / default
        const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
        document.documentElement.setAttribute("data-theme", prefersDark ? "dark" : "light");
      }
      
      onClose();
    } catch (err) {
      console.error("Failed to save settings:", err);
      alert("儲存設定失敗");
    } finally {
      setSaving(false);
    }
  };

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
            {/* Sidebar Tabs */}
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
            </div>

            {/* Tab Contents */}
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

                  <div className="settings-field row">
                    <label>
                      <strong>語音雲端推論同意</strong>
                      <span className="field-desc">是否允許將語音輸入發送至雲端 Whisper 進行高精準度辨識，未開啟將使用本地推理。</span>
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
                      <span className="field-desc">是否允許與雲端資料庫（Supabase PostgreSQL）進行非對稱資料同步與備份。</span>
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
                    <label>
                      <strong>主題風格</strong>
                      <span className="field-desc">設定該角色的預設色彩風格（淺色、深色、跟隨系統）。</span>
                    </label>
                    <select
                      value={settings.theme}
                      onChange={(e) => setSettings({ ...settings, theme: e.target.value })}
                    >
                      <option value="default">跟隨系統 (Default)</option>
                      <option value="light">淺色模式 (Light)</option>
                      <option value="dark">深色模式 (Dark)</option>
                    </select>
                  </div>

                  <div className="settings-field">
                    <label>
                      <strong>每日日報生成時間</strong>
                      <span className="field-desc">系統彙整今日專注時數、生成每日反思與 XP 結算的時間。</span>
                    </label>
                    <input
                      type="time"
                      value={settings.daily_report_time}
                      onChange={(e) => setSettings({ ...settings, daily_report_time: e.target.value })}
                    />
                  </div>

                  <div className="settings-field">
                    <label>
                      <strong>每日專注時間區段</strong>
                      <span className="field-desc">在此區段內觸發深色模式時防打擾守衛會主動過濾推播通知。</span>
                    </label>
                    <div className="time-range-row">
                      <input
                        type="time"
                        value={settings.focus_hours_start}
                        onChange={(e) => setSettings({ ...settings, focus_hours_start: e.target.value })}
                      />
                      <span>至</span>
                      <input
                        type="time"
                        value={settings.focus_hours_end}
                        onChange={(e) => setSettings({ ...settings, focus_hours_end: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="settings-field row">
                    <label>
                      <strong>啟用靜音/通知防打擾</strong>
                      <span className="field-desc">是否允許系統在專注時間（Deep Work）時自動切換 Windows 通知模式。</span>
                    </label>
                    <input
                      type="checkbox"
                      className="settings-toggle-checkbox"
                      checked={settings.notification_enabled}
                      onChange={(e) => setSettings({ ...settings, notification_enabled: e.target.checked })}
                    />
                  </div>
                </div>
              )}

              {activeTab === "system" && (
                <div className="settings-section">
                  <h3>系統與本地 AI 配置</h3>

                  <div className="settings-field">
                    <label>
                      <strong>Ollama 本地連接位址</strong>
                      <span className="field-desc">邊緣推理伺服器的連接端點（如 local Ollama 或 iPad M1 ai.local）。</span>
                    </label>
                    <input
                      type="text"
                      value={settings.ai_local_host}
                      placeholder="http://127.0.0.1:11434"
                      onChange={(e) => setSettings({ ...settings, ai_local_host: e.target.value })}
                    />
                  </div>

                  <div className="settings-field">
                    <label>
                      <strong>Gemma 邊緣模型名稱</strong>
                      <span className="field-desc">用於本地端點進行意圖分析與安全過濾的模型 Identifier。</span>
                    </label>
                    <input
                      type="text"
                      value={settings.gemma_model}
                      placeholder="gemma-4-e4b-it-4bit"
                      onChange={(e) => setSettings({ ...settings, gemma_model: e.target.value })}
                    />
                  </div>

                  <div className="settings-field">
                    <label>
                      <strong>iPad M1 ai.local 位址</strong>
                      <span className="field-desc">用於多裝置推理分流時連線至 iPad 的 IP 位置。</span>
                    </label>
                    <input
                      type="text"
                      value={settings.ipad_ai_local_host}
                      placeholder="192.168.0.42:11434"
                      onChange={(e) => setSettings({ ...settings, ipad_ai_local_host: e.target.value })}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        <div className="settings-footer">
          <button className="settings-cancel-btn" onClick={onClose} disabled={saving}>
            取消
          </button>
          <button className="settings-save-btn" onClick={handleSave} disabled={loading || saving}>
            {saving ? "儲存中..." : "儲存設定"}
          </button>
        </div>
      </div>
    </div>
  );
}
