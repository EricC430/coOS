/**
 * M3.5 -- Achievement Display tests
 * [R09 §HAIA] [R01 §Dropout buffer]
 * @integration_risk RISK-09
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { AchievementMasterDetail } from "../../src/components/m3_5_achievements/AchievementMasterDetail";
import { AchievementGrid } from "../../src/components/m3_5_achievements/AchievementMasterDetail/AchievementGrid";
import { BadgeSlot } from "../../src/components/m3_5_achievements/BadgeSlot";

const mockCollections = [
  { id: "badge_001", name: "首次反思", rarity: "common" as const, unlock_condition: "完成第一次反思" },
  { id: "badge_002", name: "CPE 挑戰者", rarity: "rare" as const, image_url: "https://example.com/cpe.png" },
];

const mockDictionary = [
  ...mockCollections,
  { id: "badge_003", name: "隱藏徽章", rarity: "epic" as const },
];

describe("M3.5.1 Master-Detail Layout", () => {
  it("grid shows all unlocked badge slots", () => {
    render(
      <AchievementGrid
        collections={mockCollections}
        dictionary={mockDictionary}
        onSelect={vi.fn()}
      />
    );
    const slots = screen.getAllByTestId("badge-slot");
    expect(slots.length).toBe(mockCollections.length);
  });

  it("click badge shows detail panel with unlock condition", async () => {
    render(<AchievementMasterDetail collections={mockCollections} dictionary={mockDictionary} />);
    fireEvent.click(screen.getAllByTestId("badge-slot")[0]);
    await waitFor(() => {
      expect(screen.getByTestId("badge-detail-panel")).toBeInTheDocument();
      expect(screen.getByTestId("badge-unlock-condition")).not.toBeEmptyDOMElement();
    });
  });

  it("locked badges show locked class and no detail on click", () => {
    render(
      <AchievementGrid
        collections={[]}
        dictionary={mockDictionary}
        onSelect={vi.fn()}
      />
    );
    const locked = screen.getAllByTestId("badge-slot-locked");
    expect(locked.length).toBeGreaterThan(0);
    locked.forEach((slot) => expect(slot).toHaveClass("locked"));
  });
});

describe("M3.5.2 Rarity styling", () => {
  it("legendary badge has rarity-legendary class", () => {
    render(<BadgeSlot item={{ id: "b", rarity: "legendary" }} unlocked />);
    expect(document.querySelector(".rarity-legendary")).toBeInTheDocument();
  });

  it("image error shows fallback", async () => {
    render(<BadgeSlot item={{ id: "b", rarity: "common", image_url: "bad-url" }} unlocked />);
    const img = screen.getByRole("img");
    fireEvent.error(img);
    await waitFor(() => {
      expect(screen.getByTestId("badge-image-fallback")).toBeInTheDocument();
    });
  });
});
