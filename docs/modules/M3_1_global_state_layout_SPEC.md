# M3.1 — 全域狀態與佈局 (Global State & Layout)

**標籤**:`[MVP]`
**版本**:`1.0`
**最後更新**:2026-06-03

## 1. Purpose

以 Zustand 作為唯一的前端真實資料來源 (Single Source of Truth),管理全域 UI 狀態變數,並透過 Pub/Sub 事件派發觸發全局重繪——讓角色切換、XP 更新等任意狀態變化在 100ms 內反映至所有訂閱元件。

## 2. References

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R08 | §一 認知負荷轉移 | 全域狀態集中管理,避免各元件自行維護狀態造成的認知不一致 |
| R09 | §第四章 SDT | `CurrentRole` 切換必須清晰呈現「自主選擇」感,需要快速響應支撐儀式感 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M3.2 角色切換手勢 | `{ action: "ROLE_SWITCH", role_id: string }` | `{ action: "ROLE_SWITCH", role_id: "csie_001" }` |
| M4.5 XP 結算事件 (via Tauri IPC) | `{ event: "XP_GRANTED", amount: number, new_total: number }` | `{ event: "XP_GRANTED", amount: 50, new_total: 1200 }` |
| M4.3 角色隔離狀態機 | `{ role_id: string, active_expert_id: string }` | `{ role_id: "csie_001", active_expert_id: "robert_001" }` |
| M0.2 Tauri SSE 通道 | 後端廣播的任意系統事件 | `{ type: "BREAKPOINT_DETECTED" }` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M3.2 訂閱 `ROLE_SWITCHED` | `{ role_id: string, prev_role_id: string, timestamp: number }` | `{ role_id: "family_002", prev_role_id: "csie_001" }` |
| M3.3 訂閱 `XP_BALANCE_CHANGED` | `{ xp_balance: number, level: number }` | `{ xp_balance: 1200, level: 5 }` |
| M3.4 訂閱 `ACTIVE_EXPERT_CHANGED` | `{ expert_id: string }` | `{ expert_id: "robert_001" }` |
| 所有訂閱元件 | Zustand store state snapshot | — |

## 4. Dependencies

### 上游 (我依賴誰)

- **M0.1** (Monorepo 結構):React/Vite 前端工作區已初始化,Zustand 可安裝
- **M0.2** (Tauri IPC):後端事件透過 SSE/WebSocket 推送到前端,M3.1 訂閱並更新 store

### 下游 (誰依賴我)

- **M3.2** (角色儀表板):訂閱 `currentRole`、`xpBalance`
- **M3.3** (日報反思):訂閱 `currentRole` 以過濾角色資料
- **M3.4** (AI 幫手):訂閱 `activeExpert`
- **M3.5** (成就展示):訂閱 `xpBalance`、`level`
- **M3.6** (工作流彈窗):訂閱 `currentRole`
- 幾乎所有 M3.x 元件

## 5. Known Risks

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| RISK-06 | `currentRole` 狀態若跨 Role 洩漏,M4.3 隔離失效 | M3.1 角色切換時必須觸發 M4.3 的 `role_context_flush`;`currentRole` 更新與 M4.3 沙盒重置必須在同一個 Zustand action 中執行 |

## 6. Acceptance Criteria

```typescript
// tests/m3_1/global_state.test.ts

describe("M3.1.1 全域變數管理", () => {
  it("初始化時 currentRole 預設為第一個角色", () => {
    const { currentRole } = useCoOSStore.getState();
    expect(currentRole).not.toBeNull();
  });

  it("dispatch ROLE_SWITCH 後 currentRole 在 100ms 內更新", async () => {
    const store = useCoOSStore.getState();
    const before = Date.now();
    store.switchRole("family_002");
    await waitFor(() => {
      expect(useCoOSStore.getState().currentRole.id).toBe("family_002");
    });
    expect(Date.now() - before).toBeLessThan(100);
  });

  it("XP_GRANTED 事件後 xpBalance 正確累加", () => {
    const store = useCoOSStore.getState();
    store.applyXPGrant({ amount: 50, new_total: 1200 });
    expect(useCoOSStore.getState().xpBalance).toBe(1200);
  });

  it("activeExpert 更新不影響其他狀態欄位", () => {
    const store = useCoOSStore.getState();
    const prevRole = store.currentRole;
    store.setActiveExpert("beth_002");
    expect(useCoOSStore.getState().currentRole).toEqual(prevRole);
  });
});

describe("M3.1.2 Pub/Sub 事件派發", () => {
  it("switchRole 必須廣播 ROLE_SWITCHED 事件給所有訂閱者", () => {
    const listener = vi.fn();
    useCoOSStore.subscribe(
      (state) => state.currentRole,
      listener
    );
    useCoOSStore.getState().switchRole("csie_001");
    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener.mock.calls[0][0].id).toBe("csie_001");
  });

  it("同一 role_id 重複切換不觸發重繪 (避免無謂渲染)", () => {
    const store = useCoOSStore.getState();
    store.switchRole("csie_001");
    const listener = vi.fn();
    useCoOSStore.subscribe((state) => state.currentRole, listener);
    store.switchRole("csie_001"); // 相同角色
    expect(listener).not.toHaveBeenCalled();
  });
});
```

## 7. Implementation Notes

### 7.1 Store 定義

```typescript
// apps/web/src/stores/m3_1_global_store.ts
import { create } from "zustand";
import { subscribeWithSelector } from "zustand/middleware";

interface Role {
  id: string;
  name: string;
  themeColorPalette: Record<string, string>;
}

interface Expert {
  id: string;
  expertName: string;
  personalityPrompt: string;
  trustLevel: number;
}

interface CoOSState {
  currentRole: Role | null;
  xpBalance: number;
  level: number;
  activeExpert: Expert | null;

  // Actions
  switchRole: (roleId: string) => void;
  applyXPGrant: (payload: { amount: number; new_total: number }) => void;
  setActiveExpert: (expertId: string) => void;
}

export const useCoOSStore = create<CoOSState>()(
  subscribeWithSelector((set, get) => ({
    currentRole: null,
    xpBalance: 0,
    level: 1,
    activeExpert: null,

    switchRole: (roleId) => {
      const current = get().currentRole;
      // [RISK-06] 相同角色不重複觸發,避免不必要的 M4.3 沙盒重置
      if (current?.id === roleId) return;
      // 實際角色資料從 M6.3 快取取得 (由 M3.2 預快取注入)
      const role = getRoleFromCache(roleId);
      set({ currentRole: role });
    },

    applyXPGrant: ({ new_total }) => {
      // level 計算公式由 M6.5 定義,前端只做顯示
      const level = computeLevel(new_total);
      set({ xpBalance: new_total, level });
    },

    setActiveExpert: (expertId) => {
      const expert = getExpertFromCache(expertId);
      set({ activeExpert: expert });
    },
  }))
);
```

### 7.2 Tauri 事件橋接

```typescript
// apps/web/src/stores/m3_1_tauri_bridge.ts
import { listen } from "@tauri-apps/api/event";
import { useCoOSStore } from "./m3_1_global_store";

export async function initTauriBridge() {
  // 後端 XP 事件橋接
  await listen<{ amount: number; new_total: number }>("XP_GRANTED", (e) => {
    useCoOSStore.getState().applyXPGrant(e.payload);
  });

  // 後端角色同步 (M4.3 主導切換時)
  await listen<{ role_id: string; active_expert_id: string }>(
    "ROLE_CONTEXT_SYNCED", (e) => {
      useCoOSStore.getState().switchRole(e.payload.role_id);
      useCoOSStore.getState().setActiveExpert(e.payload.active_expert_id);
    }
  );
}
```

### 7.3 異常處理

- `getRoleFromCache` 找不到角色 → 維持現有 `currentRole`,記錄 warning 至 `raw_tracking_logs`
- Tauri bridge 連線斷線 → 前端繼續以最後已知狀態運作,重連後重新同步
- `computeLevel` 收到負值 xp → 強制 level = 1,不允許負 level

## 8. Anti-patterns

- ❌ **不要在各個元件內維護自己的 `currentRole` local state**。角色資料必須從 `useCoOSStore` 訂閱,否則角色切換時部分元件不會重繪 (引用 RISK-06)
- ❌ **不要讓 M3.1 直接讀取 DB**。Store 只持有記憶體狀態,DB 讀寫由 M6.x 負責,透過 Tauri IPC 事件橋接進 Store
- ❌ **不要在 switchRole 中做任何非同步 API 呼叫**。Store action 必須同步,以確保 100ms 切換 SLA。非同步的角色資料預快取由 M3.2.3.2 負責
- ❌ **不要直接 `setState({ currentRole: ... })` 繞過 switchRole action**,否則 RISK-06 的沙盒重置邏輯不會執行

## 9. Open Questions

- [ ] **`computeLevel` 的等級計算公式由誰定義?** 目前暫由前端硬編碼,是否統一由 M6.5 透過 API 提供?
- [ ] **多視窗/多頁籤場景下,Zustand store 是否需要跨 tab 同步?** (Tauri 應用理論上單視窗,但需確認)
- [ ] **角色資料快取的 TTL 是多少?** 若使用者在 M3.2 修改了角色主題色,何時失效並重新拉取?

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責,不能拆解
- [x] §2 至少 1 個 `Rxx` 引用
- [x] §3 Schema 用 TypeScript interfaces
- [x] §4 依賴是真實模組編號
- [x] §5 至少 grep 過 `05_integration_risk_audit.md`
- [x] §6 測試先於程式碼
- [x] §8 至少 3 條反模式
- [x] §9 至少 1 個開放問題
