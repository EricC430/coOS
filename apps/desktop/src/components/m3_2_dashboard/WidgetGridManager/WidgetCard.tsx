/**
 * M3.2.5 -- Widget Card
 * Single widget wrapper with title bar, move buttons, and delete.
 */

import React from "react";

interface Props {
  title: string;
  canMoveLeft: boolean;
  canMoveRight: boolean;
  onMoveLeft: () => void;
  onMoveRight: () => void;
  onDelete: () => void;
  children: React.ReactNode;
  isDragging?: boolean;
  dragHandleProps?: React.HTMLAttributes<HTMLDivElement>;
}

export function WidgetCard({
  title,
  canMoveLeft,
  canMoveRight,
  onMoveLeft,
  onMoveRight,
  onDelete,
  children,
  isDragging,
  dragHandleProps,
}: Props) {
  return (
    <div
      className="glass-card widget-card"
      style={{
        display: "flex",
        flexDirection: "column",
        opacity: isDragging ? 0.5 : 1,
        transition: "opacity 0.2s",
      }}
    >
      {/* Widget toolbar */}
      <div className="widget-toolbar">
        <div className="widget-drag-handle" {...dragHandleProps} title="拖曳排列">
          ⠿
        </div>
        <span className="widget-title">{title}</span>
        <div style={{ display: "flex", gap: 2 }}>
          <button
            className="widget-ctrl-btn"
            onClick={onMoveLeft}
            disabled={!canMoveLeft}
            title="向左移"
            aria-label="向左移"
          >
            ‹
          </button>
          <button
            className="widget-ctrl-btn"
            onClick={onMoveRight}
            disabled={!canMoveRight}
            title="向右移"
            aria-label="向右移"
          >
            ›
          </button>
          <button
            className="widget-ctrl-btn widget-ctrl-delete"
            onClick={onDelete}
            title="移除此子卡片"
            aria-label="移除"
          >
            ✕
          </button>
        </div>
      </div>
      {/* Widget content */}
      <div style={{ flex: 1, minHeight: 0, overflow: "auto", padding: "8px 4px 4px" }}>
        {children}
      </div>
    </div>
  );
}
