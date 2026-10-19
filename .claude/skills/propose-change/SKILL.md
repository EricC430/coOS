---
name: propose-change
description: Use this skill when a coOS request would change, add, or remove behavior defined in a module SPEC (docs/modules/Mx_y_*_SPEC.md), add a new module, change an API contract or schema, adjust a threshold/constant, or resolve a DEVIATION-xx / GAP-xx that needs new behavior. Also use when the user says "改成…", "新增功能", "開一個 change", "提案". It runs DEV_WORKFLOW P1-P3 (clarify → proposal + spec delta → risk audit → user approval → tasks + consistency check) and produces docs/changes/<change-id>/. Do NOT use for typo/doc fixes (T0) or bugs where the SPEC already defines correct behavior (T1).
---

# Skill: Propose Change (DEV_WORKFLOW P1–P3)

完整規則見 `docs/DEV_WORKFLOW.md` §3。本 skill 是執行清單。

## 0. 分級確認

問自己:「改完之後,SPEC 上的文字還對嗎?」

- 對 → 不是本 skill 的範圍 (T0 直接改;T1 走 DEV_WORKFLOW §5)。告訴使用者你判定的 Track 與理由,然後照做。
- 不對 / 沒有 SPEC / 判斷不出來 → 繼續。

## P1 釐清

1. 定向讀取 (不要整份讀 03/05):

   ```bash
   ls docs/modules/ | grep -i "M4_4"                        # 找 SPEC
   grep -n -A 40 "^### M4.4 " docs/04_module_registry.md   # 模組條目 (標籤、依賴、Criteria)
   grep -n -A 35 "^## R08 " docs/03_research_index.md      # SPEC §2 引用的研究
   grep -n "M4\.4" docs/05_integration_risk_audit.md       # 相關 RISK 行號,再讀那幾段
   grep -n "M4\.4\|M4_4" docs/SPEC_DEVIATION_REPORT.md docs/IMPLEMENTATION_GAP_REPORT.md
   ls docs/changes/                                         # 有沒有進行中的同模組 change
   ```

2. 讀相關程式碼現況 (`services/mx_y_*/`、`apps/desktop/src/components/mx_y_*/`),記下 `path:line`。
3. 用一句話重述需求:「在 X 情境下,系統應該 Y,因為 Z」。
4. 模糊點**一次問一個**;能查到的不要問。有設計選擇時給 2~3 個方案 + 取捨 + 建議。
5. 若需求會鬆綁研究約束 (R08 摩擦、R03 反向安撫、隱私分層…),明說「這會鬆綁 [Rxx §y]」。

**本階段不寫程式碼、不寫測試。**

## P2 提案

1. change-id:動詞開頭 kebab-case + 模組號 (`m4-4-per-context-probe-limit`)。
2. 複製範本:

   ```bash
   mkdir -p docs/changes/<id>/specs
   cp docs/changes/_templates/proposal.md docs/changes/<id>/
   cp docs/changes/_templates/tasks.md docs/changes/<id>/
   cp docs/changes/_templates/specs/SPEC_NAME.delta.md docs/changes/<id>/specs/<SPEC 檔名>.delta.md
   # 條件必要:跨 2+ 模組 / schema / 新外部依賴 / 研究演算法 / 多方案
   cp docs/changes/_templates/design.md docs/changes/<id>/
   ```

3. 寫 `proposal.md` 的 Why / What Changes / Impact / Out of Scope。
4. 寫 delta:只寫有變的需求;每條 `REQ-Mx.y-NN` 用 SHALL 敘述 + 至少一個 WHEN/THEN 情境。SPEC 尚無 `REQ-` 編號時,把受影響的舊驗收條目改寫成編號需求放進 MODIFIED。
5. T3 新模組:另依 `docs/modules/_TEMPLATE_SPEC.md` 建 SPEC,`狀態: draft`。
6. 呼叫 skill `audit-integration`,把結果填進 `proposal.md`「整合風險」段 (**不另外問使用者 y/n**)。
7. 研究引用遵守 skill `cite-research`;查不到就不寫,不要編。
8. 拍板項標 `[NEEDS DECISION]`,最多 5 個,各附建議。
9. 在 `docs/changes/README.md` 索引加一列,狀態 `proposed`。

## G1 提案拍板 (必停)

呈給使用者 (簡潔):

```
## Change 提案:<change-id>
Track:T2 | 模組:M4.4 (+M4.1) | 分支:feat/<change-id>

**為什麼**:…
**改什麼**:
- MODIFIED REQ-M4.4-03:…
- ADDED REQ-M4.4-07:…
**整合風險**:RISK-04 (已緩解,維持);無新風險
**研究**:維持 [R08 …];無鬆綁
**不做**:…

**需要你拍板**:
1. …?建議:…
```

等明確同意。同意後:`proposal.md` 狀態改 `approved`、填拍板日期、把 `[NEEDS DECISION]` 改寫為「拍板:…」。
使用者修改需求 → 更新 proposal/delta 後再確認一次,不要邊做邊改。

## P3 計畫

1. 寫 `tasks.md`:每個任務 = 一個測試 + 最小實作;寫出確切檔案路徑、`REQ-` 編號、Red 指令與預期失敗原因。
2. 路徑以 `CLAUDE.md` §專案地圖為準:後端測試 `testing/mx_y/`、前端測試 `apps/desktop/tests/mx_y/`。
3. 先實跑一次基線測試數,填入 `tasks.md`。
4. 填「一致性分析」三張表;任何空格 → 補任務或回 P2。跨 2+ 模組必須有閉環測試任務。
5. T3 或任務 > 15:把 `tasks.md` 給使用者過目 (不需拍板)。
6. 建議分支 `feat/<change-id>`;若工作區有不相關的未提交改動,先問使用者怎麼處理,不要混進來。

完成後:接 skill `implement-module` 進入 P4。
