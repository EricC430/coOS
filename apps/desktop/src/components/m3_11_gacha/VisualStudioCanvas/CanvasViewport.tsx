import React from "react";
import { CanvasLayer, VisualItem } from "../types";

export interface CanvasViewportProps {
  background: VisualItem | null;
  layers: CanvasLayer[];
  selectedLayerId: string | null;
  onSelectLayer: (id: string | null) => void;
  onUpdateLayer?: (id: string, updates: Partial<CanvasLayer>) => void;
  canvasWidth?: number;
  canvasHeight?: number;
}

export const CanvasViewport: React.FC<CanvasViewportProps> = ({
  background,
  layers,
  selectedLayerId,
  onSelectLayer,
  canvasWidth = 800,
  canvasHeight = 500,
}) => {
  return (
    <div
      data-testid="canvas-viewport"
      onClick={(e) => {
        // Deselect if clicking canvas background directly
        if (e.target === e.currentTarget) {
          onSelectLayer(null);
        }
      }}
      style={{
        width: "100%",
        maxWidth: `${canvasWidth}px`,
        height: `${canvasHeight}px`,
      }}
      className="relative mx-auto overflow-hidden rounded-2xl border-2 border-slate-700 bg-slate-950 shadow-2xl select-none"
    >
      {/* Background Layer */}
      {background?.image_url ? (
        <img
          src={background.image_url}
          alt={background.name}
          className="pointer-events-none absolute inset-0 h-full w-full object-cover"
        />
      ) : (
        <div className="absolute inset-0 flex items-center justify-center bg-slate-900 text-xs text-slate-500">
          尚未選取背景底圖
        </div>
      )}

      {/* Object Layers */}
      {layers.map((layer) => {
        const isSelected = layer.id === selectedLayerId;

        return (
          <div
            key={layer.id}
            data-testid="canvas-layer-object"
            onClick={(e) => {
              e.stopPropagation();
              onSelectLayer(layer.id);
            }}
            style={{
              left: `${layer.x}px`,
              top: `${layer.y}px`,
              transform: `translate(-50%, -50%) rotate(${layer.rotation}deg) scale(${layer.scale})`,
              zIndex: layer.zIndex,
            }}
            className={`absolute cursor-pointer transition-shadow ${
              isSelected
                ? "ring-2 ring-indigo-400 ring-offset-2 ring-offset-black/50"
                : "hover:ring-1 hover:ring-white/50"
            }`}
          >
            <img
              src={layer.image_url}
              alt={layer.name}
              draggable={false}
              className="h-28 w-28 object-contain pointer-events-none drop-shadow-md"
            />
            {isSelected && (
              <span className="absolute -top-5 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-indigo-600/90 px-1.5 py-0.5 text-[10px] font-bold text-white shadow">
                {layer.name}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
};
