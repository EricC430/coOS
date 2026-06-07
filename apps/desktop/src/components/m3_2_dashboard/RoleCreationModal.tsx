import React, { useState } from "react";
import { apiCall } from "../../lib/ipc";
import { useCoOSStore } from "../../stores/m3_1_global_store";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onCreated: () => void;
}

export function RoleCreationModal({ isOpen, onClose, onCreated }: Props) {
  const [name, setName] = useState("");
  const [color, setColor] = useState("#d4915e");
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (!name) return;
    setLoading(true);
    try {
      await apiCall("/api/m6_2/roles", {
        method: "POST",
        body: JSON.stringify({ name, color }),
      });
      onCreated();
      onClose();
      setName("");
    } catch (err) {
      alert("建立角色失敗");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="settings-backdrop" style={{ zIndex: 2000 }} onClick={onClose}>
      <div className="settings-dialog glass-card" style={{ maxWidth: '400px', height: 'auto' }} onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>建立新角色</h2>
          <button className="settings-close-btn" onClick={onClose}>&times;</button>
        </div>
        <div className="settings-body" style={{ padding: '20px' }}>
          <div className="settings-field">
            <label><strong>角色名稱</strong></label>
            <input 
              type="text" 
              value={name} 
              onChange={(e) => setName(e.target.value)} 
              placeholder="例如: 研究員, 健身達人..."
              autoFocus
            />
          </div>
          <div className="settings-field">
            <label><strong>代表顏色</strong></label>
            <input 
              type="color" 
              value={color} 
              onChange={(e) => setColor(e.target.value)} 
              style={{ height: '40px', padding: '2px' }}
            />
          </div>
        </div>
        <div className="settings-footer">
          <button className="settings-cancel-btn" onClick={onClose}>取消</button>
          <button className="settings-save-btn" onClick={handleSubmit} disabled={loading || !name}>
            {loading ? "建立中..." : "確定建立"}
          </button>
        </div>
      </div>
    </div>
  );
}
