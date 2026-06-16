/**
 * M3.4 -- Multi-Agent AI Helper Module
 *
 * SPEC: docs/modules/M3_4_multi_agent_helper_SPEC.md
 * Research: [R03 SS1] [R05 §therapy alliance] [R09 SS6.1 SS4] [R10] [R01 §DDA]
 * Risk mitigation: RISK-04, RISK-11, RISK-12, RISK-16, RISK-17
 */

import React, { useState, useEffect, useRef, useCallback } from "react";
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

// thread_id: role 的工具型 AI 聊天室 = thread_{roleId}
//            專家聊天室 = thread_{roleId}_{expertId}
function buildThreadId(roleId: string, expertId?: string | null): string {
  if (!expertId || expertId === "__tool__") return `thread_${roleId}`;
  return `thread_${roleId}_${expertId}`;
}

interface Props {
  onWorkflowOpen?: () => void;
}

export function MultiAgentHelper({ onWorkflowOpen }: Props) {
  const { activeExpert, currentRole, expertCache, setActiveExpert, seedExpertCache } = useCoOSStore();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [showMatchSuggestion, setShowMatchSuggestion] = useState(false);
  const sseRef = useRef<EventSource | null>(null);

  // Current thread depends on both role and active expert
  const activeExpertId = activeExpert?.id ?? null;
  const threadId = buildThreadId(currentRole?.id ?? "default", activeExpertId);

  // Load history whenever the active thread changes (role or expert switch)
  const loadHistory = useCallback(async (roleId: string, expertId: string | null) => {
    setMessages([]);
    setShowMatchSuggestion(false);
    const tid = buildThreadId(roleId, expertId);
    try {
      const res = await fetch(`/api/m4_1/history?role_id=${encodeURIComponent(roleId)}&thread_id=${encodeURIComponent(tid)}&limit=30`);
      if (res.ok) {
        const rows: Array<{ role: string; content: string; persona_id?: string }> = await res.json();
        if (rows.length > 0) {
          const restored: ChatMessage[] = rows.map((r, i) => ({
            id: `hist_${i}`,
            role: r.role === "user" ? "user" : "assistant",
            content: r.content,
            expertName: r.role === "assistant" ? (r.persona_id ?? undefined) : undefined,
          }));
          setMessages(restored);
        }
      }
    } catch {
      // non-fatal
    }
  }, []);

  // On role change: reload experts + reset to tool AI + load tool AI history
  useEffect(() => {
    if (!currentRole?.id) return;

    async function init() {
      try {
        const res = await fetch(`/api/m6_2/roles/${currentRole!.id}/experts`);
        if (res.ok) seedExpertCache(await res.json());
      } catch { /* non-fatal */ }

      await loadHistory(currentRole!.id, null);
    }

    init();
  }, [currentRole?.id]);

  // On expert switch (only when switching TO a real expert, not on role reset)
  useEffect(() => {
    if (!currentRole?.id || !activeExpertId) return;
    loadHistory(currentRole.id, activeExpertId);
  }, [activeExpertId]);

  const activeExperts = Object.values(expertCache);

  // [RISK-04] SSE for Observer events -- no Modal popup
  useEffect(() => {
    let es: EventSource | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    let retryCount = 0;
    const MAX_RETRIES = 10;
    const RETRY_DELAY_MS = 3000;
    let destroyed = false;

    function connect() {
      if (destroyed) return;
      es = new EventSource("/api/m4_6/events");
      sseRef.current = es;

      es.onmessage = (e) => {
        retryCount = 0;
        try {
          const event = JSON.parse(e.data) as ObserverEvent;
          if (event.type === "PING") return;
          setMessages((prev) => [
            ...prev,
            { id: nextId(), role: "system_event", content: "", observerEvent: event },
          ]);
        } catch { /* ignore malformed SSE frames */ }
      };

      es.onerror = () => {
        es?.close();
        es = null;
        sseRef.current = null;
        if (destroyed) return;
        if (retryCount >= MAX_RETRIES) return;
        retryCount++;
        retryTimer = setTimeout(connect, RETRY_DELAY_MS);
      };
    }

    connect();

    return () => {
      destroyed = true;
      if (retryTimer) clearTimeout(retryTimer);
      es?.close();
    };
  }, []);

  const handleSend = async (text: string, _attachments: File[]) => {
    if (!text.trim()) return;

    setShowMatchSuggestion(false);
    setMessages((prev) => [...prev, { id: nextId(), role: "user", content: text }]);

    try {
      const res = await fetch("/api/m4_1/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          thread_id: threadId,
          content: text,
          role: "user",
          role_id: currentRole?.id,
          persona_id: activeExpert?.id !== "__tool__" ? activeExpert?.id : undefined,
        }),
      });
      if (res.ok) {
        const data = await res.json();

        // [W7] Multi-bubble rendering: if split_messages available, render sequentially
        const splitMsgs: Array<{ content: string; delay_ms: number }> =
          data.split_messages && data.split_messages.length > 1
            ? data.split_messages
            : null;

        if (splitMsgs) {
          // Render first bubble immediately
          setMessages((prev) => [
            ...prev,
            {
              id: nextId(),
              role: "assistant",
              content: splitMsgs[0].content,
              expertName: activeExpert?.expertName,
            },
          ]);
          // Render subsequent bubbles with delay
          for (let i = 1; i < splitMsgs.length; i++) {
            const delayMs = splitMsgs[i].delay_ms || 800;
            await new Promise((r) => setTimeout(r, delayMs));
            setMessages((prev) => [
              ...prev,
              {
                id: nextId(),
                role: "assistant",
                content: splitMsgs[i].content,
                expertName: activeExpert?.expertName,
              },
            ]);
          }
        } else {
          // Fallback: single bubble
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

        if (data.suggest_match === true && (activeExpert == null || activeExpert.id === "__tool__")) {
          setShowMatchSuggestion(true);
        }
      }
    } catch { /* Silently fail */ }
  };

  const handleSelectPersona = (expert: typeof activeExperts[0]) => {
    setActiveExpert(expert.id);
  };

  // [GAP-A4][RISK-17] Expert deletion with last-expert guard
  const handleDeleteExpert = async (expertId: string) => {
    if (!currentRole?.id) return;
    try {
      const res = await fetch(
        `/api/m4_1/experts/${encodeURIComponent(expertId)}?role_id=${encodeURIComponent(currentRole.id)}`,
        { method: "DELETE" }
      );
      if (res.ok) {
        const data = await res.json();
        // Remove from local cache
        const updated = { ...expertCache };
        delete updated[expertId];
        seedExpertCache(Object.values(updated));
        // If deleted the active expert, fall back to tool AI
        if (activeExpert?.id === expertId) {
          setActiveExpert("__tool__");
        }
        if (data.pool_empty) {
          // pool_empty: EXPERT_POOL_EMPTY SSE will arrive via EventSource and show in chat
        }
      }
    } catch { /* non-fatal */ }
  };

  const isToolAI = !activeExpert || activeExpert.id === "__tool__";

  return (
    <div className="flex h-full">
      {/* Sidebar — each expert is an independent chat room */}
      <div className="flex flex-col w-48 flex-shrink-0">
        <div className="flex-1 overflow-hidden">
          <ExpertSidebar
            activeExperts={activeExperts}
            activeExpertId={activeExpert?.id}
            onSelectTool={() => setActiveExpert("__tool__")}
            onSelectPersona={handleSelectPersona}
            onDeleteExpert={handleDeleteExpert}
          />
        </div>
        <div className="p-2 border-t">
          <MatchPersonaButton
            currentPersonaId={activeExpert?.id}
            onGreeting={(msg) => {
              setMessages((prev) => prev.some((m) => m.content === msg.content) ? prev : [...prev, msg]);
              setShowMatchSuggestion(false);
            }}
          />
        </div>
      </div>

      {/* Chat area */}
      <div className="flex flex-col flex-1 min-w-0">
        <ChatMessageList messages={messages} />

        {/* AI-triggered match suggestion banner */}
        {showMatchSuggestion && isToolAI && (
          <div
            style={{
              margin: "0 16px 8px",
              padding: "10px 14px",
              background: "var(--glass-bg, rgba(255,255,255,0.08))",
              border: "1px solid var(--accent, #7c6fff)",
              borderRadius: 10,
              display: "flex",
              alignItems: "center",
              gap: 10,
              fontSize: 13,
              color: "var(--text-primary)",
            }}
          >
            <span style={{ flex: 1 }}>✨ 看起來你的需求很明確，我幫你配對一位專家吧？</span>
            <MatchPersonaButton
              currentPersonaId={undefined}
              onGreeting={(msg) => {
                setMessages((prev) => prev.some((m) => m.content === msg.content) ? prev : [...prev, msg]);
                setShowMatchSuggestion(false);
              }}
            />
            <button
              onClick={() => setShowMatchSuggestion(false)}
              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", fontSize: 16, lineHeight: 1 }}
              aria-label="關閉建議"
            >
              ✕
            </button>
          </div>
        )}

        <MultimodalInputBar
          onSend={handleSend}
          onWorkflowOpen={onWorkflowOpen ?? (() => {})}
        />
      </div>
    </div>
  );
}
