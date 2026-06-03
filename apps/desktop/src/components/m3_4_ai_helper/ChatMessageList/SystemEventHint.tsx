/**
 * M3.4.4.1 -- System Event Hint (Invisible automation notification)
 * [R09 SS6.1 MAS] Observer events shown inline, NEVER as Modal/Toast
 * [RISK-04] L2 defer: only sidebar badge, no interruption during deep work
 */

import React from "react";

export interface ObserverEvent {
  type: string;
  project_name?: string;
  goal?: string;
  expert_name?: string;
  text?: string;
  title?: string;
  deadline?: string;
}

const EVENT_MESSAGES: Record<string, (e: ObserverEvent) => string> = {
  PROJECT_CREATED: (e) => `Project 偵測為「${e.project_name}」已建立`,
  GOAL_INFERRED: (e) => `目標「${e.goal}」已記錄`,
  GOAL_CONFIRMED: (e) => `與 ${e.expert_name} 確立目標「${e.title}」`,
  PROMISE_RECORDED: (e) =>
    `承諾「${e.text}」已記錄${e.deadline ? `，deadline: ${e.deadline}` : ""}`,
  PROMISE_REMINDER: (e) => `承諾「${e.text}」即將到期`,
};

interface Props {
  event: ObserverEvent;
}

export function SystemEventHint({ event }: Props) {
  const message = EVENT_MESSAGES[event.type]?.(event) ?? event.type;

  return (
    // Centered grey inline text -- not a Toast, not a Modal
    <div
      data-testid="system-event-hint"
      className="system-event-hint-inline text-center text-xs text-gray-400 py-1 select-none"
    >
      ── {message} ──
    </div>
  );
}
