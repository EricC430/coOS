/**
 * M3.6 -- In-Context Workflow Modal
 *
 * SPEC: docs/modules/M3_6_workflow_modal_SPEC.md
 * Research: [R10 §agent workflow] [R08 SS5 intent decoupling]
 * Risk: RISK-12 (GitHub payload not sent to cloud LLM)
 * Anti-pattern: NEVER navigate away from conversation to configure workflow
 */

import React, { useEffect } from "react";
import { DataSourceBindingPanel, type DataSource } from "./DataSourceBindingPanel";
import { TriggerConditionForm, type WorkflowTrigger } from "./TriggerConditionForm";
import { useQuery } from "@tanstack/react-query";
import type { SourceType } from "./DataSourceBindingPanel";

interface Props {
  open: boolean;
  onClose: () => void;
  threadId?: string;
  onBind?: (sourceType: SourceType, config: Record<string, string>) => Promise<void>;
  onCreateTrigger?: (trigger: WorkflowTrigger) => Promise<void>;
}

async function fetchConnectedSources(): Promise<DataSource[]> {
  const res = await fetch("/api/m1_4/connected_sources");
  if (!res.ok) return [];
  return res.json();
}

async function defaultBind(sourceType: SourceType, config: Record<string, string>): Promise<void> {
  const res = await fetch("/api/m1_4/bind_source", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_type: sourceType, config }),
  });
  if (!res.ok) throw new Error("bind_failed");
}

async function defaultCreateTrigger(trigger: WorkflowTrigger): Promise<void> {
  const res = await fetch("/api/m1_4/create_trigger", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(trigger),
  });
  if (!res.ok) throw new Error("trigger_create_failed");
}

export function WorkflowModal({ open, onClose, onBind, onCreateTrigger }: Props) {
  const { data: sources = [] } = useQuery({
    queryKey: ["connected_sources"],
    queryFn: fetchConnectedSources,
    enabled: open,
  });

  // Return focus to chat input on close [M3.6.1 acceptance criteria]
  useEffect(() => {
    if (!open) {
      const chatInput = document.querySelector<HTMLElement>("[data-testid='chat-input']");
      chatInput?.focus();
    }
  }, [open]);

  if (!open) return null;

  return (
    // Floating overlay -- stays above conversation [R08 SS5 in-context]
    <div className="fixed inset-0 z-40 flex items-end justify-center sm:items-center bg-black/30">
      <div
        data-testid="workflow-modal"
        className="bg-white rounded-xl shadow-xl w-full max-w-md mx-4 mb-4 sm:mb-0"
      >
        <div className="flex items-center justify-between px-5 pt-4 pb-2 border-b">
          <h3 className="font-semibold text-sm">workflow 設定</h3>
          <div className="text-xs text-gray-400">chatbot chats</div>
          <button
            data-testid="modal-close-btn"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            ✕
          </button>
        </div>

        <div className="px-5 py-4 space-y-5">
          <DataSourceBindingPanel
            sources={sources}
            onBind={onBind ?? defaultBind}
          />
          <div className="border-t" />
          <TriggerConditionForm
            onCreateTrigger={onCreateTrigger ?? defaultCreateTrigger}
          />
        </div>
      </div>
    </div>
  );
}
