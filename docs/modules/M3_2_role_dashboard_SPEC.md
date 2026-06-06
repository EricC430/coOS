# M3.2 — 角色儀表板 (Role-based Dashboard)

**標籤**:`[MVP]`
**版本**:`1.1`
**最後更新**:2026-06-03

## 1. Purpose

作為全域狀態切換中心與情境錨點,透過物理慣性輪盤、色溫背景過渡、短期記憶喚醒與活躍度熱圖四個層次,將「切換角色」從功能操作升格為具備儀式感的認知重置動作,降低角色間認知耗損。

### 1.1 線框圖對應 (軟體介面構想.pdf §3 Dashboard)

PDF 原稿確認以下三層版面結構:

```text
┌─────────────────────────────────────────────────────┐
│  Project      Role (最顯著)      Goal               │  ← Context Header (頂部 4 槽位)
│               Promises                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│                  Dashboard                          │  ← Dashboard Body (動態畫布)
│        (依當前角色渲染待辦/XP 進度/圖表)               │
│                                                     │
├─────────────────────────────────────────────────────┤
│  ◁  [諮商]  [學者]  【UNI】  [CSIE]  [FAMILY]  ▷  │  ← Role Carousel Dock (底部)
└─────────────────────────────────────────────────────┘
```

**Context Header 四槽位** (PDF 原稿手寫標示,注意: 04_module_registry.md 原記為「三槽位」,以此線框圖更正為四槽位):

- `Project` (左) — 當前角色的活躍專案名稱
- `Role` (正上中央,最顯著) — 當前角色身分標籤 (e.g. "UNI / 大學生")
- `Promises` (中) — 當前角色的短期承諾清單
- `Goal` (右) — 當前角色的長期目標

> ⚠️ **注意** 此處與 `04_module_registry.md §M3.2.3 M3.2.3.1` 所記「Bento Grid 三槽位: Project / Promises / Goal」不同。
> 線框圖明確顯示 `Role` 為第四個獨立槽位;後續 M6.3 查詢也需補上 `role.display_name` 欄位。

**Role Carousel 預設角色範例** (PDF 手繪,由左到右):

1. 諮商 — 帶動作感人像圖示
2. 學者 — 戴眼鏡人像圖示
3. **UNI** (大學生) — 位於正中央,尺寸最大,學士帽圖示;系統預設啟用角色
4. CSIE (資工系) — 使用筆電人像圖示
5. FAMILY (家庭) — 三個大小不一人像,象徵家庭成員

- 可使用滑鼠滾輪滾動前後切換

**Dashboard Body 渲染規則**:

- 頂部 Context Header 的 Project/Role/Promises/Goal 更新後,Dashboard Body 立即重新渲染
- 渲染內容依角色類型不同:學科角色 (CSIE) 渲染課業任務清單與 XP 進度;心理角色 (諮商) 渲染情緒日誌入口與 Persona 快速進入按鈕
- 空角色 (無任何專案/目標) 應顯示引導空狀態: "在 AI 幫手中描述你的目標,Dashboard 將自動填入"

### 1.2 Role 管理 UI（v1.1 新增）

Role Carousel 支援**長按**或**右上角 `⚙ 管理角色` 按鈕**進入管理模式：

```text
┌─────────────────────────────────────────────────────┐
│  Role 管理                                    [✕]   │
│─────────────────────────────────────────────────────│
│  ◁  [諮商 ✏]  [學者 ✏]  [UNI ✏]  [CSIE ✏]  ▷   │
│                     🗑️                             │ ← 選取角色後顯示刪除鈕
│─────────────────────────────────────────────────────│
│  [+ 新增角色]                                       │
│                                                     │
│  每位使用者最多 10 個角色                            │
└─────────────────────────────────────────────────────┘
```

**操作行為規範**：

- **`✏️` 編輯**（長按 Carousel 圖示或管理模式下點選）：開啟 `RoleEditModal`，可修改 `display_name`、`color_hex`（色票選擇器）、`icon_name`（圖示選擇器）、`avatar_url`；`slug` 不可修改
- **`🗑️` 刪除**（管理模式下選取角色後出現）：
  - 呼叫 `DELETE /api/m6_2/roles/{role_id}`（軟刪除）
  - M4.3 廣播 `ROLE_DELETED` 事件，前端移除該 Carousel 項目
  - 若刪除的是當前 active role，自動切換到 `sort_order` 最小的其他角色
  - Carousel 項目數降為 0 時顯示「你還沒有任何角色，點擊 + 建立第一個」
- **`[+ 新增角色]`**：開啟 `RoleCreateModal`

**`RoleCreateModal` 欄位**：

```text
┌──────────────────────────────────────────┐
│  建立新角色                               │
│                                          │
│  角色名稱 *                              │
│  ┌────────────────────────────────┐     │
│  │ 例：料理愛好者                  │     │
│  └────────────────────────────────┘     │
│                                          │
│  識別碼（自動生成，不可修改）            │
│  cooking_lover                           │
│                                          │
│  代表色     圖示                         │
│  [🟠][🟢][🔵] [👨‍🍳][📚][💼][🏠]…      │
│                                          │
│  [取消]              [建立角色]          │
└──────────────────────────────────────────┘
```

建立完成後：

1. 呼叫 `POST /api/m6_2/roles`
2. M4.3 初始化新角色沙盒（廣播 `ROLE_CREATED`）
3. Carousel 新增此角色圖示，自動 Snap to Center 切換進入
4. Dashboard Body 顯示空狀態引導：「新角色還沒有任何 AI 專家，前往 AI 幫手配對你的第一位專家」

## 2. References

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R08 | §一 認知負荷轉移與作者身分危機 | 角色切換儀式感設計:以視覺過渡降低多角色切換的認知恢復成本 |
| R08 | §五 意圖脫鉤與作者身分設計模式 | 儀式感本身作為「重新建立作者身分」的設計介入 |
| R09 | §第四章 SDT | 角色輪盤的自主選擇感滿足 SDT 的「自主」需求 |
| R06 | §第二章 數位表型探勘 | 一致性熱圖從行為紀錄反映使用者的數位表型 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M3.1 `currentRole` | `Role { id, name, themeColorPalette }` | `{ id: "csie_001", name: "資工系大學生", themeColorPalette: { primary: "#4A90D9" } }` |
| M6.3 `role_context_aggregates` (via API) | `{ role_id, projects: [], promises: [], goals: [] }` | 見 M6.3 SPEC |
| M6.4 `daily_reflections` 統計 (via API) | `{ date: string, activity_count: number }[]` | 熱圖資料,過去 365 天 |
| M3.1 `ROLE_SWITCHED` 事件 | `{ role_id, prev_role_id, timestamp }` | 觸發背景過渡動畫 |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M3.1 `switchRole` action | `role_id: string` | `"family_002"` |
| M3.1 廣播 `ROLE_SWITCHED` | `{ role_id, prev_role_id }` | 供 M3.3/M3.4 重新載入對應角色資料 |
| `raw_tracking_logs` (M0.4) | `{ source: "M3.2", event: "role_switched", role_id }` | 行為遙測 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M3.1** (全域狀態與佈局):提供 `currentRole`、`xpBalance`、`ROLE_SWITCHED` 事件
- **M6.3** (角色與情境鏈結資料表):提供 Bento Grid 三槽位資料 (Project / Promises / Goal)
- **M6.4** (日報反思核心實體):提供一致性熱圖的日期-活躍度統計

### 下游 (誰依賴我)

- **M3.3** (日報反思):角色切換後需重新載入對應角色的日報資料
- **M3.4** (AI 幫手):角色切換後需切換對應 Persona
- **M4.3** (角色情境隔離狀態機):M3.2 的切換手勢觸發 M4.3 的後端沙盒重置

## 5. Known Risks

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| RISK-06 | 角色切換時若 M4.3 後端沙盒重置延遲,前端已顯示新角色但後端仍用舊角色資料 | M3.2 在 `ROLE_SWITCHED` 廣播後,顯示 Skeleton UI 等待後端確認 `ROLE_CONTEXT_SYNCED` 事件,才渲染 Bento Grid 真實資料 |
| RISK-04 | 角色切換動畫期間若 XP 慶祝通知同步觸發,視覺層衝突 | 角色切換動畫期間 (< 500ms) 暫緩 L2 系統洞察通知派發;L1 即時慶祝 Toast 仍可通過 |

## 6. Acceptance Criteria

```typescript
// tests/m3_2/role_dashboard.test.ts

describe("M3.2.1 底部焦點橫向輪盤", () => {
  it("Carousel 滑動停頓後自動 Snap to Center 並派發 ROLE_SWITCHED", async () => {
    const { container } = render(<RoleFocusCarouselDock roles={mockRoles} />);
    const carousel = container.querySelector("[data-testid='role-carousel']");
    fireEvent.pointerDown(carousel, { clientX: 0 });
    fireEvent.pointerMove(carousel, { clientX: -150 });
    fireEvent.pointerUp(carousel);
    await waitFor(() => {
      expect(screen.getByTestId("center-role-icon")).toHaveAttribute(
        "data-role-id", "family_002"
      );
    });
  });

  it("中央 Icon 的 scale 比非中央 Icon 大至少 1.3 倍", () => {
    render(<RoleFocusCarouselDock roles={mockRoles} activeRoleId="csie_001" />);
    const centerScale = parseFloat(
      getComputedStyle(screen.getByTestId("active-role-icon")).transform
    );
    const sideScale = parseFloat(
      getComputedStyle(screen.getByTestId("side-role-icon")).transform
    );
    expect(centerScale / sideScale).toBeGreaterThanOrEqual(1.3);
  });
});

describe("M3.2.2 儀式感背景過渡引擎", () => {
  it("ROLE_SWITCHED 後 500ms 內完成色溫漸變", async () => {
    const { rerender } = render(
      <TransitionBackground roleId="csie_001" palette={csieTheme} />
    );
    const before = Date.now();
    rerender(<TransitionBackground roleId="family_002" palette={familyTheme} />);
    await waitFor(() => {
      const bg = document.body.style.background;
      expect(bg).toContain(familyTheme.primary);
    });
    expect(Date.now() - before).toBeLessThan(500);
  });

  it("Ambient Glow Filter 在切換期間對比度降低", async () => {
    render(<TransitionBackground roleId="csie_001" isTransitioning={true} />);
    const filter = getComputedStyle(
      screen.getByTestId("ambient-glow")
    ).backdropFilter;
    expect(filter).toContain("blur");
  });
});

describe("M3.2.3 短期記憶喚醒聚合區", () => {
  it("角色切換到 Bento Grid 顯示完成 ≤ 3 秒", async () => {
    const before = Date.now();
    render(<ContextHeaderAggregator roleId="csie_001" />);
    await waitFor(() => {
      expect(screen.queryByTestId("skeleton-loader")).not.toBeInTheDocument();
      expect(screen.getByTestId("project-slot")).toBeInTheDocument();
    });
    expect(Date.now() - before).toBeLessThan(3000);
  });

  it("資料載入前顯示 Skeleton UI 而非空白", () => {
    // 模擬慢速網路
    server.use(rest.get("/api/m6_3/role_context", (_req, res, ctx) =>
      res(ctx.delay(2000), ctx.json(mockContext))
    ));
    render(<ContextHeaderAggregator roleId="csie_001" />);
    expect(screen.getByTestId("skeleton-loader")).toBeInTheDocument();
  });
});

describe("M3.2.4 角色活躍度熱圖", () => {
  it("熱圖正確渲染 365 天格點", () => {
    render(<ConsistencyHeatmap data={mockHeatmapData} />);
    const cells = screen.getAllByTestId("heatmap-cell");
    expect(cells.length).toBe(365);
  });

  it("Tooltip Hover 顯示當日具體推進計數", async () => {
    render(<ConsistencyHeatmap data={mockHeatmapData} />);
    const cell = screen.getByTestId("heatmap-cell-2026-06-01");
    fireEvent.mouseEnter(cell);
    await waitFor(() => {
      expect(screen.getByTestId("heatmap-tooltip")).toHaveTextContent("3 項");
    });
  });

  it("四階色彩深淺映射正確 (0 次:灰,1-2:淺,3-5:中,6+:深)", () => {
    const cell0 = render(<HeatmapCell count={0} />).container.firstChild;
    const cell1 = render(<HeatmapCell count={1} />).container.firstChild;
    const cell6 = render(<HeatmapCell count={6} />).container.firstChild;
    expect(cell0).toHaveClass("heatmap-level-0");
    expect(cell1).toHaveClass("heatmap-level-1");
    expect(cell6).toHaveClass("heatmap-level-3");
  });
});
```

## 7. Implementation Notes

### 7.1 子模組結構

```
apps/web/src/components/m3_2_dashboard/
  ├── RoleFocusCarouselDock/      # M3.2.1
  │   ├── index.tsx
  │   └── useCarouselPhysics.ts   # 慣性滑動物理引擎
  ├── TransitionBackground/        # M3.2.2
  │   ├── index.tsx
  │   └── useColorTemperature.ts  # CSS 色溫插值
  ├── ContextHeaderAggregator/    # M3.2.3
  │   ├── index.tsx
  │   ├── BentoGrid.tsx
  │   └── useRoleContextCache.ts  # Pre-fetching Cache
  └── ConsistencyHeatmap/         # M3.2.4
      ├── index.tsx
      └── HeatmapCell.tsx
```

### 7.2 物理慣性滑動 (M3.2.1.1)

```typescript
// [R08 §一] 慣性滑動強化「主動選擇」的肌肉記憶感,加強 SDT 自主需求
export function useCarouselPhysics(itemWidth: number) {
  const velocity = useRef(0);
  const position = useRef(0);

  const onPointerMove = (delta: number) => {
    velocity.current = delta;
    position.current += delta;
  };

  const onPointerUp = () => {
    // 慣性衰減動畫 + Snap to nearest center
    const target = Math.round(position.current / itemWidth) * itemWidth;
    animateToTarget(position, target, velocity.current);
  };

  return { onPointerMove, onPointerUp };
}
```

### 7.3 色溫插值 (M3.2.2.2)

```typescript
// [R08 §一 認知耗損] 色溫漸變 500ms,避免瞬切造成視覺衝擊
export function useColorTemperature(
  fromPalette: ThemePalette,
  toPalette: ThemePalette,
  durationMs = 500
) {
  return useSpring({
    primary: toPalette.primary,
    secondary: toPalette.secondary,
    from: { primary: fromPalette.primary, secondary: fromPalette.secondary },
    config: { duration: durationMs },
  });
}
```

### 7.4 Pre-fetching Cache (M3.2.3.2)

在角色輪盤停頓時即開始預取鄰近角色的 Bento Grid 資料,不等 Snap 完成:

```typescript
// [R08 §五] 降低感知等待時間,維護「使用者是作者」的掌控感
function useRoleContextCache(adjacentRoleIds: string[]) {
  useEffect(() => {
    adjacentRoleIds.forEach((id) => {
      queryClient.prefetchQuery(["role_context", id], () =>
        fetchRoleContext(id)
      );
    });
  }, [adjacentRoleIds]);
}
```

### 7.5 異常處理

- Bento Grid API 逾時 (> 3s) → 顯示 Skeleton + 重試按鈕,不顯示空白
- 熱圖資料缺失某天 → 以 count=0 渲染灰色格點,不報錯
- 背景過渡動畫在低效能裝置 > 500ms → 偵測到 `prefers-reduced-motion` 時跳過動畫直接切換

## 8. Anti-patterns

- ❌ **不要在 Bento Grid 載入前顯示空白**。必須使用 Skeleton UI,避免版面跳動造成認知干擾 (引用 R08 §一)
- ❌ **不要讓角色切換瞬間完成 (0ms)**。缺少過渡動畫等於剝奪儀式感,使用者感受不到「切換語境」(引用 R08 §一認知恢復)
- ❌ **不要在 Carousel Snap 完成前就派發 ROLE_SWITCHED**。使用者停頓是意圖信號,動作中途派發事件會觸發 M4.3 不必要的後端切換 (引用 M3.2.1.3)
- ❌ **不要讓熱圖直接呈現原始 `raw_tracking_logs`**。必須先彙總為日期-計數格式,不可把 L1 明文資料暴露在前端元件

## 9. Open Questions

- [x] **角色數量上限是多少?** PDF 線框圖示範 5 個角色 (諮商/學者/UNI/CSIE/FAMILY);Carousel 若超過 8 個角色,是否需要摺疊或分頁? 目前上限10個，carousel滑動超過所有角色後到底就停止滑動，只會顯示連續的5~7個角色，角色切換時需左右動態滑動，並且中間的尺寸最大，越旁邊越小，可以進出邊界
- [ ] **Context Header 四槽位 (Project / Role / Promises / Goal) 的資料優先順序?** 若某角色同時有多個活躍 Project,顯示哪一個?是否有 pin 功能?
- [ ] **`Role` 槽位顯示的是 role.name 還是 role.display_name?** 需要與 M6.3 `roles` 表的欄位命名一致。
- [ ] **一致性熱圖的「推進計數」包含哪些事件?** (commit? 對話? 任務完成?) 需要 M1.x 遙測統一定義
- [ ] **色溫主題預設值由使用者設定還是系統自動分配?** 需要 M6.3 的 `theme_color_palette` 初始化策略
- [ ] **Dashboard Body 的可渲染 Widget 類型如何擴充?** 進階階段是否支援使用者拖曳自訂 Widget 排列?

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責
- [x] §2 至少 1 個 `Rxx` 引用 (R08, R09, R06)
- [x] §3 Schema 用 TypeScript
- [x] §4 依賴是真實模組編號
- [x] §5 grep 過 `05_integration_risk_audit.md` (RISK-06, RISK-04)
- [x] §6 測試涵蓋四個子模組
- [x] §8 至少 3 條反模式
- [x] §9 至少 4 個開放問題
