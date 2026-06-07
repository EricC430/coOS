/**
 * M3.2 -- Role Dashboard tests
 * [R08 SS1] [R09 SS4 SDT] [R06 SS2]
 * @integration_risk RISK-04, RISK-06
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { RoleFocusCarouselDock } from "../../src/components/m3_2_dashboard/RoleFocusCarouselDock";
import { ConsistencyHeatmap } from "../../src/components/m3_2_dashboard/ConsistencyHeatmap";
import { HeatmapCell } from "../../src/components/m3_2_dashboard/ConsistencyHeatmap/HeatmapCell";

const mockRoles = [
  { id: "csie_001", name: "CSIE", colorHex: "#4A90D9" },
  { id: "family_002", name: "FAMILY", colorHex: "#E07B39" },
  { id: "uni_001", name: "UNI", colorHex: "#6366f1" },
];

// Build 365 days of mock heatmap data
function buildMockHeatmap() {
  const today = new Date();
  return Array.from({ length: 365 }, (_, i) => {
    const d = new Date(today);
    d.setDate(today.getDate() - (364 - i));
    return { date: d.toISOString().split("T")[0], count: i % 7 };
  });
}

describe("M3.2.1 Role Focus Carousel", () => {
  it("renders all roles and marks active icon with data-testid", () => {
    render(
      <RoleFocusCarouselDock
        roles={mockRoles}
        activeRoleId="csie_001"
        onRoleSnap={vi.fn()}
      />
    );
    const active = screen.getByTestId("active-role-icon");
    expect(active).toHaveAttribute("data-role-id", "csie_001");
  });

  it("[R09 SS4] center icon vs side icon test-id check", () => {
    render(
      <RoleFocusCarouselDock
        roles={mockRoles}
        activeRoleId="uni_001"
        onRoleSnap={vi.fn()}
        onCenterClick={vi.fn()}
      />
    );
    // Framer Motion transforms are hard to test via inline styles in JSDOM
    // We check that the active-role-icon exists and side-role-icons exist
    expect(screen.getByTestId("active-role-icon")).toBeDefined();
    expect(screen.getAllByTestId("side-role-icon").length).toBeGreaterThan(0);
  });

  it("[RISK-04] onRoleSnap called on navigation button click", async () => {
    const snapSpy = vi.fn();
    render(
      <RoleFocusCarouselDock
        roles={mockRoles}
        activeRoleId="csie_001"
        onRoleSnap={snapSpy}
        onCenterClick={vi.fn()}
      />
    );
    
    // Test navigation via button instead of complex pointer events
    const nextBtn = screen.getByTestId("carousel-nav-right");
    fireEvent.click(nextBtn);
    expect(snapSpy).toHaveBeenCalledWith("family_002");
  });
});

describe("M3.2.4 Consistency Heatmap", () => {
  it("renders exactly 365 heatmap cells", () => {
    render(<ConsistencyHeatmap data={buildMockHeatmap()} />);
    // Each cell has a date-specific testid like heatmap-cell-2026-06-04
    const cells = document.querySelectorAll("[data-testid^='heatmap-cell-']");
    expect(cells.length).toBe(365);
  });

  it("hover shows tooltip with count", async () => {
    const data = [{ date: "2026-06-01", count: 3 }];
    render(<ConsistencyHeatmap data={data} />);
    const cell = screen.getByTestId("heatmap-cell-2026-06-01");
    fireEvent.mouseEnter(cell);
    await waitFor(() => {
      expect(screen.getByTestId("heatmap-tooltip")).toHaveTextContent("3 項");
    });
  });

  it("4-level colour mapping correct", () => {
    const { rerender } = render(<HeatmapCell count={0} />);
    expect(document.querySelector("[data-testid='heatmap-cell']")).toHaveClass("heatmap-level-0");

    rerender(<HeatmapCell count={1} />);
    expect(document.querySelector("[data-testid='heatmap-cell']")).toHaveClass("heatmap-level-1");

    rerender(<HeatmapCell count={6} />);
    expect(document.querySelector("[data-testid='heatmap-cell']")).toHaveClass("heatmap-level-3");
  });
});
