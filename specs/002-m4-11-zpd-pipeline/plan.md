# Implementation Plan: M4.11 動態邊界任務池與 ZPD 盲盒管線 (Dynamic ZPD Gacha Pipeline)

**Branch**: `002-m4-11-zpd-pipeline` | **Date**: 2026-10-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-m4-11-zpd-pipeline/spec.md`

## Summary

本功能實作 **M4.11 動態邊界任務池與 ZPD 盲盒管線**，作為 coOS 的進階遊戲化學習與身心平衡引擎。透過結合近端對話分析（M4.11.1）、多模態貝氏知識追蹤（M4.11.2 BKT）與 ZONE 框架（M4.11.3 REJECT + GRAD 演算法），動態生成剛剛好位於使用者能力前沿（近側發展區 ZPD）的客製化延伸挑戰；並在偵測到高認知負荷時，自適應切換為框架外生活恢復微冒險（散步、烹飪、微探店），落實注意力恢復理論（ART）與零質押（Zero-Staking, RISK-07）心理保護鐵律。

## Technical Context

**Language/Version**: Python 3.11+ (FastAPI 後端), TypeScript 5.x / React 18 (前端組件)  
**Primary Dependencies**: FastAPI, Pydantic v2, SQLAlchemy (SQLite), NumPy/SciPy (BKT 數學運算), Uvicorn, Pytest  
**Storage**: 本地 SQLite (`coos.db`)，新增 `role_skill_mastery` 與 `zpd_challenges` 表，嚴格落實 L1 隱私規範  
**Testing**: Pytest 後端測試 (`testing/m4_11/`), Vitest 前端組件測試 (`apps/desktop/src/components/m3_11_gacha/`)  
**Target Platform**: Windows 11 Desktop (Tauri Localhost / Offline-First)  
**Project Type**: 本地優先桌面應用混合服務 (Desktop Local-First Hybrid Application)  
**Performance Goals**: `POST /api/m4_11/draw_challenge` P95 < 1500ms（動態生成），雙階降級 < 300ms  
**Constraints**:
* **100% 離線可用**：網路斷線或推論超時（>5 秒）自動降級為領域種子庫與槽位填充。
* **零質押鐵律 (RISK-07)**：禁止任何扣款或 XP 質押，失敗或逾期 0 懲罰。
* **安全退縮 (RISK-09)**：高認知負荷或焦慮狀態下難度自動降級且時長 $\le 15$ 分鐘。
* **軟性跨日過期**：次日 04:00 AM 平滑結轉，無分秒倒數計時壓迫。
* **反思微摩擦**：經驗值發放由 M6.5 `XPGatekeeper` 檢驗自我申報反思後以 ACID 交易原子寫入。
* **進階模組獨立性**：M4.11 為 `[進階]` 模組，對 MVP 核心無反向硬依賴。  
**Scale/Scope**: 本地單一使用者，~10 個活動角色，數十個技能領域，每日抽取 < 10 次。

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 憲法原則 | 檢核標準 | 評估結果 | 實作保證機制 |
|---|---|---|---|
| **I. Three-Tier Privacy** | L1 對話與日誌不得明文上傳雲端 | **PASS** | BKT 計算與對話分析 100% 本地進行，LLM 請求僅發送去識別化語境或由本機 Gemma (M2.2) 處理。 |
| **II. Psychological Invariants** | 零質押 (RISK-07)、反思微摩擦 (R08)、焦慮安全退縮 (RISK-09) | **PASS** | 嚴格禁止 XP 押金；完成挑戰必須填寫反思；M4.8 焦慮狀態觸發難度與時長雙重退縮；軟性 24h 過期。 |
| **III. Specification as Contract** | 行為變更具備核可規格與明確驗收條件 | **PASS** | [spec.md](./spec.md) 涵蓋 P1~P5 使用者故事、FR-001~FR-016、16/16 檢核項通過。 |
| **IV. Test-First, Evidence-Driven** | 先寫紅燈測試再實作，依據真實 session 數據宣告完成 | **PASS** | 規劃 6 大核心測試套件 (`testing/m4_11/`)，遵循 TDD 週期。 |
| **V. MVP Independence** | 進階模組不得為 MVP 核心增加反向依賴 | **PASS** | M4.11 透過獨立資料表與 API 暴露服務，MVP 模組在無 M4.11 時依然可獨立運行。 |
| **VI. Research Citation** | 程式碼與規格書落實標準學術標籤 `[Rxx: Keyword §Chapter]` | **PASS** | 明確引用 `[R01: ZONE 框架]`, `[R01: 多模態 BKT]`, `[R01: α-DPO, RISK-07]`, `[R08: 微摩擦]`。 |
| **VII. Full Observability** | 關鍵狀態轉移向 M0.4 發布結構化日誌 | **PASS** | 抽卡、接受、完成、過期、降級事件均寫入 `raw_tracking_logs`。 |

## Project Structure

### Documentation (this feature)

```text
specs/002-m4-11-zpd-pipeline/
├── spec.md              # 需求規格書 (Clarification 固化完成)
├── checklists/
│   └── requirements.md  # 規格品質檢核表 (16/16 通過)
├── plan.md              # 本實作計畫書 (Phase 0 & 1 交付成果)
├── research.md          # Phase 0: 架構決策與 BKT / ZONE 數學模型
├── data-model.md        # Phase 1: SQLite DDL 與 Pydantic 領域實體
├── quickstart.md        # Phase 1: 可執行的端到端驗證與 API 調試指南
├── contracts/           # Phase 1: 外部合約定義
│   ├── openapi.yaml
│   └── draw_challenge.contract.json
└── tasks.md             # Phase 2 產出 (由 /speckit-tasks 生成)
```

### Source Code (repository root)

```text
services/
├── m4_11_zpd_pipeline/             # M4.11 核心後端模組
│   ├── __init__.py
│   ├── models.py                   # SQLAlchemy 實體表定義 (role_skill_mastery, zpd_challenges)
│   ├── schemas.py                  # Pydantic DTO (ZPDChallengeDTO, CompleteChallengeRequest 等)
│   ├── bkt_tracker.py              # 多模態 BKT 掌握度推斷引擎
│   ├── zone_sampler.py             # ZONE REJECT + GRAD 演算法與疲勞自適應調權
│   ├── task_synthesizer.py         # LLM Prompt 合成器與雙階種子降級備援
│   ├── seeds.json                  # 領域預載種子挑戰題庫 (含技能延伸與生活恢復題)
│   └── router.py                   # FastAPI 端點 (/draw_challenge, /accept_challenge, /complete_challenge)
└── main.py                         # 掛載 m4_11_router

testing/
└── m4_11/                          # 專屬測試套件 (遵循 TDD)
    ├── __init__.py
    ├── conftest.py                 # SQLite 記憶體資料庫與假資料 Fixtures
    ├── test_bkt_tracker.py         # BKT 數學更新與掌握度邊界測試
    ├── test_zone_sampler.py        # ZONE 篩選、疲勞自適應權重與生活任務比例測試
    ├── test_task_synthesizer.py    # Prompt 合成與雙階離線降級測試 (<300ms)
    ├── test_zero_staking.py        # RISK-07 零質押與逾期零懲罰鐵律測試
    └── test_router_integration.py  # 完整 API 端點、單一槽位替換與 M6.5 ACID 派發整合測試

apps/desktop/src/components/m3_11_gacha/
├── DrawChallengeButton/            # 前端抽挑戰組件 (相容 M4.11 API)
└── types.ts                        # 前端 ZPDChallenge 介面定義
```

**Structure Decision**:
採用清晰的模組化單一目錄 `services/m4_11_zpd_pipeline/` 組織業務邏輯，將「BKT 數學狀態機 (`bkt_tracker.py`)」、「難度篩選器 (`zone_sampler.py`)」與「任務合成器 (`task_synthesizer.py`)」完全解耦，大幅提升測試性；所有測試集中於 `testing/m4_11/`，嚴格落實 TDD。

## Complexity Tracking

> 無任何違反專案憲法原則之架構設計，無需複雜度豁免。

| 項目 | 複雜度理由 | 替代方案評估與揚棄原因 |
|---|---|---|
| **多模態 BKT** | 需數學追蹤使用者能力演進 | 揚棄簡單固定題庫，因靜態題目無法提供長期變動增強與個性化共鳴。 |
| **雙階降級機制** | 本地種子與參數化填充 | 揚棄純 LLM 無降級，確保離線與超時（>5 秒）情況下 100% 可用且 <300ms 返回。 |
