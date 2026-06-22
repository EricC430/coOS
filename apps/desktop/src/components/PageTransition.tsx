/**
 * PageTransition — Directional slide-in/out overlay pages
 *
 * Wraps child page content with framer-motion AnimatePresence.
 * The page slides in from the specified direction and slides back
 * to the same direction when dismissed.
 */

import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import { EdgeNavigationTrigger } from "./EdgeNavigationTrigger";

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
  const backSide = (() => {
    switch (direction) {
      case "left": return "right";
      case "right": return "left";
      case "top": return "bottom";
      case "bottom": return "top";
    }
  })();

  const backArrow = (() => {
    switch (direction) {
      case "left": return "›";
      case "right": return "‹";
      case "top": return "▼";
      case "bottom": return "▲";
    }
  })();

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
          {/* Edge back button trigger */}
          {onBack && (
            <EdgeNavigationTrigger
              side={backSide}
              label="返回主頁"
              arrowIcon={backArrow}
              onClick={onBack}
            />
          )}
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
