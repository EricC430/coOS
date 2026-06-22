import React, { useEffect, useRef, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { CommunityRead } from "./api";
import { useCoOSStore } from "../../stores/m3_1_global_store";

interface CommunityCarouselProps {
  communities: CommunityRead[];
  loading: boolean;
  onManageCommunity?: (communityId: string) => void;
}

const getCommunityEmoji = (name: string, theme?: string): string => {
  const normalized = (name || "").toLowerCase();
  const t = (theme || "").toLowerCase();
  if (normalized.includes("interview") || t.includes("career")) return "💼";
  if (normalized.includes("strangers") || t.includes("social")) return "🌐";
  if (normalized.includes("friend") || t.includes("friends")) return "🤝";
  if (normalized.includes("cooking") || t.includes("cooking")) return "🍳";
  if (normalized.includes("study") || t.includes("study")) return "📚";
  return "👥";
};

const getCommunityColor = (name: string, theme?: string): string => {
  const normalized = (name || "").toLowerCase();
  const t = (theme || "").toLowerCase();
  if (normalized.includes("interview") || t.includes("career")) return "#3a86c8";
  if (normalized.includes("strangers") || t.includes("social")) return "#833ab4";
  if (normalized.includes("friend") || t.includes("friends")) return "#22c55e";
  if (normalized.includes("cooking") || t.includes("cooking")) return "#f4a261";
  if (normalized.includes("study") || t.includes("study")) return "#e9c46a";
  return "#8b7355";
};

// ── Geometry Constants ────────────────────────────────────────────────────────
const R = 800;
const VISIBLE_W = 180;
const CX = R; // disc centre x in SVG coords (off-screen right)
const DEG_PER_TICK = 10; // angle spacing between items

export const CommunityCarousel: React.FC<CommunityCarouselProps> = ({
  communities,
  loading,
  onManageCommunity,
}) => {
  const { activeCommunityId, setActiveCommunity } = useCoOSStore();
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [svgH, setSvgH] = useState(() => (typeof window !== "undefined" ? window.innerHeight : 600));
  const isScrolling = useRef(false);
  const scrollTimeout = useRef<ReturnType<typeof setTimeout>>();

  // All items: joined communities + "+" add/join item
  const allItems = [
    ...communities,
    {
      id: "__add__",
      name: "+",
      type: "system",
      theme: undefined,
      member_cap: 5,
      member_count: 0,
      is_member: false,
      role: "member",
      rules: [],
      quotes: [],
    } as CommunityRead,
  ];

  // Find active index
  const getActiveIndex = useCallback(() => {
    if (!activeCommunityId || activeCommunityId === "__add__") {
      return allItems.length - 1; // Default to add button if no active community
    }
    const idx = communities.findIndex((c) => c.id === activeCommunityId);
    return idx >= 0 ? idx : allItems.length - 1;
  }, [activeCommunityId, allItems.length, communities]);

  const [activeIndex, setActiveIndex] = useState(getActiveIndex);

  // Sync index on external activeCommunityId changes
  useEffect(() => {
    setActiveIndex(getActiveIndex());
  }, [activeCommunityId, getActiveIndex]);

  const navigateTo = useCallback(
    (newIndex: number) => {
      const clamped = Math.max(0, Math.min(allItems.length - 1, newIndex));
      setActiveIndex(clamped);
      const item = allItems[clamped];
      if (item.id === "__add__") {
        setActiveCommunity("__add__");
      } else {
        setActiveCommunity(item.id);
      }
    },
    [allItems, setActiveCommunity]
  );

  const goUp = useCallback(() => navigateTo(activeIndex - 1), [activeIndex, navigateTo]);
  const goDown = useCallback(() => navigateTo(activeIndex + 1), [activeIndex, navigateTo]);

  // Wheel scroll throttling
  const handleWheel = useCallback(
    (e: WheelEvent) => {
      e.preventDefault();
      if (isScrolling.current) return;

      isScrolling.current = true;
      clearTimeout(scrollTimeout.current);

      if (e.deltaY < 0) {
        goUp();
      } else if (e.deltaY > 0) {
        goDown();
      }

      scrollTimeout.current = setTimeout(() => {
        isScrolling.current = false;
      }, 220);
    },
    [goUp, goDown]
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener("wheel", handleWheel, { passive: false });
    return () => el.removeEventListener("wheel", handleWheel);
  }, [handleWheel]);

  // ResizeObserver to track container height dynamically (HTML element avoids SVG bounding box measurement issues)
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    // Sync initial height
    const initialH = el.clientHeight || el.getBoundingClientRect().height;
    if (initialH > 0) setSvgH(initialH);

    const ro = new ResizeObserver(() => {
      const h = el.clientHeight || el.getBoundingClientRect().height;
      if (h > 0) setSvgH(h);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const handleItemClick = (index: number) => {
    if (index !== activeIndex) {
      navigateTo(index);
    } else if (allItems[index].id === "__add__") {
      setActiveCommunity("__add__");
    } else {
      if (onManageCommunity) {
        onManageCommunity(allItems[index].id);
      }
    }
  };

  if (loading && communities.length === 0) {
    return (
      <aside className="community-carousel flex items-center justify-center" style={{ width: VISIBLE_W }}>
        <div className="text-sm text-text-muted skeleton-text">載入中...</div>
      </aside>
    );
  }

  const cy = svgH / 2;
  const rimR = R - 2; // 798px
  const itemR = R - 42; // 758px

  // Calculate the edge x-coordinate for the path defensively
  const discValue = rimR * rimR - cy * cy;
  const xEdge = CX - Math.sqrt(discValue > 0 ? discValue : 0);
  const pathD = `M ${xEdge},0 A ${rimR},${rimR} 0 0,0 ${xEdge},${svgH} L ${VISIBLE_W},${svgH} L ${VISIBLE_W},0 Z`;

  // Disk rotation (when index increases, rotation increases, pushing earlier items up/out)
  const rotation = activeIndex * DEG_PER_TICK;

  // Build list of ticks and items
  const ticks = allItems
    .map((item, idx) => {
      const localAngle = 180 - idx * DEG_PER_TICK;
      const globalAngle = localAngle + rotation;
      const deviation = globalAngle - 180;
      const signedDev = (((deviation + 180) % 360) + 360) % 360 - 180;
      const absDev = Math.abs(signedDev);

      if (absDev > 90) return null; // Clip items far away from pointer

      const isSelected = idx === activeIndex;
      const isAdd = item.id === "__add__";

      // Proximity to pointer (1.0 at pointer 180°, scaling down to 0.0 at 60° deviation)
      const proximity = Math.max(0, Math.cos((signedDev * Math.PI) / 120));
      const size = isAdd
        ? (isSelected ? 100 : 64)
        : 64 + (100 - 64) * proximity;
      const fs = 13 + (17 - 13) * proximity;
      const op = 0.45 + 0.55 * proximity;
      const brightness = 0.6 + 0.4 * proximity;

      // Position in viewport coords (based on rotated globalAngle)
      const rad = (globalAngle * Math.PI) / 180;
      const ix = CX + itemR * Math.cos(rad);
      const iy = cy + itemR * Math.sin(rad);

      const bgColor = getCommunityColor(item.name, item.theme);
      const emoji = getCommunityEmoji(item.name, item.theme);

      return {
        idx,
        item,
        isSelected,
        isAdd,
        ix,
        iy,
        size,
        fs,
        op,
        brightness,
        bgColor,
        emoji,
        localAngle,
      };
    })
    .filter((t): t is NonNullable<typeof t> => t !== null);



  return (
    <aside
      ref={containerRef}
      className="community-carousel"
      data-testid="community-carousel"
      style={{
        position: "relative",
        width: VISIBLE_W,
        height: "100%",
        flexShrink: 0,
        userSelect: "none",
        overflow: "visible",
        background: "linear-gradient(to right, var(--bg-base), var(--bg-surface))",
      }}
    >
      <svg
        ref={svgRef}
        width={VISIBLE_W}
        height="100%"
        style={{ position: "absolute", left: 0, top: 0, display: "block", overflow: "visible" }}
      >
        {/* Disc Fill (Static, no rotation to keep vertical border aligned) */}
        <path
          d={pathD}
          fill="var(--glass-bg)"
          stroke="var(--glass-border)"
          strokeWidth={1.5}
        />

        {/* Upright Ticks' HTML Elements using foreignObject */}
        {ticks.map((t) => {
          const W_fo = VISIBLE_W; // Use full visible width to prevent clipping
          const H_fo = 140;
          const foY = t.iy - 6 - t.size / 2;

          return (
            <motion.foreignObject
              key={t.item.id}
              x={0}
              y={0}
              width={W_fo}
              height={H_fo}
              initial={{ y: foY, opacity: 0 }}
              animate={{
                y: foY,
                opacity: t.op,
              }}
              transition={{
                type: "spring",
                stiffness: 220,
                damping: 24,
                mass: 0.8,
              }}
              style={{ overflow: "visible", cursor: "pointer" }}
              onClick={() => handleItemClick(t.idx)}
            >
              <div
                className="community-wheel-item"
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "flex-start",
                  width: "100%",
                  height: "100%",
                  gap: 4,
                  transform: `translateX(${t.ix - W_fo / 2}px)`,
                  filter: `brightness(${t.brightness})`,
                  transition: "transform 0.42s cubic-bezier(0.34, 1.56, 0.64, 1), filter 0.3s ease",
                  paddingTop: 6,
                  boxSizing: "border-box",
                }}
              >
                {t.isAdd ? (
                  <div
                    className="add-community-btn"
                    style={{
                      width: t.size,
                      height: t.size,
                      fontSize: t.isSelected ? 44 : 30,
                      borderStyle: "dashed",
                      borderRadius: "50%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                    data-testid="add-community-btn"
                  >
                    +
                  </div>
                ) : (
                  <div
                    className={`community-avatar-ring ${t.isSelected ? "is-center" : ""}`}
                    style={{
                      width: t.size,
                      height: t.size,
                      background: `linear-gradient(135deg, ${t.bgColor}, ${t.bgColor}cc)`,
                      borderRadius: "50%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    <span
                      className="community-avatar-text"
                      style={{ fontSize: t.isSelected ? 38 : 26 }}
                    >
                      {t.emoji}
                    </span>
                  </div>
                )}
                <span
                  className="community-carousel-label"
                  style={{
                    fontSize: t.fs,
                    fontWeight: t.isSelected ? 700 : 500,
                    color: t.isSelected ? "var(--gold-accent)" : "var(--text-secondary)",
                    opacity: t.isSelected ? 1 : 0.8,
                    transition: "all 0.3s ease",
                    maxWidth: 160,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                    textAlign: "center",
                    marginTop: 2,
                  }}
                >
                  {t.item.name === "+" ? "加入新社群" : t.item.name}
                </span>
                {t.isSelected && !t.isAdd}
              </div>
            </motion.foreignObject>
          );
        })}
      </svg>

      {/* Center pointer removed per user request */}
    </aside>
  );
};
