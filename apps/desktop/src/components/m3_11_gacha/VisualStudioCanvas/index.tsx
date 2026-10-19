import React, { useState } from "react";
import {
  VisualItem,
  CanvasLayer,
  HarmonizeRequest,
  HarmonizeResult,
  CustomThemeScene,
} from "../types";
import { CanvasViewport } from "./CanvasViewport";
import { LayerControls } from "./LayerControls";
import { useCanvasCompositor } from "./useCanvasCompositor";
import { useImageHarmonizer } from "./useImageHarmonizer";
import { logGachaEvent } from "../telemetry";

export interface VisualStudioCanvasProps {
  initialBackground?: VisualItem | null;
  initialLayers?: CanvasLayer[];
  inventoryObjects?: VisualItem[];
  availableBackgrounds?: VisualItem[];
  onHarmonize?: (request: HarmonizeRequest) => Promise<HarmonizeResult>;
  onApplyTheme?: (scene: CustomThemeScene) => void;
}

export const VisualStudioCanvas: React.FC<VisualStudioCanvasProps> = ({
  initialBackground = null,
  initialLayers = [],
  inventoryObjects = [],
  availableBackgrounds = [],
  onHarmonize,
  onApplyTheme,
}) => {
  const [background, setBackground] = useState<VisualItem | null>(
    initialBackground
  );
  const [layers, setLayers] = useState<CanvasLayer[]>(initialLayers);
  const [selectedLayerId, setSelectedLayerId] = useState<string | null>(
    initialLayers.length > 0 ? initialLayers[0].id : null
  );
  const [isPreviewMode, setIsPreviewMode] = useState(false);
  const [harmonizedResult, setHarmonizedResult] =
    useState<HarmonizeResult | null>(null);

  const { compositeToDataUrl, canvasWidth, canvasHeight } =
    useCanvasCompositor();
  const { harmonize, loading: harmonizerLoading } = useImageHarmonizer({
    customHarmonizeFn: onHarmonize,
  });

  const handleUpdateLayer = (id: string, updates: Partial<CanvasLayer>) => {
    setLayers((prev) =>
      prev.map((layer) => (layer.id === id ? { ...layer, ...updates } : layer))
    );
  };

  const handleRemoveLayer = (id: string) => {
    setLayers((prev) => prev.filter((layer) => layer.id !== id));
    if (selectedLayerId === id) {
      setSelectedLayerId(null);
    }
  };

  const handleAddLayer = (item: VisualItem) => {
    const newLayer: CanvasLayer = {
      id: `layer_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
      item_id: item.id,
      name: item.name,
      image_url: item.image_url,
      semantic_features: item.semantic_features,
      x: canvasWidth / 2,
      y: canvasHeight / 2,
      scale: 1.0,
      rotation: 0,
      zIndex: layers.length + 1,
    };
    setLayers((prev) => [...prev, newLayer]);
    setSelectedLayerId(newLayer.id);
  };

  const handlePlaceAndHarmonize = async () => {
    try {
      const draftBase64 = await compositeToDataUrl(background, layers);
      const objectsSummary = layers
        .map((l) => l.semantic_features || l.name)
        .join("; ");

      const result = await harmonize({
        base64_draft: draftBase64,
        scene_description: background?.scene_description || background?.name,
        objects_summary: objectsSummary,
      });

      setHarmonizedResult(result);
      setIsPreviewMode(true);
      logGachaEvent(
        result.is_fallback
          ? "canvas_harmonize_fallback"
          : "canvas_harmonize_completed",
        { provider: result.provider }
      );
    } catch {
      // In case of unexpected unhandled errors, fallback gracefully
      const draftBase64 = await compositeToDataUrl(background, layers);
      const fallbackResult: HarmonizeResult = {
        image_url: draftBase64,
        is_fallback: true,
        provider: "canvas_2d_fallback",
      };
      setHarmonizedResult(fallbackResult);
      setIsPreviewMode(true);
      logGachaEvent("canvas_harmonize_fallback", {
        provider: "canvas_2d_fallback",
      });
    }
  };

  const handleApplyAsTheme = async () => {
    if (!onApplyTheme) return;

    let finalUrl = harmonizedResult?.image_url;
    if (!finalUrl) {
      finalUrl = await compositeToDataUrl(background, layers);
    }

    const scene: CustomThemeScene = {
      id: `theme_${Date.now()}`,
      name: background?.name ? `${background.name} 自訂佈置` : "個人專屬桌面",
      created_at: new Date().toISOString(),
      canvas_state: {
        background,
        layers,
        selectedLayerId,
        canvasWidth,
        canvasHeight,
        harmonized_preview_url: finalUrl,
        is_preview_mode: isPreviewMode,
      },
      final_image_url: finalUrl,
      is_active_theme: true,
    };

    onApplyTheme(scene);
    logGachaEvent("custom_theme_applied", { theme_id: scene.id });
  };

  const handleDownload = async () => {
    let downloadUrl = harmonizedResult?.image_url;
    if (!downloadUrl) {
      downloadUrl = await compositeToDataUrl(background, layers);
    }

    const link = document.createElement("a");
    link.href = downloadUrl;
    link.download = `coos-theme-${Date.now()}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="flex flex-col gap-5 rounded-2xl border border-slate-800 bg-slate-950 p-6 text-white shadow-2xl">
      {/* Header & Mode Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-lg font-bold text-indigo-300">
            🎨 視覺畫布工作台 (Visual Studio Canvas)
          </h2>
          <p className="text-xs text-slate-400">
            在背景之上自由排版物件底稿，點擊「放置」進行非破壞性光影 AI 融合
          </p>
        </div>

        <div className="flex items-center gap-3">
          {isPreviewMode ? (
            <button
              onClick={() => setIsPreviewMode(false)}
              className="rounded-lg bg-slate-800 px-4 py-2 text-xs font-bold text-slate-200 border border-slate-700 hover:bg-slate-700 transition"
            >
              返回編輯圖層
            </button>
          ) : (
            <button
              onClick={handlePlaceAndHarmonize}
              disabled={harmonizerLoading}
              className="rounded-lg bg-gradient-to-r from-indigo-600 via-purple-600 to-pink-600 px-5 py-2 text-xs font-bold text-white shadow-lg shadow-indigo-600/30 hover:brightness-110 active:scale-95 transition disabled:opacity-50"
            >
              {harmonizerLoading ? "AI 融合中..." : "✨ 放置（AI 融合）"}
            </button>
          )}

          <button
            onClick={handleApplyAsTheme}
            className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow-md hover:bg-emerald-500 active:scale-95 transition"
          >
            套用為主題
          </button>

          <button
            onClick={handleDownload}
            className="rounded-lg bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-300 border border-slate-700 hover:bg-slate-700"
          >
            匯出下載
          </button>
        </div>
      </div>

      {/* Main View Area */}
      {isPreviewMode && harmonizedResult ? (
        <div className="flex flex-col items-center gap-4">
          <div
            data-testid="harmonized-preview"
            data-provider={harmonizedResult.provider}
            className="relative w-full max-w-[800px] h-[500px] overflow-hidden rounded-2xl border-2 border-indigo-500/50 bg-black shadow-2xl flex items-center justify-center"
          >
            <img
              src={harmonizedResult.image_url}
              alt="AI Harmonized Scene"
              className="h-full w-full object-cover"
            />
            {harmonizedResult.is_fallback && (
              <div className="absolute top-4 left-4 rounded-lg bg-amber-950/80 border border-amber-500/50 px-3 py-1.5 text-xs text-amber-200 backdrop-blur-md shadow-lg">
                ⚠️ AI 融合暫不可用，已為您保留 2D 精準合成圖
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <CanvasViewport
              background={background}
              layers={layers}
              selectedLayerId={selectedLayerId}
              onSelectLayer={setSelectedLayerId}
              onUpdateLayer={handleUpdateLayer}
              canvasWidth={canvasWidth}
              canvasHeight={canvasHeight}
            />
          </div>

          <div>
            <LayerControls
              layers={layers}
              selectedLayerId={selectedLayerId}
              inventoryObjects={inventoryObjects}
              availableBackgrounds={availableBackgrounds}
              currentBackground={background}
              onSelectLayer={setSelectedLayerId}
              onUpdateLayer={handleUpdateLayer}
              onRemoveLayer={handleRemoveLayer}
              onAddLayer={handleAddLayer}
              onSelectBackground={setBackground}
            />
          </div>
        </div>
      )}
    </div>
  );
};
