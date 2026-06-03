/**
 * M3.6.3 -- Trigger Condition Form
 * [R10 §agent workflow state machine] Structured trigger rules
 * Anti-pattern: triggers must be role-scoped, no global triggers
 */

import React, { useState } from "react";
import { useCoOSStore } from "../../stores/m3_1_global_store";

export type TriggerEventType = "git_commit" | "time_schedule" | "keyword_match";
export type TriggerAction = "create_draft" | "send_nudge" | "update_project_status";

export interface WorkflowTrigger {
  event_type: TriggerEventType;
  condition: {
    keyword?: string;
    cron?: string;
    repo?: string;
  };
  action: TriggerAction;
  role_id: string;
}

interface Props {
  onCreateTrigger: (trigger: WorkflowTrigger) => Promise<void>;
}

const ACTION_LABELS: Record<TriggerAction, string> = {
  create_draft: "建立日報草稿",
  send_nudge: "推送提示",
  update_project_status: "更新專案進度",
};

export function TriggerConditionForm({ onCreateTrigger }: Props) {
  const currentRole = useCoOSStore((s) => s.currentRole);
  const [eventType, setEventType] = useState<TriggerEventType>("git_commit");
  const [keyword, setKeyword] = useState("");
  const [cron, setCron] = useState("0 3 * * *");
  const [action, setAction] = useState<TriggerAction>("create_draft");
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (!currentRole) return;
    setSaving(true);
    try {
      await onCreateTrigger({
        event_type: eventType,
        condition: {
          keyword: eventType === "keyword_match" ? keyword : undefined,
          cron: eventType === "time_schedule" ? cron : undefined,
        },
        action,
        role_id: currentRole.id,
      });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="text-sm font-medium text-gray-600">trigger by</div>

      <select
        data-testid="trigger-event-select"
        value={eventType}
        onChange={(e) => setEventType(e.target.value as TriggerEventType)}
        className="w-full border rounded px-2 py-1 text-sm"
      >
        <option value="git_commit">commit...</option>
        <option value="time_schedule">period...</option>
        <option value="keyword_match">keyword...</option>
      </select>

      {eventType === "keyword_match" && (
        <input
          data-testid="trigger-keyword-input"
          className="w-full border rounded px-2 py-1 text-sm"
          placeholder="關鍵字（在對話中偵測到即觸發）"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
      )}

      {eventType === "time_schedule" && (
        <input
          className="w-full border rounded px-2 py-1 text-sm font-mono"
          placeholder="Cron: 0 3 * * *"
          value={cron}
          onChange={(e) => setCron(e.target.value)}
        />
      )}

      <select
        className="w-full border rounded px-2 py-1 text-sm"
        value={action}
        onChange={(e) => setAction(e.target.value as TriggerAction)}
      >
        {(Object.keys(ACTION_LABELS) as TriggerAction[]).map((a) => (
          <option key={a} value={a}>{ACTION_LABELS[a]}</option>
        ))}
      </select>

      <button
        data-testid="save-trigger-btn"
        onClick={handleSave}
        disabled={saving || !currentRole}
        className="w-full py-1.5 text-sm bg-indigo-600 text-white rounded disabled:opacity-40"
      >
        {saving ? "儲存中..." : "儲存觸發條件"}
      </button>
    </div>
  );
}
