/**
 * M3.2.4 -- Single heatmap cell
 * [R06 SS2] Digital phenotype visualisation: 4-level colour depth
 * Uses CSS custom properties for warm-themed colors
 */

// React import not needed with JSX transform

interface Props {
  count: number;
  date?: string;
  onHover?: (date: string, count: number) => void;
  onLeave?: () => void;
}

function levelClass(count: number): string {
  if (count === 0) return "heatmap-level-0";
  if (count <= 2) return "heatmap-level-1";
  if (count <= 5) return "heatmap-level-2";
  return "heatmap-level-3";
}

export function HeatmapCell({ count, date, onHover, onLeave }: Props) {
  return (
    <div
      data-testid={date ? `heatmap-cell-${date}` : "heatmap-cell"}
      className={`heatmap-cell ${levelClass(count)}`}
      onMouseEnter={() => date && onHover?.(date, count)}
      onMouseLeave={onLeave}
      title={date ? `${date}: ${count} 項` : undefined}
    />
  );
}
