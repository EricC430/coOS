import { describe, it, expect, vi } from "vitest";
import { logGachaEvent } from "../telemetry";

describe("M3.11 FR-015: 事件遙測日誌 (raw_tracking_logs)", () => {
  it("發送遙測事件至 /api/events 端點，網路中斷時靜默降級不拋錯", async () => {
    const originalFetch = globalThis.fetch;
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    globalThis.fetch = fetchMock;

    await logGachaEvent("gacha_draw_success", { item_id: "bg_cyber_study" });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/events",
      expect.objectContaining({
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: expect.stringContaining("gacha_draw_success"),
      })
    );

    // Test offline/network error resilience
    fetchMock.mockRejectedValue(new Error("Offline"));
    await expect(
      logGachaEvent("canvas_harmonize_fallback", { provider: "canvas_2d_fallback" })
    ).resolves.toBeUndefined();

    globalThis.fetch = originalFetch;
  });
});
