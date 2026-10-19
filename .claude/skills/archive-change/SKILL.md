---
name: archive-change
description: Use this skill after a coOS change in docs/changes/<change-id>/ is implemented, verified (all tests + lint green with evidence) and self-reviewed, to merge its spec deltas into docs/modules/*_SPEC.md, bump SPEC versions, sync 04/05/06 and the DEVIATION/GAP reports, and move the change into docs/changes/archive/. Trigger on "歸檔", "archive the change", "收尾", or when the last unchecked task in tasks.md is the archive step.
---

# Skill: Archive Change (DEV_WORKFLOW P7)

## 前置檢查 (任一不成立 → 停,回報缺什麼)

- [ ] `proposal.md` 狀態為 `approved` 或 `implementing`,沒有未拍板的 `[NEEDS DECISION]`
- [ ] `tasks.md` 除歸檔任務外全部勾選,一致性分析表無空格
- [ ] 本 session 內有**新鮮的**驗證輸出:後端全套、前端、lint (DEV_WORKFLOW §3 P5)。沒有就先跑,不要沿用舊數字
- [ ] P6 憲章清單已自審

## 步驟

### 1. 合併 delta → SPEC

對 `docs/changes/<id>/specs/` 下每一份 `<SPEC>.delta.md`:

| delta 段落 | 對 `docs/modules/<SPEC>` §6 的動作 |
| ---------- | ---------------------------------- |
| ADDED | 依編號插入新需求 (含情境與測試路徑) |
| MODIFIED | **整條取代**同編號需求;刪去「變更前 / 變更理由」行 (理由留在 archive) |
| REMOVED | 刪除該需求 |

- 若 SPEC 其他段落 (§3 I/O、§4 依賴、§5 風險、§7 實作註記、§8 反模式) 與新行為矛盾,一併修正。
- SPEC 舊格式 (無 `REQ-` 編號) 時:只把被觸及的驗收條目換成 `REQ-` 格式,其他原樣保留。

### 2. SPEC 標頭

- `版本`:行為變更 → MINOR+1;契約破壞 (API/schema 不相容) → MAJOR+1;只修文字 → PATCH+1
- `狀態`:實作並驗證完 → `implemented`
- `最後更新`:今天;`最後變更`:`<change-id>`
- `變更紀錄`表加一列

### 3. 同步全域文件 (只改受影響段落)

- `docs/04_module_registry.md`:標籤、依賴、Criteria 是否仍正確
- `docs/05_integration_risk_audit.md`:新 RISK 或緩解狀態;若 audit 判定「無風險組合」,記在「已審查無風險的組合」
- `docs/06_implementation_phases.md`:路線圖勾選
- `docs/SPEC_DEVIATION_REPORT.md` / `docs/IMPLEMENTATION_GAP_REPORT.md`:本 change 關閉的條目標 ✅ 並寫 change-id;更新報告上的測試數

### 4. 移入 archive

```bash
git mv docs/changes/<id> docs/changes/archive/$(date +%Y-%m-%d)-<id>   # 未追蹤時用 mv
```

- `proposal.md` 狀態改 `archived`
- `docs/changes/README.md` 進行中索引移除該列

### 5. 驗證歸檔本身

```bash
grep -rn "<change-id>" docs/modules/ docs/changes/README.md   # SPEC 變更紀錄有、索引沒有
grep -n "REQ-Mx.y-" docs/modules/<SPEC>                        # 新需求在 SPEC 裡
ls docs/changes/<id> 2>&1                                      # 應該已不存在
```

### 6. 收尾分支

列出選項讓使用者選,不要自己決定:

1. 在本分支 commit (`docs(mx.y): archive <change-id>`)
2. commit 並開 PR 到 `master`
3. 先保留,不 commit

**不自行 push、開 PR 或 merge**,除非使用者明確要求。

## 輸出範本

```
## 已歸檔:<change-id>
- SPEC:M4_4_…_SPEC.md 1.2.0 → 1.3.0 (MODIFIED REQ-M4.4-03, ADDED REQ-M4.4-07)
- 同步:04 (Criteria)、05 (RISK-04 緩解註記)、DEVIATION-01 ✅
- 驗證:後端 462 passed / 0 failed / 21 skipped;前端 40 passed;ruff/eslint 0
- 位置:docs/changes/archive/2026-10-19-<change-id>/
下一步要怎麼處理分支?(commit / PR / 保留)
```
