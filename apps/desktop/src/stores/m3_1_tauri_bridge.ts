/**
 * M3.1 -- Tauri Event Bridge
 *
 * SPEC: docs/modules/M3_1_global_state_layout_SPEC.md SS7.2
 * Bridges backend SSE/Tauri events into Zustand store.
 */

import { useCoOSStore } from "./m3_1_global_store";

type TauriListenFn = (
  event: string,
  handler: (e: { payload: unknown }) => void
) => Promise<() => void>;

// Injected at init; mock-able in tests
let _listen: TauriListenFn | null = null;

export function setTauriListen(fn: TauriListenFn) {
  _listen = fn;
}

export async function initTauriBridge(): Promise<void> {
  if (!_listen) {
    try {
      const { listen } = await import("@tauri-apps/api/event");
      _listen = listen as unknown as TauriListenFn;
    } catch {
      console.warn("[M3.1] Tauri API not available -- bridge disabled");
      return;
    }
  }

  await _listen("XP_GRANTED", (e) => {
    const payload = e.payload as { amount: number; new_total: number };
    useCoOSStore.getState().applyXPGrant(payload);
  });

  await _listen("ROLE_CONTEXT_SYNCED", (e) => {
    const payload = e.payload as { role_id: string; active_expert_id: string };
    useCoOSStore.getState().switchRole(payload.role_id);
    useCoOSStore.getState().setActiveExpert(payload.active_expert_id);
    // Signal transition complete after backend confirms sync
    useCoOSStore.getState().setRoleTransitioning(false);
  });
}
