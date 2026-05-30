# coOS — Claude Code 專案憲章

> **此檔案為 Claude Code 每次 session 必讀。內容是「鐵則」,不是建議。**

## 你是誰

你正在協助開發 **coOS**:一款結合多智能體 AI、遊戲化、薩提爾冰山心理模型與邊緣-雲端協同推論的個人目標管理系統。本專案融合心理學、認知科學、混合主動式人機互動與 2026 年最新端側 LLM 技術。

## 開始任何任務前的鐵則

### 1. 必先閱讀 `docs/` 對應的設計文件

實作任一模組 `Mx.y` 前,**必須**依序執行:

1. `view docs/04_module_research_matrix.md` — 找出此模組對應的研究論文編號 (R01~R10)
2. `view docs/03_research_index.md` 對應段落 — 理解該模組必須遵守的學術約束
3. `view docs/05_integration_risk_audit.md` — 檢查此模組與已實作模組之間是否有「合併後效果變差」的已知風險
4. `view docs/modules/Mx_y_SPEC.md` — 讀完整模組契約

**不准跳過任一步驟。** 跳過會導致違反隱私約束 (洩漏意圖向量明文) 或破壞核心心理機制 (例如自動寫入日報摧毀 IKEA 效應)。

### 2. 引用研究時的標準格式

任何宣稱「根據研究」「依據心理學」的程式碼註解或設計決策,**必須**使用以下格式:

```python
# [R03: Echo Mode §3.2] 偵測到防衛語氣時,調降 Agency 從 0.8 → 0.3
# [R08: 微摩擦力 §四.2] 強制留白「主觀感受」欄位,觸發 System 2 思維
```

其中 `R03`、`R08` 是 `docs/03_research_index.md` 中的論文編號。**禁止**使用「根據相關研究」這類無法溯源的模糊引用。

### 3. 寫程式碼前先寫測試的驗收標準

每個模組 SPEC 都有 `Acceptance Criteria` 區塊。實作前先把這些條件寫成測試 (pytest / vitest),確保「實作完成」=「測試通過」,而不是「程式碼跑得起來」。

### 4. MVP 優先,進階模組必須通過守門檢查

只有 `[MVP]` 標籤的模組可以在 Phase 1~5 動工。 `[進階]` 模組必須等 MVP 閉環跑通並產出 `docs/MVP_CLOSURE_REPORT.md` 後才能進入。

### 5. 觸碰跨模組整合時必做風險檢查

當任務涉及 2 個以上模組互動,**必須**先呼叫 skill: `.claude/skills/audit-integration/SKILL.md`,讓它檢查 `05_integration_risk_audit.md` 中是否有對應警告。

## 程式碼規範

### 命名

所有檔案、API 路徑、資料表均以模組編號為前綴:

- `services/m4_1_router/router.py`
- `apps/web/src/components/m3_2_dashboard/`
- `POST /api/m4_4/draft`
- `CREATE TABLE m6_5_daily_reflections (...)`

這讓任何人 (人類或 Claude Code) 都能用 grep 一秒定位範圍。

### 隱私三層原則 (永遠不可違反)

| 層級 | 資料 | 儲存位置 | 上雲規則 |
| ---- | ---- | -------- | -------- |
| L1 明文 | 原始程式碼、瀏覽器內容、對話逐字稿 | 本地 SQLite | **絕對不上雲** |
| L2 意圖向量 | 經 Gemma 邊緣壓縮的 Intent Vector | 本地 SQLite buffer → 雲端 Neo4j | 僅向量,不可還原 |
| L3 業務狀態 | XP、徽章、角色配置、社群貼文 | 雲端 PostgreSQL | 跨裝置同步 |

任何 PR 若違反此原則,Claude Code 必須拒絕實作並回報。

### 觀測性

所有跨模組互動必須寫入 `raw_tracking_logs` (M0.4 定義的結構化日誌)。除錯時先 grep `raw_tracking_logs`,而不是猜。

## 技術棧 (固定,不要建議替代品)

- 桌面殼: **Tauri 2.x (Rust)**
- 前端: **React + Vite + Zustand + Tailwind + Framer Motion**
- 後端: **Python 3.11+ FastAPI + LangGraph + Pydantic v2**
- 邊緣推論: **Gemma 4 E4B (4-bit MLX 量化) @ iPad M1 via ai.local**
- 雲端 LLM: **Gemini 3.5 Pro (走 Google AI Developer Program $10 額度)**
- 本地 DB: **SQLite + SQLAlchemy 2.0**
- 雲端關聯 DB: **PostgreSQL @ Supabase / Render**
- 圖譜 DB: **Neo4j AuraDB Free**
- 任務佇列: **Redis (Pub/Sub) + BullMQ** 或純 Python `arq`

## 不要做的事

1. **不要**自動寫入 `daily_reflections` 表的 `is_reviewed = true`。這是違反 R08「草稿與核准」核心原則。
2. **不要**讓 cloud LLM 看到原始程式碼或對話逐字稿。任何上雲呼叫必須先經 M2.2.2 (意圖向量) + M2.3 (Eguard 過濾)。
3. **不要**為了「優化使用者體驗」就移除微摩擦力 (例如:省略「學到了什麼?」必填欄位)。摩擦是 feature,不是 bug,見 R08。
4. **不要**在使用者高認知負荷期間推播 (M1.2 斷點偵測引擎決定何時可推)。
5. **不要**讓 Persona Agent 直接鏡像使用者情緒 (例:使用者焦慮 → Persona 變焦慮)。應反向 (使用者焦慮 → Persona 安撫),見 R03 §4.2 與 R01 α-DPO。
6. **不要**在缺少 `is_draft = false` 確認前就發放 XP。守門員邏輯見 M4.5 → M6.5 ACID 交易。
7. **不要**為任一 `[進階]` 模組建立硬依賴於另一 `[進階]` 模組之外的 MVP 模組。MVP 必須能在進階模組全數移除時獨立運作。

## 你被授權做的事

- 主動執行 `pytest` / `vitest` 並修復失敗測試
- 主動 `git status` / `git diff` 檢查改動
- 主動建立資料庫 migration (Alembic) 但不可執行 `--autogenerate` 後直接 apply,必須先讓使用者審
- 主動 grep `docs/` 找關聯模組
- 主動讀取 `docs/03_research_index.md` 與 `docs/05_integration_risk_audit.md`

## 你必須詢問使用者的事

- 任何 schema 破壞性變更 (DROP COLUMN, RENAME TABLE)
- 任何跨模組的職責邊界調整
- 任何研究約束的鬆綁 (例如「我們真的需要 NSVIF 嗎?」→ 必須使用者明確拍板)
- 任何上雲服務 (Render, Supabase, Neo4j) 的金流相關設定

## 在 Plan Mode 中的行為

當使用者開啟 Plan Mode 時,優先輸出:

1. 將會修改的檔案清單 (依模組編號分組)
2. 對應的研究引用 `[Rxx: ...]`
3. 整合風險預警 (引用 `05_integration_risk_audit.md` 編號)
4. 驗收標準的測試清單

不要在 Plan Mode 中產生程式碼。Plan Mode 是用來達成共識,不是用來省時間。
