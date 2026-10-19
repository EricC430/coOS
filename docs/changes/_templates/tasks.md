# Tasks:<change-id>

> 每個任務 = 一個測試 + 讓它通過的最小實作 (約 2~15 分鐘)。完成即勾選並 commit。
> 依賴順序:M6 資料層 → M4/M5 邏輯 → `services/main.py` 掛載 → M3 前端 → 閉環測試 → 文件。

**基線** (開始前實跑):後端 `___ passed / ___ failed / ___ skipped`,前端 `___ passed`

## 1. <階段名稱,例:資料層>

- [ ] **1.1** <任務> — `REQ-Mx.y-NN` / Scenario「…」
  - 測試:`testing/mx_y/test_<name>.py::test_<scenario>`
  - 檔案:`services/mx_y_<name>/<file>.py`
  - Red:`cd services && .venv/Scripts/python.exe -m pytest ../testing/mx_y/test_<name>.py::test_<scenario> -q` → 預期失敗原因:<例:AttributeError: no attribute 'limit_per_context'>
  - Green:同指令 → 1 passed

- [ ] **1.2** …

## 2. <階段名稱,例:整合與閉環>

- [ ] **2.1** 閉環測試:<端到端情境> — 參考 `testing/m4_5/test_mvp_closed_loop.py`

## 3. 驗證與歸檔

- [ ] **3.1** 後端全套、前端、lint 通過 (DEV_WORKFLOW §3 P5),數字填入下方
- [ ] **3.2** P6 憲章清單自審
- [ ] **3.3** `archive-change`:delta 合併、SPEC 版本、04/05/06、報告、移入 archive

**結果**:後端 `___ passed / ___ failed / ___ skipped`,前端 `___ passed`

---

## 一致性分析 (G2,開始實作前填完,不可有空格)

| 需求 / 情境 | 任務 | 測試 |
| ----------- | ---- | ---- |
| REQ-Mx.y-NN / Scenario「…」 | 1.1 | `test_<scenario>` |

| 觸發的 RISK | 測試 (`@pytest.mark.integration_risk`) |
| ----------- | -------------------------------------- |
| RISK-xx | `test_...` |

| REMOVED 需求 | 刪除任務 |
| ------------ | -------- |
| (無) | |

跨 2+ 模組? 是 / 否 → 閉環測試任務:2.1
