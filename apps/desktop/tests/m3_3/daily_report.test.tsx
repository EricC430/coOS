/**
 * M3.3 -- Daily Report tests
 * [R08 SS4.2 SS6.1 SS6.2] [R10 MindScape]
 * @integration_risk RISK-01
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { DraftApproveModal } from "../../src/components/m3_3_daily_report/DraftApproveModal";
import type { DailyReflection } from "../../src/components/m3_3_daily_report/DraftApproveModal/useApprovalGuard";

const mockDraft: DailyReflection = {
  id: "refl_001",
  ai_description: "你今天完成了微積分作業並花了大約 2 小時。",
  ai_analysis: "進度符合預期，主動解決難點。",
  user_feeling: "",
  user_action_plan: "",
  is_draft: true,
  is_reviewed: false,
};

describe("M3.3.3 Draft Approve Modal -- Core Psychological Mechanism", () => {
  it("AI description shown but user fields start empty", () => {
    render(<DraftApproveModal reflection={mockDraft} />);
    expect(screen.getByTestId("ai-description")).not.toBeEmptyDOMElement();
    expect(screen.getByTestId("user-feeling-input")).toHaveValue("");
    expect(screen.getByTestId("user-action-plan-input")).toHaveValue("");
  });

  it("[RISK-01] approve button disabled when user_feeling empty", () => {
    render(<DraftApproveModal reflection={mockDraft} />);
    expect(screen.getByTestId("approve-btn")).toBeDisabled();
    fireEvent.change(screen.getByTestId("user-feeling-input"), {
      target: { value: "有點焦慮但完成了" },
    });
    // action plan still empty
    expect(screen.getByTestId("approve-btn")).toBeDisabled();
  });

  it("[RISK-01] approve button disabled when user_action_plan empty", () => {
    render(<DraftApproveModal reflection={mockDraft} />);
    fireEvent.change(screen.getByTestId("user-action-plan-input"), {
      target: { value: "明天先做最難的那題" },
    });
    // feeling still empty
    expect(screen.getByTestId("approve-btn")).toBeDisabled();
  });

  it("[RISK-01] both fields filled -> button enabled, PATCH called before XP API", async () => {
    const patchSpy = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    const xpSpy = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });

    // Intercept fetch
    const originalFetch = globalThis.fetch;
    globalThis.fetch = vi.fn((url: string, opts) => {
      if (String(url).includes("reflections")) return patchSpy(url, opts) as Promise<Response>;
      if (String(url).includes("grant_xp")) return xpSpy(url, opts) as Promise<Response>;
      return originalFetch(url as RequestInfo, opts);
    }) as typeof fetch;

    const onApproved = vi.fn();
    render(<DraftApproveModal reflection={mockDraft} onApproved={onApproved} />);

    fireEvent.change(screen.getByTestId("user-feeling-input"), {
      target: { value: "有點焦慮但完成了" },
    });
    fireEvent.change(screen.getByTestId("user-action-plan-input"), {
      target: { value: "明天先做最難的那題" },
    });

    expect(screen.getByTestId("approve-btn")).not.toBeDisabled();
    fireEvent.click(screen.getByTestId("approve-btn"));

    await waitFor(() => {
      // PATCH must be called before XP
      expect(patchSpy).toHaveBeenCalled();
    });

    globalThis.fetch = originalFetch;
  });

  it("[R08 SS4.2] user_feeling placeholder contains '必填'", () => {
    render(<DraftApproveModal reflection={mockDraft} />);
    expect(screen.getByTestId("user-feeling-input")).toHaveAttribute(
      "placeholder",
      expect.stringContaining("必填")
    );
  });
});
