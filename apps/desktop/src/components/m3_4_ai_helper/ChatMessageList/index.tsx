/**
 * M3.4 -- Chat Message List with SSE Observer events
 * [R09 SS6.1 MAS] Observer events as inline system hints
 */

import React, { useEffect, useRef } from "react";
import { SystemEventHint, type ObserverEvent } from "./SystemEventHint";
import { LatexRenderer } from "./LatexRenderer";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system_event";
  content: string;
  observerEvent?: ObserverEvent;
  expertName?: string;
  expertAvatarUrl?: string;
  createdAt?: string;
}

interface Props {
  messages: ChatMessage[];
  onLoadMore?: () => Promise<void>;
  hasMore?: boolean;
  isToolChatRoom?: boolean;
}

function formatFriendlyTimestamp(date: Date): string {
  const now = new Date();
  
  // Reset hours/minutes/seconds for date comparison
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const dateStart = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  
  const diffTime = todayStart.getTime() - dateStart.getTime();
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
  
  const hours = date.getHours();
  const minutes = date.getMinutes();
  const period = hours >= 12 ? "下午" : "上午";
  const displayHour = hours % 12 === 0 ? 12 : hours % 12;
  const displayMin = minutes.toString().padStart(2, "0");
  const timeStr = `${period}${displayHour}:${displayMin}`;
  
  if (diffDays === 0) {
    return timeStr;
  } else if (diffDays > 0 && diffDays < 7) {
    const weekdays = ["週日", "週一", "週二", "週三", "週四", "週五", "週六"];
    const weekday = weekdays[date.getDay()];
    return `${weekday} ${timeStr}`;
  } else {
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();
    return `${year}年${month}月${day}日 ${timeStr}`;
  }
}

export function ChatMessageList({ messages, onLoadMore, hasMore, isToolChatRoom = false }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const prevFirstIdRef = useRef<string | null>(null);
  const prevMessagesLengthRef = useRef<number>(0);
  const [loading, setLoading] = React.useState(false);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const firstId = messages[0]?.id || null;
    const isPrepend = firstId !== prevFirstIdRef.current && prevFirstIdRef.current !== null && messages.length > prevMessagesLengthRef.current;

    if (isPrepend) {
      const prevHeight = container.dataset.prevHeight ? parseInt(container.dataset.prevHeight, 10) : 0;
      const diff = container.scrollHeight - prevHeight;
      if (diff > 0) {
        container.scrollTop = diff;
      }
    } else {
      setTimeout(() => {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: "smooth"
        });
      }, 50);
    }

    prevFirstIdRef.current = firstId;
    prevMessagesLengthRef.current = messages.length;
    container.dataset.prevHeight = String(container.scrollHeight);
  }, [messages]);

  const handleScroll = async (e: React.UIEvent<HTMLDivElement>) => {
    const container = e.currentTarget;
    container.dataset.prevHeight = String(container.scrollHeight);

    if (container.scrollTop === 0 && hasMore && onLoadMore && !loading) {
      setLoading(true);
      await onLoadMore();
      setLoading(false);
    }
  };

  const renderedElements: React.ReactNode[] = [];
  let lastTimestamp: number | null = null;

  messages.forEach((msg) => {
    // System events are always rendered as permanent markers — skip timestamp header for them.
    if (msg.role === "system_event" && msg.observerEvent) {
      renderedElements.push(
        <SystemEventHint key={msg.id} event={msg.observerEvent} />
      );
      return;
    }

    let showHeader = false;
    const msgTime = msg.createdAt ? new Date(msg.createdAt).getTime() : null;

    if (msgTime) {
      if (lastTimestamp === null || msgTime - lastTimestamp > 15 * 60 * 1000) {
        showHeader = true;
      }
      lastTimestamp = msgTime;
    }

    if (showHeader && msg.createdAt) {
      const friendlyTime = formatFriendlyTimestamp(new Date(msg.createdAt));
      renderedElements.push(
        <div
          key={`time_${msg.id}`}
          style={{
            textAlign: "center",
            margin: "16px 0 8px",
            fontSize: 11,
            color: "var(--text-muted, #888)",
            fontWeight: 500,
          }}
        >
          {friendlyTime}
        </div>
      );
    }

    const isUser = msg.role === "user";

    if (isToolChatRoom) {
      renderedElements.push(
        <div
          key={msg.id}
          style={{
            padding: "10px 0",
            fontSize: 13,
            lineHeight: 1.6,
            color: "var(--text-primary)",
            width: "100%",
          }}
        >
          <div style={{ fontWeight: 600, color: isUser ? "var(--gold-accent)" : "var(--role-primary)", marginBottom: 4 }}>
            {isUser ? "你" : (msg.expertName || "工具型 AI")}
          </div>
          <LatexRenderer content={msg.content} />
        </div>
      );
    } else {
      const UUID_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      const isToolAI = !msg.expertName ||
                       msg.expertName === "工具型 AI" ||
                       msg.expertName === "__tool__" ||
                       msg.expertName === "tool_ai_default" ||
                       msg.expertName === "assistant" ||
                       msg.expertName.startsWith("tool_ai_");
      const isUuidName = msg.expertName ? UUID_REGEX.test(msg.expertName) : false;

      const avatarContent = isUser ? "👤" : (
        msg.expertAvatarUrl
          ? <img src={msg.expertAvatarUrl} alt="" style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }} />
          : (isToolAI ? "🤖" : (isUuidName ? "👤" : msg.expertName!.slice(0, 1)))
      );

      renderedElements.push(
        <div
          key={msg.id}
          style={{ display: "flex", gap: 8, flexDirection: isUser ? "row-reverse" : "row" }}
        >
          <div style={{
            width: 28, height: 28, borderRadius: "50%",
            background: isUser ? "var(--glass-border)" : "var(--gold-accent)",
            flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 13, fontWeight: 700, color: "white",
            overflow: "hidden",
          }}>
            {avatarContent}
          </div>
          <div style={{
            maxWidth: "min(320px, 72%)",
            borderRadius: 18,
            padding: "8px 14px",
            fontSize: 13,
            lineHeight: 1.55,
            background: isUser ? "var(--role-primary)" : "var(--glass-bg)",
            border: isUser ? "none" : "1px solid var(--glass-border)",
            color: isUser ? "#fff" : "var(--text-primary)",
            backdropFilter: isUser ? undefined : "blur(12px)",
          }}>
            <LatexRenderer content={msg.content} />
          </div>
        </div>
      );
    }
  });

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto px-4 py-3"
      style={{ display: "flex", flexDirection: "column", gap: 12 }}
    >
      {loading && (
        <div style={{ textAlign: "center", padding: "4px 0", color: "var(--text-muted)", fontSize: 12 }}>
          載入中更舊對話...
        </div>
      )}
      {renderedElements}
    </div>
  );
}
