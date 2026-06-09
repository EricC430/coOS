/**
 * M3.2.1 -- Coverflow Rotary Wheel Carousel (Game-Grade)
 *
 * SPEC: docs/modules/M3_2_role_dashboard_SPEC.md SS7.1
 * [R08 SS1] Inertia Snap: ritualises role switch as intentional act
 * [R09 SS4 SDT] Centre icon larger by >= 1.3x reinforces autonomy signal
 * @risk RISK-04 Do NOT emit ROLE_SWITCHED during animation -- only on snap complete
 *
 * Redesign: Coverflow 3D carousel with:
 * - Rotary wheel feel with arc decoration
 * - Mouse wheel scroll to rotate
 * - Avatar images that pop out of circles when focused
 * - "+" dashed circle to add new roles
 * - Left/right arrow navigation buttons
 * - Click center role to enter chat room
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { motion } from "framer-motion";

export interface CarouselRole {
  id: string;
  name: string;
  iconName?: string;
  colorHex?: string;
  avatarUrl?: string;
}

interface Props {
  roles: CarouselRole[];
  activeRoleId: string;
  onRoleSnap: (roleId: string) => void;
  onCenterClick: (roleId: string) => void;
  onAddRole?: () => void;
}

// Calculate 3D transform for each item based on offset from center
function getItemStyle(offset: number) {
  // offset: -N..0..+N where 0 = center
  const absOffset = Math.abs(offset);
  const direction = Math.sign(offset);

  // Center item: big, no rotation
  if (offset === 0) {
    return {
      x: 0,
      z: 0,
      rotateY: 0,
      scale: 1,
      opacity: 1,
      brightness: 1,
    };
  }

  // Side items: progressively smaller, rotated, shifted
  const xSpacing = 130; // px between items
  const zDepth = -80; // depth per offset step
  const yRotation = 35; // degrees per step

  return {
    x: direction * (absOffset * xSpacing),
    z: absOffset * zDepth,
    rotateY: -direction * Math.min(absOffset * yRotation, 65),
    scale: Math.max(0.45, 1 - absOffset * 0.2),
    opacity: Math.max(0, 1 - absOffset * 0.25),
    brightness: Math.max(0.5, 1 - absOffset * 0.15),
  };
}

const CENTER_SIZE = 110;
const SIDE_SIZE = 80;
const MAX_VISIBLE = 3; // items visible on each side

export function RoleFocusCarouselDock({
  roles,
  activeRoleId,
  onRoleSnap,
  onCenterClick,
  onAddRole,
}: Props) {
  const [activeIndex, setActiveIndex] = useState(
    Math.max(roles.findIndex((r) => r.id === activeRoleId), 0)
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const isScrolling = useRef(false);
  const scrollTimeout = useRef<ReturnType<typeof setTimeout>>();

  // All items = roles + "add" button
  const allItems = [...roles, { id: "__add__", name: "+", colorHex: undefined }];

  // Sync external activeRoleId changes
  useEffect(() => {
    const idx = roles.findIndex((r) => r.id === activeRoleId);
    if (idx >= 0 && idx !== activeIndex) setActiveIndex(idx);
  }, [activeRoleId]);

  const navigateTo = useCallback(
    (newIndex: number) => {
      const clamped = Math.max(0, Math.min(allItems.length - 1, newIndex));
      setActiveIndex(clamped);
      if (clamped < roles.length) {
        // [RISK-04] Emit only on snap complete
        onRoleSnap(roles[clamped].id);
      }
    },
    [allItems.length, roles, onRoleSnap]
  );

  const goLeft = useCallback(() => navigateTo(activeIndex - 1), [activeIndex, navigateTo]);
  const goRight = useCallback(() => navigateTo(activeIndex + 1), [activeIndex, navigateTo]);

  // Mouse wheel handler
  const handleWheel = useCallback(
    (e: WheelEvent) => {
      e.preventDefault();
      if (isScrolling.current) return;

      isScrolling.current = true;
      clearTimeout(scrollTimeout.current);

      if (e.deltaY < 0) {
        // Scroll up → rotate left
        goLeft();
      } else if (e.deltaY > 0) {
        // Scroll down → rotate right
        goRight();
      }

      scrollTimeout.current = setTimeout(() => {
        isScrolling.current = false;
      }, 300);
    },
    [goLeft, goRight]
  );

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener("wheel", handleWheel, { passive: false });
    return () => el.removeEventListener("wheel", handleWheel);
  }, [handleWheel]);

  const handleItemClick = (index: number) => {
    const item = allItems[index];

    if (index !== activeIndex) {
      // Side item — always just snap to center; never open chat or add dialog
      navigateTo(index);
      return;
    }

    // Center item clicked
    if (item.id === "__add__") {
      onAddRole?.();
    } else {
      onCenterClick(item.id);
    }
  };

  return (
    <div
      ref={containerRef}
      data-testid="role-carousel"
      className="coverflow-container"
      style={{ touchAction: "none" }}
    >
      {/* Arc decoration */}
      <div className="carousel-arc" />

      {/* Left arrow */}
      <button
        className="carousel-nav-btn left"
        onClick={goLeft}
        data-testid="carousel-nav-left"
        aria-label="Previous role"
        disabled={activeIndex === 0}
        style={{ opacity: activeIndex === 0 ? 0.3 : 1 }}
      >
        ‹
      </button>

      {/* Right arrow */}
      <button
        className="carousel-nav-btn right"
        onClick={goRight}
        data-testid="carousel-nav-right"
        aria-label="Next role"
        disabled={activeIndex === allItems.length - 1}
        style={{ opacity: activeIndex === allItems.length - 1 ? 0.3 : 1 }}
      >
        ›
      </button>

      {/* Coverflow track */}
      <div className="coverflow-track">
        {allItems.map((item, idx) => {
          const offset = idx - activeIndex;
          const absOffset = Math.abs(offset);

          // Don't render items too far away
          if (absOffset > MAX_VISIBLE + 1) return null;

          const isAdd = item.id === "__add__";
          const isCenter = offset === 0;
          const isSide = absOffset === 1;
          const style = getItemStyle(offset);
          const size = isCenter ? CENTER_SIZE : SIDE_SIZE;
          const bgColor = item.colorHex ?? "#8b7355";

          const posClass = isCenter
            ? "is-center"
            : isSide
            ? "is-side"
            : "is-far";

          return (
            <motion.div
              key={item.id}
              className={`coverflow-item ${posClass}`}
              data-testid={isCenter ? "active-role-icon" : "side-role-icon"}
              data-role-id={item.id}
              animate={{
                x: style.x,
                z: style.z,
                rotateY: style.rotateY,
                scale: style.scale,
                opacity: style.opacity,
              }}
              transition={{
                type: "spring",
                stiffness: 200,
                damping: 25,
                mass: 0.8,
              }}
              onClick={() => handleItemClick(idx)}
              style={{
                filter: `brightness(${style.brightness})`,
                cursor: "pointer",
              }}
            >
              {isAdd ? (
                /* Add role button */
                <div
                  className="add-role-btn"
                  style={{ width: size, height: size }}
                  data-testid="add-role-btn"
                >
                  +
                </div>
              ) : (
                /* Role avatar */
                <>
                  <div
                    className={`role-avatar-ring ${isCenter ? "is-center" : ""}`}
                    style={{
                      width: size,
                      height: size,
                      background: `linear-gradient(135deg, ${bgColor}, ${bgColor}cc)`,
                    }}
                  >
                    {(item as CarouselRole).avatarUrl ? (
                      <img
                        src={(item as CarouselRole).avatarUrl}
                        alt={item.name}
                        className="role-avatar-image"
                        draggable={false}
                      />
                    ) : (
                      <span
                        className="role-avatar-text"
                        style={{ fontSize: isCenter ? 28 : 20 }}
                      >
                        {(item as CarouselRole).iconName ??
                          item.name.slice(0, 2).toUpperCase()}
                      </span>
                    )}
                  </div>
                  <span className="role-label">{item.name}</span>
                </>
              )}
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
