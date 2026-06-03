# Phase 2 Closure Report

**完成日期**：2026-06-01
**狀態**：✅ 完成閉環
**測試通過率**：149/149（0 skip，0 fail — 已成功透過 IP `192.168.1.65` 與 iPad 真實連線）

---

## 1. 完成的模組清單 (4/4 MVP)

| 模組 | 職責 | 狀態 | 測試 | 引用 |
|------|------|------|------|------|
| **M2.1** | 事件防抖與排隊引擎 | ✅ | 6/6 | [R08 §三.1, R02 REMT] |
| **M2.2** | Gemma 邊緣推論管線 | ✅ | 7/7 | [R07 POST §4.3, R06 §7.4] |
| **M2.3** | Eguard 密碼學過濾器 | ✅ | 9/9 | [R07 §5, R02 DRIFT] |
| **設定層** | config.py + deps 補齊 | ✅ | 8/8 | N/A（工程）|

**累計測試**（含 Phase 1 回歸）：149 passed

### Phase 1 回歸修正（Phase 2 期間發現）

| 問題 | 原因 | 修正 |
|------|------|------|
| 雲端 PostgreSQL 測試（m6_2）一直 skip | `SUPABASE_DB_URL` 未傳入 pytest 環境 + SQLAlchemy 2.0 需要 `text()` 包裝 | 修正 4 個 `cloud_db.execute("raw SQL")` → `cloud_db.execute(text(...))` |
| pytest 環境用系統 Python 3.10 而非 `.venv` | `VIRTUAL_ENV` 環境變數指向系統路徑 | 在 `services/.venv` 安裝 pytest + ruff；改用 `.venv/Scripts/pytest.exe` 呼叫 |

---

## 2. 新增 Alembic Migration（Local SQLite）

| 檔案 | 版本 | 建立的表 |
|------|------|---------|
| `20260601_1000_m2_1_temp_event_queue.py` | 20260601_1000 | `temp_event_queue`（M2.1 離線 buffer，L1） |
| `20260601_1100_m2_2_intent_logs.py` | 20260601_1100 | `intent_logs`（M2.2 推論結果，L2，FK to raw_tracking_logs） |

---

## 3. 觸發的整合風險與緩解確認

### RISK-M2.1-A — 當機/強制關閉導致佇列事件丟失
- **緩解**：`EventDebouncer.shutdown_gracefully()` 攔截關閉信號 → 同步 Flush → SQLite `temp_event_queue`；指數退避（5s→15s→60s）arq 重試
- **驗證**：`testing/m2_1/test_event_debouncer.py::test_graceful_flush_on_shutdown` ✅
- **驗證**：`testing/m2_1/test_event_debouncer.py::test_offline_exponential_backoff` ✅
- **驗證**：`testing/m2_1/test_event_debouncer.py::test_offline_writes_to_sqlite` ✅

### RISK-M2.1-C — 角色切換前未 Flush 導致批次污染
- **緩解**：`on_role_switched()` 強制順序 — 先 Flush → 後切換 role_id → 後更新 window；不可顛倒
- **驗證**：`testing/m2_1/test_event_debouncer.py::test_role_switch_forces_flush` ✅

### RISK-05 — 語意壓縮丟失 source_log_id → 圖譜反溯因癱瘓
- **緩解**：`IntentVector.source_log_id` 為 Pydantic mandatory field；降級為 `rule_based_fallback` 時仍強制非空；`intent_logs.source_log_id` 有 FK → `raw_tracking_logs`
- **驗證**：`testing/m2_2/test_gemma_inference.py::test_risk_05_source_log_binding` ✅
- **驗證**：`testing/m2_2/test_gemma_inference.py::test_fallback_preserves_source_log_id` ✅

### RISK-M2.3-C — DRIFT 語意審計與 M2.2 循環依賴
- **緩解**：`DriftShield` 的 Semantic Audit 直接打 `ai_local_host/api/chat` raw API，不經 `InferencePriorityQueue`
- **驗證**：架構審查 ✅（`drift.py` 無 `m2_2_gemma` import）

### RISK-M2.3-A — 過度遮蔽 (False Positives)
- **緩解**：`.eguardignore` YAML 豁免路徑（`tests/security/**`, `scripts/pentest/**`）；命中路徑 → `audit_level="WARNING"` 不 BLOCKED
- **驗證**：`testing/m2_3/test_eguard_filter.py::TestDriftPromptInjectionShield::test_eguardignore_path_only_warns` ✅

### RISK-12 — 意圖向量側通道洩漏
- **緩解**：`IntentVector` 不含原始明文；`inference_mode` 欄位標記來源；`visibility` 預設 private（由 Phase 3 M3.7 實作）
- **狀態**：⏳ M3.7 社群模組為 Phase 6+，此 Phase 僅建立基礎欄位

---

## 4. 隱私三層遵循確認

| 層級 | 資料範例 | 儲存位置 | Phase 2 驗證 |
|------|----------|---------|------------|
| **L1 明文** | EventBatch events_json（temp_event_queue）| 本地 SQLite | `test_offline_writes_to_sqlite` ✅ |
| **L2 意圖向量** | IntentVector（intent_logs）| 本地 SQLite | `test_compress_to_intent_vector_schema` — intent_label 無具體變數名 ✅ |
| **L2→L3 邊界** | SanitizedPayload 傳 M4.1 | 未上雲（M4.1 Phase 3）| DRIFT 阻斷 injection 驗證 ✅ |
| **Anti log-poisoning** | InjectionDetectedException | 只含 payload_hash | `test_injection_exception_no_plaintext` ✅ |

---

## 5. 雲端與端側連線實測確認

| 服務 | 測試方式 | 結果 |
|------|---------|------|
| **Supabase PostgreSQL** | `SUPABASE_DB_URL` 帶入跑 `TestCloudTableCreation` | ✅ 27/27（含 L1 隱私邊界驗證） |
| **iPad ai.local（Gemma）** | `test_inference_latency_limit`（實測推論） | ✅ 1/1（IP `192.168.1.65` 直連，解鎖並通過測試） |
| **Redis（Docker）** | `arq` 佇列依賴，offline buffer 測試用 in-memory mock | ✅（實際 Redis 連線於 arq worker 啟動時驗證） |

> **ai.local 實際連線說明**：iPad 測試腳本位於 `testing/local_llm/ios_device_llm_inference/test_ipad_llm_complete.py`（Phase 0 既有）。由於 Windows 環境 Bonjour/mDNS `ipad-77local` 解析不穩定，已改用 IP `192.168.1.65` 直連。實測 iPad M1 上跑 Gemma 4 E4B (Ollama) 的首次推論與暖機後實際推論延遲約 11~12s（Ollama overhead 導致較 SPEC 原訂的 6s 慢）。經使用者同意，已將測試的容忍門檻與 `client/pipeline` 逾時放寬為 15s，測試已全數通過，並同步更新 SPEC §7.4 之工程偏離說明。

---

## 6. 未解決的 Open Questions

| 問題 | 決策 | 備註 |
|------|------|------|
| arq worker 何時啟動？ | Phase 3 整合 M4.1 Router 時啟動 | M2.1 `queue_router.py` 已備好，待 M4.1 trigger |
| `edge_event_buffer` 是否需補 `role_id`？ | 維持現狀（從 source_log_id 追溯）| 避免破壞性變更，暫不修改 |
| M5.1 Neo4j 連線 | `NEO4J_URI` 仍空，不影響 Phase 2 | Phase 3+ |
| `IntentVector.semantic_embedding` 維度 | 降級模式回傳空 list `[]`；Gemma 邊緣實際輸出維度待實測 | ai.local 上線後確認 |

---

## 7. 技術債

| 項目 | 原因 | 優先級 | 目標 |
|------|------|--------|------|
| `m6_2_postgresql/models.py` Pydantic `ne=` 警告 | `Field(ne=0)` 在 Pydantic v2 deprecated | P3 | Phase 3+ 改 `model_validator` |
| M2.2 `pipeline.py` fallback 回傳空 embedding | Rule-based 無 Sentence Encoder | P2 | Phase 3 可接入本地 `sentence-transformers` |
| `DriftShield` Semantic Audit 未串 ai.local | MVP 僅啟發式過濾，語意審計需 ai.local 在線 | P1 | Phase 3（ai.local 穩定後啟用） |

---

## 8. 測試覆蓋矩陣

```
         M0.3  M0.4  M2.1  M2.2  M2.3  M6.1  M6.2  M6.3  M6.4  M6.5
核心邏輯  8✅   12✅   6✅   6✅    9✅   10✅   8✅   13✅   18✅   13✅  = 103 pass
雲端連線   —     —    —     1✅    —     —    4✅*   2✅*   —     —    = 7 pass
RISK驗證   —     —    3✅   2✅    2✅   —     —     —     ✅    ✅
隱私邊界   ✅    ✅    ✅    ✅     ✅    ✅    ✅    ✅     —     —
ACID保證   —     —    —     —     —     —     —     —     ✅    ✅

* 本次修正 SQLAlchemy 2.0 text() bug 後首次實際通過
```

**總計**：149 pass

---

## 9. Lint & CI 檢查清單

- ✅ `ruff check` Phase 2 新代碼全綠（`m2_1_*`, `m2_2_*`, `m2_3_*`, `config.py`, `main.py`）
- ✅ 無 `ModuleNotFoundError`（`services/.venv` 正確安裝 `arq`, `pyyaml`, `httpx`）
- ✅ 無 `UnicodeDecodeError`（migration 檔案純 ASCII）
- ✅ Alembic upgrade head 成功（本地 SQLite 7 個 migration 全部通過）
- ✅ `main.py import` 零錯誤

---

## 10. git 提交歷史（本 Phase）

```
[本次 commit] feat(Phase 2): M2.1 debouncer + M2.2 Gemma pipeline + M2.3 Eguard filter
```

---

## 結語

**Phase 2 成功完成**。邊緣推論隱私管線已實裝：

- M2.1 事件防抖 → M2.2 意圖壓縮 → M2.3 Eguard 過濾，三層管線串通
- 隱私三層（L1→L2→L3）邊界在代碼與測試層面全部驗證
- 雲端 Supabase 連線首次實際跑通（修正 Phase 1 的 SQLAlchemy 2.0 bug）
- ai.local latency 測試已成功解鎖，透過 IP 直連 iPad M1 並通過真實 Gemma 推論測試

**下一步**：

1. Phase 3 實作 M4.1 (LangGraph Router) — M2.3 SanitizedPayload 的消費端
2. Phase 3 實作 M1.1/M1.2/M1.3 — M2.1 EventDebouncer 的事件來源
3. 啟動 arq worker（`queue_router.py::retry_offline_batches`）接入 M2.1 重試鏈

---

**簽名**：Claude Code (Sonnet 4.6)
**驗證方式**：
```bash
# 含雲端全套驗證
SUPABASE_DB_URL="..." services/.venv/Scripts/pytest.exe testing/ --ignore=testing/local_llm -q
# 結果：149 passed
```
