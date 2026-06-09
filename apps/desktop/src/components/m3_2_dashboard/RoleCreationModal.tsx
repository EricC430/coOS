import React, { useState, useRef } from "react";
import { apiCall } from "../../lib/ipc";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export function RoleCreationModal({ isOpen, onClose, onCreated }: Props) {
  const [name, setName] = useState("");
  const [color, setColor] = useState("#d4915e");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarFile(file);
    const reader = new FileReader();
    reader.onload = (ev) => setAvatarPreview(ev.target?.result as string);
    reader.readAsDataURL(file);
  }

  function handleClearAvatar() {
    setAvatarFile(null);
    setAvatarPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  async function handleSubmit() {
    if (!name) return;
    setLoading(true);
    try {
      let avatarUrl: string | undefined;

      // If an avatar image was selected, upload it as base64 data URL
      // The backend stores it in the roles.avatar_url column (L1 local — never leaves device)
      if (avatarPreview) {
        avatarUrl = avatarPreview;
      }

      await apiCall("/api/m6_2/roles", {
        method: "POST",
        body: JSON.stringify({ name, color, avatar_url: avatarUrl }),
      });
      onCreated();
      onClose();
      // Reset form
      setName("");
      setColor("#d4915e");
      setAvatarFile(null);
      setAvatarPreview(null);
    } catch {
      alert("建立角色失敗");
    } finally {
      setLoading(false);
    }
  }

  const initials = name ? name.slice(0, 2).toUpperCase() : "?";

  return (
    <div className="settings-backdrop" style={{ zIndex: 2000 }} onClick={onClose}>
      <div
        className="settings-dialog glass-card"
        style={{ maxWidth: "420px", height: "auto" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="settings-header">
          <h2>建立新角色</h2>
          <button className="settings-close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="settings-body" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Avatar preview + upload */}
          <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
            <div
              style={{
                width: 80,
                height: 80,
                borderRadius: "50%",
                background: avatarPreview ? "transparent" : `linear-gradient(135deg, ${color}, ${color}cc)`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                overflow: "hidden",
                flexShrink: 0,
                border: "2px solid rgba(255,255,255,0.15)",
                cursor: "pointer",
                position: "relative",
              }}
              onClick={() => fileInputRef.current?.click()}
              title="點擊上傳圖片"
            >
              {avatarPreview ? (
                <img
                  src={avatarPreview}
                  alt="avatar preview"
                  style={{ width: "100%", height: "100%", objectFit: "cover" }}
                />
              ) : (
                <span style={{ fontSize: 26, fontWeight: 700, color: "#fff" }}>{initials}</span>
              )}
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  background: "rgba(0,0,0,0.4)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  opacity: 0,
                  transition: "opacity 0.15s",
                  borderRadius: "50%",
                  fontSize: "1.4rem",
                }}
                className="avatar-hover-overlay"
              >
                📷
              </div>
            </div>

            <div style={{ flex: 1 }}>
              <div style={{ fontSize: "0.8rem", opacity: 0.6, marginBottom: "6px" }}>頭像圖片（選填）</div>
              <div style={{ display: "flex", gap: "8px" }}>
                <button
                  className="settings-tab-btn"
                  onClick={() => fileInputRef.current?.click()}
                  style={{ fontSize: "0.8rem", padding: "4px 10px" }}
                >
                  選擇圖片
                </button>
                {avatarFile && (
                  <button
                    className="settings-cancel-btn"
                    onClick={handleClearAvatar}
                    style={{ fontSize: "0.8rem", padding: "4px 10px" }}
                  >
                    移除
                  </button>
                )}
              </div>
              {avatarFile && (
                <div style={{ fontSize: "0.75rem", opacity: 0.5, marginTop: "4px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: 200 }}>
                  {avatarFile.name}
                </div>
              )}
            </div>

            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              style={{ display: "none" }}
              onChange={handleFileChange}
            />
          </div>

          <div className="settings-field">
            <label><strong>角色名稱</strong></label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="例如: 研究員, 健身達人..."
              autoFocus
              onKeyDown={(e) => { if (e.key === "Enter") handleSubmit(); }}
            />
          </div>

          <div className="settings-field">
            <label><strong>代表顏色</strong></label>
            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              <input
                type="color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                style={{ height: "40px", width: "60px", padding: "0", cursor: "pointer", border: "none", borderRadius: "12px", overflow: "hidden" }}
              />
              <span style={{ fontSize: "0.85rem", opacity: 0.6 }}>{color}</span>
            </div>
          </div>
        </div>

        <div className="settings-footer">
          <button className="settings-cancel-btn" onClick={onClose}>取消</button>
          <button
            className="settings-save-btn"
            onClick={handleSubmit}
            disabled={loading || !name}
          >
            {loading ? "建立中..." : "確定建立"}
          </button>
        </div>
      </div>

      <style>{`
        .avatar-hover-overlay { opacity: 0 !important; }
        div:hover > .avatar-hover-overlay { opacity: 1 !important; }
      `}</style>
    </div>
  );
}
