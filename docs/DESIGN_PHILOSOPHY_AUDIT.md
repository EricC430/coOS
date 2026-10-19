# coOS 設計哲學稽核與轉向建議 (Design Philosophy Audit)

**日期**：2026-08-08
**範圍**：`coOS/docs/` 全部 7 份核心文件 + 40 份模組 SPEC + `services/` / `apps/` 實作 + `Eric's Obsidian Vault` (11,462 筆記)
**性質**：外部視角稽核。不修改任何程式碼或既有文件。
**架構立場（全文前提）**：**Obsidian Vault = 底層 (System of Record)；coOS = 這個底層之上的高階介面 (Interface & Runtime)。** Obsidian 不被取代、不被搬空、不進入維護模式——它欠缺的只是輸入頻寬，而那正是 coOS 的專長。
**與既有文件的分工**：
- `IMPLEMENTATION_GAP_REPORT.md` 處理「東西不存在」
- `SPEC_DEVIATION_REPORT.md` 處理「行為改了要拍板」
- `reports/coOS_審查報告.md` 處理「論文的證據不足」
- **本文處理「設計哲學是否自洽、Obsidian 兩年的資產該怎麼接、以及產品該往哪轉」**

---

## 0. 執行摘要

三個判斷，按重要性排序：

**判斷一：coOS 的架構品質遠高於它的迴圈品質。**
19 篇研究、105 個子模組、18 條整合風險、446 個測試——這是一套罕見完整的設計治理體系。但整套體系服務的核心迴圈（對話 → 觀測 → 草稿 → 核准 → XP）目前**沒有任何證據顯示它會被持續使用**。而你手邊就有一份最有說服力的反面證據：Obsidian Vault 的每日筆記從 2026-01 的 9 篇、02 的 20 篇、03 的 18 篇，掉到 04 的 6 篇、05 的 1 篇、06 的 2 篇。Skill 的 XP 紀錄同樣從 2 月 86 條掉到 5 月 2 條。coOS 要對抗的「記錄疲勞」不是文獻上的抽象概念，是你自己系統的死因。而 coOS 目前的解法（把「寫」換成「審核 + 填兩欄」）**尚未被證明不會死於同一條曲線**。

**判斷二：產品定位第一句話目前是空的。**
`01_product_vision.md` 開宗明義：「結合多智能體 AI、遊戲化機制**與薩提爾冰山心理模型**」。但 `services/` 底下沒有 `m5_*` 任何檔案，Neo4j 沒有被寫入過任何節點，M4.8 隱性狀態推論在 Phase 6 被明確標記「先不實作、改採 mock」。薩提爾冰山目前是 0 行程式碼。三大賣點中已實作的只有兩個（多智能體 + 遊戲化），而這兩個恰好是最不具差異化的兩個。

**判斷三：Obsidian 不是要被取代的舊系統，而是 coOS 的底層；coOS 是這個底層之上的高階介面。**

這是本次稽核最重要的架構判斷，也是全文其餘建議的前提。

Vault 已經是一套有 frontmatter schema、有 Dataview 查詢契約、有 Templater 建構器、有 JS 運算引擎、有外部觸發檔事件匯流排（`_System/.level_up_trigger.json` → `level_up_notifier.py`）的**完整個人本體論與運行時 (personal ontology + runtime)**。它欠缺的不是設計，而是**輸入頻寬**——所有事實都必須由人手動敲進去，所以它死於記錄疲勞。

coOS 欠缺的恰好相反：它有極強的輸入頻寬（OS 遙測、VS Code 熵、Git、瀏覽器、對話），但**沒有身分本體**——冷啟動時 role 是空的、goals 是空的、heatmap 回傳 `[]`。

**兩者是互補的兩層，不是競品**：

```
┌──────────────────────────────────────────────────────────────┐
│  coOS — 高階介面層 (Interface & Runtime)                      │
│  感測 · 對話 · 邊緣推論 · 草稿生成 · 即時心理狀態機            │
│  擁有：raw_tracking_logs / intent_logs / chat_transcripts     │
│        （高頻、短生命週期、可重建的 runtime state）            │
└──────────────────────────────────────────────────────────────┘
        ↑ 讀治理（誰是我、我信什麼）    ↓ 寫事實（核准後才寫）
┌──────────────────────────────────────────────────────────────┐
│  Obsidian Vault — 底層 (Substrate / System of Record)         │
│  Governance：Vision → Domain → Role → Skill → Principle       │
│  Executive ：Project · Event · Routine · Period               │
│  Resource  ：Concept · Artifact · Input · People · Media      │
│  擁有：身分、原則、技能樹、XP 帳本、長期記憶                   │
│        （低頻、永久、純文字、可攜、不依賴任何 app）            │
└──────────────────────────────────────────────────────────────┘
```

`M4_7_obsidian_sync_SPEC.md` 目前的設計與這個分層不一致：它把 Vault 當成「輸出垃圾桶」，寫一個不帶 frontmatter 的 `coOS/2026-06-03_csie.md` 進去——這種檔案不會被任何一條 Dataview 查詢撈到，**寫入即死檔**。M4.7 需要重寫成雙向的分層契約（見 §3.5、§3.6）。

---

## 1. 哲學譜系：coOS 實際站在哪些思想傳統上

`03_research_index.md` 列的是 19 篇論文，但論文不等於哲學。把 19 篇歸納後，coOS 實際上同時採用了**五個彼此獨立、且部分互斥**的思想傳統。

### 家族 A — 心理所有權學派（Psychological Ownership）

| 主張 | 來源 | 落地模組 |
| --- | --- | --- |
| 勞動創造價值歸屬感（IKEA 效應） | `[R08 §六.1]` | M4.5 三重守門、M6.5 ACID |
| 摩擦是 feature 不是 bug | `[R08 §四.2]` | M3.3.3 強制留白欄位 |
| 草稿與核准優於全自動 | `[R08 §五]` | M4.4.3 → M3.3.3 → M4.5 |
| 從量化自我到質性自我 | `[R10 §典範轉移]` | M3.3 日報結構 |

**核心公理**：*「使用者必須付出足以感受到的勞動，洞察才會屬於他。」*
這是 coOS 最原創、也最站得住腳的設計命題，且已完整落地（三重守門在 `m4_5_xp_settlement/engine.py` 與 `m6_5_acid_gatekeeper/gatekeeper.py` 都有實作與測試）。

### 家族 B — 混合主動式控制論（Mixed-Initiative Control）

**核心公理**：*「系統的介入時機比介入內容更重要。」*
`[R08 §二 Defer-to-Breakpoint]`、`[R08 §三 警報疲勞]`、`[R01 ZONE]`、`[R02 HMM]`。落地於 M1.2 斷點偵測（`m1_2_breakpoint/breakpoint_engine.py`，601 行，已實作）。

**但**：這一家族的完整版需要「認知負荷估計」作為輸入，而估計器就是 M4.8（POMDP + 多模態 BKT），已被推遲且改 mock。目前 M1.2 只能靠視窗切換這種粗訊號。**控制論的迴圈缺了感測器。**

### 家族 C — 關係性人格學派（Relational Persona）

篇幅最大的家族：`R03` Persona Drift / Echo Mode、`R05` ToM + 治療同盟、`R09` HAIA/SDT/BDI、`R12` Character-LLM、`R13` PersonaLLM OCEAN、`R14` RoleLLM、`R15` MemGPT、`R16` MI/OARS、`R17` WAI、`R18` 反諂媚。

**核心公理**：*「一個穩定、有邊界、不諂媚的他者，比一面鏡子更能促成改變。」*
落地最厚（`m4_2_persona/` 2,426 行，是全專案最大模組）。PersonaCard v2、ClaimLedger、message_splitter、副語言注入、MI selector 都在。

**這是目前 coOS 真正的產品核心**——不論文件怎麼寫，程式碼的重心在這裡。

### 家族 D — 深層心理本體論（Depth Psychology Ontology）

`R04` 薩提爾冰山七層 + DGNN + NSVIF、`R06` 應對姿態 + 數位表型。
**核心公理**：*「行為只是冰山一角，可以被結構化地往下溯因。」*
**落地：零。** M5.1 / M5.2 / M5.3 全部 `[進階]` 且 `services/` 無對應目錄。

### 家族 E — 隱私主權派（Privacy Sovereignty）

`R07` POST/Eguard/PRISM、`R19` sqlite-vec。
**核心公理**：*「敏感明文的物理位置決定隱私，而非政策宣示。」*
落地紮實（`m2_2_gemma` 913 行 + `m2_3_eguard` 397 行 + L1/L2/L3 白名單分流 + `daily_reflection_segments` 表級 hard block）。這是外部審查者評價最高的部分。

### 家族 F、G、H — 只存在於 Obsidian Vault、從未進入研究索引的三個傳統

這三個是**你自己發明的**，而且已經運作了兩年，但 `03_research_index.md` 裡一篇都沒有：

| 家族 | 公理 | Vault 中的體現 |
| --- | --- | --- |
| **F 自我治理論** | 「人生應該像組織一樣被治理：領域 → 角色 → 技能 → 原則」 | `Governance/` 的四層結構、10 個 Role 各有 `mission`、6 條 Principle 有 The Logic / The Algorithm / Anti-Patterns 三段式 |
| **G 具象化成長** | 「抽象的成長必須被鑄造成可見資產才有重量」 | 130 個 Skill 各配 Badge 圖、技能樹 `parent_skill` 遞迴、`level = floor(sqrt(XP/100))+1` |
| **H 資料主權與可查詢性** | 「我的資料必須是純文字，視圖是查詢的結果而非資料本身」 | 全 Vault 用 Dataview / DataviewJS 動態組裝，沒有任何鎖死的 UI |

**這是本次稽核最重要的發現之一**：`01_product_vision.md` 寫「不是 Notion / Obsidian 競品，我們不存內容只建模狀態」，這句話原意是好的（不做 PKM 競品），但實際效果是讓 coOS 主動放棄了家族 F/G/H——**而這三個恰好是你唯一有兩年實戰驗證的設計傳統。**

正確的表述應該是：**F/G/H 由底層（Vault）負責，A/B/C/D/E 由高階介面（coOS）負責。** coOS 不需要重新發明 F/G/H，它需要的是**讀懂並尊重**它們。這句定位聲明建議改寫為：

> 「coOS 不重建個人知識庫。它把 Obsidian Vault 當作身分與長期記憶的底層，自己負責感測、對話與即時心理狀態——**Vault 記錄我是誰，coOS 負責照顧今天的我。**」

§3 完整記錄底層的哲學與規格。

---

## 2. 哲學一致性稽核：五組尚未被 `05_integration_risk_audit.md` 涵蓋的張力

18 條 RISK 涵蓋的是「模組 A + 模組 B 合併後效果變差」。以下五條是**更上層的、公理之間的矛盾**，目前沒有任何文件處理。

### 張力 T-01：摩擦力的方向盤上有兩隻手

同一個系統裡同時存在：

- `[R08 §四.2]`「強制留白，摩擦是 feature」→ M3.3.3、M4.5 三重守門
- 模組 M4.5 的正式名稱是「**零摩擦** XP 自動結算引擎」
- `01_product_vision.md` 指標：「平均每日反思時長 3~7 分鐘，< 1 分鐘 = 無腦點擊」

問題不在於兩者矛盾（分流設計是合理的：Ambient XP 走零摩擦、Earned XP 走高摩擦），而在於**沒有任何模組在測量總摩擦量**。`m4_5_xp_settlement/ambient.py` 有 `AMBIENT_XP_DAILY_CAP_RATIO = 0.05` 這種漂亮的硬約束，但「使用者今天總共花了幾分鐘在 coOS 上」沒有對應的 cap，也沒有對應的 controller。

外部審查的魔鬼代言人已經指出這點（DA M3「審核疲勞」）：半自動化可能只是把摩擦從「寫」搬到「審 + 填 + 停留」。而**你的 Vault 提供了這個假設的實測資料**：Vault 的日記模板本身就是「已填好 13 條 Routine 的 checklist + 4 個 Dataview 自動區塊 + 只要填 Highlights / Improvements 兩欄」——這已經非常接近 coOS 的草稿與核准設計了，而它在 4 個月內從每月 20 篇掉到 1 篇。

> **建議**：把「每日總互動時間預算」升格為一級設計約束（見 §5.2）。

### 張力 T-02：定位聲明與程式碼行為背離

`01_product_vision.md`：「不是 Notion / Obsidian 競品。**我們不存儲使用者的內容，我們建模使用者的狀態。**」

實際 schema：`chat_transcripts`（逐字稿明文）、`daily_reflection_segments`（`ai_description` L1 原文）、`role_projects`、`goals`、`promises`、`m6_6_social_posts`。coOS **已經是**一個內容系統，而且是一個與 Vault 直接競爭的內容系統（`daily_reflections` vs `Executive/Period/Daily`）。

這造成兩個具體後果：
1. M4.7 被設計成單向輸出（因為「我們不存內容」所以沒必要雙向），錯過了最大的整合機會。
2. 使用者（你）現在同時維護兩套日記系統。這保證兩套都做不好。

**分層架構就是這條張力的解**：coOS 存的是 runtime state（高頻、可重建、隱私敏感），Vault 存的是 record of truth（低頻、永久、純文字）。兩者存的**不是同一種內容**，所以不衝突。真正要改的是定位聲明的措辭——把「我們不存內容」改成「**我們不擁有內容的所有權**」（見 §1 家族 F/G/H 段落的建議表述）。至於「兩套日記」：`daily_reflections` 是 coOS 的草稿工作區，`Executive/Period/Daily` 是核准後的歸檔——同一份日記的兩個生命階段，不是兩套系統。

### 張力 T-03：治療同盟越成功，隱私風險越大（結構性反向誘因）

這條張力**完全沒有在任何文件中出現**，但它是 coOS 最深的結構性問題。

- 家族 C 的目標：透過 `[R17: WAI]` 三成分建立情感連結，讓使用者願意說出真話
- 家族 E 的目標：敏感明文絕不離端
- `DEVIATION-09` 已承認：Persona 對話逐字稿（L1）直送 Gemini，只過 DRIFT 不過 Eguard

**推論**：Persona 做得越好，使用者說的話越私密，送上雲的 L1 明文就越敏感。產品成功與隱私風險**正相關**。這不是 bug，是兩個公理放在同一個系統裡的必然結果。

`DEVIATION-09` 的拍板決議寫了回退手段（意圖向量上雲 → Local LLM 生成回應 + 人設後處理），**但這個回退手段目前 0 行程式碼**，而且 `GAP-C2` 指出本地 Gemma 的 `generate_json` 語意錯位、承諾萃取空轉——也就是說，本地 LLM 通道本身還不夠健康到能承擔這個任務。

### 張力 T-04：SDT 與 XP 經濟的擠出效應

`[R09 §第四章 SDT]` 被引用來支撐「自主、勝任、連結」三需求。但 SDT 文獻的核心發現之一正是 **crowding-out effect**：外在獎勵會擠出內在動機。coOS 卻在 SDT 的名義下建了一套完整的 XP 經濟（XP 帳本、等級、徽章、質押對賭、Gacha 待做）。

`01_product_vision.md` 的反 KPI 設計得非常漂亮——「Gacha 抽卡次數爆增 → 觸發 RISK-09」「連續登入天數高但 mood_score 低 → RISK-10」。**但沒有任何模組在計算這些反 KPI。** mood_score 的來源是 M4.8（未實作）。反 KPI 目前是一份沒有執行機關的憲法。

而 Vault 的 XP 系統已經先驗證過這件事對你本人的效果：268 條 XP 紀錄，5 月只剩 2 條。外在獎勵沒有救活那套系統。

### 張力 T-05：學術憲法的執行成本正在拖慢迭代

`CLAUDE.md` 要求實作任一模組前必讀 4 份文件、引用必須精確到 `[Rxx §y.z]`、跨模組必跑 audit-integration skill。這在品質上極為出色（審查報告 5 位審查者一致肯定），但代價是：

- 40 份 SPEC，其中 M5.x / M4.8-4.12 / M3.8-3.11 共 14 個模組的 SPEC 已寫、程式碼為零 → **設計債（documentation ahead of implementation）**
- `Governance/Principles/Principle - 最小可行迭代法則.md` 你自己寫的原則是：「完成比完美更重要，拒絕教學地獄，堅持住在爛泥中產出」

**你的個人原則與專案憲章正在互相打架。** 這不是要放棄嚴謹，而是 SPEC 的撰寫節奏應該跟上實作節奏，而非領先 14 個模組。

---

## 3. 底層規範：Obsidian Vault 的設計哲學與規格

> **架構立場（本節前提）**：Obsidian Vault 是 coOS 的**底層 (substrate / system of record)**，coOS 是這個底層之上的**高階介面 (higher-order interface)**。Vault 不被取代、不被搬空、不進入維護模式。以下把底層的哲學與規格正式記錄下來，讓 coOS 的設計有明確的契約可依循。

### 3.0 底層的三條哲學（家族 F / G / H 的完整版）

#### F — 自我治理論：人生應該像組織一樣被治理

Vault 的 `Governance/` 不是資料夾分類，是一套**憲政結構**，五層由抽象到具體：

```
Vision   (北極星，3–5 年)     ← Governance/Visions
  ↓ 座落於
Domain   (生活領域，5 個)      ← Governance/Domains
  ↓ 由誰負責
Role     (角色 / 內在代理人，10 個，各有 mission)  ← Governance/Roles
  ↓ 需要什麼能力
Skill    (技能，130 個，樹狀 parent_skill)         ← Governance/Skills
  ↓ 依什麼準則行動
Principle(個人原則，6 條)      ← Governance/Principles
```

三個關鍵設計，coOS 都沒有：

1. **Role 是「內在代理人」而非資料標籤**。每個 Role 有 `mission`（「管理自我時間、準則、成長、決策的內在 CEO」、「市場價值變現。負責寫履歷、刷 LeetCode…」），有自己的 Quest / Inbox / Skill Tree / Allies / Codex 五個區塊。這是 `[R03: 自我複雜度]` 概念的完整實作，且比 coOS 的「Role = 資料沙盒」語意豐富得多。
2. **Vision Template 內建角色衝突解決機制**。`Vision Template.md` 有 `## 🛤️ Multi-Track Scenarios（多軌道劇本）` 與 `## ⚔️ Conflict Resolution（衝突整合）`——明確處理「同一領域下不同角色的夢想資源衝突」。**coOS 完全沒有角色衝突的概念**，M4.3 的角色隔離只做技術隔離，不做價值取捨。
3. **Principle 是可執行的演算法，不是格言**。固定三段式結構：

   ```
   ## 🧠 The Logic (為什麼有效？)      → 信念的理由，可作為 Persona stance
   ## ⚙️ The Algorithm (如何執行？)   → IF (觸發條件) THEN (行動) ELSE IF …
   ## 🚫 Anti-Patterns (反面教材)      → 已知失敗模式，可作為偵測器
   ```

#### G — 具象化成長：抽象的成長必須被鑄造成可見資產才有重量

Vault 的 XP 經濟是一套完整規格，`coOS` 若要與之互通必須遵守：

| 項目 | 底層規格 | 來源 |
| --- | --- | --- |
| 全域等級公式 | `level = floor(0.1 × sqrt(total_xp))` | `calculateRPGStats.js:303` |
| 升級門檻 | `xp_for_level(L) = (L / 0.1)² = 100 L²` | `calculateRPGStats.js:307` |
| 單一技能等級 | `level = floor(sqrt(skill_xp / 100)) + 1` | Role / Skill 頁面的 DataviewJS |
| XP 六大來源 | `routine` / `event` / `task` / `alchemy` / `life` / `project` | `xp_breakdown` |
| XP 權重 | task 5、routine 10、project_bonus 200、default_resource 10 | `XP_WEIGHTS` |
| 技能 XP 紀錄格式 | `- YYYY-MM-DD: +N XP (Task: …)`（append 在 `## 📜 Experience Log`） | `logSkillXP.js` / 各 Skill note |
| 一天的邊界 | **凌晨 5 點**（`moment().subtract(5,'hours')`）——凌晨 2 點算前一天 | `claimXP.js` v6.4 |
| 階段參數化 | Routine 的 `xp_value` / `freq` / `status` 依 `active_period` 取不同值 | `getProp(fm, prop)` |

> ⚠️ **底層本身有一個一致性瑕疵**：全域公式 `floor(0.1·√XP)` 與技能公式 `floor(√(XP/100))+1` 相差一個常數 1。若 coOS 要顯示等級，必須先拍板統一，否則兩邊數字對不上。

#### H — 資料主權與可查詢性：資料是純文字，視圖是查詢的結果

Vault 沒有任何鎖死的 UI。它由五種機制動態組裝，**這五種機制就是 coOS 必須遵守的底層 API**：

| 機制 | 角色 | 具體檔案 |
| --- | --- | --- |
| **frontmatter 契約** | 資料庫 schema | `class:` / `type:` / `related_roles:` / `domains:` / `skills:` / `status:` |
| **Dataview 查詢** | 視圖層（等同 SELECT） | Role 頁的 `WHERE contains(related_roles, this.file.link)` |
| **Templater 建構器** | 帶互動 prompt 的寫入器 | `_System/Templates/` 19 份，含自動命名、自動歸檔、防衝突 |
| **JS 運算引擎** | 業務邏輯層 | `calculateRPGStats.js`（單一真相來源，被 Home Note / XP Stats / Widget 共用） |
| **觸發檔事件匯流排** | **對外整合點** | `_System/.level_up_trigger.json` → `level_up_notifier.py`（生圖 + 寄信） |

**最後一條是關鍵發現**：Vault 已經有一個**檔案式事件匯流排**，外部 Python 程式（`level_up_notifier.py`、`exportDashboardData.js` → iOS Widget）已經在消費它。coOS 不需要發明新的整合機制，**沿用這條匯流排即可**。

### 3.0.1 底層已經設計好、但 coOS 重新發明了一次的東西

`ai_architecting/obsidian design.md`（65,729 行的設計對話紀錄）裡，你早就設計過一套五段式反思鷹架：

```
## 描述
## 發生了…（客觀、整體）
## 觸動了我…（主觀、感受）
## 我聯想到了…（突觸連結、過去）
## 我有新的點子…（整合、創造）
## 觸發新任務…（評估、決策）
```

這與 coOS 的 M4.4.3 `gibbs_template.py`（880 行）在做同一件事，而且**你的版本多了「突觸連結」這一段**（把當下經驗連回過去的概念與筆記）——這正是 `[R11: Park et al. §3.3 Reflection]` 的核心，也正是 coOS 目前最弱的一環（`daily_reflections` 沒有任何連回 `Resource/Concepts` 的機制）。

同樣被重新發明的還有 Event Template 的四段式（`發生了什麼(客觀) / 觸動了我(主觀) / 連結與分析 / 轉化與行動`）。

> **建議**：M4.4.3 的 Gibbs 模板應該對齊底層既有的五段式，而不是另立一套。這樣草稿寫回 Vault 時格式天然相容。

### 3.0.2 底層目前的健康狀況（誠實盤點）

底層是好的，但它有五個必須修的問題——而其中三個 coOS 剛好可以幫忙修：

| 問題 | 證據 | coOS 能否協助 |
| --- | --- | --- |
| **`Governance/Visions` 是空的** | `ls Governance/Visions` → 0 個檔案，但 Domain / Vision 頁面都有 `FROM "Governance/Visions"` 查詢 | ⚠️ 憲政結構的最頂層缺席，只能由你自己補 |
| **`00 Inbox` 資料夾已不存在** | Domain 與 Role 頁面仍有 `FROM "00 Inbox"` → 死查詢 | ⚠️ 需手動修查詢 |
| **兩套 level 公式並存** | 見 §3.0 G | ⚠️ 需拍板 |
| **45 個 active 專案（共 58）** | `grep "^status:" Executive/Projects/*.md` | ✅ coOS 的 M4.6 可以偵測「哪些專案已經 30 天沒有任何遙測活動」→ 建議降級為 `on_hold` |
| **手動 claim 導致衰減** | Daily 9→20→18→6→1→2；XP 268 條，5 月剩 2 條 | ✅ **這正是 coOS 存在的理由**：coOS 補上底層唯一欠缺的東西——輸入頻寬 |

### 3.1 概念對照表

| Vault 概念 | 規模 | coOS 對應 | 語意是否相同 | 狀態 |
| --- | --- | --- | --- | --- |
| **Domain** 生活領域 | 5 | 無 | — | ❌ coOS 沒有 Role 之上的層級 |
| **Role** 角色 | 10（各有 mission） | `m6_2` roles | ⚠️ Vault Role = 人格分身 + 使命；coOS Role = 資料沙盒 | 🟡 半對應 |
| **Skill** 技能 | 130（樹狀 `parent_skill` + Badge 圖 + XP log） | M3.10 技能樹 `[進階]` | ⚠️ Vault XP 記在 Skill；coOS XP 記在 user/role | ❌ 未實作 |
| **Principle** 個人原則 | 6（IF-THEN-ELSE 演算法格式） | 無 | — | ❌ **最大遺珠**（見 3.3） |
| **Vision** 願景 | **0** | goals | — | ⚠️ Vault 的最頂層是空的 |
| **Project** 專案 | 58（45 個 active） | `role_projects` | ⚠️ coOS 的 project 已被 `DEVIATION-06` 改為「聊天主題標籤」 | 🟡 語意分歧 |
| **Routine** 習慣 | 28（`xp_value` / `freq_type` / `periods` 分階段參數） | 無 | — | ❌ coOS 沒有週期性習慣概念 |
| **Event** 行事曆 | 108（Google Calendar 雙向） | 無 | — | ❌ |
| **Daily** 日記 | 56（模板含時間鎖定 + Quest Log + Save Point） | `daily_reflections` | ✅ 高度重疊 | ⚠️ **直接競爭** |
| **Resource/People** | 1,176 | 無 | — | ❌ |
| **Resource/Media** | 1,467 | 無 | — | ❌ |
| **Global Settings `active_period`** | 1（semester / vacation / exam_week） | 無 | — | ❌ **第二大遺珠**（見 5.6） |

### 3.2 M4.7 SPEC 的根本誤解

`M4_7_obsidian_sync_SPEC.md` §7.3 的輸出是：

```
{vault_path}/coOS/2026-06-03_csie.md
```
內容為純 Markdown 標題 + 條列，**沒有 frontmatter**。

在你的 Vault 裡，一份筆記若沒有 `class:` / `type:` / `related_roles:` / `skills:` 等 frontmatter，就不會被任何一條 Dataview 查詢撈到。你的 Role 頁面查的是 `FROM "Executive/Projects" WHERE contains(related_roles, this.file.link)`；Domain 頁面查的是 `FROM "Governance/Visions"`；Daily 頁面查的是 `FROM "Executive/Events" WHERE contains(daily_link, this.file.link)`。

**M4.7 寫進去的檔案會漂在 Vault 裡，不屬於任何角色、任何領域、任何專案，永遠不會出現在任何儀表板上。** SPEC §9 的 Open Question「每個 Session 一個檔還是按日合併？」問錯了問題——真正的問題是「寫進去的東西如何進入 Vault 既有的查詢契約」。

順帶一提，SPEC §7.4 的 PII 正則 `[一-鿿]{2,3}(?:小|大|老)\w` 會誤殺大量正常中文（例如「機器學習」不會中，但「專題小組」會中），而 §6 的驗收測試 `assert "陳小明" not in content` 用這條正則其實也匹配不到（「陳小明」是「姓+小+名」，正則要求 2-3 個中文字後接 小/大/老，「陳」只有 1 字）。這條測試會失敗。

### 3.3 被錯過的最大資產：`Governance/Principles`

你的 6 條 Principle 不是勵志格言，它們的結構是：

```
## 🧠 The Logic (為什麼有效？)      → 信念的理由
## ⚙️ The Algorithm (如何執行？)   → IF (觸發條件) THEN (行動) ELSE IF ...
## 🚫 Anti-Patterns (反面教材)      → 已知失敗模式
```

例如「最小可行迭代法則」的 Algorithm 是：

> IF (我發現自己正在看第 3 個教學影片卻還沒寫下一行 code) THEN (強制啟動髒手模式：關掉瀏覽器 / 寫最爛的一段 code / 讓程式報錯)

**這正是 M1.5 微 Nudges 引擎需要的規則，而且是使用者自己寫的、自己認可的。**
它同時也是 `[R16: MI §Rolling with Resistance]` 夢寐以求的東西：一條使用者在冷靜時自己訂下的規則，AI 在他阻抗時可以引用「這是你自己說的」，而不是 AI 在說教——這是**繞過心理阻抗 `[R03 §4]` 的最強路徑**。

`M4_2_persona_state_machine_SPEC.md` 的 PersonaCard v2 有 `stances`（立場）欄位用來防諂媚。Principle 的 The Logic 段落可以直接餵進去，讓專家的立場**來自使用者自己的價值觀**，而不是 LLM 生成的通用人格。

### 3.4 分層契約：誰擁有什麼

不是「遷移」，是**定義兩層之間的所有權邊界**。任何一筆資料只能有一個 owner，另一層只能讀或提議。

| 資料 | Owner | 另一層的權限 | 理由 |
| --- | --- | --- | --- |
| Vision / Domain / Role / Principle | **Vault** | coOS 唯讀 | 身分與價值觀屬於使用者，不該住在 app 裡 |
| Skill 樹結構、Badge | **Vault** | coOS 唯讀 | 130 個節點是兩年的手工資產 |
| Skill XP 帳本 | **Vault** | coOS 可 append（核准後） | 底層是唯一等級真相；coOS 只是新增一個輸入來源 |
| Project 定義（status / deadline / 目標） | **Vault** | coOS 可提議新建、可提議降級 | 人決定什麼是專案，AI 只提供證據 |
| Routine 定義與週期 | **Vault** | coOS 唯讀 + 可回報完成 | |
| `active_period` 人生階段 | **Vault** | coOS 唯讀（並據此調參） | |
| Daily 日記檔 | **Vault** | coOS 可寫入指定區塊（核准後） | |
| 遙測日誌 / 意圖向量 / 對話逐字稿 | **coOS** | Vault **永不接收** | L1/L2 隱私分層，且高頻資料不該汙染純文字 Vault |
| Persona / 信任等級 / 心理狀態機 | **coOS** | Vault 唯讀（可展示） | runtime state，可重建 |
| 草稿（未核准） | **coOS** | Vault 永不接收 | `[R08 §六.1 IKEA]`：未核准的東西不算數 |

**三條鐵律**：

1. **coOS 對 Vault 的寫入必須是 append-only 且可撤銷**——只 append 到既有區塊，不修改既有行；所有寫入帶 `coos_generated: true` 或行內標記，可用一條 Dataview 全數查出並刪除。
2. **未經 `is_reviewed = true` 的內容，一個字都不准進 Vault**。這同時滿足 `[R08 §六.1]` 與「Vault 只收乾淨資料」。
3. **L1 明文（逐字稿、螢幕內容、程式碼）永不寫入 Vault**。Vault 有 `obsidian-git` 外掛做 GitHub 跨裝置同步——寫進去等同上雲。這條比 `M4_7_obsidian_sync_SPEC.md` §5 現有的「偵測 iCloud / Dropbox 就警告」嚴格得多，因為你的 Vault **本來就在同步**。

### 3.5 M4.7 重寫：從「單向輸出」到「雙向分層契約」

**M4.7a — Vault Governance Reader（讀，優先做）**

```
Vault/Governance/Roles/*.md      → coOS roles（mission 進 role 描述）
Vault/Governance/Domains/*.md    → coOS 新增 domain 層（見 5.6）
Vault/Governance/Skills/*.md     → coOS skill 樹 + XP 基準（parent_skill 遞迴）
Vault/Governance/Principles/*.md → PersonaCard.stances + M1.5 nudge 規則
Vault/Executive/Projects/*.md    → coOS role_projects（status=active 的 45 個）
Vault/_System/Global Settings.md → coOS active_period
```

價值：**coOS 從第一天起就知道使用者是誰**。目前 coOS 的冷啟動是空的（E2E 測試報告顯示 heatmap 回傳 `[]`、`goals: []`、`promises: []`）。M4.7a 一次匯入即可讓 M3.2 儀表板、M4.1 路由、M4.2 PersonaCard 全部有真實內容。這是**單位工時價值最高的一件事**。

**M4.7b — Vault Writer with Contract（寫，次之）**

不寫 `coOS/2026-06-03_csie.md`。改為：

1. **XP 回寫既有格式**：append 到對應 `Governance/Skills/Skill - X.md` 的 `## 📜 Experience Log` 區塊，格式完全遵守 Vault 既有慣例 `- YYYY-MM-DD: +N XP (Task: ...)`。這樣 `calculateRPGStats.js` 與 `skillStatus.js` 會自動吃到，Vault 的等級會動起來。
2. **日報寫入 `Executive/Period/Daily/YYYY-MM-DD.md` 的 Save Point 區塊**，而非另開檔案。
3. **必帶 frontmatter**：`class: period` / `type: daily` / `coos_generated: true` / `coos_thread_id: ...`。`coos_generated` 讓你能一條 Dataview 查出所有 AI 生成內容，隨時撤銷。

> **必須守住的鐵則**：回寫是**核准後**才發生（`is_reviewed = true`）。這既是 `[R08 §六.1 IKEA]` 的要求，也讓 Vault 只收乾淨資料。

### 3.6 整合機制：沿用底層既有的事件匯流排，不要發明新的

`M4_7_obsidian_sync_SPEC.md` §4 假設寫入要透過 Tauri `fs` API（因為 Python sidecar 不能直接寫）。但底層**已經有一套跑了半年的整合模式**：

```
Obsidian 內部事件  →  寫一個 JSON 觸發檔  →  外部 Python 程式 watch 並消費
（calculateRPGStats.js 偵測升級 → _System/.level_up_trigger.json → level_up_notifier.py 生圖 + 寄信）
```

建議 coOS 用**對稱**的方式接上，兩個方向各一個目錄：

| 方向 | 路徑 | 內容 | 消費者 |
| --- | --- | --- | --- |
| **Vault → coOS** | `_System/.coos_outbox/*.json` | 升級事件、Routine 完成、Project 狀態變更、`active_period` 切換 | coOS FastAPI sidecar（watchdog） |
| **coOS → Vault** | `_System/.coos_inbox/*.json` | 已核准的 XP 條目、日報段落、Project 提議 | 一個新的 `_System/Scripts/applyCoosInbox.js`（QuickAdd 手動觸發或 Templater 開機執行） |

這個設計有三個好處：

1. **不需要 Tauri fs 權限**。Python sidecar 直接讀寫 `.coos_inbox/` 的 JSON 即可，`.md` 的實際修改由 Vault 自己的 JS 完成——**寫入 Vault 的永遠是 Vault 自己的程式**，格式一定合乎契約。
2. **天然的 Draft & Approve 第二道關卡**。`applyCoosInbox.js` 可以做成 QuickAdd 指令，你在 Obsidian 裡按一下才落地。這符合 `[R08 §五 意圖脫鉤]`，也讓 Vault 永遠是你按下確認才會變的。
3. **離線安全**。coOS 沒開時 Vault 照常運作；Vault 沒開時 coOS 照常收集。兩層鬆耦合。

**同步衝突處理**：Vault 由 `obsidian-git` 管版本。所有 coOS 寫入都是 append-only，天然無衝突；若 `applyCoosInbox.js` 發現目標區塊不存在（模板改版），寫進 `_System/.coos_inbox/_failed/` 並在 Obsidian 發 Notice，不靜默失敗。

### 3.7 雙寫與收斂：底層必須保持可獨立寫入

分層架構最容易被做錯的一點，是「高階介面接手之後，低階就只能被動接收」。**這在這裡是錯的。** Vault 是你的東西，它必須在 coOS 完全沒開的情況下照常運作、照常被寫入。

#### 3.7.1 三條寫入路徑，缺一不可

| 路徑 | 觸發者 | 機制 | 現況 |
| --- | --- | --- | --- |
| **P1 桌面直接輸入** | 人 | Templater 19 份模板（自動命名 / 自動歸檔 / 防衝突）+ QuickAdd 6 個巨集（`Quick Capture` / `Finish & Claim XP` / `Finish Resource` / `Update Widget Data` …） | ✅ 現役，**一級路徑** |
| **P2 行動端捕捉** | 人 | iOS 捷徑 → Advanced URI → Templater Direct Mode（Vault 根目錄的 Event 初始化腳本 v13.1，可直接帶 `name` / `time` / `rank` / `desc` 參數） | ✅ 現役 |
| **P3 coOS 回寫** | 系統（**核准後**） | `.coos_inbox/*.json` → `applyCoosInbox.js` | ❌ 待建 |

> **設計原則**：**coOS 是「新增一個輸入來源」，不是「接管輸入」。** P1 / P2 在任何時候都不能因為 P3 的存在而退化、失效或需要先開 coOS。這是分層架構的底線——底層不能反過來依賴高階介面。

#### 3.7.2 收斂模型：Vault 永遠是真相，coOS 只有快照

```
Vault (source of truth)
   │  ← 人隨時透過 P1 / P2 修改
   ↓  週期重掃 (啟動時 / obsidian-git commit 後 / 每 N 分鐘掃 mtime)
coOS vault_snapshot + last_seen_hash
   │  diff → 更新 runtime state (roles / skills / projects / active_period)
   ↓  絕不反向覆寫
```

三條規則：

1. **coOS 對 Vault 的認知永遠是「重掃出來的」，不是「import 進來的」。** 你昨天在 Obsidian 手動新增一個 Skill、改一條 Principle、把 Project 設成 `on_hold`，coOS 今天必須自動看得到。
2. **衝突一律以 Vault 為準。** coOS 端的對應紀錄直接被覆蓋，不詢問——因為 coOS 端的是快照，不是資料。
3. **Vault 檔案被刪除時，coOS 不重建。** 只在 `raw_tracking_logs` 記 `vault_entity_disappeared`，並在下次相關對話時詢問。

#### 3.7.3 冪等性：防止「人工 claim + coOS 回寫」重複計算

現況風險（實測）：`logSkillXP.js` 的寫入格式是

```
- 2026-08-10: +30 XP (Task: 讀論文)
```

**沒有任何唯一識別碼**，插在 `## 📜 Experience Log (修煉日誌)` 標題的下一行。如果 coOS 也寫一條格式相同的紀錄，`calculateRPGStats.js` 會把兩條都算進去——這正是 `RISK-14`（lifetime XP 同步失敗）在跨系統情境下的版本。

**建議的最小改動**：coOS 寫入的每一行帶一個穩定標記，用 Dataview inline field 語法（不影響既有正則解析）：

```
- 2026-08-10: +30 XP (Task: 讀論文) [coos:: seg_a1b2c3]
```

| 情境 | 處理 |
| --- | --- |
| coOS 重放同一個 segment | `applyCoosInbox.js` 先掃該檔案有無同 `coos::` id → 有就跳過 |
| coOS 重掃時發現同日同技能已有人工 claim 的相近條目 | 標記 `possible_duplicate`，**在下一張草稿卡上問你**，不自動合併也不自動跳過 |
| 你想撤銷 coOS 寫過的所有 XP | 一條 Dataview：`WHERE coos != null`，全數查出後刪除 |

#### 3.7.4 從 coOS 直接輸入筆記（低階寫入的第三條路）

你希望在 coOS 裡也能直接產出筆記（而非只有系統生成的日報）。底層的落點已經有明確契約，**照抄即可**：

QuickAdd 的 `Quick Capture` 巨集設定（`.obsidian/plugins/quickadd/data.json`）：

| 欄位 | 值 | 意義 |
| --- | --- | --- |
| `captureTo` | `Executive/Period/Daily/{{DATE:}}` | 落在**今天的日記**，不另開檔 |
| `insertAfter.after` | `📥 Inbox / Sparks` | 插在該區塊 |
| `insertAtEnd` | `true` | 附加到區塊末尾 |
| `createFileIfItDoesntExist` | `false` | ⚠️ 今天的日記不存在就**靜默失敗** |
| `createIfNotFound` | `false` | ⚠️ 區塊不存在也**靜默失敗** |

所以 coOS 的 quick capture 應該產生：

```json
// _System/.coos_inbox/20260810T2314_capture.json
{
  "op": "capture_spark",
  "date": "2026-08-10",
  "text": "讓 AI 挑出不同程度適當數量的資料，再經由個人挑選",
  "role_id": "role_202601212137",
  "coos_id": "cap_9f3e21"
}
```

由 `applyCoosInbox.js` 落地為 Daily note `📥 Inbox / Sparks` 區塊的一行：

```
- [ ] 讓 AI 挑出不同程度適當數量的資料，再經由個人挑選 [coos:: cap_9f3e21]
```

這樣它會被 `Inbox Zero.md` 的 Dataview（掃 `inboxSection: ["Inbox","Sparks","收件匣"]`、回看 60 天）自動撈到，**與你手動捕捉的靈感長得一模一樣**。

**兩個必須補的防呆**（底層現有設定的已知脆弱點，coOS 這條路徑要一併處理）：

- 今天的日記檔不存在 → `applyCoosInbox.js` 必須先用 Daily Template 建檔，不能靜默失敗
- `📥 Inbox / Sparks` 區塊不存在（模板改版）→ 建立該區塊，並發 Notice

#### 3.7.5 一條反模式

❌ **不要讓 coOS 直接呼叫 Templater 或直接改 `.md`。**
Templater / QuickAdd 是 Obsidian 執行期內部 API，Obsidian 沒開就不存在。coOS 的所有寫入必須先落到 `.coos_inbox/*.json`，等 Obsidian 開啟時由 `applyCoosInbox.js` 套用模板邏輯落地。

這意味著 coOS 的 capture **有延遲**——這是可接受的，甚至是好的：它天然構成第二道核准關卡，符合 `[R08 §五 意圖脫鉤]`，也保證寫進 Vault 的每一個字都經過 Vault 自己的格式邏輯。

---

## 4. 未完成之處：以實際程式碼為準的完成度稽核

以下狀態以 `services/` 與 `apps/` 實際檔案為判準，非以文件宣稱為準。

### 4.1 模組完成度

| 層 | 已實作 | 未實作 | 備註 |
| --- | --- | --- | --- |
| **M0** 基礎 | M0.4 (717 行) | — | M0.1-0.3 為結構性，已隨 repo 存在 |
| **M1** 感知 | M1.1 (Rust)、M1.2 (601)、M1.4 (451) | M1.5 微 Nudges、M1.6 WebGPU | M1.3 在 `apps/vscode-extension` + `apps/browser-extension`，非 `services/` |
| **M2** 邊緣 | M2.1 (320)、M2.2 (913)、M2.3 (397) | M2.4 進階隱私、M2.5 PRISM、M2.6 128K | |
| **M3** UI | M3.1-M3.7 | M3.8 Wrapped、M3.9 通知儀表板、M3.10 技能樹、M3.11 Gacha | 前端 10,759 行、M3.1–M3.7 各 1 個 vitest 檔（`GAP-A2` 已解除，報告成文時尚未更新）|
| **M4** 邏輯 | M4.1 (1,505)、M4.2 (2,426)、M4.3 (690)、M4.4 (1,654)、M4.5 (266)、M4.6 (1,493)、M4.13 (1,795) | **M4.7 Obsidian**、M4.8 隱性狀態、M4.9 ARPM、M4.10 NSVIF、M4.11 ZPD、M4.12 隱藏成就 | M4.13 提前落地 |
| **M5** 圖譜 | **全部未實作** | M5.1、M5.2、M5.3 | 🔴 產品定位第一句話無實作 |
| **M6** 資料庫 | M6.1-M6.6 全部 | — | |
| **M7** 素材 | 全部未實作 | M7.1 | |

**MVP 標稱 29 個模組，實際落地 ~20 個。** 但已落地的部分品質高（446 測試通過、E2E 8 步驟 7 步 PASS）。

### 4.2 尚未解除的技術缺口

| 編號 | 問題 | 影響 | 我的判斷 |
| --- | --- | --- | --- |
| `GAP-C2` | Gemma adapter `generate_json` 語意錯位，本地承諾萃取空轉 | 🔴 高 | 這條擋住了 `DEVIATION-09` 的隱私回退方案。**應該升為 P0**，不是 Phase 6 |
| `GAP-C3` | M4.4 套問缺 `TelemetrySegmentReport.confidence` 檢查 | 🟡 中 | 沒有這個檢查，套問會在系統已經知道答案時仍然發問 → 直接觸發「被審問感」 |
| `GAP-C8` | Elicitation turn counter 語意錯（算注入次數非對話輪數） | 🟡 中 | cooldown 實際比 SPEC 短 |
| `DEVIATION-09` | 逐字稿直送雲端；回退方案已拍板但 0 行程式碼 | 🔴 高 | 至少先補 `eguard.mask_pii()`（成本極低，`m2_3_eguard` 已有函式）|
| 反 KPI | `mood_score` / Persona 一致性分數 / CARE 觸發次數皆無計算實作 | 🔴 高 | 憲法沒有執行機關 |
| 評估 | 零使用者數據、零效能實測 | 🔴 高 | 審查報告 P0；資料多半已在 SQLite |

### 4.3 UX 缺口（來自 `docs/manual_test_log.md` 的真實使用回饋）

你自己記錄的問題非常精準，值得升格為正式 backlog：

| 問題 | 根因 | 對應研究 |
| --- | --- | --- |
| 首次問候 121 字，「一般人打招呼不會這樣」 | PersonaCard 缺長度硬約束 | `[R05 §跨越恐怖谷]` — 過度自我介紹是典型 AI tell |
| 人格都很急迫催促（「別浪費時間在那些華而不實的…」） | `_ai_generate_expert` 的具體性檢查只驗年代/學經歷，未驗溫度 | `[R05 §治療同盟]` — 缺 Bond 維度 |
| 氣泡分割仍太長、延遲太短 | `message_splitter` 缺「一氣泡一問題」規則與 `delay = f(字數, WPM)` | `[R05 §副語言線索]` |
| 每回合都產生 project 標記 | M4.6 三段式偵測缺「與當前標籤同一專案？」的前置比對 | `DEVIATION-06` 已改語意但未補去重顯示邏輯 |
| 返回聊天室後氣泡合併、標記消失 | 前端未持久化 `split_messages` 與 system event | — |
| Project board 新標籤擠掉舊的 | 前端固定高度 + 滾動未做（`manual_test_log` 已提） | — |

---

## 5. 轉向建議：九項，按投入產出比排序

### 5.1 【P0】把「證據」當成下一個 Phase 的主要交付物，而不是新功能

不是做使用者研究，是**把已經躺在 SQLite 裡的資料變成報告**。

具體 metric 定義（都能用現有表算）：

| 指標 | 資料來源 | 為什麼重要 |
| --- | --- | --- |
| 草稿核准率 = `is_reviewed=1` / 全部草稿 | `daily_reflections` | 直接檢驗「審核疲勞」假設 |
| 草稿產生 → 核准的中位延遲 | `daily_reflections.created_at` vs `reviewed_at` | 延遲拉長 = 疲勞早期訊號 |
| 每張卡片 `user_feeling` + `user_action_plan` 字數分布 | `daily_reflection_segments` | 字數趨近下限 = IKEA 效應失效 |
| 每日 coOS 互動總分鐘數 | `raw_tracking_logs` | 對照 vision 的 3~7 分鐘目標 |
| Eguard 遮蔽計數 / 誤殺計數 | `raw_tracking_logs` | 支撐最重要的隱私宣稱 |
| Gemma vs Cloud fallback 比例、快取命中率 | `llm_inference_logs` | 支撐延遲與成本宣稱 |

**加碼建議**：把 Vault 的衰減曲線（Daily 9→20→18→6→1→2、XP 86→86→44→35→2→15）作為 baseline 寫進論文。這是你獨有的、極有說服力的前測資料——「我先用純手動系統驗證了記錄疲勞真的會殺死一套個人系統，這是 coOS 存在的理由」。這一段能同時解除審查報告的 C1 與 M2（確認偏誤），因為你**先呈現了自己的失敗**。

### 5.2 【P0】把「摩擦預算」升格為一級設計約束

目前微摩擦力散落在各模組的規則裡。建議 formalize 成一個新模組（暫稱 **M1.7 Friction Budget Controller**）：

```python
# [R08 §四.2 微摩擦力] + [R08 §三 警報疲勞]
DAILY_INTERACTION_BUDGET_MIN = 7   # 01_product_vision 的上界
DAILY_INTERACTION_FLOOR_MIN  = 3   # 下界，低於此 = 無腦點擊

# 超出預算時系統自己降級，而非要求使用者更自律：
#   - 停止一切套問 (M4.4)
#   - 草稿 segment 數量減半
#   - 只保留最高信心的一張卡
```

這直接回應審查報告 DA 的 M3（審核疲勞替代解釋），而且是**唯一能證明「摩擦是設計不是失控」的方式**：一個會主動限制自己索取使用者時間的系統，才有資格說摩擦是 feature。

### 5.3 【P0】把分層架構寫進憲章，並先做 M4.7a Vault Governance Reader

**兩件事，順序不能反：**

**(a) 先修文件，確立分層立場。** 這不是文書工作，是所有後續模組設計的前提：

- `02_architecture.md` §1 的四層架構圖上方，新增 **Layer 0：Obsidian Vault（底層 / System of Record）**，並在 §3 隱私分層表新增一列：「**Vault 檔案 = L3-local**——已核准的結構化事實，經 `obsidian-git` 跨裝置同步，因此 L1 明文永不寫入」
- `01_product_vision.md`「不是什麼」的第二條改寫（見 §1 建議表述）
- `04_module_registry.md` 的 M4.7 拆為 M4.7a / M4.7b，並補上 M4.7c（事件匯流排橋接）
- `CLAUDE.md` 新增一條鐵則：「**任何寫入 Vault 的行為必須經 `.coos_inbox/` 契約，不得由 Python 直接改 `.md`**」

**(b) 再做 M4.7a Vault Governance Reader。** 見 §3.5。它把兩年的手工本體論一次變成 coOS 的初始狀態——目前 coOS 冷啟動時 role 空、goals 空、heatmap 回傳 `[]`，而底層有 10 個 Role（含 mission）、130 個 Skill、45 個 active Project、6 條 Principle 現成可用。

估計工作量：Vault 是純 Markdown + YAML frontmatter，用 `python-frontmatter` 解析即可，約 500 行覆蓋 Roles / Domains / Skills / Principles / Projects / Global Settings。**這是全報告投入產出比最高的一項。**

> **設計提醒**：Reader 必須是**唯讀 + 週期重掃**，不做一次性 import。因為底層會持續被你手動編輯（新增 Role、改 Principle），coOS 必須跟著變，而不是拿一份過期快照。建議 `obsidian-git` commit 後觸發重掃，或每次 coOS 啟動時掃一次（11k 檔案的 frontmatter 掃描在幾秒內）。

### 5.4 【P1】薩提爾：要嘛做輕量版，要嘛從定位第一句話下架

目前狀態（`R04` 全套 DGNN + Hawkes + Neo4j + NSVIF）對 N=1 的資料量是嚴重過度工程。建議**輕量冰山**：

- **不做** Neo4j / DGNN / Hawkes 過程
- **改做** SQLite 一張 `m5_1_iceberg_claims` 表：`layer`（7 層 enum）、`content`、`evidence_log_ids`（JSON array，指向 `raw_tracking_logs`）、`confidence`、`created_by`、`user_confirmed`
- **NSVIF 降級為符號檢查**：`[R04 §反溯因驗證]` 的核心其實只需要「這條洞察有沒有對應的行為證據？沒有就丟棄」。這在 SQL 層就能做，不需要 D-ALP
- **復用既有機制**：`m4_2_persona/claim_ledger.py` 已經在做「事實宣稱一致性檢查」，冰山宣稱可以走同一套

**關鍵設計**：冰山節點必須 `user_confirmed`。AI 只能提出假設，使用者確認才升級為圖譜事實——這同時是 `[R08 §五 草稿與核准]` 在心理建模場域的延伸，也回應了 R2 審查者關於「深層心理建模的責任邊界」的批評。

**若不做**：請把 `01_product_vision.md` 與 README 第一句的「薩提爾冰山心理模型」改為「薩提爾冰山模型啟發的分層反思架構」，避免名實落差。

### 5.5 【P1】凍結第二波遊戲化

建議明確凍結（不是砍，是寫進文件說明理由後暫停）：

| 模組 | 凍結理由 |
| --- | --- |
| M3.11 Gacha | 反 KPI 的執行機關（mood_score）不存在前引入變動比例增強，等於在沒有煞車的情況下踩油門。`RISK-09` 已預警 |
| M4.11 ZPD 任務池 | 需要 M4.8 的能力估計作輸入，而 M4.8 已推遲 |
| M4.12 隱藏成就 | 邊際價值低 |
| M7.1 生圖管線 | 純美術，可用 Vault 既有的 130 張 Badge 圖 |

**理由的根**：Vault 的 XP 系統是同一設計哲學的先驗實驗，它沒有救活那套系統。在拿到 5.1 的證據之前，再加一層外在獎勵是拿 `RISK-09` / `RISK-10` 換不確定的留存。

### 5.6 【P1】補上「人生階段（Period / Season）」這個一級概念

Vault 的 `_System/Global Settings.md` 的 `active_period: 2026_spring_semester` 是整個 Vault 最聰明的設計：同一個 Routine 在不同人生階段有不同的 `xp_value` / `freq` / `status`（見 `Routine - 倒垃圾.md` 的 `periods:` 巢狀欄位）。

coOS 完全沒有這個概念。對「自主學習者 + 大學生」這個目標受眾，學期 / 期末週 / 寒暑假 / 實習期的認知負荷差異是數量級的。沒有 period，M1.2 的斷點閾值、M4.4 的套問頻率、M1.7 的摩擦預算全都只能用一組固定參數。

建議：`m6_3` 新增 `life_periods` 表 + `active_period` 全域狀態，所有心理參數改為 `period` 的函數。

### 5.7 【P1】UX 轉向：從「儀表板」到「今日一張卡」

`manual_test_log.md` 的抱怨集中在一個模式：**資訊密度過高**（board 擠爆、標記重複、氣泡太長、聊天室狀態遺失）。而 `01_product_vision.md` 的目標是每日 3~7 分鐘。

3~7 分鐘的產品不該有拖拉式 Widget 網格、圓餅選單、3D Coverflow、邊緣導航。建議把主入口收斂為：

```
今日一張卡：
  [AI 觀察到的 2-3 個時段]  ← 可展開，預設收合
  [一個問題]                ← 來自 Persona，一次只問一個
  [兩個必填欄位]            ← 微摩擦力
  [核准]
其他一切（社群、成就、技能樹、儀表板）藏在第二層
```

現有的儀表板不必刪，改為「探索模式」的第二層入口即可。

### 5.8 【P1】Persona 語氣的硬約束化

把 `manual_test_log.md` 的觀察直接寫進 PersonaCard v2 schema 與 `message_splitter`：

```python
# [R05 §跨越恐怖谷] 過度自我介紹是最強的 AI tell
GREETING_MAX_CHARS = 40           # 首次問候硬上限
BUBBLE_MAX_SENTENCES = 3          # 一般氣泡
BUBBLE_MAX_SENTENCES_EMOTIONAL = 20  # 情緒場景例外，且需 trust_level > 0.7
QUESTIONS_PER_BUBBLE = 1          # 一氣泡一問題（真人不會連問三個）
# 延遲改為字數函數，而非固定值
delay_ms = len(bubble) / TYPING_CPS * 1000 + random.gauss(300, 100)
```

另外把 `_FORBIDDEN_PHRASES` 從「我是AI」這類擴充到催促語氣模式（「別浪費時間在…」「與其…不如…」「既然你…就直接…」），這些在 `manual_test_log` 裡被明確標記為「沒有共情、沒有溫度」。

### 5.9 【P2】隱私宣稱的前後一致化

- `02_architecture.md` §3 隱私三層表新增一列：「**L1 例外：使用者主動發送之對話訊息**——經知情同意通道送往雲端 LLM，送出前強制 `eguard.mask_pii()`」
- 補上 `mask_pii` 呼叫（`m2_3_eguard` 已有函式，成本極低）
- 修 `GAP-C2`，讓 `DEVIATION-09` 的本地回退通道真的可用
- 在 UI 上讓使用者看得見：對話框旁一個小圖示標示「本則將送往雲端 / 僅在本機處理」

---

## 6. 建議路線圖

> 📄 Now 這一段的完整範疇、驗收契約與拍板事項，見 **`PHASE1_SCOPE_AND_ACCEPTANCE.md`**。

### Now（4 週）— 確立分層 · 證據 · 冷啟動

1. §5.3(a) 把「Vault = Layer 0 底層」寫進 `02_architecture.md` / `01_product_vision.md` / `04_module_registry.md` / `CLAUDE.md`
2. §5.3(b) M4.7a Vault Governance Reader（唯讀 + 週期重掃）
3. §5.1 N=1 使用數據報告（含 Vault 衰減曲線作 baseline）
4. §5.9 `mask_pii` 補上 + 隱私表加註 L1 例外 + 新增「Vault = L3-local」列
5. 修 `GAP-C3`（套問 confidence 檢查）、`GAP-C8`（turn counter）

### Next（8 週）— 把哲學變成執行機關 · 接通回寫

6. §3.6 M4.7c 事件匯流排（`.coos_outbox/` ↔ `.coos_inbox/` + `applyCoosInbox.js`）
7. §3.5 M4.7b Vault Writer with Contract（XP 回寫 Skill note、日報寫進 Daily 的 Save Point）
8. §5.6 人生階段（Period）一級概念——直接讀底層的 `active_period`
9. §5.2 M1.7 摩擦預算控制器
10. §5.8 Persona 語氣硬約束 + `message_splitter` 重寫
11. §5.7 「今日一張卡」主入口收斂
12. 反 KPI 計算器（先做能算的：核准率、互動時長、Persona 一致性抽測）

### Later — 深度與擴張

13. §5.4 輕量冰山（`m5_1_iceberg_claims` + 符號驗證 + user_confirmed）
14. M1.5 微 Nudges（規則來源 = Vault Principles 的 The Algorithm）
15. M4.4.3 Gibbs 模板對齊底層既有五段式，補上「突觸連結」段（連回 `Resource/Concepts`）
16. 專案健康度回報：coOS 偵測 30 天無遙測活動的 Project → 提議降級為 `on_hold`（解底層 45 個 active 的 WIP 超載）
17. 解凍評估：拿到 §5.1 的數據後，重新評估 M3.11 / M4.11 / M4.12

---

## 7. 需要你拍板的問題

| # | 問題 | 為何需要你決定 |
| --- | --- | --- |
| Q1 | 薩提爾冰山：做輕量版，還是從定位第一句話下架？ | 屬「研究約束的鬆綁」，`CLAUDE.md` 明定須使用者拍板 |
| Q2 | 分層架構是否正式入憲？（Vault = Layer 0 底層，coOS = 高階介面） | 屬跨模組職責邊界調整，須寫進 `02_architecture.md` 與 `CLAUDE.md` |
| Q2b | 等級公式統一為哪一套？（全域 `floor(0.1√XP)` vs 技能 `floor(√(XP/100))+1`） | 兩層要顯示同一個等級，必須先統一 |
| Q2c | `.coos_inbox/` 的落地是自動（開機執行）還是手動（QuickAdd 按一下）？ | 影響 `[R08 §五 意圖脫鉤]` 的強度：手動 = 多一道心理所有權關卡，但多一次摩擦 |
| Q3 | 「不存內容只建模狀態」改寫為「不擁有內容的所有權」是否接受？ | 目前程式碼已違反字面定義；分層架構下語意需重述 |
| Q4 | 第二波遊戲化凍結是否接受？ | 影響 Phase 6b 全部規劃 |
| Q5 | Vault 衰減曲線是否願意寫進期末報告作為前測證據？ | 學術上極有價值，但屬個人資料揭露，你決定 |
| Q6 | 摩擦預算的上限值：沿用 vision 的 7 分鐘，還是實測後再定？ | 影響 M1.7 的硬編碼常數 |

---

## 附錄 A：本報告的證據來源

| 宣稱 | 驗證方式 |
| --- | --- |
| M5 未實作 | `ls services/` 無 `m5_*`；`grep -rn "neo4j" services/` 僅見設定 |
| Vault Daily 衰減 | `ls Executive/Period/Daily \| cut -c1-7 \| sort \| uniq -c` |
| Vault XP 衰減 | `grep -rhoE "20[0-9]{2}-[0-9]{2}-[0-9]{2}: \+[0-9]+ XP" Governance/Skills/*.md` → 268 條，按月 86/86/44/35/2/15 |
| Governance/Visions 為空 | `ls -a Governance/Visions` → 僅 `.` / `..`，但 Domain 頁面有 `FROM "Governance/Visions"` 查詢 |
| `00 Inbox` 不存在 | Domain 與 Role 頁面均有 `FROM "00 Inbox"` 查詢，資料夾已不存在 → 死查詢 |
| 45 個 active 專案 | `grep -h "^status:" Executive/Projects/*.md \| sort \| uniq -c` |
| 模組行數 | 逐目錄 `find -name "*.py" \| xargs wc -l` |
| M4.7 零程式碼 | `ls services/` 無 `m4_7_*`（與 `GAP-A1` 一致，該 GAP 於 2026-06-10 拍板移至 Phase 6） |
| 測試數 446 | `README.md` 專案現況 + `CLOSURE_REPORT_PHASE_5.5.md` §1 |
| 全域等級公式 `floor(0.1√XP)` | `_System/Scripts/calculateRPGStats.js:303`；門檻 `:307` `(L/0.1)²` |
| 技能等級公式 `floor(√(XP/100))+1` | Role note 與 Skill note 的 DataviewJS 區塊 |
| XP 六大來源與權重 | `calculateRPGStats.js` `XP_WEIGHTS` + `xp_breakdown` 回傳欄位 |
| 一天邊界為凌晨 5 點 | `claimXP.js` v6.4 `getLogicalToday()` |
| 事件匯流排已存在 | `calculateRPGStats.js` 寫 `_System/.level_up_trigger.json` → `_System/Scripts/level_up_notifier.py` watch 並生圖寄信 |
| 19 份 Templater 模板 | `ls _System/Templates/` |
| Vision Template 含角色衝突解決 | `_System/Templates/Vision Template.md` §Multi-Track Scenarios / §Conflict Resolution |
| 五段式反思鷹架早於 coOS | `ai_architecting/obsidian design.md`（65,729 行）第 1234–1264 行 |
| Vault 已在雲端同步 | `.obsidian/plugins/obsidian-git`；`Project - Obsidian Personal Life OS.md` 「github 裝置間同步」已勾選 |

## 附錄 B：本報告未涵蓋的範圍

- 未執行 `pytest`（本次為唯讀稽核，未啟動後端）
- 未驗證 Rust 端 (`apps/desktop/src-tauri`) 的實作完整度
- 未逐條檢視 40 份模組 SPEC 的內部一致性
- 未評估 `Resource/People` (1,176) 與 `Resource/Media` (1,467) 的資料品質（疑似 Notion 批量匯入，未經人工整理）
- 未涵蓋商業模式與市場面
