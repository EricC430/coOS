# Implementation Plan: M4.12 隱藏成就驗證引擎 (Hidden Achievement Verification Engine)

**Branch**: `003-m4-12-hidden-achievement` | **Date**: 2026-10-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-m4-12-hidden-achievement/spec.md`

## Summary

本功能實作 **M4.12 隱藏成就驗證引擎**，作為 coOS 進階遊戲化激勵與全人發展（薩提爾冰山、注意力恢復 ART、跨領域思維融合）之核心模組。系統透過「主動探索特徵捕捉網（M4.12.1）」在背景無感監聽使用者對話歷史與每日反思，藉由「快慢雙軌混合觸發架構」識別使用者自主深探高階概念、心理盲點轉化與生活滋養行為；實作 M3.11.3 鐵律——未解鎖狀態下 API 與 DOM 0% 資料洩漏（絕對無 UI 狀態防 FOMO）；並透過「心流感知廣播器（M4.12.2）」在自然微斷點（M1.2 Breakpoint）以 WebSocket 即時推送無預警驚喜彈窗（M3.11.4），配合 M6.5 ACID 交易原子寫入與 XP 結算。

## Technical Context

**Language/Version**: Python 3.11+ (FastAPI 後端), TypeScript 5.x / React 18 (桌面端客戶端)  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy (SQLite), Uvicorn, WebSockets, Pytest, Pytest-Asyncio  
**Storage**: 本地 SQLite (`coos.db`)，新增 `hidden_achievements`, `user_achievements`, `epistemic_evidence_queue` 表，落實 L1 隱私規範  
**Testing**: Pytest 後端測試 (`testing/m4_12/`), Vitest 前端整合測試 (`apps/desktop/src/components/m3_11_gacha/`)  
**Target Platform**: Windows 11 Desktop (Tauri Localhost / Offline-First)  
**Project Type**: 本地優先桌面應用混合服務 (Desktop Local-First Hybrid Application)  
**Performance Goals**: 快軌特徵預篩 P95 < 100ms；端到端解鎖至 WebSocket 廣播 < 1000ms；API 零洩漏查詢 < 50ms  
**Constraints**:
* **絕對無 UI 狀態 (Zero-Leaked State, M3.11.3)**：未解鎖隱藏成就 100% 於 API 查詢層過濾，DOM 不得存在任何佔位節點、問號輪廓或剩餘計數（防 FOMO）。
* **在地隱私保證 (L1 Privacy, Principle I)**：對話與反思語意特徵掃描 100% 於本機端執行，明文逐字稿絕不上傳外部雲端。
* **心流感知微斷點推播 (Flow-Gated Delivery, RISK-04)**：高認知負荷或深層編程期間暫存廣播佇列，待 M1.2 斷點發布（送出訊息、任務交接）才觸發彈窗。
* **離線與推論逾時佇列 (Offline & Timeout Fallback)**：本機 Gemma (M2.2) 離線或逾時（>3s）時，特徵佐證安全寫入 `epistemic_evidence_queue` 待命重試，不阻斷主流程。
* **開機單一精選上限 (Single Cap Catch-Up)**：斷線重連或開機若有積壓成就，至多展示 1 筆最高稀有度之 `SurpriseModal`，其餘標註「NEW」徽章靜默點亮入庫。
* **M6.5 ACID 交易冪等性**：解鎖與經驗值結算於單一 DB 交易內完成，完全冪等防重複刷獎。
* **進階模組獨立性 (Principle V)**：M4.12 屬 `[進階]` 模組，不對 MVP 核心產生反向硬依賴。  
**Scale/Scope**: 本地單一使用者，4 大核心原型，~20+ 預定義與領域動態成就，終身累計 < 100 筆解鎖紀錄。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 憲法原則 | 檢核標準 | 評估結果 | 實作保證機制 |
|---|---|---|---|
| **I. Three-Tier Privacy** | L1 對話與反思明文不得上傳雲端 | **PASS** | 快慢雙軌特徵提取與 Gemma (M2.2) 推論 100% 本地化，僅本地 SQLite 存取。 |
| **II. Psychological Invariants** | 零洩漏防 FOMO (M3.11.3)、心流微斷點保護 (RISK-04)、反思微摩擦 | **PASS** | API 強制過濾未解鎖隱藏項；M1.2 斷點門禁防心流中斷；成就不預告、不功利引導。 |
| **III. Specification as Contract** | 行為變更具備核可規格與明確驗收條件 | **PASS** | [spec.md](./spec.md) 涵蓋 P1~P5 使用者故事、FR-001~FR-015、16/16 檢核項全數通過。 |
| **IV. Test-First, Evidence-Driven** | 先寫紅燈測試再實作，依據真實 session 數據宣告完成 | **PASS** | 規劃 5 大核心測試套件 (`testing/m4_12/`)，落實 TDD 驗收。 |
| **V. MVP Independence** | 進階模組不得為 MVP 核心增加反向依賴 | **PASS** | M4.12 透過獨立路由與 WebSocket 事件解耦，MVP 模組移除 M4.12 仍完全獨立運行。 |
| **VI. Research Citation** | 程式碼與規格書落實標準學術標籤 `[Rxx: Keyword §Chapter]` | **PASS** | 引用 `[R01: 動態邊界]`, `[R01: 變動比例增強]`, `[R04: 認知中斷, RISK-04]`, `[R09: 防沉迷與 FOMO]`。 |
| **VII. Full Observability** | 關鍵狀態轉移向 M0.4 發布結構化日誌 | **PASS** | 特徵命中、排隊、微斷點推播、ACID 入庫均寫入 `raw_tracking_logs`。 |

## Project Structure

### Documentation (this feature)

```text
specs/003-m4-12-hidden-achievement/
├── spec.md              # 需求規格書 (Clarification 固化完成)
├── checklists/
│   └── requirements.md  # 規格品質檢核表 (16/16 通過)
├── plan.md              # 本實作計畫書 (Phase 0 & 1 交付成果)
├── research.md          # Phase 0: 架構決策、快慢雙軌設計與反 FOMO 資料庫隔離
├── data-model.md        # Phase 1: SQLite DDL、Pydantic 領域實體與狀態轉移
├── quickstart.md        # Phase 1: 可執行的端到端驗證與 API / WebSocket 調試指南
├── contracts/           # Phase 1: 外部合約定義
│   ├── openapi.yaml
│   └── websocket_events.json
└── tasks.md             # Phase 2 產出 (由 /speckit-tasks 生成)
```

### Source Code (repository root)

```text
services/
├── m4_12_hidden_achievement/            # M4.12 核心後端模組
│   ├── __init__.py
│   ├── models.py                       # SQLAlchemy 實體表定義 (hidden_achievements, user_achievements, epistemic_evidence_queue)
│   ├── schemas.py                      # Pydantic DTO (HiddenAchievementDTO, UnlockEventPayload 等)
│   ├── archetypes.py                   # 四大核心成長原型定義與宣告式 DSL 規則庫
│   ├── feature_trap.py                 # M4.12.1 特徵捕捉網 (Fast Path 正則嵌入 + Slow Path Gemma 評估)
│   ├── evidence_queue.py               # 離線與推論逾時非同步待命佇列守護器
│   ├── surprise_dispatcher.py          # M4.12.2 心流感知微斷點排隊器與 WebSocket 廣播引擎
│   └── router.py                       # FastAPI 端點 (/api/achievements 零洩漏查詢, /api/m4_12/ws, 手動重試端點)
└── main.py                             # 掛載 m4_12_router

testing/
└── m4_12/                              # 專屬測試套件 (遵循 TDD)
    ├── __init__.py
    ├── conftest.py                     # SQLite 記憶體資料庫與假資料 Fixtures
    ├── test_zero_leakage.py            # M3.11.3 絕對無 UI 狀態與 API 0% 洩漏測試
    ├── test_dual_track_eval.py         # 快慢雙軌特徵識別與偽陽性防刷測試
    ├── test_flow_gated_broadcast.py    # M1.2 微斷點延遲排隊與開機單上限 (Single Cap) 補發測試
    ├── test_offline_queue.py           # 本機 Gemma 離線/逾時佇列暫存與出隊重試測試
    └── test_acid_settlement.py         # M6.5 ACID 交易原子寫入與冪等防重發測試

apps/desktop/src/components/m3_11_gacha/
├── HiddenAchievement/                  # 隱藏成就零洩漏網格與驚喜彈窗
│   ├── AchievementGrid.tsx             # 嚴格 0 佔位過濾器
│   └── SurpriseModal.tsx               # M3.11.4 驚喜解鎖彈窗組件
└── types.ts                            # 前端 WebSocket 事件與成就介面定義
```

**Structure Decision**:
在 `services/m4_12_hidden_achievement/` 中將「特徵捕捉網 (`feature_trap.py`)」、「離線重試佇列 (`evidence_queue.py`)」、「心流微斷點推播 (`surprise_dispatcher.py`)」與「核心原型定義 (`archetypes.py`)」完全模組化解耦；後端 API 在 `router.py` 實作資料庫層級的零洩漏過濾（`WHERE is_hidden = false OR (is_hidden = true AND unlocked_at IS NOT NULL)`），前端組件嚴格遵循零 DOM 殘留原則。

## Complexity Tracking

> 無任何違反專案憲法原則之架構設計，無需複雜度豁免。

| 項目 | 複雜度理由 | 替代方案評估與揚棄原因 |
|---|---|---|
| **快慢雙軌架構** | 兼顧即時命中（<100ms）與深度元認知評估 | 揚棄純即時慢推論（開銷過大）與純批次掃描（缺乏當下突破驚喜感）。 |
| **離線待命佇列** | 應對 Gemma 離線、未載入或推論逾時 | 揚棄直接丟棄（遺漏寶貴學習突破）與同步阻塞（卡死對話主流程）。 |
| **開機單上限補發** | 杜絕斷線重連或開機連續彈窗轟炸 | 揚棄全部逐一彈出（嚴重干擾啟動體驗）與全部靜默跳過（錯失儀式感）。 |
| **SQL 零洩漏過濾** | 徹底消除 DevTools / Redux 看到未解鎖成就之可能性 | 揚棄前端布林值隱藏（前端傳輸 payload 仍會洩漏 ID 與名稱，引發 FOMO 逆向破解）。 |
