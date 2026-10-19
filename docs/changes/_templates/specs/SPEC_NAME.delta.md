# Delta:`docs/modules/<SPEC 檔名>`

> 只寫**有變的需求**。歸檔時由 `archive-change` skill 合併回 SPEC 的 §6。
> 需求編號 `REQ-Mx.y-NN`:沿用 SPEC 既有編號;SPEC 尚無編號時,從 01 開始並在 MODIFIED 段把舊驗收條目對應過來。
> 每條需求用 **SHALL / MUST** 敘述可驗證的行為,至少一個 `WHEN / THEN` 情境;情境 = 測試。

## ADDED Requirements

### REQ-Mx.y-NN:<需求名稱>

系統 SHALL <可觀察、可測試的行為>。

依據:`[Rxx: 關鍵字 §章節]` (無則省略) 風險:`RISK-xx` (無則省略)

#### Scenario:<情境名稱>

- **GIVEN** <前置狀態>
- **WHEN** <觸發>
- **THEN** <可斷言的結果>
- **AND** <額外斷言>

測試:`testing/mx_y/test_<name>.py::test_<scenario>`

## MODIFIED Requirements

<!-- 貼上「修改後的完整需求」,不要只寫差異;歸檔時整條取代舊需求 -->

### REQ-Mx.y-NN:<需求名稱>

系統 SHALL <新行為>。

變更前:<一句話描述舊行為,或引用 SPEC 舊段落 §x.y>
變更理由:<對應 proposal Why>

#### Scenario:<情境名稱>

- **WHEN** …
- **THEN** …

## REMOVED Requirements

### REQ-Mx.y-NN:<需求名稱>

**Reason**:為什麼移除
**Migration**:既有資料 / 呼叫端如何處理;要刪掉哪些測試
