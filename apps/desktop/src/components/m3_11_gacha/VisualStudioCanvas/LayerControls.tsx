import React from "react";
import { CanvasLayer, VisualItem } from "../types";

export interface LayerControlsProps {
  layers: CanvasLayer[];
  selectedLayerId: string | null;
  inventoryObjects?: VisualItem[];
  availableBackgrounds?: VisualItem[];
  currentBackground?: VisualItem | null;
  onSelectLayer: (id: string | null) => void;
  onUpdateLayer: (id: string, updates: Partial<CanvasLayer>) => void;
  onRemoveLayer: (id: string) => void;
  onAddLayer: (item: VisualItem) => void;
  onSelectBackground?: (bg: VisualItem) => void;
}

export const LayerControls: React.FC<LayerControlsProps> = ({
  layers,
  selectedLayerId,
  inventoryObjects = [],
  availableBackgrounds = [],
  currentBackground,
  onSelectLayer,
  onUpdateLayer,
  onRemoveLayer,
  onAddLayer,
  onSelectBackground,
}) => {
  const selectedLayer = layers.find((l) => l.id === selectedLayerId);

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-slate-700 bg-slate-900/80 p-4 text-white">
      {/* Background Selector */}
      {availableBackgrounds.length > 0 && onSelectBackground && (
        <div className="border-b border-slate-800 pb-3">
          <label className="mb-1 block text-xs font-semibold text-slate-400">
            更換背景底圖
          </label>
          <div className="flex gap-2 overflow-x-auto pb-1">
            {availableBackgrounds.map((bg) => (
              <button
                key={bg.id}
                onClick={() => onSelectBackground(bg)}
                className={`relative h-12 w-20 shrink-0 overflow-hidden rounded-lg border text-left transition ${
                  currentBackground?.id === bg.id
                    ? "border-indigo-400 ring-2 ring-indigo-500/40"
                    : "border-slate-700 opacity-60 hover:opacity-100"
                }`}
              >
                <img
                  src={bg.image_url}
                  alt={bg.name}
                  className="h-full w-full object-cover"
                />
                <span className="absolute bottom-0 inset-x-0 truncate bg-black/70 px-1 text-[9px] text-white">
                  {bg.name}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Layer List */}
      <div>
        <h4 className="mb-2 text-xs font-bold text-slate-300">
          圖層清單 ({layers.length})
        </h4>
        <div className="flex flex-col gap-1.5 max-h-36 overflow-y-auto">
          {layers.map((layer) => {
            const isSelected = layer.id === selectedLayerId;
            return (
              <div
                key={layer.id}
                data-testid="canvas-layer-item"
                onClick={() => onSelectLayer(layer.id)}
                className={`flex items-center justify-between rounded-lg px-3 py-1.5 text-xs transition cursor-pointer ${
                  isSelected
                    ? "bg-indigo-600/80 text-white font-semibold"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  <img
                    src={layer.image_url}
                    alt=""
                    className="h-5 w-5 object-contain"
                  />
                  <span className="truncate">{layer.name}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemoveLayer(layer.id);
                  }}
                  className="ml-2 text-slate-400 hover:text-rose-400"
                  aria-label={`刪除 ${layer.name}`}
                >
                  ✕
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Selected Layer Attributes */}
      {selectedLayer && (
        <div className="rounded-lg border border-slate-700/80 bg-slate-800/60 p-3">
          <span className="text-[11px] font-bold text-indigo-300">
            微調選取圖層: {selectedLayer.name}
          </span>
          <div className="mt-2 grid grid-cols-2 gap-2 text-xs">
            <div>
              <label
                htmlFor="layer-x"
                className="block text-[10px] text-slate-400"
              >
                X 坐標
              </label>
              <input
                id="layer-x"
                aria-label="X 坐標"
                type="number"
                value={selectedLayer.x}
                onChange={(e) =>
                  onUpdateLayer(selectedLayer.id, {
                    x: Number(e.target.value) || 0,
                  })
                }
                className="w-full rounded bg-slate-900 px-2 py-1 text-white border border-slate-700 focus:outline-none"
              />
            </div>

            <div>
              <label
                htmlFor="layer-y"
                className="block text-[10px] text-slate-400"
              >
                Y 坐標
              </label>
              <input
                id="layer-y"
                aria-label="Y 坐標"
                type="number"
                value={selectedLayer.y}
                onChange={(e) =>
                  onUpdateLayer(selectedLayer.id, {
                    y: Number(e.target.value) || 0,
                  })
                }
                className="w-full rounded bg-slate-900 px-2 py-1 text-white border border-slate-700 focus:outline-none"
              />
            </div>

            <div>
              <label
                htmlFor="layer-scale"
                className="block text-[10px] text-slate-400"
              >
                縮放比例
              </label>
              <input
                id="layer-scale"
                aria-label="縮放比例"
                type="number"
                step="0.1"
                min="0.2"
                max="3.0"
                value={selectedLayer.scale}
                onChange={(e) =>
                  onUpdateLayer(selectedLayer.id, {
                    scale: parseFloat(e.target.value) || 1,
                  })
                }
                className="w-full rounded bg-slate-900 px-2 py-1 text-white border border-slate-700 focus:outline-none"
              />
            </div>

            <div>
              <label
                htmlFor="layer-rotation"
                className="block text-[10px] text-slate-400"
              >
                旋轉角度
              </label>
              <input
                id="layer-rotation"
                aria-label="旋轉角度"
                type="number"
                value={selectedLayer.rotation}
                onChange={(e) =>
                  onUpdateLayer(selectedLayer.id, {
                    rotation: Number(e.target.value) || 0,
                  })
                }
                className="w-full rounded bg-slate-900 px-2 py-1 text-white border border-slate-700 focus:outline-none"
              />
            </div>
          </div>
        </div>
      )}

      {/* Inventory Add to Canvas */}
      {inventoryObjects.length > 0 && (
        <div className="border-t border-slate-800 pt-3">
          <h4 className="mb-2 text-xs font-bold text-slate-300">
            從背包加入裝飾物件
          </h4>
          <div className="grid grid-cols-2 gap-2 max-h-36 overflow-y-auto">
            {inventoryObjects.map((obj) => (
              <button
                key={obj.id}
                onClick={() => onAddLayer(obj)}
                aria-label={`加入 ${obj.name}`}
                className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800/80 p-2 text-left hover:border-indigo-400 hover:bg-slate-700 transition"
              >
                <img
                  src={obj.image_url}
                  alt={obj.name}
                  className="h-7 w-7 object-contain"
                />
                <span className="truncate text-[11px] text-slate-200">
                  {obj.name}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
