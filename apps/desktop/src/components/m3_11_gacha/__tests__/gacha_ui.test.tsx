import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { GachaDrawButton } from "../GachaDrawButton";
import { GachaResultToast } from "../GachaDrawButton/GachaResultToast";
import { AchievementGrid } from "../HiddenAchievement/AchievementGrid";
import { SurpriseModal } from "../HiddenAchievement/SurpriseModal";
import { HiddenAchievementListener } from "../HiddenAchievement/HiddenAchievementListener";
import { GachaPromotion } from "../GachaPromotion";
import { DrawChallengeButton } from "../DrawChallengeButton";
import {
  MOCK_USER_ITEMS,
  MOCK_HIDDEN_ACHIEVEMENT,
  MOCK_UNLOCKED_HIDDEN_ACHIEVEMENT,
  MOCK_ZPD_CHALLENGE,
  MockWebSocketClient,
} from "./mocks";
import { VisualItem } from "../types";

describe("M3.11 User Story 1: XP 盲盒抽獎與開獎系統", () => {
  it("FR-001: 顯示單次抽獎費用（100 XP）與使用者即時 XP 餘額", () => {
    render(
      <GachaDrawButton
        userXp={250}
        cost={100}
        onDraw={vi.fn()}
      />
    );
    expect(screen.getByText(/單次抽獎: 100 XP/)).toBeInTheDocument();
    expect(screen.getByText(/餘額: 250 XP/i)).toBeInTheDocument();
  });

  it("FR-002: XP 不足時（< 100 XP），抽獎按鈕禁用並提示餘額不足", () => {
    render(
      <GachaDrawButton
        userXp={60}
        cost={100}
        onDraw={vi.fn()}
      />
    );
    const btn = screen.getByRole("button", { name: /盲盒抽獎/i });
    expect(btn).toBeDisabled();
    expect(screen.getByText(/需要 100 XP（餘額不足）/i)).toBeInTheDocument();
  });

  it("FR-004: 抽獎成功時立即透過 L1 即時通道彈出 GachaResultToast 展示抽得物品", async () => {
    const handleDraw = vi.fn().mockResolvedValue({
      success: true,
      item: MOCK_USER_ITEMS[0],
      cost: 100,
      remaining_xp: 150,
    });

    render(
      <GachaDrawButton
        userXp={250}
        cost={100}
        onDraw={handleDraw}
      />
    );

    const btn = screen.getByRole("button", { name: /盲盒抽獎/i });
    await act(async () => {
      fireEvent.click(btn);
    });

    expect(handleDraw).toHaveBeenCalledTimes(1);

    // Verify Toast is rendered with immediate defer strategy
    const toast = screen.getByTestId("gacha-result-toast");
    expect(toast).toBeInTheDocument();
    expect(toast).toHaveAttribute("data-defer-strategy", "immediate");
    expect(screen.getByText(MOCK_USER_ITEMS[0].name)).toBeInTheDocument();
  });

  it("FR-003: 60 分鐘內連續抽獎達 5 次後強制鎖定按鈕並顯示剩餘冷卻時間", async () => {
    const now = Date.now();
    // Simulate 5 draws in the past 10 minutes
    const initialHistory = [
      now - 500000,
      now - 400000,
      now - 300000,
      now - 200000,
      now - 100000,
    ];

    render(
      <GachaDrawButton
        userXp={1000}
        cost={100}
        initialDrawHistory={initialHistory}
        onDraw={vi.fn()}
      />
    );

    const btn = screen.getByRole("button", { name: /盲盒抽獎/i });
    expect(btn).toBeDisabled();
    expect(screen.getByText(/已達 1 小時上限（5\/5）/i)).toBeInTheDocument();
  });

  it("FR-005: 支援切換「官方精選池」與「自創混合池」，自創作品可被抽取", async () => {
    const userCustomItem: VisualItem = {
      id: "user_bg_custom_01",
      name: "我的秘密基地",
      description: "自訂生成的賽博龐克工坊",
      category: "background",
      rarity: "epic",
      image_url: "data:image/svg+xml;utf8,<svg></svg>",
      has_transparency: false,
      is_user_generated: true,
      in_gacha_pool: true,
      hidden: false,
    };

    const handleDraw = vi.fn().mockImplementation((poolMode) => {
      return Promise.resolve({
        success: true,
        item: poolMode === "hybrid" ? userCustomItem : MOCK_USER_ITEMS[0],
        cost: 100,
        remaining_xp: 400,
      });
    });

    render(
      <GachaDrawButton
        userXp={500}
        cost={100}
        onDraw={handleDraw}
        userPoolItems={[userCustomItem]}
      />
    );

    // Switch to hybrid pool
    const poolToggle = screen.getByRole("button", { name: /切換為自創混合池/i });
    fireEvent.click(poolToggle);
    expect(screen.getByText(/目前獎池: 自創混合池/i)).toBeInTheDocument();

    const drawBtn = screen.getByRole("button", { name: /盲盒抽獎/i });
    await act(async () => {
      fireEvent.click(drawBtn);
    });

    expect(handleDraw).toHaveBeenCalledWith("hybrid");
    expect(screen.getByText("我的秘密基地")).toBeInTheDocument();
  });
});

describe("M3.11 User Story 5: 心理防護機制與隱藏成就", () => {
  it("FR-011: AchievementGrid 未解鎖之隱藏成就 0 洩漏（DOM 中絕無節點或問號佔位符）", () => {
    const items = [
      MOCK_USER_ITEMS[0],
      MOCK_HIDDEN_ACHIEVEMENT, // hidden: true, unlocked_at: null
    ];

    const { container } = render(<AchievementGrid items={items} />);

    // Normal item should be visible
    expect(screen.getByText(MOCK_USER_ITEMS[0].name)).toBeInTheDocument();

    // Hidden item must NOT be anywhere in DOM
    expect(screen.queryByText(MOCK_HIDDEN_ACHIEVEMENT.name)).toBeNull();
    expect(screen.queryByText(/量子躍遷/i)).toBeNull();
    expect(container.querySelectorAll('[data-testid="hidden-achievement-placeholder"]').length).toBe(0);
    expect(container.textContent).not.toContain("???");
  });

  it("FR-011: 已解鎖之隱藏成就在 AchievementGrid 中正常呈現", () => {
    const items = [MOCK_UNLOCKED_HIDDEN_ACHIEVEMENT];
    render(<AchievementGrid items={items} />);
    expect(screen.getByText(MOCK_UNLOCKED_HIDDEN_ACHIEVEMENT.name)).toBeInTheDocument();
  });

  it("FR-012: WebSocket 廣播 HIDDEN_ACHIEVEMENT_UNLOCKED 觸發 SurpriseModal，複數事件依序 FIFO 排隊", async () => {
    const ws = new MockWebSocketClient();
    render(<HiddenAchievementListener socket={ws as any} />);

    expect(screen.queryByTestId("surprise-modal")).toBeNull();

    // Send first hidden achievement
    act(() => {
      ws.emit({
        type: "HIDDEN_ACHIEVEMENT_UNLOCKED",
        item: MOCK_UNLOCKED_HIDDEN_ACHIEVEMENT,
      });
    });

    // Send second hidden achievement while first is displayed
    const secondAchievement: VisualItem = {
      ...MOCK_UNLOCKED_HIDDEN_ACHIEVEMENT,
      id: "ach_second_secret",
      name: "心流極致星辰勳章",
    };

    act(() => {
      ws.emit({
        type: "HIDDEN_ACHIEVEMENT_UNLOCKED",
        item: secondAchievement,
      });
    });

    // First modal should be visible
    expect(screen.getByTestId("surprise-modal")).toBeInTheDocument();
    expect(screen.getByText(MOCK_UNLOCKED_HIDDEN_ACHIEVEMENT.name)).toBeInTheDocument();
    expect(screen.queryByText("心流極致星辰勳章")).toBeNull();

    // Dismiss first modal
    const closeBtn = screen.getByRole("button", { name: /收下驚喜/i });
    fireEvent.click(closeBtn);

    // Second modal now surfaces from FIFO queue
    expect(screen.getByText("心流極致星辰勳章")).toBeInTheDocument();
  });

  it("FR-013: 焦慮/逃避/沮喪等隱性狀態下，GachaPromotion 促銷橫幅返回 null 徹底不渲染", () => {
    const { container: anxiousContainer } = render(
      <GachaPromotion implicitState={{ label: "anxiety" }} />
    );
    expect(anxiousContainer.firstChild).toBeNull();

    const { container: avoidanceContainer } = render(
      <GachaPromotion implicitState={{ label: "avoidance" }} />
    );
    expect(avoidanceContainer.firstChild).toBeNull();

    const { container: depressionContainer } = render(
      <GachaPromotion implicitState={{ label: "depression" }} />
    );
    expect(depressionContainer.firstChild).toBeNull();

    // When neutral or flow, promotion banner renders
    const { container: flowContainer } = render(
      <GachaPromotion implicitState={{ label: "flow" }} />
    );
    expect(flowContainer.firstChild).not.toBeNull();
    expect(screen.getByText(/今天手感絕佳！/i)).toBeInTheDocument();
  });

  it("FR-014: DrawChallengeButton 抽取 ZPD 任務，介面嚴格無 XP 質押（Stake）選項", async () => {
    const handleDrawChallenge = vi.fn().mockResolvedValue(MOCK_ZPD_CHALLENGE);

    render(<DrawChallengeButton onDrawChallenge={handleDrawChallenge} />);

    const challengeBtn = screen.getByRole("button", { name: /🎲 抽挑戰/i });
    await act(async () => {
      fireEvent.click(challengeBtn);
    });

    expect(handleDrawChallenge).toHaveBeenCalledTimes(1);
    expect(screen.getByText(MOCK_ZPD_CHALLENGE.title)).toBeInTheDocument();

    // Verify ABSOLUTELY NO staking inputs, bet sliders, or gamble terminology
    expect(screen.queryByPlaceholderText(/質押|stake|賭注/i)).toBeNull();
    expect(screen.queryByText(/質押|stake|賭注/i)).toBeNull();
  });
});
