/**
 * PageTransition — Directional slide-in/out overlay pages
 *
 * Wraps child page content with framer-motion AnimatePresence.
 * The page slides in from the specified direction and slides back
 * to the same direction when dismissed.
 */

import React from "react";
import { motion, AnimatePresence } from "framer-motion";

type Direction = "left" | "right" | "top" | "bottom";

interface Props {
  isOpen: boolean;
  direction: Direction;
  children: React.ReactNode;
  onBack?: () => void;
}

function getInitial(dir: Direction) {
  switch (dir) {
    case "left":   return { x: "-100%" };
    case "right":  return { x: "100%" };
    case "top":    return { y: "-100%" };
    case "bottom": return { y: "100%" };
  }
}

function getAnimate(dir: Direction) {
  switch (dir) {
    case "left":
    case "right":  return { x: 0 };
    case "top":
    case "bottom": return { y: 0 };
  }
}

function getExit(dir: Direction) {
  return getInitial(dir);
}

export function PageTransition({ isOpen, direction, children, onBack }: Props) {
  return (
    <AnimatePresence mode="wait">
      {isOpen && (
        <motion.div
          className="page-overlay"
          initial={getInitial(direction)}
          animate={getAnimate(direction)}
          exit={getExit(direction)}
          transition={{
            type: "spring",
            stiffness: 260,
            damping: 30,
            mass: 0.8,
          }}
          data-testid={`page-transition-${direction}`}
        >
          {/* Back button */}
          {onBack && (
            <button
              onClick={onBack}
              data-testid="page-back-btn"
              className="glass-card"
              style={{
                position: "absolute",
                top: 16,
                left: 16,
                zIndex: 60,
                width: 40,
                height: 40,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
                fontSize: 18,
                color: "var(--gold-accent)",
                border: "1px solid var(--glass-border)",
                background: "var(--glass-bg)",
                backdropFilter: "blur(8px)",
                borderRadius: 12,
              }}
              title="返回主頁"
            >
              ←
            </button>
          )}
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
