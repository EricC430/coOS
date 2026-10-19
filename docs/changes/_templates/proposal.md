# <change-id>:<一句話標題>

**狀態**:`proposed`  <!-- proposed → approved → implementing → done → archived -->
**Track**:`T2 Change` / `T3 New Module`
**模組**:`Mx.y`, `Mx.z`
**標籤**:`[MVP]` / `[進階]`
**分支**:`feat/<change-id>`
**提出**:YYYY-MM-DD **拍板**:YYYY-MM-DD

## Why (為什麼要改)

1~3 句。描述問題或機會,不描述解法。若來自既有報告,寫出 `DEVIATION-xx` / `GAP-xx`。

## What Changes (改什麼)

- 條列行為層面的變化,不寫實作細節。
- 標註 **BREAKING** 的項目 (API 契約、schema、使用者可見流程改變)。

## Impact (影響)

| 類型 | 項目 |
| ---- | ---- |
| 受影響 SPEC | `docs/modules/Mx_y_*_SPEC.md` (delta: `specs/Mx_y_*_SPEC.delta.md`) |
| 程式碼 | `services/mx_y_*/…`、`apps/desktop/src/components/mx_y_*/…` |
| API | `POST /api/mx_y/...` |
| 資料表 / migration | `mx_y_...` (需使用者審 migration) |
| 文件 | `04` / `05` / `06` 哪些段落要同步 |

## 研究依據

| 引用 | 用途 |
| ---- | ---- |
| `[Rxx: 關鍵字 §章節]` | 此 change 的哪個決策依據它 |

若此 change **鬆綁**任何研究約束,在此明寫「鬆綁 [Rxx §y]:原因」,並列入下方拍板項。無研究依據時寫「無 (工程 / 產品決策)」。

## 整合風險 (audit-integration 結果)

- **觸及模組**:Mx.y, Mx.z
- **觸發的 RISK**:
  - `RISK-xx` — 緩解:已實作 / 本 change 實作 → 測試 `test_...`
- **未觸發但相關**:`RISK-yy` (理由)
- **新發現的風險**:無 / 已新增 `RISK-zz` 至 `05_integration_risk_audit.md`

## 憲章檢查

- [ ] 不涉及 L1 明文上雲 (或已說明如何經 M2.2.2 + M2.3)
- [ ] 不自動核准草稿、不繞過 XP 守門
- [ ] 不移除微摩擦
- [ ] MVP 不硬依賴進階模組

## Out of Scope (本 change 不做)

- 明確列出相關但不在這次處理的事,避免範圍蔓延。

## 後續 (實作中發現、留給之後的 change)

- (實作中追加)

## 拍板項

<!-- 最多 5 個;每個附建議。拍板後改寫成「拍板:…(日期)」 -->

- [NEEDS DECISION] 問題 1?建議:…,理由:…
