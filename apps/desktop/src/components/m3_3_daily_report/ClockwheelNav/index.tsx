/**
 * M3.3.4 -- ClockwheelNav
 *
 * Geometry:
 *   SVG width = VISIBLE_W px.  Disc centre at x = CX = VISIBLE_W - R (off-screen left).
 *   SVG clips at its own viewport — no CSS overflow tricks needed.
 *
 *   The pointer is at the rightmost point of the disc = global angle 0° (3-o'clock).
 *
 *   Clockwise = increasing angle = NEWER dates (future).
 *   Counter-clockwise = decreasing angle = OLDER dates (past).
 *
 *   Each tick i sits at disc-local angle: localAngle = mod360(i * DEG_PER_TICK)
 *   After <g> rotates by `rotation` degrees, the tick's global angle becomes:
 *     globalAngle = mod360(localAngle + rotation)
 *   The tick at globalAngle ≈ 0 is at the pointer → that is the selected date.
 *   signed offset from pointer: signedGlobal = globalAngle > 180 ? globalAngle - 360 : globalAngle
 *   dayOffset = round(signedGlobal / DEG_PER_TICK)   [positive = future, negative = past]
 *   tickDate  = addDays(selectedDate, dayOffset * granStep)
 *
 *   Scroll wheel down → newer (future) date → disc rotates CCW → rotation decreases
 *   Scroll wheel up   → older (past)   date → disc rotates CW  → rotation increases
 *
 *   Font/opacity scale with proximity to pointer: cos(globalAngle), max at 0°.
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

export type Granularity = "day" | "week" | "month" | "year";

interface Props {
  date: string;
  granularity: Granularity;
  onDateChange: (d: string) => void;
  onGranularityChange: (g: Granularity) => void;
}

const GRAN_ORDER: Granularity[] = ["day", "week", "month", "year"];
const GRAN_LABEL: Record<Granularity, string> = { day: "日", week: "週", month: "月", year: "年" };
const GRAN_STEP: Record<Granularity, number> = { day: 1, week: 7, month: 30, year: 365 };

// ── Geometry ──────────────────────────────────────────────────────────────────
const R = 800;
const VISIBLE_W = 175;
const STRIP_W = VISIBLE_W + 10;
const CX = VISIBLE_W - R;   // disc centre x in SVG coords (negative = off-screen)

const TICK_COUNT = 36;
const DEG_PER_TICK = 360 / TICK_COUNT; // 10°

const FS_MAX = 20;
const FS_MIN = 8;

// ── Helpers ───────────────────────────────────────────────────────────────────
function addDays(iso: string, n: number): string {
  const d = new Date(iso);
  d.setDate(d.getDate() + n);
  return d.toISOString().split("T")[0];
}

/** Normalise angle to [0, 360) */
function mod360(a: number): number {
  return ((a % 360) + 360) % 360;
}

function tickLines(iso: string, gran: Granularity): string[] {
  const d = new Date(iso);
  const yr = `${d.getFullYear()}`;
  const mo = `${d.getMonth() + 1}`;
  const dy = `${d.getDate()}`;
  if (gran === "year") return [yr];
  if (gran === "month") return [yr, `${mo}月`];
  if (gran === "week") return [yr, `${mo}/${dy}週`];
  return [yr, `${mo}月${dy}日`];
}

function GranBtn({ symbol, enabled, onClick, title }: {
  symbol: string; enabled: boolean; onClick: () => void; title: string;
}) {
  return (
    <button onClick={onClick} disabled={!enabled} title={title} style={{
      width: 22, height: 22, borderRadius: "50%",
      border: "1px solid var(--glass-border)",
      background: enabled ? "var(--glass-bg)" : "transparent",
      color: enabled ? "var(--text-primary)" : "var(--text-muted)",
      fontSize: 14, lineHeight: 1, cursor: enabled ? "pointer" : "not-allowed",
      display: "flex", alignItems: "center", justifyContent: "center",
      opacity: enabled ? 1 : 0.25, padding: 0, flexShrink: 0,
      transition: "all 0.15s",
    }}>
      {symbol}
    </button>
  );
}

// ── Tick data type ────────────────────────────────────────────────────────────
interface TickData {
  i: number;
  ox: number; oy: number;
  ix: number; iy: number;
  lx: number; ly: number;
  localAngle: number;   // disc-local angle (for <g transform>)
  globalAngle: number;  // after rotation — determines proximity to pointer
  lines: string[];
  isSelected: boolean;
  isFuture: boolean;
  fs: number; lineH: number; opacity: number;
}

// ── Main component ─────────────────────────────────────────────────────────────
export function ClockwheelNav({ date, granularity, onDateChange, onGranularityChange }: Props) {
  /**
   * `rotation` = cumulative degrees the disc has turned.
   * CW (positive) = older dates arrive at pointer.
   * CCW (negative) = newer dates arrive at pointer.
   *
   * When the user scrolls to a new date, `date` prop changes AND `rotation`
   * changes by ±DEG_PER_TICK.  The <g> CSS transition animates the rotation.
   * On next render, the tick whose globalAngle ≈ 0 represents `date`, giving
   * correct orange highlight without any accumulated offset.
   */
  const [rotation, setRotation] = useState(0);
  const [svgH, setSvgH] = useState(600);
  const stripRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const throttled = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const h = el.clientHeight || el.getBoundingClientRect().height;
      if (h > 0) setSvgH(h);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  /**
   * delta = +1 → go to TOMORROW (newer): disc turns CCW → rotation -= DEG_PER_TICK
   * delta = -1 → go to YESTERDAY (older): disc turns CW  → rotation += DEG_PER_TICK
   *
   * CW rotation makes current date tick move clockwise (downward), and the tick
   * that was one step CCW (= older, past) arrives at the pointer.
   * Wait — we want CW = newer.  So:
   *   newer (delta=+1): disc CW (+) → the NEXT tick (i+1, CW from current) arrives at pointer
   *   But tick i+1 at localAngle (i+1)*10 is CW from tick i.
   *   After disc rotates CW by +10°, globalAngle of tick i+1 = localAngle(i+1) + rotation_new
   *     = (i+1)*10 + (rotation_old + 10) = i*10 + 10 + rotation_old + 10 — that's not 0.
   *
   * Let's reason from scratch:
   *   Tick i at localAngle L_i = i * 10°.
   *   After <g> rotation R, tick i's globalAngle G_i = mod360(L_i + R).
   *   Selected tick: G_i ≈ 0  →  L_i ≈ -R (mod 360)  →  i ≈ -R/10 (mod 36).
   *
   *   To go to NEWER (CW direction), we want the tick that is 1 step CW (L = L_selected + 10)
   *   to come to globalAngle 0.  So new R must satisfy:
   *     mod360(L_selected + 10 + R_new) = 0
   *     R_new = -(L_selected + 10) mod 360 = R_old - 10
   *   → rotation DECREASES by 10 for newer (CW).
   *
   *   To go to OLDER (CCW direction):
   *     R_new = R_old + 10
   *   → rotation INCREASES by 10 for older (CCW).
   *
   *   Scroll wheel DOWN (deltaY > 0) → newer → rotation -= 10
   *   Scroll wheel UP   (deltaY < 0) → older  → rotation += 10
   */
  const step = useCallback((delta: number) => {
    const today = new Date().toISOString().split("T")[0];
    const next = addDays(date, GRAN_STEP[granularity] * delta);
    if (next > today) return;
    // delta > 0 (newer) → rotation decreases; delta < 0 (older) → rotation increases
    setRotation((r) => r - delta * DEG_PER_TICK);
    onDateChange(next);
  }, [date, granularity, onDateChange]);

  /**
   * Scroll down (deltaY > 0) → newer date (tomorrow)
   * Scroll up   (deltaY < 0) → older date (yesterday)
   */
  const handleWheel = useCallback((e: WheelEvent) => {
    e.preventDefault();
    if (throttled.current) return;
    throttled.current = true;
    clearTimeout(timer.current);
    step(e.deltaY > 0 ? 1 : -1);
    timer.current = setTimeout(() => { throttled.current = false; }, 220);
  }, [step]);

  useEffect(() => {
    const host = stripRef.current?.closest(".clockwheel-host") as HTMLElement | null;
    const el = host ?? stripRef.current;
    if (!el) return;
    el.addEventListener("wheel", handleWheel, { passive: false });
    return () => el.removeEventListener("wheel", handleWheel);
  }, [handleWheel]);

  const granIdx = GRAN_ORDER.indexOf(granularity);
  const canMore = granIdx < GRAN_ORDER.length - 1;
  const canLess = granIdx > 0;
  const today = new Date().toISOString().split("T")[0];

  const cy = svgH / 2;
  const rimR = R - 2;

  // ── Build ticks ────────────────────────────────────────────────────────────
  const ticks: TickData[] = Array.from({ length: TICK_COUNT }, (_, i): TickData | null => {
    const localAngle = mod360(i * DEG_PER_TICK);
    // After <g> rotates by `rotation`, tick's position in viewport:
    const globalAngle = mod360(localAngle + rotation);
    // Signed offset from pointer: [-180, 180], positive = CW = newer
    const signed = globalAngle > 180 ? globalAngle - 360 : globalAngle;
    // Day offset: positive = future (CW), negative = past (CCW)
    const dayOffset = Math.round(signed / DEG_PER_TICK);

    // Only show ticks within visible arc range (~±80° from pointer visible at VISIBLE_W=175)
    const absGlobal = Math.abs(signed);
    if (absGlobal > 85) return null;

    const tickDate = addDays(date, dayOffset * GRAN_STEP[granularity]);
    const isFuture = tickDate > today;
    const isSelected = dayOffset === 0;

    // Geometry in disc-local coords (before <g> rotation)
    const rad = (localAngle * Math.PI) / 180;
    const cosA = Math.cos(rad);
    const sinA = Math.sin(rad);

    const tickLen = isSelected ? 40 : 22;
    const ox = CX + rimR * cosA;
    const oy = cy + rimR * sinA;
    const ix = CX + (rimR - tickLen) * cosA;
    const iy = cy + (rimR - tickLen) * sinA;
    const labelR = rimR - tickLen - 55;
    const lx = CX + labelR * cosA;
    const ly = cy + labelR * sinA;

    // Proximity to pointer based on globalAngle (0° = at pointer = maximum size)
    const proximity = Math.max(0, Math.cos((globalAngle * Math.PI) / 60));
    const fs = FS_MIN + (FS_MAX - FS_MIN) * proximity;
    const lineH = fs + 3;
    const opacity = isFuture ? 0.15 : Math.max(0.2, proximity * 0.8 + 0.2);

    const lines = tickLines(tickDate, granularity);

    return {
      i, ox, oy, ix, iy, lx, ly,
      localAngle, globalAngle,
      lines, isSelected, isFuture,
      fs, lineH, opacity,
    };
  }).filter((t): t is TickData => t !== null);

  // Minor ticks (always in disc-local coords, filtered by whether they're visible)
  const minorTicks = Array.from({ length: TICK_COUNT * 4 }, (_, i) => {
    if (i % 4 === 0) return null;
    const localAngle = mod360((i / 4) * DEG_PER_TICK);
    const globalAngle = mod360(localAngle + rotation);
    const signed = globalAngle > 180 ? globalAngle - 360 : globalAngle;
    if (Math.abs(signed) > 85) return null;
    const rad = (localAngle * Math.PI) / 180;
    return {
      key: `m${i}`,
      ox: CX + rimR * Math.cos(rad),
      oy: cy + rimR * Math.sin(rad),
      ix: CX + (rimR - 8) * Math.cos(rad),
      iy: cy + (rimR - 8) * Math.sin(rad),
    };
  }).filter((t): t is { key: string; ox: number; oy: number; ix: number; iy: number } => t !== null);

  const discTransform = `rotate(${rotation}, ${CX}, ${cy})`;

  return (
    <div
      ref={stripRef}
      data-testid="clockwheel-nav"
      style={{ position: "relative", width: STRIP_W, height: "100%", flexShrink: 0, userSelect: "none" }}
    >
      <svg
        ref={svgRef}
        width={VISIBLE_W}
        height="100%"
        style={{ position: "absolute", left: 0, top: 0, display: "block" }}
      >
        <g
          transform={discTransform}
          style={{ transition: "transform 0.42s cubic-bezier(0.34, 1.56, 0.64, 1)" }}
        >
          {/* Disc fill */}
          <circle
            cx={CX} cy={cy} r={rimR}
            fill="var(--glass-bg)"
            stroke="var(--glass-border)"
            strokeWidth={1.5}
          />

          {/* Minor ticks */}
          {minorTicks.map((t) => (
            <line
              key={t.key}
              x1={t.ox} y1={t.oy} x2={t.ix} y2={t.iy}
              stroke="var(--glass-border)" strokeWidth={0.6} strokeLinecap="round"
            />
          ))}

          {/* Major ticks + date labels */}
          {ticks.map(({ i, ox, oy, ix, iy, lx, ly, localAngle, lines, isSelected, fs, lineH, opacity }) => (
            <g key={i} opacity={opacity}>
              <line
                x1={ox} y1={oy} x2={ix} y2={iy}
                stroke={isSelected ? "var(--gold-accent)" : "var(--text-secondary)"}
                strokeWidth={isSelected ? 3.5 : 1.5}
                strokeLinecap="round"
              />
              {/* Text parallel to tick = radial direction = localAngle */}
              <text
                transform={`rotate(${localAngle}, ${lx}, ${ly})`}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={fs}
                fontWeight={isSelected ? 800 : 500}
                fill={isSelected ? "var(--gold-accent)" : "var(--text-muted)"}
                fontFamily="Inter, 'Segoe UI', sans-serif"
              >
                {lines.map((line: string, li: number) => (
                  <tspan key={li} x={lx} y={ly + (li - (lines.length - 1) / 2) * lineH}>
                    {line}
                  </tspan>
                ))}
              </text>
            </g>
          ))}
        </g>
      </svg>

      {/* Fixed gold pointer at arc edge */}
      <div style={{
        position: "absolute", left: VISIBLE_W - 22, top: "50%",
        transform: "translateY(-50%)",
        width: 22, height: 2,
        background: "var(--gold-accent)", borderRadius: 1,
        boxShadow: "0 0 6px var(--gold-accent)",
        zIndex: 20, pointerEvents: "none",
      }} />
      <div style={{
        position: "absolute", left: VISIBLE_W - 6, top: "50%",
        transform: "translate(-50%, -50%)",
        width: 10, height: 10, borderRadius: "50%",
        background: "var(--gold-accent)",
        boxShadow: "0 0 10px var(--gold-accent)",
        zIndex: 21, pointerEvents: "none",
      }} />

      {/* Granularity controls */}
      <div style={{
        position: "absolute", right: 2, bottom: 16,
        display: "flex", flexDirection: "column", alignItems: "center",
        gap: 5, zIndex: 20,
      }}>
        <AnimatePresence mode="wait">
          <motion.span
            key={granularity}
            initial={{ opacity: 0, scale: 0.7 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.7 }}
            transition={{ duration: 0.12 }}
            style={{
              fontSize: 9, fontWeight: 800, color: "var(--gold-accent)",
              letterSpacing: 1, writingMode: "vertical-rl", marginBottom: 2,
            }}
          >
            {GRAN_LABEL[granularity]}
          </motion.span>
        </AnimatePresence>
        <GranBtn
          symbol="+"
          enabled={canMore}
          onClick={() => { if (canMore) onGranularityChange(GRAN_ORDER[granIdx + 1]); }}
          title={canMore ? `→ ${GRAN_LABEL[GRAN_ORDER[granIdx + 1]]}` : "已是最大粒度"}
        />
        <GranBtn
          symbol="−"
          enabled={canLess}
          onClick={() => { if (canLess) onGranularityChange(GRAN_ORDER[granIdx - 1]); }}
          title={canLess ? `→ ${GRAN_LABEL[GRAN_ORDER[granIdx - 1]]}` : "已是最細粒度"}
        />
      </div>
    </div>
  );
}
