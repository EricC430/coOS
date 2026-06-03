/**
 * M3.4 -- Chat Message List with SSE Observer events
 * [R09 SS6.1 MAS] Observer events as inline system hints
 */

import React, { useEffect, useRef } from "react";
import { SystemEventHint, type ObserverEvent } from "./SystemEventHint";

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
    <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
      {messages.map((msg) => {
        if (msg.role === "system_event" && msg.observerEvent) {
          return <SystemEventHint key={msg.id} event={msg.observerEvent} />;
        }

        const isUser = msg.role === "user";
        return (
          <div
            key={msg.id}
            className={`flex gap-2 ${isUser ? "flex-row-reverse" : "flex-row"}`}
          >
            <div className="w-7 h-7 rounded-full bg-indigo-100 flex-shrink-0 flex items-center justify-center text-sm">
              {isUser ? "👤" : (msg.expertAvatarUrl ? (
                <img src={msg.expertAvatarUrl} alt="" className="w-full h-full rounded-full object-cover" />
              ) : "🤖")}
            </div>
            <div
              className={`max-w-xs lg:max-w-md rounded-2xl px-3 py-2 text-sm ${
                isUser
                  ? "bg-indigo-600 text-white"
                  : "bg-white border text-gray-700"
              }`}
            >
              {msg.content}
            </div>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
