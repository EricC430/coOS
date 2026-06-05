/**
 * EdgeNavigationTrigger — Hover-activated navigation on screen edges
 *
 * Three triggers: left (日報), right (社群), top (成就)
 * Shows a curved, semi-transparent panel with arrow + label
 * when the mouse approaches the screen edge.
 */

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence, type Variants } from "framer-motion";

type EdgeSide = "left" | "right" | "top";

interface Props {
  side: EdgeSide;
  label: string;
  arrowIcon: string;
  onClick: () => void;
  /** Distance in px from edge to trigger visibility */
  threshold?: number;
}

const VARIANTS: Record<EdgeSide, Variants> = {
  left: {
    initial: { x: -60, opacity: 0 },
    animate: { x: 0, opacity: 1 },
    exit: { x: -60, opacity: 0 },
  },
  right: {
    initial: { x: 60, opacity: 0 },
    animate: { x: 0, opacity: 1 },
    exit: { x: 60, opacity: 0 },
  },
  top: {
    initial: { y: -60, opacity: 0 },
    animate: { y: 0, opacity: 1 },
    exit: { y: -60, opacity: 0 },
  },
};

export function EdgeNavigationTrigger({
  side,
  label,
  arrowIcon,
  onClick,
  threshold = 28,
}: Props) {
  const [visible, setVisible] = useState(false);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      const { clientX, clientY } = e;
      const w = window.innerWidth;

      let shouldShow = false;
      if (side === "left") shouldShow = clientX <= threshold;
      else if (side === "right") shouldShow = clientX >= w - threshold;
      else if (side === "top") shouldShow = clientY <= threshold;

      setVisible(shouldShow);
    },
    [side, threshold]
  );

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [handleMouseMove]);

  const className = `edge-trigger edge-trigger-${side}`;

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className={className}
          variants={VARIANTS[side]}
          initial="initial"
          animate="animate"
          exit="exit"
          transition={{ type: "spring", stiffness: 300, damping: 28 }}
          onClick={onClick}
          data-testid={`edge-trigger-${side}`}
        >
          <span className="edge-trigger-arrow">{arrowIcon}</span>
          <span className="edge-trigger-label">{label}</span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
