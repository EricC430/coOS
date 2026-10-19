# M4.7a — Vault 治理層唯讀器 (Vault Governance Reader)

**標籤**:`[進階]`
**狀態**:`draft`
**版本**:`0.1.0`
**最後更新**:2026-10-19
**最後變更**:`initial`

> **定位**:`MVP_CLOSURE_REPORT.md` §7.2b D-3 (2026-10-19,使用者交由 Claude 決定) 將 M4.7a 升為 M5 之前的下一階段主軸。
> **動工條件**:憲章第五條——`MVP_CLOSURE_REPORT.md` 最新判定為 **GO** 之後 (目前為「待 W4 人工 E2E,完成即 GO」,§9.5)。本 SPEC 可先寫,程式碼不可先動。
> **與 M4.7 的關係**:`M4_7_obsidian_sync_SPEC.md` (v1.0,寫入型) 的「Session 結束寫一個 `coOS/日期.md`」設計已被 `DESIGN_PHILOSOPHY_AUDIT.md` §3.2 判定為根本誤解 (寫進去的檔案不屬於任何 Dataview 查詢)。M4.7 依 §3.5 拆為 M4.7a (讀,本 SPEC)、M4.7b (寫回)、M4.7c (`.coos_inbox/` 事件匯流排)。M4.7a **不繼承** M4.7 v1.0 的任何寫入行為;M4.7 舊 SPEC 的處置見 §9 Q12。

---

## 1. Purpose (目的)

以**唯讀 + 週期重掃**的方式,把使用者 Obsidian Vault 治理層 (Roles / Domains / Skills / Principles / Projects / `active_period`) 投影成 coOS 的本地快照,讓 coOS 從第一天起就知道「使用者是誰」;Vault 永遠是真相,coOS 只持有快照,**絕不寫回 Vault**。

> 單一職責檢查:「讀 Vault」與「寫 Vault」是兩個職責 (分屬 M4.7a / M4.7b);「把 Principles 注入 Persona」是第三個職責 (屬 M4.2)。M4.7a 只負責「讀出、正規化、對帳、提供查詢」。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R08 | §五 意圖脫鉤與作者身分五大設計模式 | Role 的 mission、Principle 的三段式內容是使用者親手寫的身分與價值觀。M4.7a 逐字讀出、不改寫、不摘要、不用 LLM 重述,讓作者身分留在使用者手上;衝突一律以 Vault 為準 (REQ-M4.7a-07) |
| R16 | §Rolling with Resistance (阻抗滾動順應) | **下游應用點,非本模組實作**:M4.2 日後若引用 Principle 回應使用者的阻抗 (「這是你自己訂的規則」),前提是 M4.7a 交出的是使用者原文而非 AI 改寫 (§8 第 4 條) |
| R08 | §三 醫療級警報疲勞防範 | 重掃發現的差異 (新增 / 變更 / 消失) **不即時推播**,只寫 `raw_tracking_logs` 並累積為待確認清單,由下游在相關對話中自然帶出 (REQ-M4.7a-08) |

其餘 (frontmatter 解析、增量重掃、外鍵對帳) 為**純工程**,不宣稱研究依據。

> 引用衛生註記:`DESIGN_PHILOSOPHY_AUDIT.md` §3.0 以 R03「自我複雜度」 支撐「Role 是內在代理人」,但 `docs/03_research_index.md` 的 R03 條目沒有「自我複雜度」章節 (§1–§6 為微觀認知架構 / ARPM / Echo Mode / 阻抗理論 / KPM / 狀態機移轉)。依 `cite-research` 規則,本 SPEC **不引用**此項;若要沿用,須先在研究索引補上章節 (§9 Q11)。

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M0.3 `Settings.obsidian_vault_path` (env `OBSIDIAN_VAULT_PATH`) | `str \| None` (本機絕對路徑) | `"C:/Users/chent/Documents/Vault"` |
| M0.3 `Settings.vault_rescan_interval_min` | `int`,預設 `15`,`0` = 停用週期掃描 | `15` |
| M0.3 `Settings.vault_folder_map` | `VaultFolderMap` (見 §7.2),預設值對應 `DESIGN_PHILOSOPHY_AUDIT.md` §3.5 | `{"roles": "Governance/Roles", ...}` |
| Vault 檔案 (唯讀,**僅白名單資料夾**) | Markdown + YAML frontmatter | `Governance/Roles/Role - 大學專題生.md` |
| Vault `_System/Global Settings.md` | frontmatter `active_period: str` | `active_period: 2026_spring_semester` |
| Vault `.git/logs/HEAD` 的 mtime (選用) | `float` | obsidian-git commit 後 mtime 改變 → 觸發重掃 |
| HTTP `POST /api/m4_7a/rescan` | `RescanRequest { force: bool = False }` | `{"force": true}` |
| lifespan 啟動 / 週期計時器 | 內部觸發,`trigger ∈ {startup, interval, git_commit, manual}` | — |

**白名單資料夾** (預設,可由 `vault_folder_map` 覆寫):

| 實體 | 預設路徑 | 規模 (2026-10 盤點) |
| ---- | -------- | ------------------- |
| Role | `Governance/Roles/*.md` | 10 (各有 `mission`) |
| Domain | `Governance/Domains/*.md` | 5 |
| Skill | `Governance/Skills/*.md` (樹狀 `parent_skill`) | 130 |
| Principle | `Governance/Principles/*.md` (三段式) | 6 |
| Project | `Executive/Projects/*.md` | 58 (45 個 `status: active`) |
| LifePeriod | `_System/Global Settings.md` | 1 |

白名單以外的資料夾 (`Executive/Period/Daily`、`Resource/People` 1,176 篇、`Resource/Media` 等) **一律不開啟、不 stat 內容** (REQ-M4.7a-10)。

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| 本地 SQLite `m4_7a_vault_entities` (快照,M4.7a 擁有) | 見 §7.2 DDL | `{vault_id: "role_202601212137", entity_type: "role", status: "present", ...}` |
| 本地 SQLite `m4_7a_scan_runs` (掃描紀錄) | 見 §7.2 DDL | `{trigger: "startup", outcome: "ok", files_seen: 209, added: 0, changed: 1, missing: 0}` |
| 本地 SQLite `roles` 投影 (M6.3 擁有表,M4.7a 只寫 `source='vault'` 的列) | 新增可空欄位 `source`, `vault_id`, `mission`, `vault_status` (§7.2,需 §9 Q9 拍板) | `{id: uuid5(vault_id), slug: "role_202601212137", display_name: "🔬 大學專題生", source: "vault", mission: "…全文…"}` |
| 本地 SQLite `role_projects` 投影 (同上) | 新增可空欄位 `source`, `vault_id`, `deadline`, `vault_status` | `{role_id: …, name: "coOS 期末專題", status: "active", source: "vault"}` |
| HTTP `GET /api/m4_7a/status` | `VaultStatus` | `{"configured": true, "last_scan": {...}, "counts": {"role": 10, ...}}` |
| HTTP `GET /api/m4_7a/roles` / `GET /api/m4_7a/roles/{role_id}/projects` | `list[VaultRole]` / `list[VaultProject]` | — |
| HTTP `GET /api/m4_7a/skills` | `list[VaultSkillNode]` (樹) | — |
| HTTP `GET /api/m4_7a/principles?role_id=` | `list[VaultPrinciple]` | — |
| HTTP `GET /api/m4_7a/domains`、`GET /api/m4_7a/active_period` | `list[VaultDomain]`、`LifePeriod` | `{"active_period": "2026_spring_semester", "source_path": "_System/Global Settings.md"}` |
| HTTP `GET /api/m4_7a/pending_confirmations` | `list[VaultChange]` (消失 / 衝突待使用者確認) | `[{"vault_id": "proj_…", "kind": "disappeared", "since": "…"}]` |
| Python 讀取介面 (供下游 import,**選用**) | `services/m4_7a_vault_reader/api.py`:`get_roles()`, `get_principles(role_id)`, `get_active_period()`, `get_skill_tree()` | — |
| M0.4 `raw_tracking_logs` | `{source: "M4.7a", action: <見下>, payload}` | `vault_scan_completed` / `vault_entity_added` / `vault_entity_changed` / `vault_entity_disappeared` / `vault_parse_error` / `vault_path_not_configured` / `vault_path_unreachable` / `vault_scan_aborted` |

**M4.7a 沒有任何對 Vault 的輸出。**

## 4. Dependencies

### 上游 (我依賴誰)

- **M0.3** (Settings):`obsidian_vault_path`、`vault_rescan_interval_min`、`vault_folder_map` 三個欄位 (目前 `services/config.py` 皆未定義,需新增)
- **M0.4** (結構化日誌):所有掃描結果與錯誤寫入 `raw_tracking_logs`
- **M6.1** (SQLite):快照表落在本地 `data/coos.db`
- **M6.3** (角色與情境表):`roles` / `role_projects` 的 schema 擁有者;M4.7a 以**新增可空欄位**方式投影 (非破壞性,需 §9 Q9 拍板)
- 外部:Vault 檔案系統 (唯讀);`pyyaml>=6.0` (已在 `services/pyproject.toml`,不新增依賴)

### 下游 (誰依賴我)

全部為**軟依賴**:下游讀的是 `roles` / `role_projects` 這兩張既有表,不 import `m4_7a_*`。M4.7a 不存在或 Vault 未設定時,下游行為與現況完全相同。

- **M3.2** (角色儀表板):冷啟動時側欄出現 Vault 的 10 個 Role 與各自的 active Project (`PHASE1_SCOPE_AND_ACCEPTANCE.md` §4.2 步驟 1、2)
- **M4.1** (Agent 路由):路由所見的角色清單來自 `roles`;M4.7a 不改路由規則
- **M4.2** (Persona 狀態機):可經 `get_principles(role_id)` 讀取 Principle 的 The Logic 段作為 PersonaCard `stances` 素材——**注入與否、如何注入由 M4.2 的 change 決定**,不在本模組 (§8)
- **M4.6** (Observer):`detect_and_upsert_project` 的模糊比對對象 (`existing_projects`) 自動包含 Vault 專案,避免 Observer 再建一個同名 AI 專案
- **M4.4.4** (角色歸屬推論,`role_inference.py`):`fetch_role_anchor_map` 讀 `role_projects WHERE status='active'`,Vault 專案自動成為歸屬錨點
- **M4.4.5** (草稿收斂,`M4_4_5_draft_consolidation_SPEC.md`):以 `source='vault'` 的專案為第一優先分組鍵
- 未來:M4.7b (寫回需要 `vault_id` 與檔案路徑)、M4.7c、M5.5 (Principles 作為小實驗素材)、M3.10 技能樹 (`[進階]`)

**MVP 獨立性 (憲章第五條)**:MVP 模組不得 `import m4_7a_vault_reader`;若要用讀取介面,必須包在 `try/except ImportError` + log 的選用分支中。驗收:REQ-M4.7a-12。

## 5. Known Risks (整合風險)

稽核方式:`grep -n "^## RISK-" docs/05_integration_risk_audit.md` (RISK-01 ~ RISK-25),再以 `M4\.7|M3\.2|M4\.1|M4\.2|M4\.6|M6\.3|Vault|Obsidian` grep 觸發組合。05 檔中**沒有任何 RISK 提及 M4.7 或 Vault**;以下為依失效機制比對後判定觸發者。

| 風險編號 | 描述 | 緩解策略 | 測試 |
| -------- | ---- | -------- | ---- |
| **RISK-06** | Vault Project 綁錯角色 / Principle 跨角色流入 → 角色沙盒失效 | Project 只依 `related_roles` 綁定;無 `related_roles` 的 Project **不投影**到任何角色 (寧可不顯示,不可歸錯);`get_principles(role_id)` 只回傳明確關聯該角色或標為全域的 Principle | `test_project_without_related_roles_not_projected`、`test_principles_scoped_by_role` |
| **RISK-12** | Vault 文字 (專案名、mission) 經雲端表同步 → 側通道 | M4.7a 只寫本地 SQLite;`roles` / `role_projects` 目前在 `main.py` 的 local-table 清單內 (`main.py:101-124`);M4.7a 不呼叫任何 LLM、不寫 PostgreSQL。Vault 內容的隱私等級待 §9 Q3 拍板 | `test_reader_makes_no_network_calls` |
| **RISK-13** | Vault 專案消失 → 若連帶刪除 coOS 列 → 已核准 / 已結算的 segment 失去根據 | 消失一律**軟標記** (`vault_status='missing'`),從不 DELETE coOS 列 | `test_disappeared_project_is_soft_flagged_not_deleted` |
| **RISK-17** | Vault Role 被刪或改名 → 若停用 coOS 角色 → 該角色 Persona 白名單變空 → Router 靜默降級 | Role 消失時**不改 `is_active`**,只設 `vault_status='missing'` 並列入 `pending_confirmations` | `test_disappeared_role_keeps_personas_routable` |
| **RISK-24** | M0.5 合成使用者若指向真實 Vault → 真實治理資料混入合成實驗,或反之 | 合成 DB 的 Settings 必須使用 fixture Vault;M4.7a 偵測到 `PRAGMA application_id` 為合成 sentinel 且 `obsidian_vault_path` 不在 `testing/` 之下時拒絕掃描 | `test_synthetic_db_refuses_real_vault` |
| **候選 RISK-26** (未登記) | **Vault 重掃 + coOS 外鍵 → 身分漂移與誤判消失**:(a) 使用者在 Obsidian 改檔名或缺 `id:` → 被當成「舊的消失 + 新的出現」→ Persona、segment、XP 掛在孤兒角色上,側欄出現重複角色;(b) 掃描中途失敗 (路徑暫時不可讀、雲端同步鎖檔) → 未掃到的實體被誤判為消失 | (a) 身分鍵優先用 frontmatter `id:`,coOS 主鍵 = `uuid5(NS, vault_id)`,改名不換身分;缺 `id:` 時退回相對路徑並寫 `vault_parse_error{reason: "missing_id"}`;(b) 只有 `outcome='ok'` 的完整掃描可以標記消失,`aborted` / `partial` 掃描一律不標記 | `test_rename_with_stable_id_keeps_identity`、`test_aborted_scan_marks_nothing_missing` |

> 依 `audit-integration` 規定,新風險須先登記到 `05_integration_risk_audit.md` 再填表。本次任務限定只建立兩個 SPEC 檔,**未修改 05**;候選 RISK-26 的登記列為 §9 Q10,拍板後由 change 補登。

**已審查、判定未觸發**:RISK-01 (M4.7a 不碰草稿與 XP)、RISK-08 (Principle 是使用者自己寫的,不是 Observer 推論;注入 Persona 的路徑屬 M4.2,屆時由 M4.2 的 change 重新稽核)、RISK-14 (v1 不讀 Skill Experience Log 的 XP,見 §9 Q8)、RISK-15 (不讀 `content_summary`)。

## 6. Requirements & Acceptance (需求與驗收)

**測試檔**:`testing/m4_7a/test_vault_reader.py`
**Fixture**:`testing/m4_7a/fixtures/mini_vault/`——**合成的**小型 Vault (3 Role、2 Domain、6 Skill 含一個環、2 Principle、5 Project 含 `on_hold` 與缺 `related_roles` 各一、`_System/Global Settings.md`,另放一份 `Resource/People/某人.md` 作為白名單外的誘餌)。每個測試複製到 `tmp_path` 再掃,並以 tmp SQLite 覆寫 `local_db_path` (CLAUDE.md 除錯備忘 #7)。
**黃金樣本**:`testing/golden/phase1/golden_role_import.json` 由**使用者手寫** (`PHASE1_SCOPE_AND_ACCEPTANCE.md` §2.2 鐵則);目前不存在。AI 不得新增或修改;缺檔時對應測試 `skip` 並註明原因,不得以 AI 產生的樣本代替。

### REQ-M4.7a-01:絕不寫入 Vault

系統 SHALL 在任何觸發、任何錯誤路徑下都不建立、修改、刪除、重新命名 Vault 內的任何檔案或資料夾 (含 `.obsidian/`、`.git/`、快取檔、`.coos_inbox/`)。

依據:`[R08: 意圖脫鉤 §五]` 風險:候選 RISK-26

#### Scenario:完整掃描後 Vault 位元組不變

- **GIVEN** fixture Vault,記錄每個檔案的 (相對路徑, size, mtime_ns, sha256) 與目錄清單
- **WHEN** 依序執行 `startup` 掃描、修改一個 Role 後的 `interval` 掃描、`force=True` 的 `manual` 掃描
- **THEN** 三次掃描後的清單與初始清單逐項相等 (除了測試自己修改的那一個檔)

測試:`test_full_scan_leaves_vault_bytes_unchanged`

#### Scenario:寫入嘗試在檔案層被攔下

- **GIVEN** 以 monkeypatch 包住 `builtins.open` / `Path.write_text` / `Path.write_bytes` / `os.replace` / `os.remove`,目標路徑落在 Vault 之下且模式含 `w` / `a` / `x` / `+` 時拋出 `AssertionError`
- **WHEN** 執行一次完整掃描 (含一個 YAML 格式錯誤的檔)
- **THEN** 沒有 `AssertionError` 被拋出

測試:`test_reader_never_opens_vault_files_for_writing`

### REQ-M4.7a-02:Role 匯入保留 mission 全文與身分

系統 SHALL 將每個 Role 檔投影為一列 `source='vault'` 的 `roles`,`display_name` 含 Vault 的 emoji 與名稱、`mission` 逐字等於 frontmatter (或對應段落) 原文、無截斷;coOS 主鍵為 `uuid5(VAULT_NS, vault_id)`。

依據:`[R08: 意圖脫鉤 §五]`

#### Scenario:fixture 的 3 個 Role 全部出現且 mission 無截斷

- **GIVEN** fixture Vault 有 3 個 Role,其中一個 mission 長 600 字
- **WHEN** 首次掃描
- **THEN** `GET /api/m4_7a/roles` 回傳 3 筆;600 字那筆的 `mission == 原文`;每筆 `role_id == uuid5(VAULT_NS, vault_id)`

測試:`test_roles_imported_with_full_mission`

#### Scenario:與使用者手寫黃金樣本逐欄比對 (L1)

- **GIVEN** `testing/golden/phase1/golden_role_import.json` 存在 (使用者手寫,指向使用者真實 Vault 的一個 Role)
- **WHEN** 以 `OBSIDIAN_VAULT_PATH` 指向真實 Vault、tmp SQLite 執行掃描
- **THEN** 該 Role 投影結果與黃金樣本逐欄相等;不相等時預設是實作錯,測試失敗,**不得修改樣本**
- 黃金樣本不存在或 `OBSIDIAN_VAULT_PATH` 未設 → `pytest.skip("golden sample is user-authored; not present")`

測試:`test_role_import_matches_user_golden_sample` (marker `real_vault`,預設不跑)

### REQ-M4.7a-03:Project 只依 `status` 與 `related_roles` 投影

系統 SHALL 只把 `status: active` 的 Project 列為該角色的 active 專案,角色歸屬**只**依 `related_roles` 解析;一個 Project 關聯 N 個角色時投影 N 列 (每角色一列,`UNIQUE(role_id, name)` 不變);無 `related_roles` 或連結解析不到的 Project 不投影任何角色。

依據:純工程 風險:`RISK-06`

#### Scenario:on_hold 專案不在 active 清單

- **GIVEN** fixture 中 `Project B` 為 `status: on_hold`、關聯 Role 1
- **WHEN** 掃描後查 `GET /api/m4_7a/roles/{role1}/projects`
- **THEN** 不含 `Project B`;`role_projects` 中 `Project B` 那列 `status == 'on_hold'`

測試:`test_only_active_projects_listed`

#### Scenario:缺 related_roles 的專案不歸給任何角色

- **GIVEN** `Project E` 沒有 `related_roles`
- **WHEN** 掃描
- **THEN** `role_projects` 沒有任何 `vault_id == Project E` 的列;`raw_tracking_logs` 有 `vault_parse_error{reason: "project_without_role"}`

測試:`test_project_without_related_roles_not_projected`

#### Scenario:wikilink 形式的 related_roles 可解析

- **GIVEN** `related_roles: ["[[Role - 大學專題生|專題生]]"]`
- **WHEN** 掃描
- **THEN** 解析到檔名 `Role - 大學專題生` 對應的 `vault_id`,投影到該角色

測試:`test_related_roles_wikilink_resolution`

### REQ-M4.7a-04:Skill 樹可容錯建構

系統 SHALL 依 `parent_skill` 建立技能樹;偵測到環時斷開環上最後一條邊並記 `vault_parse_error{reason: "skill_cycle"}`;父節點不存在時掛到根並記 `skill_orphan`;不因單一壞節點放棄整棵樹。

依據:純工程

#### Scenario:環與孤兒都不阻擋建樹

- **GIVEN** fixture 有 6 個 Skill,其中 S4→S5→S4 成環、S6 的 parent 不存在
- **WHEN** `GET /api/m4_7a/skills`
- **THEN** 回傳 6 個節點、樹無環;`raw_tracking_logs` 各有一筆 `skill_cycle`、`skill_orphan`

測試:`test_skill_tree_breaks_cycles_and_adopts_orphans`

### REQ-M4.7a-05:Principle 三段式逐字讀出

系統 SHALL 把每條 Principle 解析為 `logic` / `algorithm` / `anti_patterns` 三段原文 (依 `## 🧠 The Logic`、`## ⚙️ The Algorithm`、`## 🚫 Anti-Patterns` 標題切段,比對時忽略 emoji 與括號內中文);缺段時該欄為 `None` 並記 `principle_section_missing`,不失敗;M4.7a **不**對內容做任何 LLM 處理。

依據:`[R08: 意圖脫鉤 §五]` 風險:`RISK-06`

#### Scenario:三段完整的 Principle

- **GIVEN** fixture Principle「最小可行迭代法則」三段齊全
- **WHEN** `GET /api/m4_7a/principles`
- **THEN** `algorithm` 欄逐字含 `IF (` 與 `THEN (`;三欄皆非空

測試:`test_principle_three_sections_verbatim`

#### Scenario:Principle 依角色範圍回傳

- **GIVEN** Principle P1 `related_roles` 含 Role 1;P2 無 `related_roles` (視為全域)
- **WHEN** `get_principles(role_id=role2)`
- **THEN** 只回傳 P2

測試:`test_principles_scoped_by_role`

### REQ-M4.7a-06:Domain 與 `active_period` 只讀出、不調參

系統 SHALL 讀出 Domains 與 `_System/Global Settings.md` 的 `active_period` 並經 API 提供;本版**不得**依 `active_period` 改變任何心理或排程參數 (M1.2 斷點閾值、M4.4 套問頻率等) (`PHASE1_SCOPE_AND_ACCEPTANCE.md` §4.4)。

依據:純工程

#### Scenario:讀出 active_period

- **GIVEN** `active_period: 2026_spring_semester`
- **WHEN** `GET /api/m4_7a/active_period`
- **THEN** 回傳 `{"active_period": "2026_spring_semester", ...}`

測試:`test_active_period_read`

#### Scenario:切換 active_period 不改其他模組常數

- **GIVEN** 記錄 `m4_4_elicitation.controller.CONFIDENCE_THRESHOLD`、`ElicitationController.MAX_PER_THREAD` 等常數值
- **WHEN** 把 fixture 的 `active_period` 改為 `exam_week` 並重掃
- **THEN** 上述常數值不變

測試:`test_active_period_change_does_not_tune_parameters`

### REQ-M4.7a-07:週期重掃與「Vault 為準」的收斂

系統 SHALL 在 lifespan 啟動時、每 `vault_rescan_interval_min` 分鐘、偵測到 `.git/logs/HEAD` mtime 變化時、以及 `POST /api/m4_7a/rescan` 時重掃;以 (mtime_ns, size) 快篩、sha256 確認做增量;Vault 端變更一律覆寫 coOS 的 `source='vault'` 列;coOS 端 API 試圖修改 `source='vault'` 列時回 `409 {"error": "vault_owned"}`。

依據:`[R08: 意圖脫鉤 §五]`

#### Scenario:Obsidian 手動改動在重掃後同步

- **GIVEN** 首次掃描完成
- **WHEN** 在 fixture 新增一個 Skill、把 `Project A` 改為 `on_hold`,然後 `POST /api/m4_7a/rescan`
- **THEN** 新 Skill 出現在 `/skills`;`Project A` 不在 active 清單;`m4_7a_scan_runs` 最新一筆 `added == 1, changed == 1`

測試:`test_manual_vault_edit_visible_after_rescan` (對應 Phase 1 劇本步驟 9)

#### Scenario:沒有變更的重掃不寫任何實體列

- **GIVEN** 掃描完成且 Vault 未變
- **WHEN** 再掃一次
- **THEN** `m4_7a_vault_entities` 所有列的 `updated_at` 不變;`scan_runs` 新增一筆 `changed == 0`

測試:`test_unchanged_rescan_is_noop`

#### Scenario:coOS 端不可改 Vault 擁有的專案

- **GIVEN** `Project A` 為 `source='vault'`
- **WHEN** 呼叫既有的專案改名 / 封存 API (`main.py:3989`、`main.py:4019` 一帶)
- **THEN** 回 `409 vault_owned`;資料列不變

測試:`test_coos_edit_of_vault_owned_project_rejected`

#### Scenario:改名但 id 不變 → 身分不變

- **GIVEN** `Role - 大學專題生.md` 有 `id: role_202601212137`
- **WHEN** 把檔名改為 `Role - 專題研究者.md` 後重掃
- **THEN** `roles` 中同一 `id` 那列的 `display_name` 更新;沒有新增角色;沒有 `vault_entity_disappeared`

測試:`test_rename_with_stable_id_keeps_identity`

### REQ-M4.7a-08:消失不重建、不刪除、不推播

系統 SHALL 在**完整成功**的掃描中發現實體消失時:不在 Vault 重建、不 DELETE coOS 列、Role 不改 `is_active`、Project 設 `vault_status='missing'` 並退出 active 清單;寫一筆 `vault_entity_disappeared`;列入 `GET /api/m4_7a/pending_confirmations`;**不發 SSE / 推播**。

依據:`[R08: 警報疲勞 §三]` 風險:`RISK-13`、`RISK-17`

#### Scenario:專案檔被刪除

- **GIVEN** `Project A` 已投影,且有一個 `daily_reflection_segments` 以它為分組鍵 (M4.4.5) 並已核准
- **WHEN** 刪除 fixture 中的 `Project A.md` 並重掃
- **THEN** `role_projects` 該列仍在且 `vault_status == 'missing'`;該 segment 不變;`pending_confirmations` 含 `Project A`;本次掃描沒有任何 SSE 事件發出

測試:`test_disappeared_project_is_soft_flagged_not_deleted`

#### Scenario:角色檔被刪除,Persona 仍可路由

- **GIVEN** Role 1 下有一位 Persona
- **WHEN** 刪除 `Role 1.md` 並重掃
- **THEN** `roles.is_active` 仍為 1、`vault_status == 'missing'`;M4.1 Router 對該角色的白名單不為空

測試:`test_disappeared_role_keeps_personas_routable`

### REQ-M4.7a-09:失敗路徑不破壞既有狀態

系統 SHALL 在以下情況保留上一份成功快照、記錄原因並繼續服務,且 coOS 其他功能不受影響:

- `obsidian_vault_path` 未設定 → 不掃描,記 `vault_path_not_configured` (每次啟動一次,不重複洗版)
- 路徑不存在 / 無讀取權限 → `outcome='aborted'`,記 `vault_path_unreachable`
- 單檔 YAML 錯誤、非 UTF-8、> 1 MB → 跳過該檔,記 `vault_parse_error{path, reason}`,其他檔照常
- 掃描中途例外 → `outcome='aborted'`,**不標記任何消失**

依據:純工程 風險:候選 RISK-26

#### Scenario:未設定 Vault 路徑

- **GIVEN** `Settings(_env_file=None)` 且未設 `OBSIDIAN_VAULT_PATH`
- **WHEN** lifespan 啟動
- **THEN** `GET /api/m4_7a/status` 回 `{"configured": false}`;`raw_tracking_logs` 恰有一筆 `vault_path_not_configured`;`roles` 不變

測試:`test_unconfigured_vault_is_noop`

#### Scenario:單檔壞掉不影響其他

- **GIVEN** fixture 中一個 Role 檔的 frontmatter 是不合法 YAML
- **WHEN** 掃描
- **THEN** 其餘 2 個 Role 正常投影;有一筆 `vault_parse_error`,`payload.path` 為該檔相對路徑;`outcome == 'ok'`

測試:`test_malformed_yaml_skips_only_that_file`

#### Scenario:中途中止不誤判消失

- **GIVEN** 首次掃描完成;monkeypatch 讓第二次掃描在讀到一半時拋 `PermissionError`
- **WHEN** 第二次掃描
- **THEN** `outcome == 'aborted'`;沒有任何實體 `status` 變為 `missing`;沒有 `vault_entity_disappeared`

測試:`test_aborted_scan_marks_nothing_missing`

### REQ-M4.7a-10:只讀白名單、不碰 L1 與他人個資

系統 SHALL 只開啟 `vault_folder_map` 列出的資料夾與檔案;不跟隨指向 Vault 外部的 symlink;不開啟 `Resource/People`、`Executive/Period/Daily` 等白名單外路徑;不發出任何網路請求、不呼叫任何 LLM。

依據:純工程 風險:`RISK-12`

#### Scenario:白名單外的誘餌檔從未被開啟

- **GIVEN** fixture 有 `Resource/People/某人.md`,以 monkeypatch 記錄所有被 `open` 的路徑
- **WHEN** 完整掃描
- **THEN** 被開啟的路徑全部落在白名單內;`某人.md` 不在其中

測試:`test_only_whitelisted_folders_opened`

#### Scenario:symlink 逃逸被拒

- **GIVEN** `Governance/Roles/escape.md` 是指向 Vault 外部檔案的 symlink (Windows 無權限建立 symlink 時 skip)
- **WHEN** 掃描
- **THEN** 該檔被跳過並記 `vault_parse_error{reason: "outside_vault"}`

測試:`test_symlink_outside_vault_skipped`

#### Scenario:掃描期間零網路呼叫

- **GIVEN** monkeypatch `socket.socket.connect` 一律拋錯
- **WHEN** 完整掃描
- **THEN** 掃描 `outcome == 'ok'`

測試:`test_reader_makes_no_network_calls`

### REQ-M4.7a-11:可觀測性與效能

系統 SHALL 為每次掃描寫一筆 `m4_7a_scan_runs` 與一筆 `raw_tracking_logs{action: "vault_scan_completed", payload: {trigger, outcome, duration_ms, files_seen, added, changed, missing, errors}}`;對 ~200 個白名單檔案,完整掃描 SHALL ≤ 5 秒、無變更的增量掃描 SHALL ≤ 1 秒 (於開發機量測,不設 CI 硬門檻,只記錄)。

依據:純工程

#### Scenario:掃描摘要可查

- **WHEN** 任一掃描結束 (含 aborted)
- **THEN** `raw_tracking_logs` 最新一筆 `vault_scan_completed` 的 counts 與 `scan_runs` 一致

測試:`test_scan_summary_logged`

#### Scenario:增量掃描效能紀錄

- **GIVEN** 由 fixture 複製出 200 個 Skill 檔
- **WHEN** 先完整掃描,再無變更重掃
- **THEN** 兩次 `duration_ms` 皆寫入 `scan_runs`;增量掃描 `duration_ms` < 完整掃描 (斷言相對關係,不斷言絕對秒數)

測試:`test_incremental_scan_faster_than_full`

### REQ-M4.7a-12:下游接縫與 MVP 獨立

系統 SHALL 讓既有 MVP 消費者在不修改程式碼的情況下看到 Vault 資料 (經 `roles` / `role_projects`),且在 M4.7a 停用時 MVP 閉環照常運作。

依據:純工程 風險:憲章第五條

#### Scenario:Vault 專案成為角色歸屬錨點與 Observer 去重對象

- **GIVEN** 掃描後 Role 1 有 Vault 專案「coOS 期末專題」
- **WHEN** 呼叫 `DBAdapter.fetch_role_anchor_map(user_id)`,並以訊息「我今天在弄 coOS 期末專題的前端」跑 M4.6 `detect_and_upsert_project`
- **THEN** anchor map 的 Role 1 含「coOS 期末專題」;Observer 回傳既有名稱,`role_projects` 沒有新增 `source='ai'` 的同義列

測試:`test_vault_projects_feed_anchor_map_and_observer_dedup` (閉環,跨 M4.7a / M4.4.4 / M4.6)

#### Scenario:M4.7a 停用時 MVP 閉環仍綠

- **GIVEN** 未設 `OBSIDIAN_VAULT_PATH`,且 `m4_7a_*` 表不存在
- **WHEN** 執行 `testing/m4_5/test_mvp_closed_loop.py::test_chat_to_xp_closed_loop`
- **THEN** 通過

測試:`test_mvp_loop_passes_without_vault_reader`

#### Scenario:MVP 模組不 import M4.7a

- **WHEN** 以 AST 掃描 `services/` 下所有 `[MVP]` 模組目錄
- **THEN** 沒有頂層 `import m4_7a_vault_reader` / `from m4_7a_vault_reader`;選用分支必須在 `try/except ImportError` 內

測試:`test_mvp_modules_do_not_hard_import_m4_7a`

## 7. Implementation Notes

### 7.1 演算法選擇

**掃描流程** (`services/m4_7a_vault_reader/scanner.py`):

```
scan(trigger):
  1. 取得 vault_root;未設定 → log once, return
  2. 對 vault_folder_map 每個實體類型:
       列出 *.md (只一層,不遞迴子資料夾,除非 map 指定 recursive)
       resolve() 後必須仍在 vault_root 之下 → 否則 skip(outside_vault)
       stat → (mtime_ns, size);與快照相同且非 force → 沿用
       不同 → read_bytes() → sha256;hash 相同 → 只更新 mtime
       hash 不同 → parse_frontmatter → normalize(entity_type) → upsert 快照
  3. 解析跨實體連結 (related_roles / domains / parent_skill) → 以檔名 stem 對 vault_id
  4. 若整輪無例外 (outcome='ok'):
       快照中 status='present' 但本輪未見 → 標 missing + log + pending_confirmations
  5. 投影:roles / role_projects 的 source='vault' 列 (單一 SQLite transaction)
  6. 寫 scan_runs + raw_tracking_logs summary
```

- **frontmatter 解析**:檔首 `---\n ... \n---` 之間交給 `yaml.safe_load` (`pyyaml` 已存在);**禁止** `yaml.load` / `yaml.unsafe_load`。不新增 `python-frontmatter` 依賴。
- **wikilink 解析**:`[[目標|別名]]` / `[[目標#段落]]` → 取 `目標`,以檔名 stem 對照本輪掃到的實體;同 stem 多檔時記 `ambiguous_link` 並不投影 (RISK-06:寧可不顯示,不可歸錯)。
- **身分**:`vault_id = frontmatter["id"]`;缺 → `"path:" + 相對路徑 (POSIX 形式)` 並記 `missing_id`。coOS 端 `roles.id = str(uuid5(VAULT_NS, vault_id))`,`VAULT_NS` 為寫死的常數 UUID,讓 DB 重建後主鍵仍一致。
- **重掃觸發**:lifespan 啟動一次;`asyncio` 背景任務每 `vault_rescan_interval_min` 分鐘;同一任務每次 tick 額外 stat `.git/logs/HEAD`,mtime 變動即提前掃 (obsidian-git commit 的低成本訊號,不需 watchdog 依賴)。同時只允許一個掃描在跑 (`asyncio.Lock`),後到的觸發合併。
- **為什麼不用 watchdog**:Vault 經 obsidian-git 與雲端同步,檔案事件會成批湧入;週期 + mtime 快篩在 ~200 檔規模下已足夠,且行為可預期、好測。

**Frontmatter 欄位對應** (預設值,實際欄位名待 §9 Q1 以使用者提供的樣本確認;一律經 `VaultFieldMap` 設定,不寫死在解析邏輯中):

| 實體 | 欄位 | 來源 |
| ---- | ---- | ---- |
| 共通 | `vault_id` | `id:` |
| 共通 | `class` / `type` | `class:` / `type:` |
| Role | `display_name` | 檔名去掉 `Role - ` 前綴;frontmatter `aliases` 第一項若有 emoji 則採用 |
| Role | `mission` | `mission:`;缺則取 `## Mission` 段落原文 |
| Role | `domain_ids` | `domains:` (wikilink 陣列) |
| Project | `name` / `status` / `deadline` / `role_ids` / `skill_ids` | 檔名 / `status:` / `deadline:` / `related_roles:` / `skills:` |
| Skill | `name` / `parent_id` | 檔名 / `parent_skill:` |
| Principle | `logic` / `algorithm` / `anti_patterns` / `role_ids` | 三個 `##` 段落原文 / `related_roles:` (缺 = 全域) |
| Domain | `name` / `vision_ids` | 檔名 / `visions:` (目前 Visions 為空,允許空陣列) |
| LifePeriod | `active_period` | `_System/Global Settings.md` 的 `active_period:` |

### 7.2 資料結構

```python
# services/m4_7a_vault_reader/models.py
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

EntityType = Literal["role", "domain", "skill", "principle", "project", "life_period"]

class VaultFolderMap(BaseModel):
    roles: str = "Governance/Roles"
    domains: str = "Governance/Domains"
    skills: str = "Governance/Skills"
    principles: str = "Governance/Principles"
    projects: str = "Executive/Projects"
    global_settings: str = "_System/Global Settings.md"

class VaultEntityBase(BaseModel):
    vault_id: str
    entity_type: EntityType
    rel_path: str                      # POSIX,相對 vault_root
    title: str
    status: Literal["present", "missing"] = "present"
    parse_warnings: list[str] = Field(default_factory=list)

class VaultRole(VaultEntityBase):
    entity_type: Literal["role"] = "role"
    role_id: str                       # uuid5(VAULT_NS, vault_id)
    display_name: str
    mission: str | None                # 逐字,不截斷
    domain_ids: list[str] = []

class VaultProject(VaultEntityBase):
    entity_type: Literal["project"] = "project"
    name: str
    project_status: str                # active / on_hold / done / ... (原值)
    deadline: str | None = None
    role_ids: list[str] = []           # 解析後的 coOS role_id
    skill_ids: list[str] = []

class VaultSkillNode(VaultEntityBase):
    entity_type: Literal["skill"] = "skill"
    name: str
    parent_id: str | None
    children: list["VaultSkillNode"] = []

class VaultPrinciple(VaultEntityBase):
    entity_type: Literal["principle"] = "principle"
    name: str
    logic: str | None
    algorithm: str | None
    anti_patterns: str | None
    role_ids: list[str] = []           # 空 = 全域

class VaultDomain(VaultEntityBase):
    entity_type: Literal["domain"] = "domain"
    name: str
    vision_ids: list[str] = []

class LifePeriod(BaseModel):
    active_period: str | None
    source_path: str

class ScanReport(BaseModel):
    run_id: str
    trigger: Literal["startup", "interval", "git_commit", "manual"]
    outcome: Literal["ok", "aborted", "skipped_unconfigured"]
    started_at: datetime
    duration_ms: int
    files_seen: int = 0
    added: int = 0
    changed: int = 0
    missing: int = 0
    errors: list[dict] = []

class VaultChange(BaseModel):
    vault_id: str
    entity_type: EntityType
    kind: Literal["disappeared", "name_collision", "ambiguous_link"]
    since: datetime
    detail: str | None = None
```

```sql
-- 本地 SQLite (services/alembic_local.ini 歷史),M4.7a 擁有
CREATE TABLE m4_7a_vault_entities (
    vault_id        TEXT PRIMARY KEY,
    entity_type     TEXT NOT NULL,          -- role|domain|skill|principle|project|life_period
    rel_path        TEXT NOT NULL,
    title           TEXT NOT NULL,
    content_sha256  TEXT NOT NULL,
    mtime_ns        INTEGER NOT NULL,
    size_bytes      INTEGER NOT NULL,
    fields_json     TEXT NOT NULL,          -- 正規化後的 Vault* 模型 JSON
    status          TEXT NOT NULL DEFAULT 'present',  -- present|missing
    parse_warnings_json TEXT,
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL,
    missing_since   TEXT,
    updated_at      TEXT NOT NULL
);
CREATE INDEX idx_m4_7a_ve_type_status ON m4_7a_vault_entities(entity_type, status);

CREATE TABLE m4_7a_scan_runs (
    id              TEXT PRIMARY KEY,
    trigger         TEXT NOT NULL,
    outcome         TEXT NOT NULL,          -- ok|aborted|skipped_unconfigured
    started_at      TEXT NOT NULL,
    duration_ms     INTEGER NOT NULL,
    files_seen      INTEGER NOT NULL DEFAULT 0,
    added           INTEGER NOT NULL DEFAULT 0,
    changed         INTEGER NOT NULL DEFAULT 0,
    missing         INTEGER NOT NULL DEFAULT 0,
    errors_json     TEXT
);

-- 投影用的可空欄位 (非破壞性 ADD COLUMN;M6.3 擁有表,需 §9 Q9 拍板)
ALTER TABLE roles         ADD COLUMN source TEXT DEFAULT 'coos';   -- coos|vault
ALTER TABLE roles         ADD COLUMN vault_id TEXT;
ALTER TABLE roles         ADD COLUMN mission TEXT;
ALTER TABLE roles         ADD COLUMN vault_status TEXT;            -- NULL|present|missing
ALTER TABLE role_projects ADD COLUMN source TEXT DEFAULT 'ai';     -- ai|manual|vault
ALTER TABLE role_projects ADD COLUMN vault_id TEXT;
ALTER TABLE role_projects ADD COLUMN deadline TEXT;
ALTER TABLE role_projects ADD COLUMN vault_status TEXT;
CREATE INDEX idx_role_projects_vault ON role_projects(vault_id);
```

- 遷移檔依 CLAUDE.md「你被授權做的事」只建立**檔案**,不 `--autogenerate` 後直接 apply,需使用者審。`main.py` lifespan 內既有的 `ALTER TABLE ... ADD COLUMN` 自動補欄位模式 (`main.py:971-986`) 可沿用作為本地開發相容層。
- `roles.slug` 對 Vault 角色填 `vault_id`,滿足既有 `UNIQUE(user_id, slug)`。`user_id` 填 `get_safe_user_id` 的本機預設使用者 (Vault 為單人資產)。

### 7.3 異常處理

| 情境 | 處理 (一律寫 log;跨模組影響寫 `raw_tracking_logs`;禁止靜默吞例外) |
| ---- | ---- |
| `obsidian_vault_path` 未設定 | `outcome='skipped_unconfigured'`;每個 process 只記一次 `vault_path_not_configured` |
| 路徑不存在 / 權限不足 / 雲端同步鎖檔 (`PermissionError`) | `outcome='aborted'` + `vault_path_unreachable`;保留舊快照;不標消失 |
| YAML 錯誤 / 非 UTF-8 / 檔案 > 1 MB / symlink 出界 | 跳過該檔,`vault_parse_error{path, reason}`;本輪 `outcome` 仍可為 `ok` |
| 跳過的檔案原本在快照中 | 視為「本輪有見到但無法解析」:**不**標 missing,保留舊版並在 `parse_warnings` 記 `stale_due_to_parse_error` |
| wikilink 解析不到 / 多義 | 不投影該關聯,記 `unresolved_link` / `ambiguous_link`,列入 `pending_confirmations` |
| Vault 專案名與既有 `source='ai'` 專案同角色同名 (`UNIQUE(role_id, name)` 衝突) | v1 預設:不覆寫、不合併,記 `name_collision` 並列入 `pending_confirmations` (處置見 §9 Q6) |
| 投影 transaction 失敗 | rollback;快照表仍更新 (下次掃描重投影);`outcome='aborted'`,記 `vault_projection_failed` |
| 掃描進行中又被觸發 | 合併為一次,記 `vault_scan_coalesced` (debug 級) |

## 8. Anti-patterns (反模式)

- ❌ **不要對 Vault 做任何寫入,包括「只是建個快取檔」或「順手修死查詢」**。寫入屬 M4.7b,且必須經 M4.7c 的 `.coos_inbox/` 契約,由 Vault 自己的 `applyCoosInbox.js` 落地 (`DESIGN_PHILOSOPHY_AUDIT.md` §3.6、§3.7.5)。理由:`[R08: 意圖脫鉤 §五]`;Vault 有 obsidian-git 同步,任何寫入都等同上雲。
- ❌ **不要做一次性 import**。Vault 會持續被手動編輯,coOS 對 Vault 的認知必須永遠是「重掃出來的」(`DESIGN_PHILOSOPHY_AUDIT.md` §3.7.2 規則 1)。
- ❌ **不要掃整個 Vault (11k 檔)**。只讀治理白名單;`Resource/People` 是第三方個資,`Daily` 可能含 L1 等級的私密書寫 (RISK-12)。
- ❌ **不要用 LLM 摘要、改寫、翻譯 mission 或 Principle**。它們是使用者的原話;改寫會讓 Persona 引用「你自己說的」時其實是 AI 說的,破壞 `[R16: Motivational Interviewing §Rolling with Resistance]` 想取得的效果 (此效果的實作屬 M4.2,但前提由 M4.7a 守住)。
- ❌ **不要在 M4.7a 裡把 Principle 注入 Persona prompt**。注入涉及 RISK-08 類的「外部內容進 Persona」邊界與雲端 prompt 的隱私等級,屬 M4.2 的 change,需另行稽核。
- ❌ **不要在消失時 DELETE coOS 列或停用角色**。理由:RISK-13 (已結算 segment 失去根據)、RISK-17 (Persona 白名單空集合 → 靜默降級)。
- ❌ **不要以檔名當身分**。改名會造成重複角色與孤兒外鍵 (候選 RISK-26)。
- ❌ **不要讓不完整的掃描標記消失**。暫時不可讀 ≠ 被刪除。
- ❌ **不要自動合併 coOS 既有角色與 Vault 角色**,即使名稱相同。合併是跨模組的職責邊界調整 (CLAUDE.md「必須詢問使用者的事」)。
- ❌ **不要依 `active_period` 調整任何心理參數**。本階段只讀出顯示 (`PHASE1_SCOPE_AND_ACCEPTANCE.md` §4.4);參數化是 M1.7 / §5.6 的獨立 change。
- ❌ **不要由 AI 產生 `testing/golden/` 下的黃金樣本**。AI 生成的樣本會與 AI 的實作自動對齊,驗收失去意義 (`PHASE1_SCOPE_AND_ACCEPTANCE.md` §2.2)。合成 fixture Vault (`testing/m4_7a/fixtures/`) 不是黃金樣本,可以由 AI 建立。
- ❌ **不要讓任何 `[MVP]` 模組硬 import `m4_7a_vault_reader`** (憲章第五條)。

## 9. Open Questions / 拍板紀錄

- **Q1 [NEEDS DECISION] Frontmatter 實際欄位名**。本 SPEC 的欄位對照來自 `DESIGN_PHILOSOPHY_AUDIT.md` 的盤點描述,未逐檔核對 (本次未讀取使用者 Vault)。
  *建議*:使用者提供每種實體各一份真實檔案 (可去識別),作為 `golden_role_import.json` 的來源並寫進 `VaultFieldMap` 預設值;解析邏輯只讀 `VaultFieldMap`,不寫死欄位名。

- **Q2 [NEEDS DECISION] 缺 `id:` 的檔案如何定身分**。
  *建議*:退回相對路徑並記 `missing_id`;同時建議使用者在 Role / Project / Skill / Principle 模板加 `id:` (使用者自己改 Vault,coOS 不改)。

- **Q3 [NEEDS DECISION] Vault 內容的隱私等級**。憲章第一條只定義 L1 (原始碼、瀏覽器內容、對話逐字稿) / L2 / L3,沒有 Vault。`DESIGN_PHILOSOPHY_AUDIT.md` §5.3(a) 建議「Vault 檔案 = L3-local」。這決定 M4.2 日後能否把 mission / Principle 送進雲端 Persona prompt。
  *建議*:Governance 白名單內容 (使用者自寫的身分與原則,不含第三方個資) 定為 **L3-local**:預設只存本地;可進雲端 prompt,但專案名須先過 M2.3 Eguard。拍板前 M4.7a 一律只存本地 (本 SPEC 已如此設計)。

- **Q4 [NEEDS DECISION] 需要使用者同意的 `CLAUDE.md` 修改** (本次依指示**未修改** `CLAUDE.md`,列出供拍板):
  1. 憲章第一條隱私表新增一列「Vault 治理層 = L3-local」(依 Q3 結果)。
  2. 新增鐵則:「M4.7a 對 Vault 唯讀;任何寫入 Vault 的行為必須經 `_System/.coos_inbox/` 契約,不得由 Python 直接改 `.md`,不得呼叫 Templater API」(`PHASE1_SCOPE_AND_ACCEPTANCE.md` §6 防線 1 第 3 條)。
  3. Phase 1 鐵則:「`testing/golden/` 由使用者手寫,AI 不得新增或修改;AI 不得在文件中寫『L2 通過』」(同 §6 防線 1 第 1、2 條)。
  4. 專案地圖新增 `services/m4_7a_vault_reader/`、`testing/m4_7a/`、`testing/golden/phase1/`。
  5. `services/config.py` `Settings` 新增 `obsidian_vault_path` / `vault_rescan_interval_min` / `vault_folder_map` (Windows 備忘 #4:`.env` 新增變數讀不到 → 先查 `Settings`)。
  *建議*:1、2、4 隨 M4.7a 的 change 一起拍板;3 屬 Phase 1 全體規則,可單獨拍板。

- **Q5 [NEEDS DECISION] coOS 既有角色 (手動 / demo 建立) 與 Vault 角色的關係**。
  *建議*:v1 並存,不自動合併;既有角色 `source='coos'`。之後若要合併,另開 change 並由使用者逐一確認對應。

- **Q6 [NEEDS DECISION] Observer 已推論出、與 Vault 專案同角色同名的 `source='ai'` 專案**。
  *建議*:由 Vault 收編 (把該列改為 `source='vault'`、填 `vault_id`),因為 Vault 是專案定義的 owner (`DESIGN_PHILOSOPHY_AUDIT.md` §3.4);但 v1 先只記 `name_collision` 並列入待確認,收編由使用者按一下。

- **Q7 [NEEDS DECISION] 重掃頻率**。
  *建議*:啟動一次 + 每 15 分鐘 + `.git/logs/HEAD` mtime 變動 + 手動;週期可設 `0` 停用。

- **Q8 [NEEDS DECISION] 是否在 v1 讀 Skill 的 `## 📜 Experience Log` XP**。
  *建議*:不讀。等級公式 (`PHASE1_SCOPE_AND_ACCEPTANCE.md` §9 D2) 未拍板前,讀出的 XP 無法正確顯示,且會把 RISK-14 帶進本模組。依同文件 §7 砍尾巴規則,v1 只讀樹結構。

- **Q9 [NEEDS DECISION] 投影方式:在 M6.3 的 `roles` / `role_projects` 加可空欄位,或 M4.7a 自建 `m4_7a_roles` / `m4_7a_projects` 並要求下游改讀**。這是跨模組職責邊界調整,依 CLAUDE.md 須詢問。
  *建議*:加可空欄位。理由:M3.2、M4.1、M4.4.4、M4.6 已經讀這兩張表,零修改即可吃到 Vault 資料 (REQ-M4.7a-12);變更為非破壞性 `ADD COLUMN`。代價是 M6.3 SPEC 需同步一條 spec delta。

- **Q10 [NEEDS DECISION] 登記候選 RISK-26 (Vault 重掃 + coOS 外鍵 → 身分漂移與誤判消失) 到 `05_integration_risk_audit.md`**。
  *建議*:登記;緩解與測試已寫在 §5 與 REQ-M4.7a-07 / 09。

- **Q11 [NEEDS DECISION] R03「自我複雜度」 引用**。研究索引查無此章節。
  *建議*:若使用者希望保留此論據,先在 `03_research_index.md` 補上來源與章節;否則所有文件改稱「產品架構決策」。本 SPEC 未引用。

- **Q12 [NEEDS DECISION] 舊 `M4_7_obsidian_sync_SPEC.md` (v1.0) 的處置**。其寫入行為已被稽核否定,且 §6 的 PII 測試本身會失敗 (`DESIGN_PHILOSOPHY_AUDIT.md` §3.2)。
  *建議*:M4.7a change 歸檔時,把 M4.7 v1.0 標為 `deprecated`,`04_module_registry.md` 的 M4.7 拆成 M4.7a / M4.7b / M4.7c 三列。

- **Q13 [NEEDS DECISION] 開工前的 Phase 1 四件套**。`PHASE1_SCOPE_AND_ACCEPTANCE.md` §2 規定劇本、黃金樣本、反例清單、基線量測完成前「一行實作程式碼都不准寫」;目前 `docs/phase1/` 與 `testing/golden/` 皆不存在。
  *建議*:M4.7a 只需要其中兩件即可動工:`golden_role_import.json` (使用者手寫) 與 §2.4 基線中的「冷啟動空白程度」(roles / projects / goals 各幾筆)。其餘兩件隨 M4.7b 補齊。

## 變更紀錄

| 日期 | 版本 | change-id | 摘要 |
| ---- | ---- | --------- | ---- |
| 2026-10-19 | 0.1.0 | initial | 首版草稿 (D-3 衍生);12 條需求、29 個驗收情境、13 個待拍板問題 |

---

## SPEC 撰寫 Checklist (轉 `approved` 前自我檢查)

- [x] §1 Purpose 是單一職責 (讀 / 正規化 / 對帳 / 提供查詢;寫入與注入另屬 M4.7b / M4.2)
- [x] §2 研究引用皆有章節;純工程部分已註明;R03「自我複雜度」 因查無章節未引用
- [x] §3 Schema 用 Pydantic / SQL
- [x] §4 依賴是真實模組編號;MVP 對 M4.7a 只有軟依賴
- [x] §5 已 grep `05_integration_risk_audit.md` (RISK-01 ~ RISK-25);候選 RISK-26 待登記
- [x] §6 每條需求有 `REQ-` 編號與至少一個 GIVEN/WHEN/THEN 情境
- [x] §8 至少 3 條反模式 (12 條)
- [ ] §9 沒有未拍板的 `[NEEDS DECISION]` (尚有 Q1–Q13,維持 `draft`)
