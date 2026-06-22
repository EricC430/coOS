import { motion } from "framer-motion";
import { useEffect } from "react";

interface PieMenuProps {
  x: number;
  y: number;
  onClose: () => void;
  onOpenSettings: () => void;
  dark: boolean;
  toggleTheme: () => void;
}

export function PieMenu({
  x,
  y,
  onClose,
  onOpenSettings,
  dark,
  toggleTheme,
}: PieMenuProps) {
  // Esc key closes the menu
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  return (
    <>
      {/* Click outside to close */}
      <motion.div
        className="pie-menu-backdrop"
        onClick={onClose}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
      />

      <div
        className="pie-menu-container"
        style={{ left: x, top: y }}
      >
        {/* Center node indicator */}
        <motion.div
          className="pie-menu-center-node"
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 0.8 }}
          exit={{ scale: 0, opacity: 0 }}
          transition={{ type: "spring", stiffness: 350, damping: 20 }}
        />

        {/* Settings button */}
        <motion.button
          className="pie-menu-item"
          title="系統與隱私設定"
          onClick={(e) => {
            e.stopPropagation();
            onOpenSettings();
          }}
          initial={{ x: 0, y: 0, scale: 0, opacity: 0 }}
          animate={{ x: -45, y: -30, scale: 1, opacity: 1 }}
          exit={{ x: 0, y: 0, scale: 0, opacity: 0 }}
          transition={{ type: "spring", stiffness: 400, damping: 22 }}
        >
          ⚙️
        </motion.button>

        {/* Theme toggle button */}
        <motion.button
          className="pie-menu-item"
          title={dark ? "切換淺色模式" : "切換深色模式"}
          onClick={(e) => {
            e.stopPropagation();
            toggleTheme();
            onClose(); // Auto-dismiss
          }}
          initial={{ x: 0, y: 0, scale: 0, opacity: 0 }}
          animate={{ x: 45, y: -30, scale: 1, opacity: 1 }}
          exit={{ x: 0, y: 0, scale: 0, opacity: 0 }}
          transition={{ type: "spring", stiffness: 400, damping: 22 }}
        >
          {dark ? "☀" : "🌙"}
        </motion.button>
      </div>
    </>
  );
}
