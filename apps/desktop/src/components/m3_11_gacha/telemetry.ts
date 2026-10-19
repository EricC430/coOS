/**
 * M3.11 Telemetry & Event Logging (FR-015)
 * Dispatches gamification events to local L1 raw_tracking_logs
 * Completely non-blocking and offline resilient.
 */

export type GachaEventType =
  | "gacha_draw_initiated"
  | "gacha_draw_success"
  | "gacha_draw_ratelimited"
  | "background_generated"
  | "object_generated"
  | "canvas_harmonize_requested"
  | "canvas_harmonize_completed"
  | "canvas_harmonize_fallback"
  | "surprise_modal_displayed"
  | "custom_theme_applied";

export interface LogEventPayload {
  module: "M3.11";
  event_type: GachaEventType;
  timestamp: string;
  metadata?: Record<string, any>;
}

export async function logGachaEvent(
  event_type: GachaEventType,
  metadata?: Record<string, any>
): Promise<void> {
  const payload: LogEventPayload = {
    module: "M3.11",
    event_type,
    timestamp: new Date().toISOString(),
    metadata,
  };

  try {
    if (typeof fetch !== "undefined") {
      await fetch("/api/events", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }).catch(() => {
        // Offline / silent fallback, never block UI
      });
    }
  } catch {
    // Non-blocking
  }
}
