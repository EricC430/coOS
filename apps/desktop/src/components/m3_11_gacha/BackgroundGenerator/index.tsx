import React, { useState } from "react";
import { VisualItem } from "../types";
import { BackgroundStyle, buildBackgroundPrompt } from "../promptBuilder";
import { logGachaEvent } from "../telemetry";

export interface BackgroundGeneratorProps {
  initialItem?: VisualItem | null;
  onGenerate: (prompt: string, style: BackgroundStyle) => Promise<VisualItem>;
  onSave: (item: VisualItem) => void;
}

export const BackgroundGenerator: React.FC<BackgroundGeneratorProps> = ({
  initialItem,
  onGenerate,
  onSave,
}) => {
  const [sceneDescription, setSceneDescription] = useState("");
  const [style, setStyle] = useState<BackgroundStyle>("cyberpunk");
  const [currentItem, setCurrentItem] = useState<VisualItem | null>(
    initialItem || null
  );
  const [inGachaPool, setInGachaPool] = useState(
    initialItem ? initialItem.in_gacha_pool : false
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!sceneDescription.trim() && !initialItem) return;
    setLoading(true);
    setError(null);

    const fullPrompt = buildBackgroundPrompt(sceneDescription, style);
    try {
      const generated = await onGenerate(fullPrompt, style);
      setCurrentItem(generated);
      setInGachaPool(generated.in_gacha_pool || false);
      logGachaEvent("background_generated", {
        style,
        in_gacha_pool: generated.in_gacha_pool,
      });
    } catch (err: any) {
      setError(`生成失敗：${err.message || "連線逾時"}`);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = () => {
    if (!currentItem) return;
    onSave({
      ...currentItem,
      in_gacha_pool: inGachaPool,
      is_user_generated: true,
    });
  };

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-slate-700 bg-slate-900/90 p-5 text-white shadow-xl backdrop-blur-md">
      <div className="border-b border-slate-800 pb-3">
        <h3 className="text-base font-bold text-indigo-300">
          🎨 AI 背景場景生成器
        </h3>
        <p className="text-xs text-slate-400">
          輸入具體場景描述，系統將採用自然語言句式重構光影與空間氛圍
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <div>
          <label
            htmlFor="scene-description"
            className="mb-1 block text-xs font-semibold text-slate-300"
          >
            背景場景描述
          </label>
          <textarea
            id="scene-description"
            aria-label="背景場景描述"
            rows={3}
            placeholder="例如：安靜的賽博龐克研究室，窗外有霓虹雨夜與遠景大樓..."
            value={sceneDescription}
            onChange={(e) => setSceneDescription(e.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-800/80 p-3 text-xs text-white placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
          />
        </div>

        <div>
          <label
            htmlFor="style-template"
            className="mb-1 block text-xs font-semibold text-slate-300"
          >
            風格模板
          </label>
          <select
            id="style-template"
            aria-label="風格模板"
            value={style}
            onChange={(e) => setStyle(e.target.value as BackgroundStyle)}
            className="w-full rounded-xl border border-slate-700 bg-slate-800/80 p-2.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
          >
            <option value="cyberpunk">賽博龐克 (Cyberpunk Neon)</option>
            <option value="zen">日式禪風 (Zen Garden & Tea Room)</option>
            <option value="scifi">未來科幻 (Sci-Fi High-Tech)</option>
            <option value="nature">自然原野 (Pristine Nature)</option>
            <option value="minimalist">極簡原木 (Scandinavian Minimal)</option>
            <option value="fantasy">奇幻極光 (Aurora Fantasy)</option>
          </select>
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading || (!sceneDescription.trim() && !initialItem)}
          className="rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 py-2.5 px-4 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 hover:brightness-110 active:scale-[0.99] transition disabled:opacity-50"
        >
          {loading ? "AI 生成中，請稍候..." : "生成背景"}
        </button>
      </div>

      {error && (
        <div className="flex items-center justify-between rounded-xl border border-rose-500/40 bg-rose-950/40 p-3 text-xs text-rose-300">
          <span>{error}</span>
          <button
            onClick={handleGenerate}
            className="rounded bg-rose-700 px-2 py-1 font-semibold text-white hover:bg-rose-600"
          >
            重新生成
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {loading && (
        <div className="flex h-48 w-full animate-pulse items-center justify-center rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-400">
          正在調用自然語言圖像生成管道...
        </div>
      )}

      {/* Preview & Save Controls */}
      {currentItem && !loading && (
        <div className="flex flex-col gap-3 rounded-xl border border-slate-700/80 bg-slate-800/40 p-3">
          <div
            data-testid="background-preview"
            className="relative h-48 w-full overflow-hidden rounded-lg bg-black border border-slate-700"
          >
            <img
              src={currentItem.image_url}
              alt={currentItem.name}
              className="h-full w-full object-cover"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                aria-label="投入抽獎池"
                checked={inGachaPool}
                onChange={(e) => setInGachaPool(e.target.checked)}
                className="h-4 w-4 rounded border-slate-600 bg-slate-700 text-indigo-600 focus:ring-indigo-500"
              />
              <span>投入抽獎池（後續抽卡有機率抽中）</span>
            </label>

            <button
              onClick={handleSave}
              className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-md hover:bg-emerald-500 active:scale-95 transition"
            >
              儲存至收藏庫
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
