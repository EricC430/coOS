import React, { useState } from "react";
import { ZPDChallenge } from "../types";

export interface DrawChallengeButtonProps {
  onDrawChallenge: () => Promise<ZPDChallenge>;
  onAcceptChallenge?: (challenge: ZPDChallenge) => void;
}

/**
 * DrawChallengeButton: Complies with Constitution Rule 2 (RISK-07)
 * ZPD Dynamic Challenge Draw:
 * Draws tailored proximal development challenges.
 * STRICTLY FORBIDS ANY XP STAKING, WAGERING, OR LOSS MECHANISMS.
 */
export const DrawChallengeButton: React.FC<DrawChallengeButtonProps> = ({
  onDrawChallenge,
  onAcceptChallenge,
}) => {
  const [loading, setLoading] = useState(false);
  const [currentChallenge, setCurrentChallenge] = useState<ZPDChallenge | null>(
    null
  );
  const [error, setError] = useState<string | null>(null);

  const handleDraw = async () => {
    setLoading(true);
    setError(null);
    try {
      const challenge = await onDrawChallenge();
      setCurrentChallenge(challenge);
    } catch (err: any) {
      setError(err.message || "取得動態挑戰失敗");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-700 bg-slate-800/80 p-4 text-white shadow-md">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-bold text-slate-200">
            🎯 ZPD 動態延伸挑戰
          </h4>
          <p className="text-xs text-slate-400">
            抽取符合目前能力前沿的專注任務，自由挑戰零風險
          </p>
        </div>

        <button
          onClick={handleDraw}
          disabled={loading}
          aria-label="🎲 抽挑戰"
          className="rounded-lg bg-gradient-to-r from-teal-600 to-emerald-600 px-3.5 py-2 text-xs font-bold text-white shadow-md hover:brightness-110 active:scale-95 transition disabled:opacity-50"
        >
          {loading ? "抽取中..." : "🎲 抽挑戰"}
        </button>
      </div>

      {error && <p className="text-xs text-rose-400">{error}</p>}

      {currentChallenge && (
        <div
          data-testid="challenge-result-card"
          className="mt-2 rounded-lg border border-teal-500/40 bg-teal-950/40 p-3.5 backdrop-blur-sm"
        >
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold text-teal-200">
              {currentChallenge.title}
            </span>
            <span className="rounded bg-teal-900/80 px-2 py-0.5 text-[11px] font-semibold text-teal-300 border border-teal-500/30">
              +{currentChallenge.xp_reward} XP
            </span>
          </div>

          <p className="mt-1.5 text-xs text-slate-300 leading-relaxed">
            {currentChallenge.description}
          </p>

          <div className="mt-2.5 flex items-center justify-between text-[11px] text-teal-400">
            <span>預估時間：約 {currentChallenge.estimated_minutes} 分鐘</span>
            {onAcceptChallenge && (
              <button
                onClick={() => onAcceptChallenge(currentChallenge)}
                className="rounded bg-teal-600/90 px-3 py-1 font-bold text-white hover:bg-teal-500 transition"
              >
                接受挑戰
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
