import React, { useState, useEffect } from "react";
import { useCoOSStore } from "../../stores/m3_1_global_store";
import {
  VisualItem,
  CustomThemeScene,
  GachaPoolMode,
  DrawResponse,
  ZPDChallenge,
} from "./types";
import { GachaDrawButton } from "./GachaDrawButton";
import { DrawChallengeButton } from "./DrawChallengeButton";
import { GachaPromotion } from "./GachaPromotion";
import { BackgroundGenerator } from "./BackgroundGenerator";
import { ObjectGenerator } from "./ObjectGenerator";
import { VisualStudioCanvas } from "./VisualStudioCanvas";
import { AchievementGrid } from "./HiddenAchievement/AchievementGrid";
import { PRESET_BACKGROUNDS } from "./presetBackgrounds";
import { PRESET_OBJECTS } from "./presetObjects";
import { BackgroundStyle, buildBackgroundPrompt, buildObjectPrompt } from "./promptBuilder";

export interface GachaStudioHubProps {
  onClose?: () => void;
  onApplyTheme?: (scene: CustomThemeScene) => void;
  defaultTab?: "gacha" | "studio" | "bg_gen" | "obj_gen" | "achievements";
}

export const GachaStudioHub: React.FC<GachaStudioHubProps> = ({
  onClose,
  onApplyTheme,
  defaultTab = "gacha",
}) => {
  const [activeTab, setActiveTab] = useState<
    "gacha" | "studio" | "bg_gen" | "obj_gen" | "achievements"
  >(defaultTab);

  // Global XP balance
  const xpBalance = useCoOSStore((s) => s.xpBalance);
  const applyXPGrant = useCoOSStore((s) => s.applyXPGrant);

  // Custom generated or won assets
  const [userBackgrounds, setUserBackgrounds] = useState<VisualItem[]>(() => {
    try {
      const saved = localStorage.getItem("coos_custom_backgrounds");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [userObjects, setUserObjects] = useState<VisualItem[]>(() => {
    try {
      const saved = localStorage.getItem("coos_custom_objects");
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Persist to local storage
  useEffect(() => {
    try {
      localStorage.setItem("coos_custom_backgrounds", JSON.stringify(userBackgrounds));
    } catch (e) {
      console.warn("Failed to persist custom backgrounds:", e);
    }
  }, [userBackgrounds]);

  useEffect(() => {
    try {
      localStorage.setItem("coos_custom_objects", JSON.stringify(userObjects));
    } catch (e) {
      console.warn("Failed to persist custom objects:", e);
    }
  }, [userObjects]);

  // Combine presets with user creations
  const allBackgrounds = [...PRESET_BACKGROUNDS, ...userBackgrounds];
  const allObjects = [...PRESET_OBJECTS, ...userObjects];

  // Gacha draw function
  const handlePerformDraw = async (poolMode: GachaPoolMode): Promise<DrawResponse> => {
    // Attempt backend draw first
    try {
      const res = await fetch("/api/m6_5/gacha/draw", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cost_xp: 100, pool_mode: poolMode }),
      });
      if (res.ok) {
        const data = await res.json();
        if (data.item) {
          applyXPGrant({ amount: -100, new_total: Math.max(0, xpBalance - 100) });
          return data;
        }
      }
    } catch {
      // Backend unavailable: fallback to client pool
    }

    // Client fallback selection
    const pool =
      poolMode === "hybrid" && (userBackgrounds.length > 0 || userObjects.length > 0)
        ? [...allBackgrounds, ...allObjects]
        : [...PRESET_BACKGROUNDS, ...PRESET_OBJECTS];

    const randomItem = pool[Math.floor(Math.random() * pool.length)];
    const drawnItem: VisualItem = {
      ...randomItem,
      id: `item_draw_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      unlocked_at: new Date().toISOString(),
    };

    applyXPGrant({ amount: -100, new_total: Math.max(0, xpBalance - 100) });

    return {
      success: true,
      item: drawnItem,
      cost: 100,
      remaining_xp: Math.max(0, xpBalance - 100),
    };
  };

  // Item acquired handler
  const handleItemAcquired = (item: VisualItem) => {
    if (item.category === "background") {
      setUserBackgrounds((prev) => [item, ...prev]);
    } else {
      setUserObjects((prev) => [item, ...prev]);
    }
  };

  // ZPD Challenge Draw handler
  const handleDrawChallenge = async (): Promise<ZPDChallenge> => {
    try {
      const res = await fetch("/api/m4_11/zpd_tasks/next");
      if (res.ok) {
        return await res.json();
      }
    } catch {
      // fallback
    }

    const challenges: ZPDChallenge[] = [
      {
        id: `zpd_${Date.now()}_1`,
        title: "深度專注：完成一段 25 分鐘番茄鐘無干擾反思",
        description: "在專注模式下記錄今日的心得，挑戰心理舒適區邊界。",
        difficulty: "just-manageable",
        estimated_minutes: 25,
        xp_reward: 80,
      },
      {
        id: `zpd_${Date.now()}_2`,
        title: "認知重構：為困擾情境寫下 3 個非防衛性視角",
        description: "運用薩提爾冰山隱喻，嘗試梳理對話深層期待與自我價值感。",
        difficulty: "stretch",
        estimated_minutes: 20,
        xp_reward: 120,
      },
      {
        id: `zpd_${Date.now()}_3`,
        title: "跨步躍進：重構一個歷史任務清單並消除阻礙",
        description: "挑選擱置超過三日的微型專案進行破冰拆解。",
        difficulty: "stretch",
        estimated_minutes: 30,
        xp_reward: 150,
      },
    ];

    return challenges[Math.floor(Math.random() * challenges.length)];
  };

  // Background generator: onGenerate
  const handleGenerateBackground = async (
    prompt: string,
    style: BackgroundStyle
  ): Promise<VisualItem> => {
    const fullPrompt = buildBackgroundPrompt(prompt, style);
    const encoded = encodeURIComponent(fullPrompt);
    const imageUrl = `https://image.pollinations.ai/prompt/${encoded}?width=1280&height=720&nologo=true&seed=${Date.now()}`;

    return {
      id: `bg_${Date.now()}`,
      name: prompt.trim().substring(0, 16) || "自訂 AI 生成背景",
      description: prompt,
      category: "background",
      rarity: "rare",
      image_url: imageUrl,
      has_transparency: false,
      scene_description: prompt,
      is_user_generated: true,
      in_gacha_pool: false,
      hidden: false,
      unlocked_at: new Date().toISOString(),
    };
  };

  // Object generator: onGenerate
  const handleGenerateObject = async (
    semanticFeatures: string,
    category: "badge" | "prop"
  ): Promise<VisualItem> => {
    const fullPrompt = buildObjectPrompt(semanticFeatures, category);
    const encoded = encodeURIComponent(fullPrompt);
    const imageUrl = `https://image.pollinations.ai/prompt/${encoded}?width=512&height=512&nologo=true&transparent=true&seed=${Date.now()}`;

    return {
      id: `obj_${Date.now()}`,
      name: semanticFeatures.trim().substring(0, 16) || "自訂裝飾物件",
      description: semanticFeatures,
      category,
      rarity: "epic",
      image_url: imageUrl,
      has_transparency: true,
      semantic_features: semanticFeatures,
      is_user_generated: true,
      in_gacha_pool: false,
      hidden: false,
      unlocked_at: new Date().toISOString(),
    };
  };

  // Apply theme handler
  const handleApplyTheme = (scene: CustomThemeScene) => {
    try {
      localStorage.setItem("coos_active_desktop_theme", JSON.stringify(scene));
      window.dispatchEvent(
        new CustomEvent("coos:theme-scene-applied", { detail: scene })
      );
    } catch (e) {
      console.warn("Failed to cache applied theme scene:", e);
    }
    onApplyTheme?.(scene);
  };

  return (
    <div className="flex flex-col h-full w-full bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Header bar */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/60 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <span className="text-2xl">✨</span>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
              視覺抽卡工坊
              <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                M3.11
              </span>
            </h1>
            <p className="text-xs text-slate-400">
              變動比例盲盒抽獎 × 現代自然語言 AI 生圖 × 畫布光影智能融合
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-indigo-950/40 border border-indigo-800/40">
            <span className="text-xs text-indigo-300">持有 XP</span>
            <span className="text-sm font-bold text-indigo-400">{xpBalance}</span>
          </div>

          {onClose && (
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
              title="關閉工坊"
              aria-label="關閉"
            >
              ✕
            </button>
          )}
        </div>
      </header>

      {/* Tab Navigation */}
      <nav className="flex items-center px-6 gap-2 border-b border-slate-800 bg-slate-900/30 overflow-x-auto">
        <button
          onClick={() => setActiveTab("gacha")}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
            activeTab === "gacha"
              ? "border-indigo-500 text-indigo-400 bg-indigo-500/10"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>🎰</span>
          <span>盲盒抽獎</span>
        </button>

        <button
          onClick={() => setActiveTab("studio")}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
            activeTab === "studio"
              ? "border-indigo-500 text-indigo-400 bg-indigo-500/10"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>🎨</span>
          <span>合成畫布</span>
        </button>

        <button
          onClick={() => setActiveTab("bg_gen")}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
            activeTab === "bg_gen"
              ? "border-indigo-500 text-indigo-400 bg-indigo-500/10"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>🖼️</span>
          <span>背景生成</span>
        </button>

        <button
          onClick={() => setActiveTab("obj_gen")}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
            activeTab === "obj_gen"
              ? "border-indigo-500 text-indigo-400 bg-indigo-500/10"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>🔮</span>
          <span>物件生成</span>
        </button>

        <button
          onClick={() => setActiveTab("achievements")}
          className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-all ${
            activeTab === "achievements"
              ? "border-indigo-500 text-indigo-400 bg-indigo-500/10"
              : "border-transparent text-slate-400 hover:text-slate-200"
          }`}
        >
          <span>🏆</span>
          <span>成就圖鑑</span>
        </button>
      </nav>

      {/* Tab Panels */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Tab 1: Gacha */}
        {activeTab === "gacha" && (
          <div className="max-w-4xl mx-auto flex flex-col gap-8">
            {/* Promotion banner with psychological suppression */}
            <GachaPromotion
              implicitState={{ label: "focused", confidence: 0.9 }}
              onOpenGacha={() => setActiveTab("gacha")}
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Card 1: XP Gacha Draw */}
              <div className="flex flex-col gap-4 p-6 rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl">
                <div className="flex items-center justify-between">
                  <h2 className="text-base font-semibold text-white flex items-center gap-2">
                    <span>🎰</span> 幸運盲盒抽卡
                  </h2>
                  <span className="text-xs px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">
                    消耗 100 XP
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  消耗日常賺取的 XP 進行變動比例盲盒抽獎。支援切換「精選獎池」與「自創混合池」，即刻開獎並附防沉迷冷卻保護。
                </p>

                <div className="mt-2 flex flex-col items-center justify-center p-6 rounded-xl bg-slate-950/60 border border-slate-800/80">
                  <GachaDrawButton
                    userXp={xpBalance}
                    cost={100}
                    onDraw={handlePerformDraw}
                    onItemAcquired={handleItemAcquired}
                    userPoolItems={[...userBackgrounds, ...userObjects]}
                  />
                </div>
              </div>

              {/* Card 2: ZPD Challenge Task Draw */}
              <div className="flex flex-col gap-4 p-6 rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl">
                <div className="flex items-center justify-between">
                  <h2 className="text-base font-semibold text-white flex items-center gap-2">
                    <span>🎯</span> 抽取近側發展區 (ZPD) 挑戰
                  </h2>
                  <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                    免質押 0 XP
                  </span>
                </div>
                <p className="text-xs text-slate-400 leading-relaxed">
                  根據您的能力近側發展區程序化生成成長挑戰任務，不損失現有 XP 資產，激發內在探索動機。
                </p>

                <div className="mt-2 flex flex-col items-center justify-center p-6 rounded-xl bg-slate-950/60 border border-slate-800/80">
                  <DrawChallengeButton
                    onDrawChallenge={handleDrawChallenge}
                    onAcceptChallenge={(task) => console.log("Challenge accepted:", task)}
                  />
                </div>
              </div>
            </div>

            {/* Inventory preview */}
            <div className="flex flex-col gap-3 p-5 rounded-2xl border border-slate-800/80 bg-slate-900/40">
              <h3 className="text-sm font-semibold text-slate-300 flex items-center gap-2">
                <span>🎒</span> 目前收藏資產總覽
              </h3>
              <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 gap-3">
                {allBackgrounds.slice(0, 3).map((bg) => (
                  <div
                    key={bg.id}
                    className="flex flex-col items-center gap-1.5 p-2 rounded-xl bg-slate-950/60 border border-slate-800 text-center"
                  >
                    <div className="w-full h-16 rounded-lg overflow-hidden bg-slate-800 flex items-center justify-center">
                      <img
                        src={bg.image_url}
                        alt={bg.name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <span className="text-xs text-slate-300 truncate w-full">
                      {bg.name}
                    </span>
                    <span className="text-[10px] text-slate-500">背景</span>
                  </div>
                ))}
                {allObjects.slice(0, 3).map((obj) => (
                  <div
                    key={obj.id}
                    className="flex flex-col items-center gap-1.5 p-2 rounded-xl bg-slate-950/60 border border-slate-800 text-center"
                  >
                    <div className="w-full h-16 rounded-lg overflow-hidden bg-slate-900/80 flex items-center justify-center p-1">
                      <img
                        src={obj.image_url}
                        alt={obj.name}
                        className="w-full h-full object-contain"
                      />
                    </div>
                    <span className="text-xs text-slate-300 truncate w-full">
                      {obj.name}
                    </span>
                    <span className="text-[10px] text-slate-500">物件</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Visual Studio Canvas */}
        {activeTab === "studio" && (
          <div className="max-w-6xl mx-auto">
            <VisualStudioCanvas
              availableBackgrounds={allBackgrounds}
              inventoryObjects={allObjects}
              onApplyTheme={handleApplyTheme}
            />
          </div>
        )}

        {/* Tab 3: Background Generator */}
        {activeTab === "bg_gen" && (
          <div className="max-w-2xl mx-auto">
            <BackgroundGenerator
              onGenerate={handleGenerateBackground}
              onSave={(bg) => {
                setUserBackgrounds((prev) => [bg, ...prev]);
                alert("背景已成功儲存至收藏庫！");
              }}
            />
          </div>
        )}

        {/* Tab 4: Object Generator */}
        {activeTab === "obj_gen" && (
          <div className="max-w-2xl mx-auto">
            <ObjectGenerator
              onGenerate={handleGenerateObject}
              onSave={(obj) => {
                setUserObjects((prev) => [obj, ...prev]);
                alert("物件已成功儲存至背包！");
              }}
            />
          </div>
        )}

        {/* Tab 5: Hidden Achievements */}
        {activeTab === "achievements" && (
          <div className="max-w-4xl mx-auto flex flex-col gap-4">
            <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-800/40 text-xs text-indigo-300 leading-relaxed">
              💡 <strong>防 FOMO 心理機制保護</strong>：所有未解鎖的隱藏成就均嚴格採「零 UI 洩漏」原則，介面無佔位格或剩餘計數；唯有在您達成特定深度心理探索時以驚喜彈窗呈現！
            </div>
            <AchievementGrid items={[...allBackgrounds, ...allObjects]} />
          </div>
        )}
      </div>
    </div>
  );
};
