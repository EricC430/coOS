/**
 * M3.4.1 -- Single expert sidebar item
 */

import React from "react";
import type { Expert } from "../../../stores/m3_1_global_store";

interface Props {
  expert: Expert & { isToolType?: boolean };
  isActive: boolean;
  onClick: () => void;
}

export function ExpertItem({ expert, isActive, onClick }: Props) {
  const isToolType = expert.isToolType ?? false;
  return (
    <div
      data-testid="expert-item"
      data-type={isToolType ? "tool" : "persona"}
      className={`flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
        isActive
          ? "bg-indigo-100 text-indigo-700"
          : "hover:bg-gray-100"
      }`}
      style={isActive ? { backgroundImage: "repeating-linear-gradient(45deg, transparent, transparent 4px, rgba(99,102,241,0.1) 4px, rgba(99,102,241,0.1) 8px)" } : undefined}
      onClick={onClick}
    >
      <div className="w-8 h-8 rounded-full bg-indigo-200 flex items-center justify-center text-sm flex-shrink-0">
        {expert.avatarUrl ? (
          <img src={expert.avatarUrl} alt="" className="w-full h-full rounded-full object-cover" />
        ) : (
          isToolType ? "🔧" : expert.expertName.slice(0, 1)
        )}
      </div>
      <div className="min-w-0">
        {expert.title && (
          <div className="text-xs text-gray-400 truncate">{expert.title}</div>
        )}
        <div className="text-sm font-medium truncate">
          {isToolType ? "工具型 AI" : expert.expertName}
        </div>
      </div>
    </div>
  );
}
