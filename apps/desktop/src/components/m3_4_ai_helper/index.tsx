/**
 * M3.4 -- Multi-Agent AI Helper Module
 *
 * SPEC: docs/modules/M3_4_multi_agent_helper_SPEC.md
 * Research: [R03 SS1] [R05 §therapy alliance] [R09 SS6.1 SS4] [R10] [R01 §DDA]
 * Risk mitigation: RISK-04, RISK-11, RISK-12, RISK-16, RISK-17
 *
 * [FIX-02] Resizable sidebar via drag splitter
 * [FIX-03] Expert avatar from avatarUrl / name initial
 * [FIX-04] Project tags persisted to Zustand store and restored on remount
 * [FIX-05] Greeting no longer injected manually — loadHistory picks it up from DB
 */

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useCoOSStore, type ProjectTagEvent } from "../../stores/m3_1_global_store";
import { ExpertSidebar } from "./ExpertSidebar";
import { MatchPersonaButton } from "./MatchPersonaButton";
import { MultimodalInputBar } from "./MultimodalInputBar";
import { ChatMessageList, type ChatMessage } from "./ChatMessageList";
import type { ObserverEvent } from "./ChatMessageList/SystemEventHint";

// [D2] Client-side sentence splitter for history restoration.
// Mirrors the backend split logic so assistant history shows as natural short bubbles.
const _SPLIT_RE = /(?<=[。？！\n])\s*/u;
const _MIN_LEN = 8;

function _clientSplit(text: string): string[] {
  const raw = text.split(_SPLIT_RE).map((s) => s.trim()).filter(Boolean);
  if (raw.length <= 1) return [text];
  // Merge tiny fragments into the previous bubble
  const out: string[] = [];
  for (const seg of raw) {
    if (out.length > 0 && seg.length < _MIN_LEN) {
      out[out.length - 1] += seg;
    } else {
      out.push(seg);
    }
  }
  return out.length > 1 ? out : [text];
}

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

// SSE events that should be persisted as project tags
const PROJECT_TAG_TYPES = new Set(["PROJECT_CREATED", "PROJECT_SWITCHED"]);

interface Props {
  onWorkflowOpen?: () => void;
}

export function MultiAgentHelper({ onWorkflowOpen }: Props) {
  const {
    activeExpert, currentRole, expertCache, setActiveExpert, seedExpertCache,
    projectTags, addProjectTag,
  } = useCoOSStore();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [showMatchSuggestion, setShowMatchSuggestion] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [dbCount, setDbCount] = useState(0);
  const sseRef = useRef<EventSource | null>(null);
  // [D1] Track last loaded thread to detect expert-switch vs same-thread return
  const lastLoadedThreadRef = useRef<string>("");

  // [FIX-02] Sidebar resize state
  const [sidebarWidth, setSidebarWidth] = useState<number>(() => {
    const saved = localStorage.getItem("coos:sidebarWidth");
    return saved ? parseInt(saved, 10) : 192;
  });
  const isDraggingRef = useRef(false);
  const dragStartXRef = useRef(0);
  const dragStartWidthRef = useRef(192);
  // [FIX-05] Use a ref to track current width inside event listeners (avoid stale closure)
  const sidebarWidthRef = useRef(sidebarWidth);
  useEffect(() => { sidebarWidthRef.current = sidebarWidth; }, [sidebarWidth]);

  // Current thread depends on both role and active expert
  const activeExpertId = activeExpert?.id ?? null;
  const threadId = buildThreadId(currentRole?.id ?? "default", activeExpertId);

  // [D2] Load history and re-split assistant bubbles client-side
  const loadHistory = useCallback(async (roleId: string, expertId: string | null) => {
    setMessages([]);
    setShowMatchSuggestion(false);
    setHasMore(true);
    setDbCount(0);
    const tid = buildThreadId(roleId, expertId);
    try {
      const limit = 50;
      const res = await fetch(`/api/m4_1/history?role_id=${encodeURIComponent(roleId)}&thread_id=${encodeURIComponent(tid)}&limit=${limit}&offset=0`);
      if (res.ok) {
        const rows: Array<{ role: string; content: string; persona_id?: string; created_at?: string }> = await res.json();
        const restored: ChatMessage[] = [];

        if (rows.length > 0) {
          rows.forEach((r, i) => {
            if (r.role === "system_event") {
              try {
                const parsed = JSON.parse(r.content);
                restored.push({
                  id: `hist_0_${i}`,
                  role: "system_event",
                  content: "",
                  observerEvent: parsed as ObserverEvent,
                  createdAt: r.created_at,
                });
              } catch (err) {
                console.error("Failed to parse system_event", err);
              }
            } else if (r.role !== "assistant") {
              restored.push({
                id: `hist_0_${i}`,
                role: "user",
                content: r.content,
                createdAt: r.created_at,
              });
            } else {
              // [D2] Re-split assistant messages into natural short bubbles, except for tool AI
              const lookupKey = r.persona_id ? r.persona_id.toLowerCase() : "";
              const isTool = !lookupKey || lookupKey === "tool_ai_default" || lookupKey.startsWith("tool_ai_");
              const bubbles = isTool ? [r.content] : _clientSplit(r.content);
              
              // [FIX-03] Look up avatar AND name from expertCache by persona_id
              // NOTE: expertCache must be seeded BEFORE loadHistory is called
              const histExpert = lookupKey ? useCoOSStore.getState().expertCache[lookupKey] : null;
              bubbles.forEach((bubble, bi) => {
                restored.push({
                  id: `hist_0_${i}_${bi}`,
                  role: "assistant",
                  content: bubble,
                  // [FIX] Use actual expertName, NOT the UUID persona_id
                  expertName: histExpert?.expertName ?? undefined,
                  expertAvatarUrl: histExpert?.avatarUrl ?? undefined,
                  createdAt: r.created_at,
                });
              });
            }
          });
        }
        setMessages(restored);
        setDbCount(rows.length);
        if (rows.length < limit) {
          setHasMore(false);
        }
      }
    } catch {
      // non-fatal
    }
  }, []);

  const loadMoreHistory = useCallback(async () => {
    if (!currentRole?.id) return;
    const tid = buildThreadId(currentRole.id, activeExpertId);
    const limit = 50;
    try {
      const res = await fetch(`/api/m4_1/history?role_id=${encodeURIComponent(currentRole.id)}&thread_id=${encodeURIComponent(tid)}&limit=${limit}&offset=${dbCount}`);
      if (res.ok) {
        const rows: Array<{ role: string; content: string; persona_id?: string; created_at?: string }> = await res.json();
        if (rows.length === 0) {
          setHasMore(false);
          return;
        }

        const olderMessages: ChatMessage[] = [];
        rows.forEach((r, i) => {
          if (r.role === "system_event") {
            try {
              const parsed = JSON.parse(r.content);
              olderMessages.push({
                id: `hist_${dbCount}_${i}`,
                role: "system_event",
                content: "",
                observerEvent: parsed as ObserverEvent,
                createdAt: r.created_at,
              });
            } catch (err) {
              console.error("Failed to parse system_event", err);
            }
          } else if (r.role !== "assistant") {
            olderMessages.push({
              id: `hist_${dbCount}_${i}`,
              role: "user",
              content: r.content,
              createdAt: r.created_at,
            });
          } else {
            const lookupKey = r.persona_id ? r.persona_id.toLowerCase() : "";
            const isTool = !lookupKey || lookupKey === "tool_ai_default" || lookupKey.startsWith("tool_ai_");
            const bubbles = isTool ? [r.content] : _clientSplit(r.content);
            const histExpert = lookupKey ? useCoOSStore.getState().expertCache[lookupKey] : null;
            bubbles.forEach((bubble, bi) => {
              olderMessages.push({
                id: `hist_${dbCount}_${i}_${bi}`,
                role: "assistant",
                content: bubble,
                expertName: histExpert?.expertName ?? undefined,
                expertAvatarUrl: histExpert?.avatarUrl ?? undefined,
                createdAt: r.created_at,
              });
            });
          }
        });

        setMessages((prev) => [...olderMessages, ...prev]);

        setDbCount((prev) => prev + rows.length);
        if (rows.length < limit) {
          setHasMore(false);
        }
      }
    } catch {
      // non-fatal
    }
  }, [currentRole?.id, activeExpertId, dbCount]);

  // [D1] On role change: reset to tool AI first, reload experts, load tool AI history.
  // CRITICAL: set lastLoadedThreadRef BEFORE setActiveExpert to avoid race with the
  // activeExpertId useEffect (which fires synchronously when Zustand updates).
  useEffect(() => {
    if (!currentRole?.id) return;

    async function init() {
      // [FIX-RACE] Set ref immediately so the activeExpertId effect skips its load
      const toolThread = buildThreadId(currentRole!.id, null);
      lastLoadedThreadRef.current = toolThread;

      // [FIX-04] Reset sidebar highlight and content to tool AI
      setActiveExpert("__tool__");

      // Seed experts BEFORE loading history so avatar lookup works
      try {
        const res = await fetch(`/api/m6_2/roles/${currentRole!.id}/experts`);
        if (res.ok) seedExpertCache(await res.json());
      } catch { /* non-fatal */ }

      await loadHistory(currentRole!.id, null);
    }

    init();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentRole?.id]);

  // [D1] On explicit expert switch — skip if already loaded
  // IMPORTANT: "__tool__" maps to the same thread as null, so normalise it.
  useEffect(() => {
    if (!currentRole?.id) return;
    // Normalise: treat "__tool__" the same as null (both = tool AI thread)
    const normId = (!activeExpertId || activeExpertId === "__tool__") ? null : activeExpertId;
    const targetThread = buildThreadId(currentRole.id, normId);
    if (lastLoadedThreadRef.current !== targetThread) {
      lastLoadedThreadRef.current = targetThread;
      loadHistory(currentRole.id, normId);
    }
  }, [activeExpertId, currentRole?.id, loadHistory]);

  const activeExperts = Object.values(expertCache);

  // [RISK-04] SSE for Observer events -- no Modal popup
  // [FIX-04] PROJECT_CREATED / PROJECT_SWITCHED → also save to Zustand store
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

          // [FIX-04] Persist project tag events to global store so they survive remounts
          if (PROJECT_TAG_TYPES.has(event.type)) {
            const tid = buildThreadId(
              useCoOSStore.getState().currentRole?.id ?? "default",
              useCoOSStore.getState().activeExpert?.id
            );
            addProjectTag(tid, event as unknown as ProjectTagEvent);
          }

          setMessages((prev) => [
            ...prev,
            { id: nextId(), role: "system_event", content: "", observerEvent: event, createdAt: new Date().toISOString() },
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
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSend = async (text: string, _attachments: File[]) => {
    if (!text.trim()) return;

    setShowMatchSuggestion(false);
    const userMsgTime = new Date().toISOString();
    setMessages((prev) => [...prev, { id: nextId(), role: "user", content: text, createdAt: userMsgTime }]);

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

        const aiMsgTime = new Date().toISOString();
        if (splitMsgs) {
          // Render first bubble immediately
          setMessages((prev) => [
            ...prev,
            {
              id: nextId(),
              role: "assistant",
              content: splitMsgs[0].content,
              expertName: activeExpert?.expertName,
              expertAvatarUrl: activeExpert?.avatarUrl ?? undefined,
              createdAt: aiMsgTime,
            },
          ]);
          // Render subsequent bubbles with delay
          for (let i = 1; i < splitMsgs.length; i++) {
            const delayMs = splitMsgs[i].delay_ms || 1200;
            await new Promise((r) => setTimeout(r, delayMs));
            setMessages((prev) => [
              ...prev,
              {
                id: nextId(),
                role: "assistant",
                content: splitMsgs[i].content,
                expertName: activeExpert?.expertName,
                expertAvatarUrl: activeExpert?.avatarUrl ?? undefined,
                createdAt: new Date().toISOString(),
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
              expertAvatarUrl: activeExpert?.avatarUrl ?? undefined,
              createdAt: aiMsgTime,
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

  // [FIX-02] Resize handler
  const handleResizeMouseDown = (e: React.MouseEvent) => {
    isDraggingRef.current = true;
    dragStartXRef.current = e.clientX;
    dragStartWidthRef.current = sidebarWidth;
    e.preventDefault();
  };

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isDraggingRef.current) return;
      const delta = e.clientX - dragStartXRef.current;
      const newWidth = Math.max(120, Math.min(400, dragStartWidthRef.current + delta));
      setSidebarWidth(newWidth);
      sidebarWidthRef.current = newWidth;
    };
    const onMouseUp = () => {
      if (!isDraggingRef.current) return;
      isDraggingRef.current = false;
      // [FIX-05] Use ref value — not stale closure — when saving
      localStorage.setItem("coos:sidebarWidth", String(sidebarWidthRef.current));
    };
    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  // Only attach once — no deps to avoid re-adding listeners on every width change
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ display: "flex", height: "100%", background: "var(--bg-base)" }}>
      {/* Sidebar — each expert is an independent chat room */}
      <div style={{ display: "flex", flexDirection: "column", width: sidebarWidth, flexShrink: 0, minWidth: 0 }}>
        <div style={{ flex: 1, overflow: "hidden" }}>
          <ExpertSidebar
            activeExperts={activeExperts}
            activeExpertId={activeExpert?.id}
            onSelectTool={() => setActiveExpert("__tool__")}
            onSelectPersona={handleSelectPersona}
            onDeleteExpert={handleDeleteExpert}
          />
        </div>
        <div style={{
          padding: "8px",
          borderTop: "1px solid var(--glass-border)",
          background: "var(--bg-surface)",
        }}>
          <MatchPersonaButton
            currentPersonaId={activeExpert?.id}
            onGreeting={(msg) => {
              setMessages((prev) => prev.some((m) => m.content === msg.content) ? prev : [...prev, msg]);
              setShowMatchSuggestion(false);
            }}
          />
        </div>
      </div>

      {/* [FIX-02] Draggable resize handle */}
      <div
        className="resize-handle"
        onMouseDown={handleResizeMouseDown}
        title="拖曳調整寬度"
      />

      {/* Chat area */}
      <div style={{ display: "flex", flexDirection: "column", flex: 1, minWidth: 0 }}>
        <ChatMessageList messages={messages} onLoadMore={loadMoreHistory} hasMore={hasMore} isToolChatRoom={isToolAI} />

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
