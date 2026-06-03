# M3.10 — 技能樹與知識網狀圖 (Skill Tree & Knowledge Graph Visualization)

**標籤**:`[進階]`
**版本**:`1.0`
**最後更新**:2026-06-03

> **MVP 策略**：Phase 1~5 不動工。**硬性前置依賴 M5.1（薩提爾圖譜寫入器）**——M5.1 必須先有 Neo4j 節點資料，M3.10 才有東西可視覺化。需等 M5.1 穩定後才可動工。

## 1. Purpose

將 M5.1 寫入 Neo4j 的薩提爾冰山節點（Behavior → Feeling → Yearning）與使用者的技能成長軌跡，以可互動的拓樸網狀圖呈現——讓抽象的「自我認識」和「能力成長」有具體的視覺形態，使節點點亮的瞬間成為強烈的進步回饋。

## 2. References

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R04 | §拓樸演化 GraphRAG | M3.10 視覺化的資料結構直接對應 M5.1 的 DGNN 節點／邊 schema；圖形佈局演算法採用力導向（Force-Directed）以反映動態圖結構 |
| R04 | §冰山本體論化 | 節點分層：技能節點（顯性）對應 Behavior；目標節點對應 Yearning；節點的深度顏色映射認知層次 |
| R09 | §第三章 HAIA 三階段 | 可互動的技能樹強化 HAIA 第二階段「依附」——使用者探索自己的圖譜本身就是一種自我賦能行為 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| `GET /api/m5_1/graph_nodes` | `GraphNode[] { id, label, type, confidence, unlocked_at? }` | `[{ id: "n_001", label: "K8s 部署", type: "skill", confidence: 0.8 }]` |
| `GET /api/m5_1/graph_edges` | `GraphEdge[] { source, target, relation, weight }` | `[{ source: "n_001", target: "n_002", relation: "ENABLES" }]` |
| M3.1 `currentRole` | `{ role_id: string }` | 過濾只顯示當前角色的子圖 |
| M4.12 WebSocket `SKILL_NODE_UNLOCKED` 事件 | `{ node_id: string }` | 即時點亮新解鎖節點 |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| 前端圖形渲染（純展示，無 DB 寫入） | SVG / Canvas 互動圖 | — |
| `raw_tracking_logs` (M0.4) | `{ source: "M3.10", event: "node_explored", node_id }` | 使用者點擊節點查看詳情 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M5.1** (薩提爾圖譜寫入器)：**硬性前置**。M3.10 無法在 M5.1 之前動工，無節點資料則圖譜為空
- **M3.1** (全域狀態)：提供 `currentRole` 以過濾顯示對應角色的子圖
- **M4.12** (隱藏成就驗證引擎，進階)：節點解鎖的即時廣播事件

### 下游 (誰依賴我)

- 無其他模組依賴 M3.10（純展示層）

## 5. Known Risks

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| （M5.1 前置風險） | M5.1 圖譜資料品質差（節點稀疏、邊缺失）→ 圖譜顯示為孤立節點或空圖，使用者困惑 | M3.10 在節點數 < 5 時顯示「你的知識網正在建立中」的引導狀態，而非空白 |
| （性能風險） | Neo4j 回傳大量節點（> 500 個）→ 力導向圖計算過重，渲染卡頓 | 首次載入限制 100 個節點，以當前角色的最活躍節點優先；使用 WebWorker 計算佈局，不阻塞主執行緒 |

## 6. Acceptance Criteria

```typescript
// tests/m3_10/skill_tree.test.ts

describe("M3.10 技能樹視覺化", () => {
  it("GraphNode 正確渲染為 SVG 節點，並依 type 分層著色", () => {
    render(<SkillTreeGraph nodes={mockNodes} edges={mockEdges} />);
    const skillNodes = screen.getAllByTestId("graph-node-skill");
    const goalNodes = screen.getAllByTestId("graph-node-yearning");
    expect(skillNodes.length).toBeGreaterThan(0);
    expect(goalNodes.length).toBeGreaterThan(0);
    // 不同類型節點顏色不同
    const skillColor = getComputedStyle(skillNodes[0]).fill;
    const goalColor = getComputedStyle(goalNodes[0]).fill;
    expect(skillColor).not.toBe(goalColor);
  });

  it("未解鎖節點以灰色半透明狀態顯示，不可點擊詳情", () => {
    render(<SkillTreeGraph nodes={[{ ...mockNode, unlocked_at: null }]} edges={[]} />);
    const lockedNode = screen.getByTestId("graph-node-locked");
    fireEvent.click(lockedNode);
    expect(screen.queryByTestId("node-detail-panel")).not.toBeInTheDocument();
  });

  it("SKILL_NODE_UNLOCKED WebSocket 事件觸發節點點亮動畫", async () => {
    const { emitWS } = setupWebSocketMock("/api/m4_12/events");
    render(<SkillTreeGraph nodes={mockNodes} edges={mockEdges} />);
    emitWS({ type: "SKILL_NODE_UNLOCKED", node_id: "n_001" });
    await waitFor(() => {
      expect(screen.getByTestId("graph-node-n_001")).toHaveClass("node-unlocked");
    });
  });

  it("節點數 < 5 時顯示引導狀態而非空圖", () => {
    render(<SkillTreeGraph nodes={mockNodes.slice(0, 2)} edges={[]} />);
    expect(screen.getByTestId("graph-onboarding-hint")).toBeInTheDocument();
  });

  it("currentRole 切換後重新拉取對應角色子圖", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({ nodes: [], edges: [] });
    render(<SkillTreeGraph onFetch={fetchSpy} roleId="csie_001" />);
    // 切換角色
    renderWithProps({ roleId: "family_002" });
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenLastCalledWith(
        expect.objectContaining({ role_id: "family_002" })
      );
    });
  });
});
```

## 7. Implementation Notes

### 7.1 子模組結構

M3.10 Registry 未列子模組，整個模組為單一視覺化元件：

```
apps/web/src/components/m3_10_skill_tree/
  ├── index.tsx                    # SkillTreeGraph 主元件
  ├── useGraphLayout.ts            # WebWorker 力導向佈局計算
  ├── GraphNode.tsx                # 單一節點渲染（依 type 分層）
  └── NodeDetailPanel.tsx          # 點擊節點後的側邊詳情面板
```

### 7.2 節點分層與著色

```typescript
// [R04 §冰山本體論化] 節點顏色映射認知層次
const NODE_LAYER_STYLES: Record<string, { color: string; opacity: number }> = {
  behavior:    { color: "#4A90D9", opacity: 1.0 },    // 顯性行為 — 藍
  coping:      { color: "#9B59B6", opacity: 0.9 },    // 應對姿態 — 紫
  feeling:     { color: "#E67E22", opacity: 0.85 },   // 情感 — 橙
  perception:  { color: "#27AE60", opacity: 0.8 },    // 認知 — 綠
  expectation: { color: "#F39C12", opacity: 0.75 },   // 期待 — 黃
  yearning:    { color: "#E74C3C", opacity: 0.9 },    // 渴望 — 紅
  self:        { color: "#ECF0F1", opacity: 1.0 },    // 核心自我 — 白，中央節點
};
```

### 7.3 WebWorker 力導向佈局

```typescript
// 防止大圖譜計算阻塞主執行緒
const worker = new Worker(new URL("./graphLayoutWorker.ts", import.meta.url));

function useGraphLayout(nodes: GraphNode[], edges: GraphEdge[]) {
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});
  useEffect(() => {
    worker.postMessage({ nodes, edges });
    worker.onmessage = (e) => setPositions(e.data.positions);
  }, [nodes, edges]);
  return positions;
}
```

### 7.4 異常處理

- M5.1 API 離線 → 顯示「知識圖譜暫時無法載入」，不影響其他 M3.x 頁面
- Neo4j 回傳節點 > 100 個 → 截斷並顯示「顯示最活躍的 100 個節點」提示，提供「查看全圖」按鈕（需另行確認）
- WebSocket 斷線 → 節點解鎖動畫降級為：下次頁面刷新時靜態更新節點狀態

## 8. Anti-patterns

- ❌ **不要在 M5.1 完成之前動工 M3.10**。沒有 Neo4j 節點資料，M3.10 只是一個空圖；且 M3.10 的節點 schema 必須與 M5.1 的 Cypher schema 嚴格對齊（R04 §冰山七大節點）
- ❌ **不要在主執行緒中計算力導向圖佈局**。超過 50 個節點的力導向計算會讓前端凍結；必須使用 WebWorker
- ❌ **不要讓 M3.10 直接查詢 Neo4j**。前端絕對不持有 Neo4j 連線；所有圖譜資料透過 FastAPI `GET /api/m5_1/graph_nodes` 取得，後端負責隱私過濾

## 9. Open Questions

- [ ] **技能樹中的「技能」節點定義由誰決定？** M5.1 的冰山節點以心理層次為主（Behavior / Feeling），但「技能樹」隱含技術能力的概念——兩者如何在同一個圖中共存需要定義
- [ ] **使用者是否可以手動新增節點？** 例如「我想學習 Rust」手動加入 Yearning 節點？這會涉及 M5.1 的寫入權限
- [ ] **圖譜資料的更新頻率如何？** 實時更新（每次 Observer 萃取後）還是每日批次重算？頻繁更新可能讓節點位置跳動，干擾使用者的空間記憶

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 單一職責：圖譜視覺化，不做計算
- [x] §2 至少 3 個 `Rxx §章節` 引用（R04×2, R09）
- [x] §3 Schema 對應 M5.1 的節點／邊格式
- [x] §4 M5.1 硬性前置依賴明確標注
- [x] §5 兩條自定義風險（資料品質 + 性能）
- [x] §6 測試含空圖引導、節點解鎖動畫、角色切換
- [x] §8 至少 3 條反模式含 M5.1 前置原則
- [x] §9 至少 3 個開放問題
