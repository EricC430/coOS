/**
 * M3.4 -- Multi-Agent AI Helper Module
 *
 * SPEC: docs/modules/M3_4_multi_agent_helper_SPEC.md
 * Research: [R03 SS1] [R05 §therapy alliance] [R09 SS6.1 SS4] [R10] [R01 §DDA]
 * Risk mitigation: RISK-04, RISK-11, RISK-12, RISK-16, RISK-17
 */

import React, { useState, useEffect, useRef } from "react";
import { useCoOSStore } from "../../stores/m3_1_global_store";
import { ExpertSidebar } from "./ExpertSidebar";
import { MatchPersonaButton } from "./MatchPersonaButton";
import { MultimodalInputBar } from "./MultimodalInputBar";
import { ChatMessageList, type ChatMessage } from "./ChatMessageList";
import type { ObserverEvent } from "./ChatMessageList/SystemEventHint";

let _msgId = 0;
function nextId() {
  return String(++_msgId);
}

interface Props {
  onWorkflowOpen?: () => void;
}

export function MultiAgentHelper({ onWorkflowOpen }: Props) {
  const { activeExpert, currentRole, expertCache, setActiveExpert } = useCoOSStore();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [threadId] = useState(() => `thread_${Date.now()}`);
  const sseRef = useRef<EventSource | null>(null);

  const activeExperts = Object.values(expertCache).filter((e) => e.isActive);

  // [RISK-04] SSE for Observer events -- no Modal popup
  useEffect(() => {
    const es = new EventSource("/api/m4_6/events");
    sseRef.current = es;

    es.onmessage = (e) => {
      const event = JSON.parse(e.data) as ObserverEvent;
      setMessages((prev) => [
        ...prev,
        {
          id: nextId(),
          role: "system_event",
          content: "",
          observerEvent: event,
        },
      ]);
    };

    es.onerror = () => {
      // Reconnect handled by browser; surface badge indicator only
    };

    return () => es.close();
  }, []);

  const handleSend = async (text: string, _attachments: File[]) => {
    if (!text.trim()) return;

    setMessages((prev) => [
      ...prev,
      { id: nextId(), role: "user", content: text },
    ]);

    try {
      const res = await fetch("/api/m4_1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          thread_id: threadId,
          content: text,
          role: "user",
          role_id: currentRole?.id,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            content: data.content,
            expertName: activeExpert?.expertName,
          },
        ]);
      }
    } catch {
      // Silently fail -- don't break the UI
    }
  };

  return (
    <div className="flex h-full">
      {/* Sidebar */}
      <div className="flex flex-col w-48 flex-shrink-0">
        <div className="flex-1 overflow-hidden">
          <ExpertSidebar
            activeExperts={activeExperts}
            activeExpertId={activeExpert?.id}
            onSelectTool={() => setActiveExpert("__tool__")}
            onSelectPersona={(e) => setActiveExpert(e.id)}
          />
        </div>
        <div className="p-2 border-t">
          <MatchPersonaButton currentPersonaId={activeExpert?.id} />
        </div>
      </div>

      {/* Chat area */}
      <div className="flex flex-col flex-1 min-w-0">
        <ChatMessageList messages={messages} />
        <MultimodalInputBar
          onSend={handleSend}
          onWorkflowOpen={onWorkflowOpen ?? (() => {})}
        />
      </div>
    </div>
  );
}
