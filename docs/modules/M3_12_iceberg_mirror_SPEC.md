# M3.12 — 冰山之鏡 (Iceberg Mirror — 透明與控制)

**標籤**:`[進階]`
**版本**:`1.0` / `draft`
**最後更新**:2026-10-19
**設計來源**:`docs/M5_ICEBERG_REDESIGN.md` §9 (拍板 Q1、Q6)
**動工前提**:`docs/MVP_CLOSURE_REPORT.md` 存在

## 1. Purpose (目的)

讓使用者在**自己想看的時候**看見 coOS 目前對他的理解與依據,並能確認、修正、封存話題、調整碰撞強度、暫停或刪除 —— 這是「作用方式隱微,但存在不是祕密」的那條線。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R08 | §五 意圖脫鉤與作者身分五大設計模式 | 使用者保有對「關於自己的敘事」的最終作者權;AI 的理解是草稿,使用者可改寫 |
| R04 | §心理幻覺的定義與生成機制 | 「信心錯位」:以三段文字信心取代精確數字,避免形式上的確定感誤導使用者 |
| R20 | §個人冰山 | 每層的溫和呈現語句 |
| R04 | §反溯因推理的對抗性驗證 | 推理路徑旁並列存活的競爭假設「也可能是…」,把系統的不確定攤開 |
| R25 | §實驗結果 | 「對,就是這樣」是使用者自己確認的洞察,作為最強證據 |

## 3. Inputs / Outputs

### Inputs (全部經本地 sidecar `127.0.0.1:8000`,不經雲端)

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| `GET /api/m5_1/mirror?role_id=` | `MirrorResponse` | 見 §7.2 |
| `GET /api/m5_1/mirror/path/{hypothesis_id}` | `ReasoningPathResponse` | 見 §7.2;由 M5.1 `IcebergGraph.ancestor_paths()` 計算 |
| `GET /api/m5_1/mirror/evidence/{hypothesis_id}` | `EvidenceItem[]` | `[{date:"2026-10-12", source:"對話", excerpt:"問了就代表我不行"}]` |
| `GET /api/m5_4/changes?role_id=` | `ChangeSummary[]` | `[{theme_title, direction:"更常開口問人了"}]` |
| `GET /api/m5_1/settings` | `MirrorSettings` | `{engine_enabled:true, max_collision_dosage:2, paused_until:null}` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| `POST /api/m5_1/consent` | `{granted: boolean}` | 寫 `user_consents` (consent_type = `m5_iceberg`) |
| `POST /api/m5_1/mirror/{id}/feedback` | `{action: "yes" \| "not_quite" \| "not_at_all" \| "dont_touch"}` | → M5.1 `apply_user_feedback` |
| `PATCH /api/m5_1/settings` | `Partial<MirrorSettings>` | `{max_collision_dosage: 3}` |
| `DELETE /api/m5_1/all` | — | → M5.1 `purge_all` (二次確認) |

## 4. Dependencies

### 上游 (我依賴誰)

- **M5.1**:假設與證據;使用者回饋寫入;`IcebergGraph` 推理路徑
- **M5.4**:變化摘要;核心渴望 (`m5_4_core_yearnings`)
- **M3.1**:全域 store (目前角色)、路由
- **M3.4 / OnboardingScreen**:同意卡的入口

### 下游 (誰依賴我)

- **M5.5**:讀 `m5_settings` 與同意狀態 (由本模組的操作寫入)

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| RISK-21 | 不可證偽 | 「不太對 / 完全不是」是使用者側的反證通道,且權重高於系統推論 |
| RISK-23 | 跨角色 | 依目前角色篩選;cross_role 假設在每個相關角色都顯示,並標「在好幾個地方都看到」,但證據只列本角色的 |
| RISK-12 | 社群側通道 | 本頁無分享、截圖分享、匯出到社群的任何按鈕 |
| RISK-19 | 上雲 | 本頁所有 API 只打本地 sidecar;vitest 以 MSW 斷言無外部網域請求 |

## 6. Acceptance Criteria (驗收標準)

```typescript
// tests/m3_12/iceberg_mirror.test.tsx

describe("M3.12.1 同意流程", () => {
  it("未同意時只顯示同意卡,不顯示任何假設", async () => {
    mockConsent(false);
    render(<IcebergMirror />);
    expect(await screen.findByTestId("m5-consent-card")).toBeInTheDocument();
    expect(screen.queryByTestId("mirror-item")).toBeNull();
  });

  it("不同意也能正常使用其他功能,且不再主動詢問", async () => {
    mockConsent(false);
    render(<IcebergMirror />);
    fireEvent.click(screen.getByTestId("consent-decline"));
    await waitFor(() => expect(postConsent).toHaveBeenCalledWith({ granted: false }));
    expect(dashboardInviteShouldShow()).toBe(false);
  });
});

describe("M3.12.2 假設列表", () => {
  it("畫面上不出現任何心理學術語", async () => {
    render(<IcebergMirror />);
    const text = (await screen.findByTestId("mirror-list")).textContent ?? "";
    for (const t of ["冰山", "應對姿態", "討好型", "指責型", "超理智", "打岔", "渴望", "yearning"]) {
      expect(text).not.toContain(t);
    }
  });

  it("信心只以三段文字呈現,不顯示數字", async () => {
    mockMirror([{ confidence: 0.82 }]);
    render(<IcebergMirror />);
    expect(await screen.findByText("比較確定")).toBeInTheDocument();
    expect(screen.queryByText(/0\.82|82%/)).toBeNull();
  });

  it("refuted / user_rejected 預設不顯示", async () => {
    mockMirror([{ status: "refuted" }, { status: "working" }]);
    render(<IcebergMirror />);
    expect(await screen.findAllByTestId("mirror-item")).toHaveLength(1);
  });

  it("只顯示目前角色的證據", async () => {
    render(<IcebergMirror currentRole="r1" />);
    fireEvent.click(await screen.findByTestId("evidence-toggle"));
    expect(getEvidenceRequest().query.role_id).toBe("r1");
  });
});

describe("M3.12.2b 推理路徑「這個猜測是怎麼來的」", () => {
  it("路徑由淺到深排列,最後一步是被點開的那一條", async () => {
    mockPath("h_perception", [["h_beh", "h_stance", "h_feel", "h_perception"]]);
    render(<IcebergMirror />);
    fireEvent.click(await screen.findByTestId("path-toggle-h_perception"));
    const steps = screen.getAllByTestId("path-step");
    expect(steps.map((el) => el.dataset.layer)).toEqual(["behavior", "coping_stance", "feeling", "perception"]);
    expect(steps.at(-1)?.dataset.hypothesisId).toBe("h_perception");
  });

  it("最多顯示 2 條路徑", async () => {
    mockPath("h_y", [["a", "h_y"], ["b", "h_y"], ["c", "h_y"]]);
    render(<IcebergMirror />);
    fireEvent.click(await screen.findByTestId("path-toggle-h_y"));
    expect(screen.getAllByTestId("reasoning-path")).toHaveLength(2);
  });

  it("路徑上每一步都能展開證據", async () => {
    mockPath("h_perception", [["h_beh", "h_perception"]]);
    render(<IcebergMirror />);
    fireEvent.click(await screen.findByTestId("path-toggle-h_perception"));
    fireEvent.click(screen.getAllByTestId("path-step-evidence")[0]);
    await waitFor(() => expect(getEvidenceRequest().params.hypothesis_id).toBe("h_beh"));
  });

  it("有存活的競爭假設時顯示「也可能是」", async () => {
    mockPath("h_perception", [["h_beh", "h_perception"]], { rivalText: "你偏好先自己想清楚再問人" });
    render(<IcebergMirror />);
    fireEvent.click(await screen.findByTestId("path-toggle-h_perception"));
    expect(screen.getByTestId("path-rival")).toHaveTextContent("也可能是");
  });

  it("推理路徑不出現術語,也不出現 self 層", async () => {
    mockPath("h_y", [["h_beh", "h_stance", "h_y"]]);
    render(<IcebergMirror />);
    fireEvent.click(await screen.findByTestId("path-toggle-h_y"));
    const text = screen.getByTestId("reasoning-path").textContent ?? "";
    for (const t of ["冰山", "應對姿態", "超理智", "渴望", "yearning"]) expect(text).not.toContain(t);
    expect(screen.queryByTestId("path-step-self")).toBeNull();
  });

  it("核心渴望顯示「在好幾件事背後都看到它」", async () => {
    mockMirror([{ hypothesisId: "h_y", layer: "yearning", isCore: true }]);
    render(<IcebergMirror />);
    expect(await screen.findByText("在好幾件事背後都看到它")).toBeInTheDocument();
  });
});

describe("M3.12.3 回饋", () => {
  it("「完全不是」需要一次確認,送出後該項消失", async () => {
    render(<IcebergMirror />);
    fireEvent.click(await screen.findByTestId("feedback-not_at_all"));
    fireEvent.click(screen.getByTestId("confirm-not_at_all"));
    await waitFor(() => expect(screen.queryByTestId("mirror-item")).toBeNull());
  });
});

describe("M3.12.4 控制", () => {
  it("碰撞強度預設 2,可調到 3,不可超過 3", async () => {
    render(<IcebergMirror />);
    const slider = await screen.findByTestId("dosage-control");
    expect(slider).toHaveValue("2");
    expect(slider).toHaveAttribute("max", "3");
  });

  it("刪除全部需要輸入確認字樣", async () => {
    render(<IcebergMirror />);
    fireEvent.click(await screen.findByTestId("purge-all"));
    expect(screen.getByTestId("purge-confirm-submit")).toBeDisabled();
    fireEvent.change(screen.getByTestId("purge-confirm-input"), { target: { value: "刪除" } });
    expect(screen.getByTestId("purge-confirm-submit")).toBeEnabled();
  });

  it("本頁所有請求都只打本地 sidecar", async () => {
    render(<IcebergMirror />);
    await flush();
    expect(requestedHosts()).toEqual(new Set(["127.0.0.1:8000"]));
  });
});
```

## 7. Implementation Notes

### 7.1 子模組結構與入口

```
apps/desktop/src/components/m3_12_iceberg_mirror/
├── index.tsx                 # 頁面容器
├── ConsentCard.tsx           # M3.12.1
├── MirrorList.tsx            # M3.12.2,依主題分組
├── MirrorItem.tsx            # 單條理解 + 信心 + 回饋按鈕
├── ReasoningPathDrawer.tsx   # 「這個猜測是怎麼來的」:推理路徑 + 競爭假設
├── EvidenceList.tsx          # 路徑上單一步驟的證據 (日期 + 來源 + 本地原文)
├── RecentChanges.tsx         # M5.4 變化摘要
└── MirrorControls.tsx        # M3.12.4
```

**入口**:SettingsModal 新增「coOS 怎麼理解你」分頁。**系統不推播、不在其他畫面放紅點**。
**同意卡出現的時機** (我的判斷):新使用者在 OnboardingScreen 最後一步;既有使用者在 P1 上線後於儀表板顯示**一次**可關閉的邀請卡。拒絕或關閉後不再出現,只能從設定頁開啟。

同意卡文案 (定稿前需使用者審):
> coOS 會在背景慢慢形成對你的理解 —— 例如你遇到困難時通常怎麼反應、什麼對你很重要 —— 並據此調整專家陪伴你的方式。這些理解**只存在你的電腦**,你隨時可以在這裡查看、修正、刪除或暫停。
> [好,開始吧] [先不要]

### 7.2 資料結構

```typescript
type ConfidenceBand = "還在猜" | "有點把握" | "比較確定";   // <0.5 / 0.5–0.75 / >0.75

interface MirrorItem {
  hypothesisId: string;
  themeId: string | null;
  displayText: string;          // 後端以層模板改寫,見 §7.3
  band: ConfidenceBand;
  crossRole: boolean;
  evidenceCount: number;
  isCore: boolean;              // 核心渴望 (M5.4.4),只對 yearning 有意義
}

interface PathStep {
  hypothesisId: string;
  layer: "behavior" | "coping_stance" | "feeling" | "meta_feeling" | "perception" | "expectation" | "yearning";
  displayText: string;          // 同 §7.3 層模板
  band: ConfidenceBand;
  evidenceCount: number;
}

interface ReasoningPath {
  steps: PathStep[];            // 由淺到深;最後一步 = 被查詢的假設
  strengthBand: ConfidenceBand; // 整條路徑強度 (節點 × 邊 confidence 連乘) 的三段呈現
}

interface ReasoningPathResponse {
  paths: ReasoningPath[];       // 最強的 1–2 條;behavior 層或無祖先時為 []
  rivalText: string | null;     // 同 rival_group 存活的競爭假設 displayText
}

interface MirrorTheme {
  themeId: string;
  title: string;                // external_name 優先,否則以該主題 perception 的 displayText
  items: MirrorItem[];          // 由淺到深排序
  isSensitive: boolean;
}

interface MirrorResponse { themes: MirrorTheme[]; ungrouped: MirrorItem[]; }

interface MirrorSettings {
  engineEnabled: boolean;
  maxCollisionDosage: 1 | 2 | 3;   // 預設 2 (拍板 Q6)
  pausedUntil: string | null;
}
```

### 7.3 呈現語言 (後端 `m5_1` 以層模板產生 `displayText`,前端不做任何改寫)

| 層 | 模板 | 例 |
| -- | ---- | -- |
| behavior | 「我們注意到:{content}」 | 我們注意到:卡關時常常一個人撐很久 |
| coping_stance | 「壓力大的時候,你好像常會{描述}」 | …常會先把感覺放一邊,只談事情 |
| feeling | 「這類時候,你可能會覺得{content}」 | …可能會覺得挫折、有點丟臉 |
| perception | 「你心裡也許有個想法:「{content}」」 | …「問了就代表我不夠好」 |
| expectation | 「你可能期待自己{content}」 | …期待自己什麼都能自己搞定 |
| yearning | 「也許對你來說,{content}很重要」 | …被肯定、被接納很重要 |
| self | 不顯示 (只作系統內部工作假設;使用者主動提及時才以 user_stated 呈現) | — |

coping_stance 的 `{描述}` 由固定對照表產生 (placating → 先照顧別人的感受、blaming → 覺得是外面出了問題、super_reasonable → 先把感覺放一邊,只談事情、irrelevant → 先轉去做別的事),**絕不出現姿態名稱**。

回饋按鈕文字:`對,就是這樣` · `不太對` · `完全不是` · `這個先不要碰`。

### 7.3b 推理路徑的組成規則

- 後端以 `IcebergGraph.ancestor_paths(hypothesis_id, role_id, min_status="working", limit=2)` 取最強路徑 (路徑強度 = 節點與邊 confidence 連乘),只在**目前角色子圖**內找 (RISK-23)
- 路徑不含 `self` 層、`refuted` / `user_rejected` 節點
- 同層多個節點只保留路徑上那一個;`meta_feeling` 與 `feeling` 視為同一步呈現
- `rivalText`:同 `rival_group` 中 status 為 working+ 且未 refuted 的其他假設,取信心最高者;無則 null
- 被查詢的假設本身為 behavior,或沒有任何 working+ 祖先 → `paths = []`,前端只顯示證據列表
- 使用者對路徑上任一步按「不太對 / 完全不是」,與在列表上按效果相同;路徑隨即重算

### 7.4 視覺

遵循 `docs/BRAND_GUIDE.md`:`card` 底、內文 IBM Plex Sans;信心以文字 + 低飽和 `terracotta` 小標籤呈現,不用進度條或百分比 (避免把「了解自己」做成分數)。推理路徑以垂直細線串起各步、由上 (淺) 到下 (深),不畫成節點網狀圖 (避免像技能樹);「也可能是…」以同層級字體呈現在路徑下方,不弱化成灰色小字。主題卡片可展開;深層項目 (yearning) 以較淺的文字色與縮排呈現,傳達「這是比較深的猜測」。新增元素先檢查明度對比 (品牌指南「教訓」一節)。

### 7.5 異常處理

- sidecar 未啟動 → 顯示「目前無法讀取」,不顯示快取 (避免呈現過期的理解)
- 證據原文已被使用者刪除 → 證據列顯示「(原始紀錄已刪除)」,並觸發 M5.1 重算
- 刪除全部失敗 → 明確告知失敗並保留重試,不可靜默

## 8. Anti-patterns (反模式)

- ❌ 不要推播「我們對你有新的理解了!」或在任何畫面放提示紅點 (冰山之鏡只在使用者主動打開時存在)
- ❌ 不要顯示精確信心數字或百分比 (R04 §心理幻覺:信心錯位)
- ❌ 不要提供分享、匯出到社群、截圖分享 (RISK-12)
- ❌ 不要把冰山理解畫成可點亮、可升級的遊戲圖 (M3.10 已排除;「自我」不遊戲化)
- ❌ 不要在前端改寫 `displayText` 或拼接 content (所有語言控制集中在後端模板,才能測試)
- ❌ 不要把整張冰山圖以網狀圖呈現 (只呈現被點開那一條的路徑;整張圖會變成「你的心理地圖」式的診斷感)

## 9. Open Questions

- [ ] 同意卡文案與四個回饋按鈕的措辭,需使用者親自審定 (這是使用者與系統之間最重要的一句話)
- [ ] 「也可能是…」若讓使用者困惑,是否改為只在信心「還在猜」時顯示 —— P1 實測後決定
- [ ] 「最近的變化」是否在變化尚未穩定 (階段 < new_status_quo) 時就顯示?建議只顯示 new_status_quo 的主題,避免過早宣告

---

## SPEC 撰寫 Checklist

- [x] §1 單一職責
- [x] §2 至少 1 個 Rxx 引用
- [x] §3 Schema 為 TypeScript
- [x] §4 依賴為真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`
- [x] §6 測試先於程式碼
- [x] §8 ≥3 條反模式
- [x] §9 ≥1 個開放問題
