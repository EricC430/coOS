import React, { useState } from "react";
import { VisualItem, ItemCategory } from "../types";
import { buildObjectPrompt } from "../promptBuilder";
import { logGachaEvent } from "../telemetry";

export interface ObjectGeneratorProps {
  initialItem?: VisualItem | null;
  onGenerate: (
    semanticFeatures: string,
    category: "badge" | "prop"
  ) => Promise<VisualItem>;
  onSave: (item: VisualItem) => void;
}

export const ObjectGenerator: React.FC<ObjectGeneratorProps> = ({
  initialItem,
  onGenerate,
  onSave,
}) => {
  const [semanticFeatures, setSemanticFeatures] = useState("");
  const [category, setCategory] = useState<"badge" | "prop">(
    (initialItem?.category as "badge" | "prop") || "prop"
  );
  const [currentItem, setCurrentItem] = useState<VisualItem | null>(
    initialItem || null
  );
  const [inGachaPool, setInGachaPool] = useState(
    initialItem ? initialItem.in_gacha_pool : false
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async () => {
    if (!semanticFeatures.trim() && !initialItem) return;
    setLoading(true);
    setError(null);

    const fullPrompt = buildObjectPrompt(semanticFeatures, category);
    try {
      const generated = await onGenerate(fullPrompt, category);
      setCurrentItem(generated);
      setInGachaPool(generated.in_gacha_pool || false);
      logGachaEvent("object_generated", {
        category,
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
      category,
      has_transparency: true,
      in_gacha_pool: inGachaPool,
      is_user_generated: true,
    });
  };

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-slate-700 bg-slate-900/90 p-5 text-white shadow-xl backdrop-blur-md">
      <div className="border-b border-slate-800 pb-3">
        <h3 className="text-base font-bold text-teal-300">
          💎 AI 獨立物體與裝飾生成器
        </h3>
        <p className="text-xs text-slate-400">
          輸入物件語意特徵，自動生成純淨去背、具備透明 Alpha 通道的獨立物體
        </p>
      </div>

      <div className="flex flex-col gap-3">
        <div>
          <label
            htmlFor="semantic-features"
            className="mb-1 block text-xs font-semibold text-slate-300"
          >
            物件語意特徵
          </label>
          <input
            id="semantic-features"
            aria-label="物件語意特徵"
            type="text"
            placeholder="例如：發光的藍色能量水晶獎盃，帶有星塵粒子..."
            value={semanticFeatures}
            onChange={(e) => setSemanticFeatures(e.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-800/80 p-3 text-xs text-white placeholder-slate-500 focus:border-teal-500 focus:outline-none"
          />
        </div>

        <div>
          <label
            htmlFor="object-category"
            className="mb-1 block text-xs font-semibold text-slate-300"
          >
            物品類別
          </label>
          <select
            id="object-category"
            aria-label="物品類別"
            value={category}
            onChange={(e) => setCategory(e.target.value as "badge" | "prop")}
            className="w-full rounded-xl border border-slate-700 bg-slate-800/80 p-2.5 text-xs text-white focus:border-teal-500 focus:outline-none"
          >
            <option value="prop">擺飾道具 (Prop / Decoration)</option>
            <option value="badge">榮譽徽章 (Achievement Badge)</option>
          </select>
        </div>

        <button
          onClick={handleGenerate}
          disabled={loading || (!semanticFeatures.trim() && !initialItem)}
          className="rounded-xl bg-gradient-to-r from-teal-600 to-emerald-600 py-2.5 px-4 text-xs font-bold text-white shadow-lg shadow-teal-600/30 hover:brightness-110 active:scale-[0.99] transition disabled:opacity-50"
        >
          {loading ? "AI 生成中，請稍候..." : "生成物體"}
        </button>
      </div>

      {error && <p className="text-xs text-rose-400">{error}</p>}

      {/* Loading Skeleton */}
      {loading && (
        <div className="flex h-40 w-full animate-pulse items-center justify-center rounded-xl bg-slate-800 border border-slate-700 text-xs text-slate-400">
          正在生成透明去背物體...
        </div>
      )}

      {/* Preview with transparency checkerboard */}
      {currentItem && !loading && (
        <div className="flex flex-col gap-3 rounded-xl border border-slate-700/80 bg-slate-800/40 p-3">
          <div
            data-testid="transparency-checkerboard"
            className="relative flex h-40 w-full items-center justify-center overflow-hidden rounded-lg border border-slate-700 bg-[linear-gradient(45deg,#1f2937_25%,transparent_25%),linear-gradient(-45deg,#1f2937_25%,transparent_25%),linear-gradient(45deg,transparent_75%,#1f2937_75%),linear-gradient(-45deg,transparent_75%,#1f2937_75%)] bg-[size:16px_16px] bg-[position:0_0,0_8px,8px_-8px,-8px_0]"
          >
            <img
              src={currentItem.image_url}
              alt={currentItem.name}
              className="max-h-32 max-w-32 object-contain drop-shadow-md"
            />
          </div>

          <div className="flex items-center justify-between pt-1">
            <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
              <input
                type="checkbox"
                aria-label="投入抽獎池"
                checked={inGachaPool}
                onChange={(e) => setInGachaPool(e.target.checked)}
                className="h-4 w-4 rounded border-slate-600 bg-slate-700 text-teal-600 focus:ring-teal-500"
              />
              <span>投入抽獎池（可被盲盒抽取）</span>
            </label>

            <button
              onClick={handleSave}
              className="rounded-lg bg-teal-600 px-4 py-2 text-xs font-bold text-white shadow-md hover:bg-teal-500 active:scale-95 transition"
            >
              收進背包
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
