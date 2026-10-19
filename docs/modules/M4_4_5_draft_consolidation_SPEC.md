# M4.4.5 — 草稿收斂器 (Draft Consolidation)

**標籤**:`[MVP]`
**狀態**:`draft`
**版本**:`0.1.0`
**最後更新**:2026-10-19
**最後變更**:`initial`

> **來源**:`MVP_CLOSURE_REPORT.md` §7.3 **W6** (D-2 衍生,最高優先、非 GO 條件,建議在 M5 動工前完成)。
> **為什麼編號是 M4.4.5 而不是 M4.4b**:
> 1. M4.4 一直用**點號子模組**編號 (`04_module_registry.md` 的 M4.4.1 套問 / M4.4.2 NER / M4.4.3 深夜排程),檔名也有 `M1_3_1_*_SPEC.md` 的先例。字母後綴 (M4.7a/b/c) 在本專案的語意是「把一個模組拆成可各自交付的獨立產物」;收斂是**同一條草稿管線**裡的一個新階段,應沿用點號。
> 2. **M4.4.4 已被程式碼佔用**:`services/m4_4_elicitation/role_inference.py` 的檔頭是「M4.4.4 -- Role Attribution Inference」,`services/main.py:390` 與 `testing/m4_4/test_natural_elicitation_draft.py:366` 也用這個編號,但 registry 沒有登記 (§9 Q9)。因此收斂取下一個空號 **M4.4.5**。
> 3. 管線順序剛好對應編號:M4.4.3 拼區塊 → M4.4.4 歸角色 → **M4.4.5 收斂成卡** → M6.4 寫入。

---

## 1. Purpose (目的)

在 M4.4.3 拼出的活動區塊寫入 M6.4 之前,把同一角色、同一天的區塊依「已知專案 / 主題」收斂成**每個專案或主題一張草稿卡**,並讓每張卡的標題就是使用者認得的那件事的名字;本模組只改變草稿的**粒度與標題**,不改變核准規則、必填欄位或 XP 守門。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R08 | §三 醫療級警報疲勞防範 | 198 張草稿 0 張核准 (使用者自述「分散過多、辨識不清」) 是警報疲勞在草稿上的表現:每天 ~16.5 張低辨識度卡片,使用者無法逐一判斷。收斂的目標是降低每日需要判斷的張數,並讓每一張都值得判斷 (REQ-M4.4.5-01、03) |
| R08 | §四 微摩擦力的必要性 (§四.2) | 收斂減少的是**卡片數量**,不是**每張卡的摩擦**:每張收斂卡仍必須由使用者親手填 `user_feeling` 與 `user_action_plan` 才能核准 (REQ-M4.4.5-06) |
| R08 | §六 IKEA 效應與結構化反思 (§六.1) | 收斂器永遠產出 `is_draft=1, is_reviewed=0`,不自動核准、不代填 (REQ-M4.4.5-06) |
| R08 | §五 意圖脫鉤與作者身分五大設計模式 | AI 只負責分組與客觀描述;分組鍵優先採用使用者自己命名的 Vault 專案名,而不是 AI 取的名字 (REQ-M4.4.5-02、03) |
| R10 | §MindScape 反思鷹架 | 鷹架必須具體到能喚起記憶;「VS Code(42 分鐘)」喚不起記憶,「coOS 期末專題」可以。標題規則見 REQ-M4.4.5-03 |
| R11 | §3.3 Reflection (定期觀察昇華) | 把低階觀察 (一分鐘級的 focus session) 依共同主題聚合成高階單位後再反思,而不是逐筆觀察反思 (REQ-M4.4.5-02) |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M4.4.3 `merge_into_blocks()` 的輸出 | `list[DaySignals]` (§7.2 新增 `log_ids`、`start_iso`) | 一天 30–110 個區塊 |
| M4.4.4 `infer_role()` 的歸屬結果 | `(role_id, score, confident)` | 只收斂已歸屬到**當前角色**的區塊 |
| M6.3 `role_projects` (`status='active'`,含 M4.7a 投影的 `source='vault'` 列) | `{id, role_id, name, description, source, vault_id}` | `{"name": "coOS 期末專題", "source": "vault"}` |
| M4.6 `topic_anchors` (`role_id` 範圍、`status='active'`、`last_seen` 在 `TOPIC_RECENCY_DAYS` 內) | `{id, role_id, label, intent, motivation}` | `{"label": "了解微積分極限的學習意義"}` |
| M4.6 `topic_sessions` (當天) | `{topic_id, thread_id, recorded_at}` | 當天聊過的主題 → 分組先驗 |
| M4.4.2 `task_slots` (當天已確認) | `{project, duration_minutes}` | 使用者自述「微積分花了兩小時」 |
| M2.2.2 `intent_logs` `source_type='chat_digest'` (當天) | `{intent_label, context_summary}` | 只作比對證據,本版不自行產生卡片 (§9 Q4) |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M6.4 `daily_reflection_segments` (每個分組一列) | 既有欄位 + 新增 `group_key`, `group_source`, `group_label`, `block_count`, `blocks_json`, `source_log_ids_json` (§7.2) | `{title: "coOS 期末專題", group_source: "vault_project", block_count: 7, activity_minutes: 190, start_time: "09:12", end_time: "17:40", is_draft: 1, is_reviewed: 0}` |
| M0.4 `raw_tracking_logs` | `{source: "M4.4.5", action: "draft_consolidation_summary", payload: ConsolidationSummary}` | 見 §7.2;是本模組驗收指標的資料來源 |
| M0.4 `raw_tracking_logs` | `consolidation_group_already_reviewed` / `consolidation_classifier_invalid_output` / `card_budget_folded` | 異常與降級事件 |

**不輸出**:不寫 `user_feeling`、`user_action_plan`、`user_learned`、`is_reviewed`、`xp_settled`;不呼叫雲端 LLM 做分組。

## 4. Dependencies

### 上游 (我依賴誰)

- **M4.4.3** (深夜排程 / `gibbs_template.py`):提供區塊 (`group_signals` → `merge_into_blocks`) 與卡片描述產生器 (`_generate_card`)。本模組在兩者之間插入「分組」並把描述產生改為**每組一次**
- **M4.4.4** (角色歸屬 / `role_inference.py`):先決定區塊屬於哪個角色,收斂只在角色內進行
- **M4.6** (Observer):`topic_anchors` / `topic_sessions` (commit `322e086`,2026-08-07) 是第二優先的分組鍵
- **M6.3** (`role_projects`):第一優先的分組鍵;其中 `source='vault'` 的列由 M4.7a 投影
- **M2.2** (本地 Gemma,選用):封閉選項分類 (§7.1 第 3 段);不可用時退回確定性比對
- **M2.3** (Eguard):`title_generalized` / `ai_description_generalized` 的泛化 (RISK-15)
- **M6.4** (`daily_reflection_segments`):寫入目標;需新增欄位 (§7.2,§9 Q7)

**M4.7a 是軟依賴**:M4.4.5 只讀 `role_projects`,不 import `m4_7a_vault_reader`。M4.7a 不存在時,分組鍵只剩 M4.6 主題錨點與 AI / 手動專案,功能照常 (憲章第五條,REQ-M4.4.5-09)。

### 下游 (誰依賴我)

- **M3.3.3** (草稿核准彈窗):核准單位仍是一列 segment;收斂後一張卡 = 一次核准。前端 `DraftApproveModal` 的兩欄必填邏輯不變
- **M6.4** `GET /api/m6_4/topic_groups` (`main.py:2504`):目前每次讀取時用 Gemma 或關鍵字重新分群,且 Gemma 分支因 `from config import settings` 永遠失敗 (LOOP-06)。收斂後應**優先依 `group_key` 分組**,不再即時重分 (需 M6.4 spec delta,§9 Q8)
- **M4.5 / M6.5** (XP 結算):以 segment 為單位結算 (`/api/m4_5/grant_xp` 預設 `amount=20`,前端不帶 `amount`)。卡片變少 → 每日可得 XP 上限變少 (§9 Q2)
- **M4.5.2** (殭屍草稿清理,7 天門檻,D-2 維持):對收斂卡照常運作
- **M5.2** (證據萃取,`[進階]`):只讀**已核准**的反思;每張卡的 `source_log_ids_json` 必須只含自己的區塊,證據才不會錯置

## 5. Known Risks (整合風險)

稽核方式:`grep -n "^## RISK-" docs/05_integration_risk_audit.md`,再以 `M4\.4|M6\.4|M4\.5|M4\.6|M3\.3` grep;觸及 M4.4.3、M4.4.4、M4.6、M6.3、M6.4、M3.3.3、M4.5 七個模組。

| 風險編號 | 描述 | 緩解策略 | 測試 |
| -------- | ---- | -------- | ---- |
| **RISK-01** | 收斂時若沿用 / 合併使用者已填內容或自動標核准 → IKEA 效應失效、未核准即發 XP | 收斂器只產生新草稿或更新**未核准**草稿;主觀欄位恆為 `NULL`;`is_reviewed` 恆為 0 | `test_consolidated_cards_are_always_drafts`、`test_rerun_never_touches_reviewed_segments` |
| **RISK-06** | Vault 專案關聯多個角色,或主題錨點跨角色比對 → 區塊被收進別的角色的卡 | 先 M4.4.4 歸角色,再於**同一角色**的候選鍵中分組;候選鍵查詢一律帶 `role_id`;歸不進任何鍵 → 未歸類,不跨角色借鍵 | `test_grouping_keys_scoped_to_role` |
| **RISK-13** | 重跑排程時刪掉舊 segment 重建 → 已核准 / 已結算的卡失去根據 | 重跑只 UPDATE 同 `(reflection_id, group_key)` 的未核准草稿;已核准的分組不動,新區塊只記 log;從不 DELETE | `test_rerun_never_touches_reviewed_segments`、`test_rerun_is_idempotent` |
| **RISK-15** | 收斂卡的描述把多個區塊的 `content_summary` 疊在一起;標題用到 Vault 專案名 → 雲端欄位可反推具體工作 | `content_summary` 只進本地 Gemma 與 L1 欄位;分組分類只用本地 Gemma 或確定性比對;`title_generalized` / `ai_description_generalized` 一律經 Eguard。已知既存偏離:`paper_eval_data` 記錄 198 列的 generalized 欄位與原文逐位元組相同 (Eguard 實質未泛化),**非本次造成**,應登記至 `SPEC_DEVIATION_REPORT.md` (§9 Q10) | `test_cloud_fields_exclude_content_summary`、`test_classifier_never_uses_cloud_llm` |
| **RISK-24** | 用 M0.5 合成資料「證明」收斂有效 → 論文 N=1 指標被污染 | 真實指標只由 `real_data` 重放測試以 `mode=ro` 讀真實 DB 產生;合成資料只能驗機制,不得寫進「真實使用」指標 | `test_replay_metrics_refuse_synthetic_db` |
| **候選 RISK-27** (未登記) | **收斂 + 核准 → 錯誤歸組被使用者核准成事實**:區塊被歸到錯的專案,使用者在疲勞下照單核准 → 錯誤反思進入 M5.2 證據與 M4.7b 寫回 Vault;另一面是「大雜燴卡」:為了壓低張數把不相干的事塞進同一張,卡片又變得辨識不清 | (1) 寧可未歸類,不要歸錯:分數門檻 + 與第二名的差距門檻,不足即未歸類 (與 RISK-06「寧可中性,不要錯」同原則);(2) 每張卡的描述列出每個區塊的時段,讓使用者核准前能看出放錯;(3) 未歸類依 app 家族分卡,不收成單一大雜燴;(4) 張數上限的超額摺疊只摺**最小**的分組,且摺疊卡列出被摺入的分組名 | `test_low_margin_match_goes_unmapped`、`test_unmapped_split_by_app_family`、`test_card_budget_folds_smallest_groups` |

> 依 `audit-integration` 規定,新風險須先登記到 `05_integration_risk_audit.md`。本次任務限定只建立兩個 SPEC 檔,**未修改 05**;候選 RISK-27 的登記列為 §9 Q6。

**已審查、判定未觸發**:RISK-04 (收斂在 02:00 批次執行,不推播)、RISK-14 (不改 XP 的加總方式;卡片數對 XP 總量的影響列為 §9 Q2)、RISK-08 (不把 Observer 推論注入 Persona,只拿主題標籤當分組鍵)。

## 6. Requirements & Acceptance (需求與驗收)

**測試檔**:`testing/m4_4/test_draft_consolidation.py` (沿用 `testing/m4_4/` 目錄;M4.4 的子模組共用一個測試目錄)。
**Fixture**:`testing/m4_4/fixtures/fragmented_day.json`——**合成的**一天:2 個角色、112 個 focus session (多為 1–5 分鐘)、3 個 Vault 專案、2 個主題錨點、1 筆 `task_slots`、若干娛樂瀏覽。所有測試使用 tmp SQLite (CLAUDE.md 除錯備忘 #7),LLM 一律以確定性替身注入。
**真實資料重放**:marker `real_data`,只有設了環境變數 `COOS_REPLAY_DB` 才執行,以 `file:...?mode=ro` 唯讀開啟、結果寫到 tmp DB。預設 CI 不跑。

**基線 (收斂前,已量測)**:2026-06-09 ~ 06-23 共 12 個活躍日產生 198 個 segment,**平均約 16.5 張 / 日**,核准 **0** 張 (`paper_eval_data`;`MVP_CLOSURE_REPORT.md` §5)。

### 量化驗收指標

所有指標由 `draft_consolidation_summary` (§7.2) 計算,REQ-M4.4.5-08 保證每次執行都會寫出。

| 代號 | 指標 | 定義 | 目標 (預設,待 §9 Q1 拍板) | 怎麼驗 |
| ---- | ---- | ---- | ---- | ---- |
| **K1** | 每日卡數 | 一個使用者一天、所有角色的收斂卡總數 | ≤ `DAILY_CARD_BUDGET` = **6** | 自動 (fixture + 重放) |
| **K2** | 降幅 | 1 − 收斂後卡數 / 收斂前卡數 (同一天、同一輸入重放) | ≥ **60%** | 自動 (重放) |
| **K3** | 已知專案對應率 (按卡) | `group_source ∈ {vault_project, topic_anchor, role_project}` 的卡 / 全部卡 | ≥ **60%** (該角色至少有 1 個已知專案或主題時) | 自動 |
| **K4** | 已知專案對應率 (按時間) | 已對應卡的 `activity_minutes` 加總 / 全部 `activity_minutes` | ≥ **70%** (同上條件) | 自動 |
| **K5** | 標題可辨識 (形式) | 已對應卡 `title == group_label` (Vault 專案名 / 主題錨點原文),未歸類卡以 `未歸類 · ` 開頭;沒有任何卡的標題只有程式名或「其他應用」 | **100%** | 自動 |
| **K6** | 標題可辨識 (保真) | 使用者看標題 3 秒內能說出「這是哪件事」的卡 / 全部卡 | ≥ **90%** | **人工 L2**:使用者對重放出的一天逐張判定並記錄,AI 不得代判 (`PHASE1_SCOPE_AND_ACCEPTANCE.md` §3) |
| **K7** | 核准率 (體感) | 連續 7 天內被核准的收斂卡 / 全部收斂卡 | 不設門檻,只記錄 (L3) | 實測;對照基線 0% |

### REQ-M4.4.5-01:一個角色一天,每個分組鍵恰好一張卡

系統 SHALL 對每個 `(user_id, role_id, reflection_date)`,把歸屬到該角色的區塊依分組鍵 (§7.1) 收斂,每個分組鍵恰好產生一列 `daily_reflection_segments`;卡片數 = 命中的已知鍵數 + 未歸類卡數 (未歸類卡依 app 家族,每角色最多 `MAX_UNMAPPED_CARDS_PER_ROLE` = 2 張)。

依據:`[R08: 警報疲勞 §三]` `[R11: Reflection §3.3]`

#### Scenario:112 個碎片收斂到預算內

- **GIVEN** `fragmented_day.json` (112 個 focus session,3 個 Vault 專案、2 個主題錨點皆有對應活動)
- **WHEN** `run_draft_cron(user_id, db, today=fixture_date + 1)`
- **THEN** 兩個角色的 segment 總數 ≤ 6 (K1);同一角色內沒有兩列 `group_key` 相同

測試:`test_fragmented_day_collapses_within_budget`

#### Scenario:同一專案分散在一天各時段仍是一張卡

- **GIVEN** 「coOS 期末專題」的活動出現在 09:12–10:05、13:30–15:10、16:50–17:40 三段,中間夾著別的活動
- **WHEN** 收斂
- **THEN** 恰有一張 `group_label == "coOS 期末專題"` 的卡,`block_count == 3`,`activity_minutes` 等於三段時長加總 (不是 09:12–17:40 的跨度)

測試:`test_non_contiguous_blocks_same_project_single_card`

### REQ-M4.4.5-02:分組鍵的優先順序與比對規則

系統 SHALL 依下列順序為每個區塊決定分組鍵,先命中者勝:

1. 當天 `task_slots` 中使用者自述的專案名,與某個候選鍵名稱正規化後相等 → 該鍵
2. 確定性比對 (§7.1):Vault 專案 (`source='vault'`) → M4.6 主題錨點 → 其他 `role_projects`;分數 ≥ `GROUP_MATCH_THRESHOLD` 且領先第二名 ≥ `GROUP_MATCH_MARGIN`
3. (本地 Gemma 可用時) 對前兩步未命中的區塊做**封閉選項**分類:只能回傳候選鍵 id 之一或 `none`;回傳值不在選項內 → 視為 `none` 並記 `consolidation_classifier_invalid_output`
4. 其餘 → 未歸類,依 app 家族 (`_APP_FAMILY`:dev / web / doc / 其他) 分組

依據:`[R08: 意圖脫鉤 §五]` `[R11: Reflection §3.3]` 風險:`RISK-06`、候選 RISK-27

#### Scenario:Vault 專案優先於同義的主題錨點

- **GIVEN** 區塊內容同時命中 Vault 專案「coOS 期末專題」與主題錨點「把 coOS 做成能每天用的系統」,分數相同
- **WHEN** 收斂
- **THEN** 該區塊歸入 `group_source == "vault_project"` 的卡

測試:`test_vault_project_outranks_topic_anchor`

#### Scenario:使用者自述的專案名直接決定分組

- **GIVEN** `task_slots` 有 `{project: "微積分期末考", duration_minutes: 120}`,且區塊內容與其他鍵的 token 重疊較高
- **WHEN** 收斂
- **THEN** 落在該自述時段的區塊歸入「微積分期末考」

測試:`test_elicited_project_name_wins`

#### Scenario:差距不足時寧可未歸類

- **GIVEN** 區塊對 A、B 兩鍵的分數分別為 0.41、0.38 (差距 < `GROUP_MATCH_MARGIN`),Gemma 不可用
- **WHEN** 收斂
- **THEN** 該區塊進入未歸類卡,不進 A 也不進 B

測試:`test_low_margin_match_goes_unmapped`

#### Scenario:分類器輸出不在選項內

- **GIVEN** Gemma 替身回傳 `{"key": "我覺得是 coOS"}` (不是任何候選 id)
- **WHEN** 收斂
- **THEN** 該區塊未歸類;`raw_tracking_logs` 有一筆 `consolidation_classifier_invalid_output`

測試:`test_classifier_out_of_set_output_rejected`

#### Scenario:分組鍵只來自當前角色

- **GIVEN** 角色 CSIE 有專案「coOS 期末專題」;角色 FAMILY 沒有任何專案;一個區塊經 M4.4.4 歸屬到 FAMILY,內容提到 coOS
- **WHEN** 為 FAMILY 收斂
- **THEN** 該區塊進入 FAMILY 的未歸類卡;FAMILY 沒有 `group_label == "coOS 期末專題"` 的卡

測試:`test_grouping_keys_scoped_to_role`

### REQ-M4.4.5-03:標題一眼可辨

系統 SHALL 讓已對應卡的 `title` **逐字等於** `group_label` (Vault 專案名或主題錨點原文,不加程式名、不加時長、不經 LLM 改寫);未歸類卡的 `title` 為 `未歸類 · <app 家族中文名>` (例:`未歸類 · 開發工具`)。時長與時段放在既有的 `activity_minutes` / `start_time` / `end_time` 欄,由前端顯示。

依據:`[R10: MindScape §反思鷹架]` `[R08: 意圖脫鉤 §五]`

#### Scenario:已對應卡的標題就是專案名

- **WHEN** fixture 收斂完成
- **THEN** 所有 `group_source != "unmapped"` 的卡 `title == group_label`;沒有任何卡的 `title` 符合 `^(VS Code|Edge|Chrome|其他應用|程式開發).*（\d+ 分鐘）$` 這類舊格式 (K5)

測試:`test_mapped_card_title_equals_group_label`

#### Scenario:LLM 產生的標題不得覆蓋專案名

- **GIVEN** Gemma 替身對該組回傳 `{"title": "今天很努力寫程式", "description": "..."}`
- **WHEN** 收斂
- **THEN** 卡片 `title` 仍是 `group_label`;LLM 的 `description` 照常採用

測試:`test_llm_title_does_not_override_group_label`

### REQ-M4.4.5-04:描述保留可核對的證據

系統 SHALL 在每張卡的 `ai_description` 中逐行列出組內每個區塊的時段與時長 (`HH:MM–HH:MM · N 分鐘`),再接 LLM 或模板產生的客觀描述;每張卡的 `source_log_ids_json` 只包含**該組區塊**的 `raw_tracking_logs.id`,且非空。

依據:`[R08: 意圖脫鉤 §五]` 風險:候選 RISK-27

#### Scenario:每個區塊的時段都看得到

- **GIVEN** 「coOS 期末專題」組有 3 個區塊
- **WHEN** 收斂
- **THEN** 該卡 `ai_description` 含 3 行符合 `\d{2}:\d{2}–\d{2}:\d{2} · \d+ 分鐘` 的時段行,順序依時間

測試:`test_description_lists_every_block_span`

#### Scenario:證據 id 不錯置

- **WHEN** 收斂後取所有卡的 `source_log_ids_json`
- **THEN** 每張卡皆非空;任兩張卡的集合交集為空;所有卡的聯集 = 當天被歸屬到該角色的區塊的 log id 聯集

測試:`test_source_log_ids_partitioned_per_card`

> 現況對照:`draft_scheduler.generate_draft` 只把 `source_log_ids` 給第一張卡 (`source_log_ids if emitted == 0 else []`),其餘為空。本需求取代該行為。

### REQ-M4.4.5-05:未歸類不成為大雜燴

系統 SHALL 把未歸類區塊依 app 家族分卡,每角色最多 `MAX_UNMAPPED_CARDS_PER_ROLE` 張 (超過時合併時長最短的家族);單一未歸類家族加總 < `MIN_CARD_MINUTES` 分鐘時併入同角色時長最長的未歸類卡,不單獨成卡。

依據:`[R08: 警報疲勞 §三]` 風險:候選 RISK-27

#### Scenario:開發與娛樂的未歸類分開

- **GIVEN** 未歸類區塊中有 dev 家族 80 分鐘、web 家族 45 分鐘
- **WHEN** 收斂
- **THEN** 恰有兩張未歸類卡:`未歸類 · 開發工具`、`未歸類 · 網頁瀏覽`

測試:`test_unmapped_split_by_app_family`

#### Scenario:零碎的未歸類不單獨成卡

- **GIVEN** doc 家族未歸類只有 6 分鐘 (< `MIN_CARD_MINUTES` = 15)
- **WHEN** 收斂
- **THEN** 沒有 `未歸類 · 文件` 卡;那 6 分鐘併入時長最長的未歸類卡,其描述有對應的時段行

測試:`test_tiny_unmapped_family_folded`

### REQ-M4.4.5-06:R08 不變式原封不動

系統 SHALL 讓每張收斂卡在寫入時 `is_draft = 1`、`is_reviewed = 0`、`xp_settled = 0`,且 `user_feeling`、`user_action_plan`、`user_learned` 為 `NULL`;`ai_analysis` 不得含主觀感受或行動建議;本模組不提供任何「整天一次核准」的捷徑,一張卡一次核准、兩欄必填的規則不變。

依據:`[R08: IKEA 效應 §六.1]` `[R08: 微摩擦力 §四.2]` `[R08: 意圖脫鉤 §五]` 風險:`RISK-01`

#### Scenario:收斂卡永遠是草稿

- **WHEN** fixture 收斂完成
- **THEN** 所有新列 `is_draft == 1 and is_reviewed == 0 and xp_settled == 0`;`user_feeling`、`user_action_plan`、`user_learned` 皆 `IS NULL`

測試:`test_consolidated_cards_are_always_drafts`

#### Scenario:只填一欄的收斂卡拿不到 XP (閉環)

- **GIVEN** 一張收斂卡,前端 PATCH 只帶 `user_feeling`
- **WHEN** 呼叫 `PATCH /api/m4_5/grant_xp`
- **THEN** `xp_ledger` 筆數不變 (沿用 W2 的 `GATEKEEPER_001` 守門)

測試:`test_feeling_only_consolidated_card_gets_no_xp` (跨 M4.4.5 / M6.4 / M6.5)

#### Scenario:分析欄不代替使用者感受

- **WHEN** 收斂完成
- **THEN** 每張卡的 `ai_analysis` 不含 `感到`、`覺得`、`應該`、`建議你` 等字樣 (既有 `_template_analysis` 只寫總時長、活動類別與狀態;此測試把「不寫主觀內容」的原則變成可執行的斷言)

測試:`test_ai_analysis_has_no_subjective_content`

### REQ-M4.4.5-07:重跑冪等,且不碰已核准的卡

系統 SHALL 在同一天重跑排程時:同一 `(reflection_id, group_key)` 的**未核准**草稿就地 UPDATE (不新增列);**已核准**的分組不新增、不修改,新進區塊只記 `consolidation_group_already_reviewed`;任何情況都不 DELETE segment。

依據:`[R08: IKEA 效應 §六.1]` 風險:`RISK-01`、`RISK-13`

#### Scenario:相同輸入重跑兩次,卡數不變

- **WHEN** 對同一天連續執行兩次收斂
- **THEN** 第二次後 segment 數與第一次相同;每列 `id` 不變

測試:`test_rerun_is_idempotent`

#### Scenario:已核准的卡在重跑後原封不動

- **GIVEN** 「coOS 期末專題」卡已由使用者核准且 `xp_settled = 1`;當天又補進一個屬於該專案的區塊
- **WHEN** 重跑收斂
- **THEN** 該卡所有欄位 (含 `ai_description`、`activity_minutes`) 不變;沒有新增同 `group_key` 的列;`raw_tracking_logs` 有一筆 `consolidation_group_already_reviewed`

測試:`test_rerun_never_touches_reviewed_segments`

### REQ-M4.4.5-08:每次收斂都留下可計算指標的摘要

系統 SHALL 在每個 `(role_id, reflection_date)` 收斂結束時寫一筆 `raw_tracking_logs{source: "M4.4.5", action: "draft_consolidation_summary"}`,payload 至少含:`blocks_in`、`cards_out`、`cards_by_source`、`mapped_minutes`、`unmapped_minutes`、`legacy_card_count` (同一輸入在收斂前管線會產生的卡數,即 `len(blocks)` 中歸屬到該角色者)、`folded_groups`、`classifier_used`、`llm_calls`。payload **不得**含任何 `content_summary`、標題或專案名原文 (只含計數與 id)。

依據:純工程 風險:`RISK-15`、`RISK-24`

#### Scenario:摘要足以算出 K1–K4

- **WHEN** fixture 收斂完成
- **THEN** 由各角色的摘要可算出 K1 (Σ`cards_out`)、K2 (1 − Σ`cards_out` / Σ`legacy_card_count`)、K3、K4,且與直接查 `daily_reflection_segments` 的結果一致

測試:`test_summary_supports_kpi_computation`

#### Scenario:摘要不含 L1 文字

- **WHEN** 收斂完成
- **THEN** 摘要 payload 序列化後不含 fixture 中任何 `content_summary` 片段或任何專案名字串

測試:`test_summary_contains_no_l1_text`

#### Scenario:真實重放達到目標 (L1 契約)

- **GIVEN** `COOS_REPLAY_DB` 指向真實 `data/coos.db` (唯讀),選定 2026-06 至 2026-09 之間至少 5 個有遙測的日子 (由使用者指定日期清單)
- **WHEN** 以 tmp DB 重放收斂
- **THEN** 每一天 K1 ≤ 6、K2 ≥ 60%、K5 = 100%;對至少有一個已知專案或主題的角色 K3 ≥ 60%、K4 ≥ 70%。結果寫成報告表,未達標的日子逐日列出,**不得**以放寬門檻通過 (憲章第四條)
- **AND** 若開啟的 DB `PRAGMA application_id` 為 M0.5 合成 sentinel → 直接失敗 (RISK-24)

測試:`test_replay_real_days_meets_kpis` (marker `real_data`)、`test_replay_metrics_refuse_synthetic_db`

### REQ-M4.4.5-09:不依賴 `[進階]` 模組,降級可預期

系統 SHALL 在以下情況仍完成收斂:沒有任何 `source='vault'` 專案 (M4.7a 未啟用)、`topic_anchors` 表不存在、本地 Gemma 不可達;此時跳過缺少的那一層分組鍵或分類器,其他層照常,並在摘要的 `classifier_used` / `cards_by_source` 反映實際狀況。

依據:純工程 風險:憲章第五條

#### Scenario:M4.7a 未啟用時只用主題錨點與 AI 專案

- **GIVEN** `role_projects` 沒有 `source` 欄位 (舊 schema) 或沒有 `source='vault'` 列
- **WHEN** 收斂
- **THEN** 成功;`cards_by_source` 沒有 `vault_project`;主題錨點命中的區塊仍各自成卡

測試:`test_works_without_vault_projects`

#### Scenario:topic_anchors 表不存在

- **GIVEN** tmp DB 未建立 `topic_anchors`
- **WHEN** 收斂
- **THEN** 成功,不拋例外;`raw_tracking_logs` 有一筆 `warning` 級紀錄說明該層被跳過 (不是靜默)

測試:`test_works_without_topic_anchor_table`

#### Scenario:分類器絕不走雲端

- **GIVEN** Gemma 不可達、`gemini_api_key` 有值
- **WHEN** 收斂
- **THEN** 沒有任何分組用途的 Gemini 呼叫 (以替身計數);未命中的區塊進未歸類;`classifier_used == "none"`

測試:`test_classifier_never_uses_cloud_llm`

### REQ-M4.4.5-10:每日卡數預算

系統 SHALL 在單一使用者單日的收斂卡總數 (跨角色) 超過 `DAILY_CARD_BUDGET` 時,從**時長最短**的分組開始,把同角色內的分組摺入一張 `其他時段` 卡,直到總數 ≤ 預算;摺疊卡的描述列出被摺入的每個分組名與時長,並記 `card_budget_folded`。不得為了符合預算而把已知專案併入另一個已知專案。

依據:`[R08: 警報疲勞 §三]` 風險:候選 RISK-27

#### Scenario:十個專案都有活動的一天

- **GIVEN** 一個角色當天有 10 個已知專案各有 10–60 分鐘活動
- **WHEN** 收斂
- **THEN** 卡數 ≤ 6;時長前 5 名各自成卡,其餘摺入一張 `其他時段` 卡,描述列出被摺入的 5 個專案名;沒有任何兩個已知專案共用同一張非摺疊卡

測試:`test_card_budget_folds_smallest_groups`

### REQ-M4.4.5-11:LLM 呼叫數不增反減

系統 SHALL 對每張卡最多呼叫一次描述產生 (`_generate_card`),對每個角色每天最多一次封閉選項分類 (把所有未命中區塊批次送入);因此單日 Gemma 呼叫數 ≤ 卡數 + 角色數,低於收斂前「每區塊一次」。

依據:純工程 (iPad M1 推論為單執行緒,`gibbs_template.build_gibbs_cards` 已序列化呼叫)

#### Scenario:呼叫數上限

- **GIVEN** fixture,Gemma 替身計數
- **WHEN** 收斂
- **THEN** 呼叫數 ≤ `cards_out + 角色數`,且 < `legacy_card_count`

測試:`test_llm_calls_bounded_by_cards`

#### Scenario:雲端欄位不含 content_summary

- **WHEN** 收斂完成
- **THEN** 每張卡的 `title_generalized`、`ai_description_generalized` 不含 fixture 的任何 `content_summary` 原文片段;送往 Gemini 描述 fallback 的 prompt (`_build_cloud_prompt`) 不含 `content_summary`

測試:`test_cloud_fields_exclude_content_summary`

## 7. Implementation Notes

### 7.1 演算法選擇

**管線位置** (`services/m4_4_elicitation/consolidator.py`,由 `draft_scheduler.generate_draft` 呼叫):

```
group_signals(logs)                    # M4.4.3,每個 focus session 一個 DaySignals
  → merge_into_blocks(signals)         # M4.4.3,相鄰同 app / 同主題合併,單塊上限 90 分
  → [M4.4.4] infer_role(block) 過濾出屬於當前角色的區塊
  → [M4.4.5] candidates = load_group_keys(role_id, date)
             assign = resolve_keys(blocks, candidates, task_slots, gemma?)
             groups = bucket(blocks, assign) + unmapped_by_family + budget_fold
  → 每組一次 _generate_card(merged_group_signals) 取得 description
  → title = group_label (REQ-03);description = 時段清單 + LLM/模板描述 (REQ-04)
  → upsert_segment(reflection_id, group_key, ...)   # REQ-07
  → log draft_consolidation_summary                  # REQ-08
```

**為什麼不在 `merge_into_blocks` 裡直接拉長合併**:`merge_into_blocks` 的兩個 pass 以「時間相鄰」為前提,並有 `_MAX_BLOCK_S = 5400` 上限,是正確的「區塊」定義。同一專案一天常分散在上午、下午、晚上 (REQ-01 第二情境),時間相鄰合併永遠做不到;分組必須是**以語意鍵為主、不看時間相鄰**的另一層。保留區塊層也讓描述能列出每段時段 (REQ-04)。

**確定性比對** (第 2 步):

- 區塊文字 = 去識別後的 `content_summaries` + `friendly_app_name(app_name)`,沿用 `role_inference._tokenize`
- 候選鍵文字:Vault 專案 = `name` + `description`;主題錨點 = `label` + `intent`;其他專案 = `name` + `description`
- 分數 = `|block_tokens ∩ key_tokens| / |key_tokens|` (與 `role_inference.score_block` 同一族,避免兩套相似度互相矛盾)
- 當天 `topic_sessions` 出現過的主題錨點加 `TOPIC_SAME_DAY_BONUS`;當天 `chat_digest` 的 `intent_label` token 併入該角色所有區塊的比對文字 (只作證據,不成卡)
- 命中條件:`best ≥ GROUP_MATCH_THRESHOLD` 且 `best − second ≥ GROUP_MATCH_MARGIN`;同分時依優先序 Vault > 主題錨點 > 其他專案

**封閉選項分類** (第 3 步,選用):把該角色所有未命中區塊的 (編號, 本地摘要前 120 字) 與候選鍵 (id, 標籤) 一次送本地 Gemma,要求輸出 `{"assignments": [{"block": 0, "key": "<id 或 none>"}]}`。任何不在選項中的值一律視為 `none`。`content_summary` 是 L1,**只能**進本地 Gemma;Gemma 不可達時跳過本步,**不得**退回 Gemini (REQ-09)。

**常數** (`consolidator.py` 模組層級,調整屬 T2 change):

| 常數 | 預設 | 理由 |
| ---- | ---- | ---- |
| `DAILY_CARD_BUDGET` | 6 | `01_product_vision.md` 每日 3–7 分鐘;約 1 分鐘一張。基線 16.5 張 → 6 張即 ~64% 降幅,與 K2 一致 |
| `MAX_UNMAPPED_CARDS_PER_ROLE` | 2 | 未歸類通常是開發雜務 + 瀏覽兩類 |
| `MIN_CARD_MINUTES` | 15 | 低於此值的未歸類家族不值得單獨反思 |
| `GROUP_MATCH_THRESHOLD` | 0.30 | 與 `_MERGE_TOPIC_OVERLAP = 0.34` 同量級;略低,因為鍵是短標籤 |
| `GROUP_MATCH_MARGIN` | 0.10 | 候選 RISK-27:差距不足寧可未歸類 |
| `TOPIC_RECENCY_DAYS` | 14 | 兩週沒再提到的主題不當分組鍵,避免舊主題吸走新活動 |
| `TOPIC_SAME_DAY_BONUS` | 0.10 | 當天聊過的主題是強先驗 |

以上數值為**產品參數,非研究推導**,不加 `[Rxx]` 引用;以 §9 Q1 拍板並由 REQ-08 的真實重放回饋調整。

### 7.2 資料結構

```python
# services/m4_4_elicitation/gibbs_template.py — DaySignals 新增兩個欄位 (向後相容)
@dataclass
class DaySignals:
    ...
    log_ids: list[str] = field(default_factory=list)   # 組成此區塊的 raw_tracking_logs.id
    start_iso: str = ""                                 # 區塊起點 (end − duration),供時段行使用
    # _merge_pair() 合併時 log_ids 取聯集,start_iso 取較早者
```

```python
# services/m4_4_elicitation/consolidator.py
from dataclasses import dataclass, field
from typing import Literal

GroupSource = Literal["vault_project", "topic_anchor", "role_project", "unmapped", "budget_fold"]

@dataclass(frozen=True)
class GroupKey:
    key: str                  # vault: "rp:<role_projects.id>";topic: "ta:<topic_anchors.id>";
                              # unmapped: "un:<family>";fold: "fold"
    source: GroupSource
    label: str                # 卡片標題原文 (REQ-03)
    role_id: str
    match_text: str           # 比對用文字,不輸出

@dataclass
class ConsolidatedGroup:
    key: GroupKey
    blocks: list["DaySignals"]
    folded_labels: list[str] = field(default_factory=list)   # 只有 budget_fold 卡使用

    @property
    def activity_minutes(self) -> float:
        return sum(b.duration_s for b in self.blocks) / 60.0

@dataclass
class ConsolidationSummary:
    role_id: str
    reflection_date: str
    blocks_in: int
    legacy_card_count: int
    cards_out: int
    cards_by_source: dict[str, int]
    mapped_minutes: float
    unmapped_minutes: float
    folded_groups: int
    classifier_used: Literal["gemma_edge", "none"]
    llm_calls: int
```

```sql
-- M6.4 daily_reflection_segments 新增可空欄位 (非破壞性,需 §9 Q7 拍板;本地 SQLite)
ALTER TABLE daily_reflection_segments ADD COLUMN group_key TEXT;
ALTER TABLE daily_reflection_segments ADD COLUMN group_source TEXT;   -- vault_project|topic_anchor|role_project|unmapped|budget_fold
ALTER TABLE daily_reflection_segments ADD COLUMN group_label TEXT;    -- L1 (可能含專案名),只存本地
ALTER TABLE daily_reflection_segments ADD COLUMN block_count INTEGER DEFAULT 1;
ALTER TABLE daily_reflection_segments ADD COLUMN blocks_json TEXT;    -- [{"start":"09:12","end":"10:05","minutes":53,"family":"dev"}]
ALTER TABLE daily_reflection_segments ADD COLUMN source_log_ids_json TEXT;
CREATE UNIQUE INDEX idx_drs_reflection_group
    ON daily_reflection_segments(reflection_id, group_key)
    WHERE group_key IS NOT NULL;
```

- `start_time` = 組內最早區塊起點;`end_time` = 最晚區塊終點;`activity_minutes` = 各區塊時長加總 (不是跨度)。
- 舊資料 (`group_key IS NULL`) 不回填、不遷移;部分唯一索引讓舊列不受影響。
- 雲端 `alembic_cloud` 的 `daily_reflection_segments` 若日後要同步,只能同步 `title_generalized` / `ai_description_generalized`,`group_label` 與 `blocks_json` 不同步 (RISK-15)。

### 7.3 異常處理

| 情境 | 處理 (一律寫 log;禁止靜默吞例外) |
| ---- | ---- |
| `role_projects` 無 `source` 欄位 (舊 schema) | 把全部 active 專案視為 `role_project` 層;`warning` 一次 |
| `topic_anchors` / `topic_sessions` 表不存在 | 跳過主題錨點層,`raw_tracking_logs` 記 `consolidation_layer_skipped{layer: "topic_anchor"}` |
| `task_slots` 不存在 | 跳過第 1 步 (與現行 `fetch_elicited_durations` 降級一致) |
| Gemma 逾時 / 不可達 / 回傳非 JSON | 跳過分類器;`classifier_used = "none"`;未命中區塊進未歸類 |
| Gemma 回傳選項外的值 | 該區塊視為 `none`,記 `consolidation_classifier_invalid_output` |
| 某組描述產生失敗 | 退回 `_template_card` 的描述;標題仍為 `group_label`;`inference_mode = "template"` |
| UNIQUE `(reflection_id, group_key)` 衝突 (並發重跑) | 改為 UPDATE 未核准列;已核准 → 記 `consolidation_group_already_reviewed` |
| 單一角色收斂例外 | 該角色退回**收斂前**的每區塊一卡行為並記 `consolidation_fallback_legacy` (寧可多卡,不可零卡);其他角色不受影響 (同 M4.4 §7.5「單角色失敗不中止」) |

## 8. Anti-patterns (反模式)

- ❌ **不要為了減少張數而提供「整天一次核准」或預設勾選**。收斂減少的是需要判斷的件數,不是每件的摩擦 (`[R08: 微摩擦力 §四.2]`、`[R08: IKEA 效應 §六.1]`、RISK-01)。
- ❌ **不要讓 AI 預填 `user_feeling` / `user_action_plan` / `user_learned`,也不要把舊卡的使用者內容搬到新卡**。主觀欄位只屬於使用者 (`[R08: 意圖脫鉤 §五]`)。
- ❌ **不要用 LLM 改寫專案名當標題**。使用者認得的是自己取的名字;AI 重新命名正是「辨識不清」的成因之一 (`[R10: MindScape §反思鷹架]`)。
- ❌ **不要把 `content_summary` 或分組分類送到 Gemini**。分組需要讀 L1 內容,只能在本地做 (RISK-15、憲章第一條)。
- ❌ **不要用「時間相鄰」取代「語意分組」,也不要拉高 `_MAX_BLOCK_S` 來湊張數**。同一專案一天會分散多段,拉長區塊只會產生「08:00–22:00 程式開發」這種更難辨識的卡。
- ❌ **不要把所有未對應活動塞進一張「其他」卡**。大雜燴卡是辨識不清的另一種形式 (候選 RISK-27);未歸類依 app 家族分,預算摺疊只摺最小的組並列出組名。
- ❌ **不要在分數不足時硬歸到最接近的專案**。歸錯比未歸類更糟:使用者在疲勞下可能照單核准,錯誤會進入 M5.2 證據與 M4.7b 寫回 (「寧可中性,不要錯」,與 RISK-06 同原則)。
- ❌ **不要在重跑時 DELETE 再重建 segment**。RISK-13;已核准 / 已結算的卡必須原封不動。
- ❌ **不要 import `m4_7a_vault_reader`**。Vault 專案只透過 `role_projects` 讀到;M4.4.5 是 `[MVP]`,不得硬依賴 `[進階]` (憲章第五條)。
- ❌ **不要用合成使用者的結果宣稱真實核准率改善**。K1–K5 可在合成資料上驗機制,K6 / K7 與論文數據只能來自真實使用 (RISK-24)。

## 9. Open Questions / 拍板紀錄

- **Q1 [NEEDS DECISION] 驗收門檻數值** (K1 ≤ 6、K2 ≥ 60%、K3 ≥ 60%、K4 ≥ 70%、K6 ≥ 90%,以及 §7.1 常數)。
  *建議*:照預設先跑一次真實重放 (REQ-08),看結果再拍板;拍板後改門檻需走 T2 change,不可在測試中直接放寬。

- **Q2 [NEEDS DECISION] 卡片變少後的 XP**。目前每張核准卡固定 20 XP (`/api/m4_5/grant_xp` 預設值,前端不帶 `amount`)。基線若真的核准完 16.5 張是 330 XP / 日,收斂後最多約 120 XP / 日。
  *建議*:維持每張 20 XP 不變。XP 獎勵的是「完成一次反思」的勞動,不是活動量;實際上過去核准數為 0,沒有人會感受到「變少」。若要改成依時長加權,另開 change 並重新稽核 RISK-01 / RISK-14。

- **Q3 [NEEDS DECISION] 核准時能否把一個區塊從 A 卡移到 B 卡或拆出**。這是 M3.3.3 的新互動,會影響 `source_log_ids_json` 的正確性。
  *建議*:v1 不做;以 REQ-04 的時段清單讓使用者至少看得出放錯,並在 L3 七天紀錄中記下「放錯」次數,再決定是否值得做。

- **Q4 [NEEDS DECISION] 只有對話、沒有遙測的日子要不要出卡 (LOOP-08)**。目前草稿只從 `focus_session_ended` 產生;`chat_digest` 只補脈絡。
  *建議*:本版不改 (草稿來源屬 M4.4.3 的行為,不屬收斂);但 Phase 1 劇本步驟 3–4 要的正是「對話 → 草稿」,建議 W4 人工 E2E 後另開 change:當天有 `topic_sessions` 但無遙測的主題錨點,產生一張 `group_source="topic_anchor"`、`block_count=0` 的對話卡。

- **Q5 [NEEDS DECISION] 主題錨點與 Vault 專案語意重疊時是否合併**。M4.6 的錨點是 10–30 字的意圖句 (「把 coOS 做成能每天用的系統」),很可能是某個 Vault 專案的子題。
  *建議*:v1 不合併,只以優先序讓 Vault 專案勝出 (REQ-02 第一情境);若重放顯示同一件事常拆成兩張卡,再考慮讓 M4.6 的錨點帶 `parent_project_id` (屬 M4.6 的 change)。

- **Q6 [NEEDS DECISION] 登記候選 RISK-27 (收斂 + 核准 → 錯誤歸組被核准成事實 / 大雜燴卡) 到 `05_integration_risk_audit.md`**。
  *建議*:登記;緩解與測試已寫在 §5 與 REQ-02 / 04 / 05 / 10。

- **Q7 [NEEDS DECISION] 在 M6.4 `daily_reflection_segments` 新增 6 個可空欄位與部分唯一索引** (跨模組 schema 變更,非破壞性)。
  *建議*:同意;需同步 M6.4 SPEC 的 spec delta,並在本地遷移檔與 `main.py` lifespan 的補欄位清單 (`main.py:971-986`) 一併加入。

- **Q8 [NEEDS DECISION] `GET /api/m6_4/topic_groups` 的處置**。該端點每次讀取都即時重分群,Gemma 分支因 `from config import settings` 永遠失敗 (LOOP-06),退回的關鍵字表寫死了「coOS 專案開發」等使用者特定字串。
  *建議*:改為依 `group_key` / `group_label` 分組,刪除即時 Gemma 分群與寫死的關鍵字表;舊資料 (`group_key IS NULL`) 才走舊路徑。屬 M6.4 / M3.3 的 change,LOOP-06 隨之關閉。

- **Q9 [NEEDS DECISION] Registry 補登**。`04_module_registry.md` 的 M4.4 子模組表只有 M4.4.1–M4.4.3;程式碼中的 M4.4.4 (角色歸屬推論) 與本 SPEC 的 M4.4.5 都未登記。
  *建議*:兩列一起補;M4.4.4 是既存偏離 (程式碼有、registry 無),應登記到 `SPEC_DEVIATION_REPORT.md` 並以同一個 change 關閉。

- **Q10 [NEEDS DECISION] Eguard 泛化未生效的既存偏離**。`paper_eval_data` 記錄 198 列 segment 的 `*_generalized` 欄位與原文逐位元組相同。收斂後標題會出現 Vault 專案名,這個偏離的影響會變大。
  *建議*:登記到 `SPEC_DEVIATION_REPORT.md`,由 M2.3 的 T1 修正;在修好前,任何雲端同步 `daily_reflection_segments` 的功能都不得開啟。

- **Q11 [NEEDS DECISION] 對齊 Vault 五段式反思鷹架**。`DESIGN_PHILOSOPHY_AUDIT.md` §3.0.1 建議 Gibbs 模板改為 Vault 的「發生了 / 觸動了我 / 我聯想到了 / 我有新的點子 / 觸發新任務」。
  *建議*:不在本模組做 (屬 M4.4.3 模板與 M3.3.3 表單的 change,且會碰到 R08 必填欄位定義);收斂完成並取得 K7 數據後再評估。

## 變更紀錄

| 日期 | 版本 | change-id | 摘要 |
| ---- | ---- | --------- | ---- |
| 2026-10-19 | 0.1.0 | initial | 首版草稿 (W6 / D-2 衍生);11 條需求、7 個量化指標、11 個待拍板問題 |

---

## SPEC 撰寫 Checklist (轉 `approved` 前自我檢查)

- [x] §1 Purpose 是單一職責 (只改草稿粒度與標題)
- [x] §2 研究引用皆有章節 (R08 §三 / §四.2 / §五 / §六.1、R10 §MindScape、R11 §3.3)
- [x] §3 Schema 用 dataclass / SQL
- [x] §4 依賴是真實模組編號;M4.7a 為軟依賴,MVP 無硬依賴進階模組
- [x] §5 已 grep `05_integration_risk_audit.md` (RISK-01 ~ RISK-25);候選 RISK-27 待登記
- [x] §6 每條需求有 `REQ-` 編號與至少一個 GIVEN/WHEN/THEN 情境;驗收指標可量測
- [x] §8 至少 3 條反模式 (10 條)
- [ ] §9 沒有未拍板的 `[NEEDS DECISION]` (尚有 Q1–Q11,維持 `draft`)
