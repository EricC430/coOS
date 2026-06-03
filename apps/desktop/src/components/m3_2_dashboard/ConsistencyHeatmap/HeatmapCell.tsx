/**
 * M3.2.4 -- Single heatmap cell
 * [R06 SS2] Digital phenotype visualisation: 4-level colour depth
 */

import React from "react";

interface Props {
  count: number;
  date?: string;
  onHover?: (date: string, count: number) => void;
  onLeave?: () => void;
}

function levelClass(count: number): string {
  if (count === 0) return "heatmap-level-0 bg-gray-200";
  if (count <= 2) return "heatmap-level-1 bg-green-200";
  if (count <= 5) return "heatmap-level-2 bg-green-400";
  return "heatmap-level-3 bg-green-600";
}

export function HeatmapCell({ count, date, onHover, onLeave }: Props) {
  return (
    <div
      data-testid={date ? `heatmap-cell-${date}` : "heatmap-cell"}
      className={`w-3 h-3 rounded-sm cursor-pointer ${levelClass(count)}`}
      onMouseEnter={() => date && onHover?.(date, count)}
      onMouseLeave={onLeave}
      title={date ? `${date}: ${count} 項` : undefined}
    />
  );
}
