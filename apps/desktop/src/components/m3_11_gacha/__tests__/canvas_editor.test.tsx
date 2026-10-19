import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { VisualStudioCanvas } from "../VisualStudioCanvas";
import { PRESET_BACKGROUNDS } from "../presetBackgrounds";
import { PRESET_OBJECTS } from "../presetObjects";
import { CanvasLayer } from "../types";

describe("M3.11 User Story 4: 畫布排版與「放置」非破壞性 AI 融合", () => {
  const initialLayers: CanvasLayer[] = [
    {
      id: "layer_01",
      item_id: PRESET_OBJECTS[0].id,
      name: PRESET_OBJECTS[0].name,
      image_url: PRESET_OBJECTS[0].image_url,
      semantic_features: PRESET_OBJECTS[0].semantic_features,
      x: 100,
      y: 150,
      scale: 1.0,
      rotation: 0,
      zIndex: 1,
    },
  ];

  it("FR-008: 載入背景並在背景上即時呈現物體圖層，支援選取與坐標微調", () => {
    render(
      <VisualStudioCanvas
        initialBackground={PRESET_BACKGROUNDS[0]}
        initialLayers={initialLayers}
        inventoryObjects={PRESET_OBJECTS}
      />
    );

    // Canvas viewport should render
    expect(screen.getByTestId("canvas-viewport")).toBeInTheDocument();
    expect(screen.getAllByText(PRESET_OBJECTS[0].name).length).toBeGreaterThan(0);

    // Select layer item in list
    const layerItem = screen.getByTestId("canvas-layer-item");
    fireEvent.click(layerItem);

    // Verify coordinate adjustment controls are rendered
    expect(screen.getByLabelText(/X 坐標/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Y 坐標/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/縮放比例/i)).toBeInTheDocument();
  });

  it("FR-008: 支援從物件庫新增圖層至畫布", () => {
    render(
      <VisualStudioCanvas
        initialBackground={PRESET_BACKGROUNDS[0]}
        initialLayers={initialLayers}
        inventoryObjects={PRESET_OBJECTS}
      />
    );

    const addObjectBtn = screen.getByRole("button", {
      name: new RegExp(`加入 ${PRESET_OBJECTS[1].name}`, "i"),
    });
    fireEvent.click(addObjectBtn);

    expect(screen.getAllByText(PRESET_OBJECTS[1].name).length).toBeGreaterThan(0);
    const layerBadges = screen.getAllByTestId("canvas-layer-item");
    expect(layerBadges.length).toBe(2);
  });

  it("FR-009: 點擊「放置」發送圖生圖融合請求，並以非破壞性方式保留物體圖層", async () => {
    const handleHarmonize = vi.fn().mockResolvedValue({
      image_url: "data:image/svg+xml;utf8,<svg id='ai-harmonized'></svg>",
      is_fallback: false,
      provider: "pollinations",
    });

    render(
      <VisualStudioCanvas
        initialBackground={PRESET_BACKGROUNDS[0]}
        initialLayers={initialLayers}
        inventoryObjects={PRESET_OBJECTS}
        onHarmonize={handleHarmonize}
      />
    );

    const placeBtn = screen.getByRole("button", { name: /✨ 放置（AI 融合）/i });
    await act(async () => {
      fireEvent.click(placeBtn);
    });

    expect(handleHarmonize).toHaveBeenCalledTimes(1);

    // AI Harmonized preview should be displayed
    expect(screen.getByTestId("harmonized-preview")).toBeInTheDocument();

    // NON-DESTRUCTIVE CHECK:
    // Layers must NOT be wiped or flattened; user can return to editing or see layers intact
    const editToggleBtn = screen.getByRole("button", { name: /返回編輯圖層/i });
    fireEvent.click(editToggleBtn);

    expect(screen.getAllByText(PRESET_OBJECTS[0].name).length).toBeGreaterThan(0);
    expect(screen.getByLabelText(/X 坐標/i)).toBeInTheDocument();
  });

  it("FR-010: 當 AI 圖生圖端點連線失敗時，100% 自動降級保留 2D 畫布合成圖", async () => {
    const handleHarmonize = vi
      .fn()
      .mockRejectedValue(new Error("Network Timeout / Free endpoint busy"));

    render(
      <VisualStudioCanvas
        initialBackground={PRESET_BACKGROUNDS[0]}
        initialLayers={initialLayers}
        inventoryObjects={PRESET_OBJECTS}
        onHarmonize={handleHarmonize}
      />
    );

    const placeBtn = screen.getByRole("button", { name: /✨ 放置（AI 融合）/i });
    await act(async () => {
      fireEvent.click(placeBtn);
    });

    // Fallback notice should appear
    expect(
      screen.getByText(/AI 融合暫不可用，已為您保留 2D 精準合成圖/i)
    ).toBeInTheDocument();

    // Preview should still be shown with fallback tag
    const preview = screen.getByTestId("harmonized-preview");
    expect(preview).toBeInTheDocument();
    expect(preview).toHaveAttribute("data-provider", "canvas_2d_fallback");
  });

  it("FR-010: 支援點擊「套用為主題」儲存場景並更新桌面主背景", async () => {
    const handleApplyTheme = vi.fn();

    render(
      <VisualStudioCanvas
        initialBackground={PRESET_BACKGROUNDS[0]}
        initialLayers={initialLayers}
        inventoryObjects={PRESET_OBJECTS}
        onApplyTheme={handleApplyTheme}
      />
    );

    const applyThemeBtn = screen.getByRole("button", { name: /套用為主題/i });
    await act(async () => {
      fireEvent.click(applyThemeBtn);
    });

    expect(handleApplyTheme).toHaveBeenCalledWith(
      expect.objectContaining({
        canvas_state: expect.any(Object),
        final_image_url: expect.any(String),
      })
    );
  });
});
