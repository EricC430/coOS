import React, { useState, useEffect, useCallback } from "react";
import { VisualItem } from "../types";
import { SurpriseModal } from "./SurpriseModal";

export interface HiddenAchievementListenerProps {
  socket?: WebSocket | null;
  onUnlocked?: (item: VisualItem) => void;
}

export const HiddenAchievementListener: React.FC<
  HiddenAchievementListenerProps
> = ({ socket, onUnlocked }) => {
  const [queue, setQueue] = useState<VisualItem[]>([]);
  const [activeItem, setActiveItem] = useState<VisualItem | null>(null);

  useEffect(() => {
    if (!socket) return;

    const handleMessage = (event: { data: string }) => {
      try {
        const payload = JSON.parse(event.data);
        if (
          payload?.type === "HIDDEN_ACHIEVEMENT_UNLOCKED" &&
          payload?.item
        ) {
          const newItem: VisualItem = payload.item;
          setQueue((prev) => [...prev, newItem]);
          if (onUnlocked) {
            onUnlocked(newItem);
          }
        }
      } catch {
        // Ignore unparseable or irrelevant WebSocket messages
      }
    };

    socket.addEventListener("message", handleMessage as any);
    return () => {
      socket.removeEventListener("message", handleMessage as any);
    };
  }, [socket, onUnlocked]);

  // FIFO Queue advancement
  useEffect(() => {
    if (!activeItem && queue.length > 0) {
      setActiveItem(queue[0]);
      setQueue((prev) => prev.slice(1));
    }
  }, [queue, activeItem]);

  const handleClose = useCallback(() => {
    setActiveItem(null);
  }, []);

  if (!activeItem) return null;

  return <SurpriseModal item={activeItem} onClose={handleClose} />;
};
