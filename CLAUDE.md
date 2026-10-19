# coOS — Claude Code 專案憲章

> **此檔案為 Claude Code 每次 session 必讀。** 本檔只寫「**不可違反什麼**」與「**去哪裡找怎麼做**」。
> 開發流程的唯一權威是 [`docs/DEV_WORKFLOW.md`](docs/DEV_WORKFLOW.md);兩者衝突時以本檔憲章條款為準,並回報衝突。

## 你是誰

你正在協助開發 **coOS**:一款結合多智能體 AI、遊戲化、薩提爾冰山心理模型與邊緣-雲端協同推論的個人目標管理系統。本專案融合心理學、認知科學、混合主動式人機互動與 2026 年最新端側 LLM 技術。使用者是產品與心理模型的決策者 (以「拍板」定案),實作多半交由你執行。

## 接到任務時:先分級,再走對應流程

先問:「**改完之後,SPEC 上的文字還對嗎?**」判斷不出來 → 當 T2。

| Track | 條件 | 用哪個 skill / 流程 |
| ----- | ---- | ------------------- |
| T0 Quick | 不改任何 SPEC 定義的行為 (錯字、文件、樣式、lint) | 直接改 → 驗證 → commit (DEV_WORKFLOW §4) |
| T1 Fix | SPEC 已定義正確行為,程式碼不符 | DEV_WORKFLOW §5 系統化除錯 (有 Superpowers 時用 `systematic-debugging`) |
| T2 Change | 改 / 增 / 刪 SPEC 行為、API、schema、常數門檻、跨模組依賴 | `propose-change` → `implement-module` → `archive-change` |
| T3 New Module | 該 `Mx.y` 沒有 SPEC 或 SPEC 為 `draft` | 同 T2,並依 `docs/modules/_TEMPLATE_SPEC.md` 建 SPEC |

T2/T3 七階段:**P1 釐清 → P2 提案 + spec delta → [G1 使用者拍板] → P3 計畫 + 一致性檢查 → P4 TDD → P5 驗證 → P6 審查 → P7 歸檔**。
只有 G1 一定要停下等使用者;其餘關卡自查並附證據。研究引用相關時使用 skill `cite-research`;跨 2+ 模組時 `audit-integration` 由 `propose-change` 呼叫。

**Plan Mode**:輸出 (1) Track 判定 (2) 將修改的檔案 (依模組分組) (3) 研究引用 `[Rxx …]` (4) 觸發的 `RISK-xx` (5) 需求情境 → 測試清單。不在 Plan Mode 產生程式碼。

---

## 憲章 (不可違反;違反時拒絕實作並回報)

### 第一條 隱私三層

| 層級 | 資料 | 儲存位置 | 上雲規則 |
| ---- | ---- | -------- | -------- |
| L1 明文 | 原始程式碼、瀏覽器內容、對話逐字稿 | 本地 SQLite | **絕對不上雲** (可傳至本地 API / 本地 LLM) |
| L2 意圖向量 | 經 Gemma 邊緣壓縮的 Intent Vector | 本地 SQLite buffer → 雲端 Neo4j | 僅向量,不可還原 |
| L3 業務狀態 | XP、徽章、角色配置、社群貼文 | 雲端 PostgreSQL | 跨裝置同步 |

- 任何上雲 LLM 呼叫必須先經 M2.2.2 (意圖向量) + M2.3 (Eguard 過濾)。cloud LLM 不可看到原始程式碼或對話逐字稿。
- 冰山假設內容 (M5) 屬 L1,僅存本地,不進任何雲端 prompt;雲端只收得到行為指令 (`docs/M5_ICEBERG_REDESIGN.md` 已拍板,RISK-19)。

### 第二條 心理機制不變式 (研究約束)

1. **草稿與核准**:不可自動寫入 `daily_reflections.is_reviewed = true` [R08: IKEA 效應 §六.1]。
2. **XP 守門**:Earned XP 只在 M6.5 `XPGatekeeper` 條件**全部**成立時發放——`is_draft = false` 且 `is_reviewed = true` 且 `user_feeling`、`user_action_plan` 非空且尚未 `xp_settled` (RISK-01、M4.5 → M6.5 ACID 交易)。
3. **微摩擦是 feature**:不可為了「優化體驗」移除必填欄位 (例:「學到了什麼?」) 或核准步驟 [R08: 微摩擦力 §四.2]。
4. **推播時機**:使用者高認知負荷期間不推播,由 M1.2 斷點偵測決定 (RISK-04)。
5. **Persona 反向安撫**:不可鏡像使用者情緒 (使用者焦慮 → Persona 安撫,而非變焦慮),見 R03 §4.2 與 R01 α-DPO (RISK-03)。

鬆綁任何一條都必須由使用者明確拍板,並記錄在 change 的 `proposal.md`。

### 第三條 規格即合約

- `docs/modules/*_SPEC.md` 描述**現況已核准行為**;要改行為,先在 `docs/changes/<change-id>/` 寫 proposal + spec delta,經 G1 拍板後才改程式碼。
- **不留「程式碼與 SPEC 不一致、之後補登」的狀態。** 實作中發現 delta 不對 → 先改 delta 再改碼。
- 觸及 2+ 模組 → 必做整合風險稽核 (`audit-integration`),結果寫進提案。
- 發現既存 (非本次造成) 的偏離 → 登記到 `docs/SPEC_DEVIATION_REPORT.md` / `docs/IMPLEMENTATION_GAP_REPORT.md`,以後續 change 關閉。

### 第四條 測試先行,證據說話

- 驗收情境先寫成測試,**親眼看它因正確原因失敗**,再實作。
- 沒有本 session 新鮮的執行輸出,不可宣稱「完成」「通過」「修好」。回報附指令與通過 / 失敗 / 跳過數。
- 跨模組改動必須有閉環測試;單元測試全綠不代表接縫正確。
- 不可為了通過而放寬測試斷言——改斷言即改需求,回提案。

### 第五條 MVP 獨立與進階守門

- 不要為任一 `[進階]` 模組建立硬依賴於另一 `[進階]` 模組之外的 MVP 模組。MVP 必須能在進階模組全數移除時獨立運作。
- `[進階]` 模組僅能在 `docs/MVP_CLOSURE_REPORT.md` **最新判定為 GO** 後動工 (報告存在 ≠ GO)。

### 第六條 研究引用格式

宣稱「依據研究」的程式碼註解、SPEC、commit 必須用 `[Rxx: 關鍵字 §章節]`,編號須存在於 `docs/03_research_index.md`:

```python
# [R03: Echo Mode §3.2] 偵測到防衛語氣時,調降 Agency 從 0.8 → 0.3
# [R08: 微摩擦力 §四.2] 強制留白「主觀感受」欄位,觸發 System 2 思維
```

禁止「根據相關研究」等無法溯源的引用;查不到就不要宣稱有研究依據。非研究推導的程式碼 (CRUD、接線、UI) 不需要引用。

### 第七條 可觀測性

- 所有跨模組互動寫入 `raw_tracking_logs` (M0.4);除錯先查它,不要猜。
- 禁止靜默吞例外 (`except: pass`、無 log 的 `return None`)。

---

## 必須詢問使用者的事

- 每個 T2/T3 change 的提案 (G1)
- 任何 schema 破壞性變更 (DROP COLUMN、RENAME TABLE)
- 任何跨模組的職責邊界調整
- 任何研究約束的鬆綁 (例:「我們真的需要 NSVIF 嗎?」)
- 任何上雲服務 (Render、Supabase、Neo4j) 的金流相關設定
- push、開 PR、merge (除非使用者已要求)

## 你被授權做的事

- 主動執行 pytest / vitest / ruff / eslint 並修復失敗
- 主動 `git status` / `git diff` / 在 change 分支上 commit
- 主動建立 Alembic migration **檔案**;不可 `--autogenerate` 後直接 apply,必須先讓使用者審
- 主動 grep `docs/`、讀 `03_research_index.md` 與 `05_integration_risk_audit.md` 的相關段落

---

## 專案地圖 (以此為準;skill 或舊文件與此衝突時以此為準)

| 東西 | 位置 |
| ---- | ---- |
| 後端模組 | `services/mx_y_<name>/` (例 `services/m4_2_persona/`) |
| 後端進入點 | `services/main.py` (唯一 FastAPI app,sidecar @ `localhost:8000`) |
| 後端測試 | `testing/mx_y/` (根目錄 `testing/`,`pytest.ini` 的 `testpaths`) |
| 前端元件 | `apps/desktop/src/components/mx_y_<name>/` |
| 前端測試 | `apps/desktop/tests/mx_y/` |
| 擴充套件 | `apps/vscode-extension/` (M1.3.1)、`apps/browser-extension/` (M1.3.2) |
| 設定 | `services/config.py` 的 `Settings` (讀取:環境變數 > `.env` > 預設) |
| 遷移 | `services/alembic_local.ini` (SQLite) 與 `services/alembic_cloud.ini` (PostgreSQL),兩條獨立歷史 |
| 模組 SPEC | `docs/modules/Mx_y_*_SPEC.md` |
| 變更提案 | `docs/changes/<change-id>/`,已完成移到 `docs/changes/archive/` |
| 文件索引 | `docs/00_README.md` |

**命名**:檔案、API、資料表一律以模組編號為前綴——`services/m4_1_router/router.py`、`POST /api/m4_4/draft`、`CREATE TABLE m6_5_daily_reflections`。

**定向讀文件** (不要整份讀 1000+ 行的 03/05):

```bash
grep -n -A 40 "^### M4.2 " docs/04_module_registry.md
grep -n -A 35 "^## R03 " docs/03_research_index.md
grep -n "M4\.2" docs/05_integration_risk_audit.md
```

## 常用指令

```bash
# 後端全套 (~5 分鐘;排除需要 sidecar / iPad 的測試)。一律用 services/.venv,系統 Python 缺套件
cd services && .venv/Scripts/python.exe -m pytest ../testing/ --ignore=../testing/local_llm --ignore=../testing/m0_2 -q 2>&1 | tail -15
# 單一模組
cd services && .venv/Scripts/python.exe -m pytest ../testing/m4_2 -q 2>&1 | tail -15
# 失敗時只展開失敗段落
cd services && .venv/Scripts/python.exe -m pytest ../testing/m4_2 -q 2>&1 | grep -A 15 "FAILED\|Error"

# 前端
pnpm --filter @coos/desktop test
# Lint (commit 前)
cd services && uv run ruff check . --fix
pnpm --filter @coos/desktop lint
# 開發
pnpm dev:backend        # FastAPI sidecar
pnpm dev                # 前端 + Tauri
```

> 根目錄 `pnpm test` 的後端段落指向 `services/testing/` (不存在),在修正前不要用它判斷測試結果。

## 技術棧 (固定,不要建議替代品)

- 桌面殼:**Tauri 2.x (Rust)**
- 前端:**React + Vite + Zustand + Tailwind + Framer Motion**
- 後端:**Python 3.11+ FastAPI + LangGraph + Pydantic v2**
- 邊緣推論:**Gemma 4 E4B (4-bit MLX 量化) @ iPad M1 via ai.local**
- 雲端 LLM:**Gemini 3.5 Flash** / **Gemini 3.1 Flash Lite** (暫時使用) (未來取得資源後使用 **Gemini 3.5 Pro**,走 Google AI Developer Program $10 額度)
- 本地 DB:**SQLite + SQLAlchemy 2.0**
- 雲端關聯 DB:**PostgreSQL @ Supabase / Render**
- 圖譜 DB:**Neo4j AuraDB Free**
- 任務佇列:**Redis (Pub/Sub) + BullMQ** 或純 Python `arq`

## Windows 與除錯備忘 (省 token)

1. **設定檔純 ASCII**:`.ini`、`pyproject.toml`、alembic 設定只用 ASCII (locale 為 cp950)。遇 `UnicodeDecodeError` 先定位非 ASCII 字元,不要把整段 stack trace 讀進 context:

   ```bash
   python -c "content = open('file.ini', encoding='utf-8').read(); [print(f'pos {i}: {repr(c)}') for i,c in enumerate(content) if ord(c)>127]"
   ```

2. **測試輸出只取尾部**:一律 `2>&1 | tail -15`;需要細節再 `grep -A 15 "FAILED"`。
3. **ModuleNotFoundError**:先確認用的是 `services/.venv`,再印 `sys.path`,不要猜。
4. **Pydantic Settings**:測試中 `Settings(_env_file=None)` 並 patch 模組層級的 `get_settings`,`monkeypatch.delenv` / `patch.dict(os.environ)` 對已快取的設定無效。`.env` 新增變數讀不到 → 檢查 `services/config.py` 的 `Settings` 是否定義該欄位。
5. **configparser 插值**:`.ini` 不可用 `%(KEY)s`,改在 `env.py` 置換。
6. **Sidecar 依賴測試**:依賴 `127.0.0.1:8000` 的測試在檔頭加 skip marker:

   ```python
   pytestmark = pytest.mark.skipif(not _sidecar_reachable(), reason="sidecar not running")
   ```

7. **測試不可碰真實 `data/coos.db`**:用 tmp SQLite + 覆寫 `local_db_path` (參考 `testing/m4_5/test_mvp_closed_loop.py`)。
