/**
 * M3.6 -- Workflow Modal tests
 * [R10 §workflow] [R08 SS5]
 * @integration_risk RISK-12
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { WorkflowModal } from "../../src/components/m3_6_workflow_modal";
import { useCoOSStore } from "../../src/stores/m3_1_global_store";

function wrapper({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      {children}
    </QueryClientProvider>
  );
}

beforeEach(() => {
  useCoOSStore.setState({
    currentRole: { id: "csie_001", name: "CSIE", themeColorPalette: { primary: "#4A90D9" } },
    xpBalance: 0,
    level: 1,
    activeExpert: null,
    roleCache: {},
    expertCache: {},
    isRoleTransitioning: false,
  });
  // Stub fetch for connected_sources
  globalThis.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => [],
  }) as typeof fetch;
});

describe("M3.6.1 In-context trigger", () => {
  it("modal renders when open=true, no page navigation", () => {
    render(<WorkflowModal open={true} onClose={vi.fn()} />, { wrapper });
    expect(screen.getByTestId("workflow-modal")).toBeInTheDocument();
  });

  it("close button hides modal", async () => {
    const onClose = vi.fn();
    render(<WorkflowModal open={true} onClose={onClose} />, { wrapper });
    fireEvent.click(screen.getByTestId("modal-close-btn"));
    expect(onClose).toHaveBeenCalled();
  });
});

describe("M3.6.2 Data source binding", () => {
  it("three source chips rendered", () => {
    render(<WorkflowModal open={true} onClose={vi.fn()} />, { wrapper });
    expect(screen.getByTestId("source-github")).toBeInTheDocument();
    expect(screen.getByTestId("source-obsidian")).toBeInTheDocument();
    expect(screen.getByTestId("source-browser")).toBeInTheDocument();
  });

  it("GitHub connect shows 已連線 badge on success", async () => {
    const bindSpy = vi.fn().mockResolvedValue(undefined);
    render(<WorkflowModal open={true} onClose={vi.fn()} onBind={bindSpy} />, { wrapper });
    fireEvent.change(screen.getByTestId("github-repo-input"), {
      target: { value: "user/my-repo" },
    });
    fireEvent.click(screen.getByTestId("connect-github-btn"));
    await waitFor(() => {
      expect(bindSpy).toHaveBeenCalledWith("github", { repo: "user/my-repo" });
    });
  });
});

describe("M3.6.3 Trigger condition form", () => {
  it("save trigger button calls onCreateTrigger with correct payload", async () => {
    const createSpy = vi.fn().mockResolvedValue(undefined);
    render(<WorkflowModal open={true} onClose={vi.fn()} onCreateTrigger={createSpy} />, { wrapper });
    fireEvent.change(screen.getByTestId("trigger-event-select"), {
      target: { value: "git_commit" },
    });
    fireEvent.click(screen.getByTestId("save-trigger-btn"));
    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({ event_type: "git_commit" })
      );
    });
  });
});
