import React, { useState } from "react";
import { createStake } from "./api";
import { useCoOSStore } from "../../stores/m3_1_global_store";

interface StakeXPInterfaceProps {
  isOpen: boolean;
  onClose: () => void;
  taskTitle: string;
  taskId?: string;
  communityId: string;
  onSuccess: (amount: number, stakeId: string) => void;
}

export const StakeXPInterface: React.FC<StakeXPInterfaceProps> = ({
  isOpen,
  onClose,
  taskTitle,
  taskId,
  communityId,
  onSuccess,
}) => {
  const { xpBalance, applyXPGrant } = useCoOSStore();
  const [amount, setAmount] = useState<number>(10);
  const [successRate, setSuccessRate] = useState<number>(80);
  const [zpdZone, setZpdZone] = useState<"comfort" | "stretch" | "edge">("stretch");
  
  // Default deadline: 24 hours from now
  const [deadline, setDeadline] = useState<string>(() => {
    const d = new Date();
    d.setHours(d.getHours() + 24);
    // Format to yyyy-MM-ddThh:mm
    return d.toISOString().slice(0, 16);
  });

  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  // Front-end RISK-07 & Balance checks
  const isBalanceInsufficient = amount > xpBalance;
  const isRisk07Blocked = successRate < 70 || zpdZone === "edge";
  const isInvalidAmount = amount <= 0;
  const isDisabled = isBalanceInsufficient || isRisk07Blocked || isInvalidAmount || loading;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (isDisabled) return;

    setLoading(true);
    try {
      const stake = await createStake({
        community_id: communityId,
        xp_amount: amount,
        task_id: taskId,
        deadline: new Date(deadline).toISOString(),
      });

      // Optimistic XP update
      const newTotal = xpBalance - amount;
      applyXPGrant({ amount: -amount, new_total: newTotal });

      onSuccess(amount, stake.id);
      onClose();
    } catch (err) {
      alert(err instanceof Error ? err.message : "質押失敗");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="stake-modal-backdrop" data-testid="stake-modal-backdrop">
      <div className="stake-modal" role="dialog" aria-modal="true">
        <h3>🎯 XP 質押與對賭</h3>
        
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1">
            <span className="text-2xs text-text-muted">質押任務</span>
            <span className="text-sm font-semibold text-text-primary pl-2 border-l-2 border-gold-accent">
              {taskTitle}
            </span>
          </div>

          <div className="stake-input-group">
            <label className="stake-input-label">質押數量 (目前 XP: {xpBalance})</label>
            <input
              type="number"
              className="stake-input"
              value={amount}
              onChange={(e) => setAmount(Number(e.target.value))}
              min={1}
              required
              data-testid="stake-amount-input"
            />
          </div>

          <div className="stake-input-group">
            <label className="stake-input-label">預估成功機率: {successRate}%</label>
            <input
              type="range"
              min="0"
              max="100"
              className="w-full accent-gold-accent cursor-pointer"
              value={successRate}
              onChange={(e) => setSuccessRate(Number(e.target.value))}
              data-testid="success-rate-slider"
            />
          </div>

          <div className="stake-input-group">
            <label className="stake-input-label">任務挑戰區間 (ZPD)</label>
            <select
              className="stake-input"
              value={zpdZone}
              onChange={(e) => setZpdZone(e.target.value as any)}
              data-testid="zpd-zone-select"
            >
              <option value="comfort">舒適區 (Comfort Zone)</option>
              <option value="stretch">拉伸區 (ZPD Zone)</option>
              <option value="edge">邊緣區 (Edge ZPD)</option>
            </select>
          </div>

          <div className="stake-input-group">
            <label className="stake-input-label">到期結算時間</label>
            <input
              type="datetime-local"
              className="stake-input"
              value={deadline}
              onChange={(e) => setDeadline(e.target.value)}
              required
            />
          </div>

          {/* Warnings */}
          {isBalanceInsufficient && (
            <div className="stake-warning" data-testid="stake-warning">
              ⚠️ 您的 XP 餘額不足以進行此數量的質押。
            </div>
          )}

          {isRisk07Blocked && (
            <div className="stake-warning" data-testid="stake-warning">
              ⚠️ 邊緣區任務或預估成功率低於 70% 時禁用 XP 質押，以防止任務失敗與扣點造成雙重打擊（Dropout 緩解策略）。
            </div>
          )}

          <div className="stake-actions">
            <button
              type="submit"
              className="stake-confirm-btn"
              disabled={isDisabled}
              data-testid="stake-btn"
            >
              {loading ? "質押中..." : "確認質押對賭"}
            </button>
            <button
              type="button"
              className="stake-cancel-btn"
              onClick={onClose}
              disabled={loading}
            >
              取消
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
