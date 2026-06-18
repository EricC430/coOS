/**
 * M3.2.5 -- Widget Grid Manager
 *
 * Shared dashboard area that renders an ordered list of sub-widget cards.
 * Supports: left/right reorder, add new widget, delete, drag-and-drop, localStorage persistence.
 *
 * [FIX-01] Replaces the fixed heatmap-only dashboard block.
 */

import React, { useState, useRef, useCallback } from "react";
import { WidgetCard } from "./WidgetCard";
import {
  type WidgetConfig,
  type WidgetType,
  WIDGET_REGISTRY,
  loadWidgetLayout,
  saveWidgetLayout,
  newWidgetId,
} from "./useWidgetLayout";
import { ConsistencyHeatmap, type HeatmapEntry } from "../ConsistencyHeatmap";

// ── Placeholder sub-widget renderers ──────────────────────────────────────
// These will be expanded as real data sources become available.

function MonthlyConsistency() {
  const bars = Array.from({ length: 30 }, (_, i) => ({
    day: i + 1,
    value: Math.random(),
  }));
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 48 }}>
      {bars.map((b) => (
        <div
          key={b.day}
          style={{
            flex: 1,
            height: `${Math.max(4, b.value * 48)}px`,
            background: b.value > 0.5 ? "var(--gold-accent)" : "var(--heatmap-1)",
            borderRadius: 2,
            opacity: 0.8,
          }}
          title={`Day ${b.day}`}
        />
      ))}
    </div>
  );
}

function WeeklyMoodChart() {
  const days = ["一", "二", "三", "四", "五", "六", "日"];
  const scores = days.map(() => Math.floor(Math.random() * 5) + 3);
  const max = 10;
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
      {days.map((d, i) => (
        <div key={d} style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 10, color: "var(--text-muted)", width: 12 }}>{d}</span>
          <div style={{ flex: 1, height: 8, background: "var(--glass-border)", borderRadius: 4, overflow: "hidden" }}>
            <div style={{ width: `${(scores[i] / max) * 100}%`, height: "100%", background: "var(--warmblue)", borderRadius: 4 }} />
          </div>
          <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{scores[i]}</span>
        </div>
      ))}
    </div>
  );
}

function WeeklyChatCount() {
  const days = ["一", "二", "三", "四", "五", "六", "日"];
  const counts = days.map(() => Math.floor(Math.random() * 8));
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 4, height: 56 }}>
      {days.map((d, i) => (
        <div key={d} style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1 }}>
          <div style={{
            width: "100%",
            height: `${Math.max(4, (counts[i] / 8) * 48)}px`,
            background: "var(--coral-accent)",
            borderRadius: "4px 4px 0 0",
            opacity: 0.8,
          }} />
          <span style={{ fontSize: 9, color: "var(--text-muted)", marginTop: 2 }}>{d}</span>
        </div>
      ))}
    </div>
  );
}

function CustomChart({ filterParams }: { filterParams?: Record<string, unknown> }) {
  return (
    <div style={{ color: "var(--text-muted)", fontSize: 12, textAlign: "center", padding: 8 }}>
      自訂圖表<br />
      <span style={{ fontSize: 10 }}>{JSON.stringify(filterParams ?? {})}</span>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────

interface Props {
  roleId: string;
  heatmapData: HeatmapEntry[];
}

export function WidgetGridManager({ roleId, heatmapData }: Props) {
  const [widgets, setWidgets] = useState<WidgetConfig[]>(() => loadWidgetLayout(roleId));
  const [showAddMenu, setShowAddMenu] = useState(false);
  const dragIdxRef = useRef<number | null>(null);
  const [dragOverIdx, setDragOverIdx] = useState<number | null>(null);

  const persist = useCallback((next: WidgetConfig[]) => {
    setWidgets(next);
    saveWidgetLayout(roleId, next);
  }, [roleId]);

  const moveLeft = (idx: number) => {
    if (idx === 0) return;
    const next = [...widgets];
    [next[idx - 1], next[idx]] = [next[idx], next[idx - 1]];
    persist(next);
  };

  const moveRight = (idx: number) => {
    if (idx >= widgets.length - 1) return;
    const next = [...widgets];
    [next[idx + 1], next[idx]] = [next[idx], next[idx + 1]];
    persist(next);
  };

  const deleteWidget = (idx: number) => {
    const next = widgets.filter((_, i) => i !== idx);
    persist(next.length > 0 ? next : loadWidgetLayout("__default__"));
  };

  const addWidget = (type: WidgetType) => {
    const meta = WIDGET_REGISTRY[type];
    const next = [...widgets, { id: newWidgetId(), type, title: meta.label }];
    persist(next);
    setShowAddMenu(false);
  };

  // Drag-and-drop reorder
  const handleDragStart = (idx: number) => {
    dragIdxRef.current = idx;
  };
  const handleDragOver = (e: React.DragEvent, idx: number) => {
    e.preventDefault();
    setDragOverIdx(idx);
  };
  const handleDrop = (e: React.DragEvent, dropIdx: number) => {
    e.preventDefault();
    const dragIdx = dragIdxRef.current;
    if (dragIdx === null || dragIdx === dropIdx) {
      setDragOverIdx(null);
      return;
    }
    const next = [...widgets];
    const [moved] = next.splice(dragIdx, 1);
    next.splice(dropIdx, 0, moved);
    persist(next);
    dragIdxRef.current = null;
    setDragOverIdx(null);
  };
  const handleDragEnd = () => {
    dragIdxRef.current = null;
    setDragOverIdx(null);
  };

  function renderWidgetContent(w: WidgetConfig) {
    switch (w.type) {
      case "heatmap_365":
        return <ConsistencyHeatmap data={heatmapData} />;
      case "monthly_consistency":
        return <MonthlyConsistency />;
      case "weekly_mood":
        return <WeeklyMoodChart />;
      case "weekly_chat_count":
        return <WeeklyChatCount />;
      case "custom_chart":
        return <CustomChart filterParams={w.filterParams} />;
      default:
        return null;
    }
  }

  // Remaining types not yet in layout
  const usedTypes = new Set(widgets.map((w) => w.type));
  const availableTypes = (Object.keys(WIDGET_REGISTRY) as WidgetType[]).filter(
    (t) => !usedTypes.has(t) || t === "custom_chart"
  );

  return (
    <div className="widget-grid-manager">
      {/* Widget list */}
      <div className="widget-grid-list">
        {widgets.map((w, idx) => (
          <div
            key={w.id}
            draggable
            onDragStart={() => handleDragStart(idx)}
            onDragOver={(e) => handleDragOver(e, idx)}
            onDrop={(e) => handleDrop(e, idx)}
            onDragEnd={handleDragEnd}
            className={`widget-grid-item${dragOverIdx === idx ? " widget-drag-over" : ""}`}
          >
            <WidgetCard
              title={w.title}
              canMoveLeft={idx > 0}
              canMoveRight={idx < widgets.length - 1}
              onMoveLeft={() => moveLeft(idx)}
              onMoveRight={() => moveRight(idx)}
              onDelete={() => deleteWidget(idx)}
              isDragging={dragIdxRef.current === idx}
            >
              {renderWidgetContent(w)}
            </WidgetCard>
          </div>
        ))}
      </div>

      {/* Add widget button */}
      <div style={{ position: "relative", marginTop: 8 }}>
        <button
          className="widget-add-btn"
          onClick={() => setShowAddMenu((v) => !v)}
          title="新增子卡片"
        >
          + 新增視覺化子卡片
        </button>
        {showAddMenu && (
          <div className="widget-add-menu">
            {availableTypes.map((t) => (
              <button
                key={t}
                className="widget-add-menu-item"
                onClick={() => addWidget(t)}
              >
                <span style={{ fontWeight: 600 }}>{WIDGET_REGISTRY[t].label}</span>
                <span style={{ fontSize: 10, color: "var(--text-muted)", display: "block" }}>
                  {WIDGET_REGISTRY[t].description}
                </span>
              </button>
            ))}
            {availableTypes.length === 0 && (
              <div style={{ padding: "8px 12px", fontSize: 12, color: "var(--text-muted)" }}>
                所有子卡片已加入
              </div>
            )}
            <button
              className="widget-add-menu-item"
              onClick={() => addWidget("custom_chart")}
            >
              <span style={{ fontWeight: 600 }}>自訂篩選圖表</span>
              <span style={{ fontSize: 10, color: "var(--text-muted)", display: "block" }}>
                新建特定篩選圖表
              </span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
