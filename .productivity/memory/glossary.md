# Glossary

> minimal 版：只收 coOS 與 Phase 1 相關。生活/學業術語留在 Vault。

## 編號系統

| 前綴 | 意思 | 權威來源 |
| --- | --- | --- |
| `M0.x` | 系統基礎與 IPC | `docs/04_module_registry.md` |
| `M1.x` | 端側感知（遙測、斷點、IDE/瀏覽器擴充、Git） | 同上 |
| `M2.x` | 邊緣推論與隱私（Gemma、Eguard、PRISM） | 同上 |
| `M3.x` | 前端 UI（React 元件） | 同上 |
| `M4.x` | 多智能體邏輯（路由、Persona、套問、XP、Observer） | 同上 |
| `M5.x` | 深層認知圖譜（薩提爾冰山、NSVIF）— **尚未實作** | 同上 |
| `M6.x` | 資料庫綱要與 ACID | 同上 |
| `M7.x` | 素材生成 | 同上 |
| `R01`–`R19` | 研究論文 | `docs/03_research_index.md` |
| `RISK-01`–`RISK-18` | 整合風險 | `docs/05_integration_risk_audit.md` |

## 容易混淆的同名概念

| 詞 | 兩種意思 |
| --- | --- |
| **L1 / L2 / L3** | (a) 隱私三層：明文 / 意圖向量 / 業務狀態　(b) 驗收階梯的層級（實際是 L0–L3：接通 / 契約 / 保真 / 體感）|
| **Role** | (a) Vault 的「內在代理人」，有 mission、Quest、Codex　(b) coOS 的資料沙盒。**語意不同，需映射** |
| **Project** | (a) Vault 的 `Executive/Projects`，人定義的　(b) coOS 的「聊天主題標籤」（`DEVIATION-06` 改過語意）|
| **等級** | (a) 全域 `floor(0.1·√XP)`　(b) 單一技能 `floor(√(XP/100))+1`。**相差常數 1，待統一（D2）** |

## Vault 專有詞

| 詞 | 意思 |
| --- | --- |
| **Governance** | Vision → Domain → Role → Skill → Principle 五層憲政結構 |
| **Executive** | Project · Event · Routine · Period（Daily / Weekly） |
| **Resource** | Concept · Artifact · Input · People · Media |
| **Alchemy / 煉金** | XP 六大來源之一，指知識轉化產出（Resource 類筆記） |
| **Quest / 副本** | Project 的任務 / Event |
| **Save Point** | Daily note 的晚間結算區塊（Highlights / Improvements） |
| **Inbox / Sparks** | Daily note 的靈感捕捉區塊，QuickAdd `Quick Capture` 的落點 |
| **active_period** | `_System/Global Settings.md`，當前人生階段（semester / vacation / exam_week…） |
| **一天的邊界** | 凌晨 5 點。凌晨 2 點的紀錄算前一天（`claimXP.js` v6.4） |

## Phase 1 專有詞

| 詞 | 意思 |
| --- | --- |
| **想像外化四件套** | 劇本 / 黃金樣本 / 反例清單 / 基線量測。開工前必備 |
| **驗收階梯** | L0 接通 → L1 契約 → L2 保真 → L3 體感 |
| **垂直切片** | Phase 1 唯一認可的那一條十一步路徑，取代「模組清單」 |
| **停車場** | `Someday` 區塊。新想法一律先進，附「不做會怎樣」 |
| **`.coos_inbox` / `.coos_outbox`** | coOS ↔ Vault 的檔案式事件匯流排 |
| **`[coos:: id]`** | coOS 寫入 Vault 的行內標記，供冪等與撤銷（語法待定，D4） |
