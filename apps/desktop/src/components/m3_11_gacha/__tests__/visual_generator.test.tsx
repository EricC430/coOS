import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { BackgroundGenerator } from "../BackgroundGenerator";
import { ObjectGenerator } from "../ObjectGenerator";
import { VisualItem } from "../types";

describe("M3.11 User Story 2: 背景圖片生成功能", () => {
  it("FR-006: 支援輸入「背景場景描述」與風格模板，組裝為自然語言具體句式並生成預覽", async () => {
    const handleGenerate = vi.fn().mockImplementation((prompt, style) => {
      // Prompt should be a detailed natural language sentence, NOT comma-separated tags
      expect(prompt).not.toMatch(/^(masterpiece, 8k, highly detailed)/i);
      expect(prompt.length).toBeGreaterThan(20);
      return Promise.resolve({
        id: "bg_gen_01",
        name: "自訂背景",
        category: "background",
        rarity: "epic",
        image_url: "data:image/svg+xml;utf8,<svg id='preview-bg'></svg>",
        has_transparency: false,
        scene_description: prompt,
        is_user_generated: true,
        in_gacha_pool: false,
        hidden: false,
      } as VisualItem);
    });

    render(<BackgroundGenerator onGenerate={handleGenerate} onSave={vi.fn()} />);

    // Fill scene description
    const input = screen.getByLabelText(/背景場景描述/i);
    fireEvent.change(input, {
      target: { value: "安靜的賽博龐克研究室，窗外有霓虹雨夜與遠景大樓" },
    });

    // Select style
    const styleSelect = screen.getByLabelText(/風格模板/i);
    fireEvent.change(styleSelect, { target: { value: "cyberpunk" } });

    const genBtn = screen.getByRole("button", { name: /生成背景/i });
    await act(async () => {
      fireEvent.click(genBtn);
    });

    expect(handleGenerate).toHaveBeenCalledTimes(1);
    expect(screen.getByTestId("background-preview")).toBeInTheDocument();
  });

  it("FR-006: 支援勾選「投入抽獎池」，儲存時設定 in_gacha_pool: true", async () => {
    const handleSave = vi.fn();
    const mockItem: VisualItem = {
      id: "bg_gen_02",
      name: "極光雪景",
      description: "美麗的雪山極光背景",
      category: "background",
      rarity: "rare",
      image_url: "data:image/svg+xml;utf8,<svg></svg>",
      has_transparency: false,
      scene_description: "雪山極光",
      is_user_generated: true,
      in_gacha_pool: false,
      hidden: false,
    };

    render(
      <BackgroundGenerator
        initialItem={mockItem}
        onGenerate={vi.fn()}
        onSave={handleSave}
      />
    );

    // Toggle gacha pool inclusion checkbox
    const gachaPoolCheckbox = screen.getByLabelText(/投入抽獎池/i);
    expect(gachaPoolCheckbox).not.toBeChecked();
    fireEvent.click(gachaPoolCheckbox);
    expect(gachaPoolCheckbox).toBeChecked();

    const saveBtn = screen.getByRole("button", { name: /儲存至收藏庫/i });
    fireEvent.click(saveBtn);

    expect(handleSave).toHaveBeenCalledWith(
      expect.objectContaining({
        in_gacha_pool: true,
        is_user_generated: true,
      })
    );
  });

  it("FR-006: 生成失敗時呈現友善錯誤訊息並提供重新生成按鈕", async () => {
    const handleGenerate = vi
      .fn()
      .mockRejectedValue(new Error("免費繪圖端點連線逾時"));

    render(<BackgroundGenerator onGenerate={handleGenerate} onSave={vi.fn()} />);

    const input = screen.getByLabelText(/背景場景描述/i);
    fireEvent.change(input, { target: { value: "晨光森林" } });

    const genBtn = screen.getByRole("button", { name: /生成背景/i });
    await act(async () => {
      fireEvent.click(genBtn);
    });

    expect(screen.getByText(/生成失敗：免費繪圖端點連線逾時/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /重新生成/i })).toBeInTheDocument();
  });
});

describe("M3.11 User Story 3: 物體與裝飾圖片生成功能", () => {
  it("FR-007: 支援輸入「物件語意特徵」，採用去背專屬句式產生具備透明背景之獨立物體", async () => {
    const handleGenerate = vi.fn().mockImplementation((features, category) => {
      return Promise.resolve({
        id: "obj_gen_01",
        name: "發光的藍色能量水晶",
        category: category || "prop",
        rarity: "epic",
        image_url: "data:image/svg+xml;utf8,<svg id='preview-obj'></svg>",
        has_transparency: true,
        semantic_features: features,
        is_user_generated: true,
        in_gacha_pool: false,
        hidden: false,
      } as VisualItem);
    });

    render(<ObjectGenerator onGenerate={handleGenerate} onSave={vi.fn()} />);

    const input = screen.getByLabelText(/物件語意特徵/i);
    fireEvent.change(input, {
      target: { value: "發光的藍色能量水晶獎盃，帶有星塵粒子" },
    });

    const genBtn = screen.getByRole("button", { name: /生成物體/i });
    await act(async () => {
      fireEvent.click(genBtn);
    });

    expect(handleGenerate).toHaveBeenCalledTimes(1);

    // Verify checkerboard transparency container is rendered
    const checkerboard = screen.getByTestId("transparency-checkerboard");
    expect(checkerboard).toBeInTheDocument();
  });

  it("FR-007: 物件支援選擇物品分類（徽章/裝飾）並儲存至背包", async () => {
    const handleSave = vi.fn();
    const mockItem: VisualItem = {
      id: "obj_gen_02",
      name: "心流印記徽章",
      description: "象徵內心平穩專注的玉石徽章",
      category: "badge",
      rarity: "rare",
      image_url: "data:image/svg+xml;utf8,<svg></svg>",
      has_transparency: true,
      semantic_features: "綠色蓮花微光徽章",
      is_user_generated: true,
      in_gacha_pool: false,
      hidden: false,
    };

    render(
      <ObjectGenerator
        initialItem={mockItem}
        onGenerate={vi.fn()}
        onSave={handleSave}
      />
    );

    const gachaCheckbox = screen.getByLabelText(/投入抽獎池/i);
    fireEvent.click(gachaCheckbox);

    const saveBtn = screen.getByRole("button", { name: /收進背包/i });
    fireEvent.click(saveBtn);

    expect(handleSave).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "obj_gen_02",
        category: "badge",
        has_transparency: true,
        in_gacha_pool: true,
      })
    );
  });
});
