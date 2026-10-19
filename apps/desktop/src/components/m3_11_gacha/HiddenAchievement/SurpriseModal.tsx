import React from "react";
import { VisualItem } from "../types";

export interface SurpriseModalProps {
  item: VisualItem;
  onClose: () => void;
}

export const SurpriseModal: React.FC<SurpriseModalProps> = ({ item, onClose }) => {
  return (
    <div
      data-testid="surprise-modal"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-fadeIn"
    >
      <div className="relative w-full max-w-sm rounded-2xl border border-amber-400/50 bg-gradient-to-b from-slate-900 via-slate-800 to-slate-900 p-6 text-center text-white shadow-2xl shadow-amber-500/20">
        <div className="mx-auto mb-4 flex h-28 w-28 items-center justify-center rounded-2xl bg-slate-950/70 border border-amber-500/30 p-2 shadow-inner">
          <img
            src={item.image_url}
            alt={item.name}
            className="max-h-full max-w-full object-contain drop-shadow-[0_0_12px_rgba(245,158,11,0.6)]"
          />
        </div>

        <span className="inline-block rounded-full bg-amber-500/20 px-3 py-1 text-xs font-bold text-amber-300 border border-amber-400/30">
          ✨ 無預警隱藏成就解鎖！
        </span>

        <h3 className="mt-3 text-lg font-extrabold text-white">{item.name}</h3>
        <p className="mt-2 text-xs text-slate-300 leading-relaxed">
          {item.description}
        </p>

        <button
          onClick={onClose}
          className="mt-6 w-full rounded-xl bg-gradient-to-r from-amber-500 to-yellow-500 py-2.5 px-4 font-bold text-slate-950 shadow-lg shadow-amber-500/30 hover:brightness-110 active:scale-[0.98] transition"
        >
          收下驚喜
        </button>
      </div>
    </div>
  );
};
