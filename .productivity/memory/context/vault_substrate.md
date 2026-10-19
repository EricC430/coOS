# Obsidian Vault（底層 / Layer 0）

> 路徑：`C:\Users\chent\Documents\Obsidian\Eric's Obsidian Vault`
> 完整分析見 `coOS/docs/DESIGN_PHILOSOPHY_AUDIT.md` §3。這裡只記 coOS 必須遵守的契約。

## 規模

11,462 筆記。Governance：5 Domain / 10 Role / 130 Skill / 6 Principle / **0 Vision（空）**。
Executive：58 Project（45 active）/ 28 Routine / 108 Event / 56 Daily。
Resource：1,176 People / 1,467 Media / 82 Input / 22 Concept / 14 Artifact。

## 五種機制 = 底層的 API

| 機制 | 角色 |
| --- | --- |
| frontmatter | schema（`class:` `type:` `related_roles:` `domains:` `skills:` `status:`）|
| Dataview | 視圖層。**沒有正確 frontmatter 的檔案等於不存在** |
| Templater（19 份模板） | 帶互動 prompt 的寫入器 |
| `calculateRPGStats.js` | 業務邏輯單一真相，被 Home Note / XP Stats / iOS Widget 共用 |
| `_System/.level_up_trigger.json` | 檔案式事件匯流排 → `level_up_notifier.py`。**coOS 沿用這條，不要發明新的** |

## XP 經濟規格（coOS 必須遵守）

- 全域等級 `floor(0.1 × sqrt(total_xp))`；門檻 `100 × L²`
- 技能等級 `floor(sqrt(skill_xp / 100)) + 1` ← **與上式差常數 1，待統一**
- 六大來源：`routine` `event` `task` `alchemy` `life` `project`
- 權重：task 5 / routine 10 / project_bonus 200 / default_resource 10
- Skill XP 行格式：`- YYYY-MM-DD: +N XP (Task: …)`，append 在 `## 📜 Experience Log (修煉日誌)` 下一行（`logSkillXP.js`，用 `app.vault.process`）
- **一天的邊界 = 凌晨 5 點**
- Routine 參數依 `active_period` 取值（`_System/Global Settings.md`，目前 `2026_spring_semester`）

## 三條寫入路徑（缺一不可）

| 路徑 | 觸發者 | 機制 | 現況 |
| --- | --- | --- | --- |
| P1 桌面 | 人 | Templater + QuickAdd 6 巨集（`Quick Capture` / `Finish & Claim XP` / `Finish Resource` / `Update Widget Data` / `Done` / `XP_Test`）| 現役，一級 |
| P2 行動 | 人 | iOS 捷徑 → Advanced URI → Templater Direct Mode | 現役 |
| P3 coOS | 系統（核准後） | `.coos_inbox/*.json` → `applyCoosInbox.js` | 待建 |

**原則：coOS 是新增一個輸入來源，不是接管輸入。** P1/P2 不能因為 P3 存在而退化。

## Quick Capture 契約（coOS 捕捉筆記要照抄）

| 欄位 | 值 |
| --- | --- |
| `captureTo` | `Executive/Period/Daily/{{DATE:}}` |
| `insertAfter.after` | `📥 Inbox / Sparks` |
| `insertAtEnd` | `true` |
| `createFileIfItDoesntExist` | `false` ← 日記不存在會靜默失敗 |
| `createIfNotFound` | `false` ← 區塊不存在會靜默失敗 |

coOS 這條路徑必須補上這兩個防呆。

## 底層待修（非 coOS 責任，但會影響驗收）

- `Governance/Visions` 是空的，但 Domain / Vision 頁面有 `FROM "Governance/Visions"` 查詢
- `00 Inbox` 資料夾已不存在，Domain / Role 頁面仍有 `FROM "00 Inbox"` → 死查詢
- 兩套 level 公式並存
- 45 個 active 專案（共 58）→ WIP 超載
- `logSkillXP.js` 寫的 XP 行**沒有唯一識別碼** → 人工 claim 與 coOS 回寫會重複計算（RISK-14 的跨系統版）

## 衰減證據（coOS 存在的理由）

| 月份 | Daily 篇數 | Skill XP 條數 |
| --- | --- | --- |
| 2026-01 | 9 | 86 |
| 2026-02 | 20 | 86 |
| 2026-03 | 18 | 44 |
| 2026-04 | 6 | 35 |
| 2026-05 | 1 | 2 |
| 2026-06 | 2 | 15 |

底層的設計沒問題，欠缺的是輸入頻寬。最新一篇 Daily（2026-06-25）mood / energy / productivity 全空、`total_xp: 0`、13 個 checkbox 全未勾、Save Point 空白。
