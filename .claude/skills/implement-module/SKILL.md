---
name: implement-module
description: Use this skill whenever the user asks to implement or build a coOS module or feature identified by a Mx.y code (e.g. "實作 M4.2", "build the M3.3.3 reflection modal", "開始做 M4.7a"), or to carry out an approved change in docs/changes/<change-id>/. It runs DEV_WORKFLOW P4-P6: TDD per task (red → green → refactor), verification with fresh evidence, and constitution self-review. If there is no approved change or SPEC yet, it routes to the propose-change skill first.
---

# Skill: Implement Module (DEV_WORKFLOW P4–P6)

完整規則見 `docs/DEV_WORKFLOW.md`。本 skill 只負責「已核准的東西怎麼做對、怎麼證明做對」。

## 0. 入口檢查 — 有沒有可以實作的東西?

```bash
ls docs/changes/ | grep -i "m4-2"                 # 進行中的 change
grep -n "^\*\*狀態" docs/changes/*/proposal.md     # 是否 approved
ls docs/modules/ | grep -i "M4_2"                  # SPEC 是否存在
```

| 情況 | 動作 |
| ---- | ---- |
| 有 `approved` change 且 `tasks.md` 已完成一致性分析 | 繼續 §1 |
| 有 change 但未 approved / 沒有 tasks.md | 回 skill `propose-change` 從缺的步驟接續 |
| 沒有 change,SPEC 狀態 `approved`/`implemented`,且要做的是 SPEC 已定義、尚未實作的需求 | 開一個 T2 change (需求不變,delta 可為空,只需 proposal + tasks) → `propose-change` |
| 沒有 SPEC 或 SPEC 為 `draft` | T3 → `propose-change` |
| 只是修 bug (SPEC 已定義正確行為) | 不用本 skill,走 DEV_WORKFLOW §5 |
| 該模組是 `[進階]` | 確認 `docs/MVP_CLOSURE_REPORT.md` 最新判定為 **GO**;不是 GO → 停,告訴使用者 |

開始前:`git status` 確認分支是 `feat/<change-id>`;工作區有不相關的未提交改動 → 問使用者怎麼處理。

## 1. 逐任務 TDD (P4)

對 `tasks.md` 的每個任務,依序:

1. **Red** — 寫測試,執行該測試,**確認它被收集到並且因為「行為不存在 / 不對」而失敗**:

   ```bash
   cd services && .venv/Scripts/python.exe -m pytest ../testing/m4_2/test_x.py::test_y -q 2>&1 | tail -15
   pnpm --filter @coos/desktop exec vitest run tests/m3_2/X.test.tsx 2>&1 | tail -15
   ```

   失敗原因是 import 錯誤、路徑錯誤、`no tests ran` → 先修測試本身,不算 Red。
2. **Green** — 最小實作讓它通過。
3. **Refactor** — 整理,保持綠燈。
4. 勾 `tasks.md`,commit (DEV_WORKFLOW §7 格式,body 寫 change-id 與 REQ 編號)。

### 路徑 (以實際目錄為準)

| 類型 | 位置 |
| ---- | ---- |
| 後端模組 | `services/mx_y_<name>/` (例 `services/m4_2_persona/`) |
| 後端測試 | `testing/mx_y/test_<name>.py` (例 `testing/m4_2/`) — **不是** `tests/`、不是 `services/tests/` |
| API 掛載 | `services/main.py`,路徑 `/api/mx_y/...` |
| 前端元件 | `apps/desktop/src/components/mx_y_<name>/` |
| 前端測試 | `apps/desktop/tests/mx_y/<Name>.test.tsx` — **不是** `src/` 底下 |
| 資料表 | `mx_y_<name>` |

### 標註

- 新檔案標頭:

  ```python
  """
  M4.2 — 擬真人設與心理狀態機
  SPEC: docs/modules/M4_2_persona_state_machine_SPEC.md
  Change: <change-id>
  """
  ```

- **研究推導的**邏輯才加 `[Rxx: 關鍵字 §章節]` (遵守 skill `cite-research`);CRUD、接線、UI 不必加。
- 整合風險測試加 `@pytest.mark.integration_risk("RISK-xx")`。

### 實作中的規則

- 發現 delta 寫錯 / 寫漏 → **先改 delta**,行為有實質變化就回 G1 問使用者,再改程式碼。
- 使用者臨時追加需求 → 記到 `proposal.md`「後續」,問使用者要另開 change 還是更新本 change (更新 = 先改 proposal/delta)。不要直接做,也不要直接拒絕。
- 想放寬測試斷言 → 那是改需求,回 P2。
- 禁止靜默吞例外;跨模組互動寫 `raw_tracking_logs`。
- 同一測試 3 次嘗試仍失敗 → 停,改走系統化除錯 (DEV_WORKFLOW §5;有 Superpowers 時用 `systematic-debugging`),仍無解就回報使用者。

## 2. 驗證 (P5) — 沒有新鮮證據不准說完成

```bash
cd services && .venv/Scripts/python.exe -m pytest ../testing/ --ignore=../testing/local_llm --ignore=../testing/m0_2 -q 2>&1 | tail -15
pnpm --filter @coos/desktop test 2>&1 | tail -15
cd services && uv run ruff check .
pnpm --filter @coos/desktop lint
```

- 跨模組:閉環測試通過 (參考 `testing/m4_5/test_mvp_closed_loop.py`)。
- API / UI 改動:實際呼叫一次 endpoint 或開 `coos-desktop` 預覽確認,並查 `raw_tracking_logs`。
- 測試數比 `tasks.md` 基線少 → 解釋原因。
- 失敗 → 修,不要回報「大致完成」。

## 3. 自審 (P6)

逐條對照 delta:每個情境都有測試與程式碼?有沒有做了 delta 沒寫的事?
再過一次 `proposal.md` 的憲章檢查與 DEV_WORKFLOW P6 清單。改動 > 300 行或跨 3+ 模組 → 建議使用者跑 `/code-review`。

## 4. 回報

```
## <change-id> 實作完成 (待歸檔)
- 任務:12/12 ✅
- 驗證:後端 470 passed / 0 failed / 21 skipped (基線 458);前端 42 passed;ruff 0、eslint 0
- 閉環:test_xxx_closed_loop ✅;實測 POST /api/m4_2/... → 200,raw_tracking_logs 有 m4_2.xxx
- 自審:憲章清單全勾;偏離 delta:無
- 後續:proposal.md「後續」有 2 項
下一步:執行 archive-change?
```

接著用 skill `archive-change` 進入 P7。

## 反模式

- ❌ 沒有 approved change / SPEC 就寫程式碼,即使「覺得知道」要做什麼
- ❌ 跳過 Red,或沒確認測試真的被執行就宣稱紅綠
- ❌ 程式碼先改,事後在 `SPEC_DEVIATION_REPORT` 補登
- ❌ 一個 commit 混多個任務或多個 change
- ❌ 只跑單一模組測試就宣稱完成
