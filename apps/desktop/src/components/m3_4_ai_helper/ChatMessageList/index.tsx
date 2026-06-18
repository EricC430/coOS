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
}

interface Props {
  messages: ChatMessage[];
}

export function ChatMessageList({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  return (
    <div
      className="flex-1 overflow-y-auto px-4 py-3"
      style={{ display: "flex", flexDirection: "column", gap: 12 }}
    >
      {messages.map((msg) => {
        if (msg.role === "system_event" && msg.observerEvent) {
          return <SystemEventHint key={msg.id} event={msg.observerEvent} />;
        }

        const isUser = msg.role === "user";
        // [FIX-03] Show expert avatar or name initial; 🤖 only for tool AI with no name
        const avatarContent = isUser ? "👤" : (
          msg.expertAvatarUrl
            ? <img src={msg.expertAvatarUrl} alt="" style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }} />
            : (msg.expertName && msg.expertName !== "__tool__"
                ? msg.expertName.slice(0, 1)
                : "🤖")
        );

        return (
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
      })}
      <div ref={bottomRef} />
    </div>
  );
}
