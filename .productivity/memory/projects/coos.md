# coOS

## 一句話

多智能體 AI + 遊戲化 + 薩提爾冰山 + 邊緣雲端協同的個人目標管理系統。是 Obsidian Vault 的高階介面，不是它的替代品。

## 現況（2026-08）

- Phase 0 → 1 → 1.5 → 2 → 3 → 4+5 → 5.5 已關閉
- 後端 446 測試通過 / 0 failed / 7 skipped
- 已落地：M0.4、M1.1、M1.2、M1.4、M2.1–2.3、M3.1–3.7、M4.1–4.6、M4.13、M6.1–6.6
- **未實作**：M1.5、M1.6、M2.4–2.6、M3.8–3.11、M4.7–4.12、M5.1–5.3、M7.1
- 最大名實落差：產品定位第一句話的「薩提爾冰山」目前 0 行程式碼（M5 全空，Neo4j 只在 `config.py` 出現）

## 技術棧（固定，不建議替代品）

| 層 | 技術 |
| --- | --- |
| 桌面殼 | Tauri 2.x (Rust) |
| 前端 | React + Vite + Zustand + Tailwind + Framer Motion |
| 後端 | Python 3.11 + FastAPI + LangGraph + Pydantic v2 |
| 邊緣推論 | Gemma 4 E4B (4-bit MLX) @ iPad M1 via `ai.local` |
| 雲端 LLM | Gemini 3.5 Flash / 3.1 Flash Lite（四層 Tier + fallback） |
| 本地 DB | SQLite + SQLAlchemy 2.0 |
| 雲端 DB | PostgreSQL @ Supabase |
| 圖譜 DB | Neo4j AuraDB Free（尚未使用） |

## 開發指令

```bash
# 後端
cd services && uv run uvicorn main:app --port 8000
# 前端
cd apps/desktop && pnpm dev
# 測試
cd services && .venv/Scripts/python.exe -m pytest ../testing/ \
  --ignore=../testing/local_llm --ignore=../testing/m0_2 -q
```

## 重要文件

| 檔案 | 用途 |
| --- | --- |
| `CLAUDE.md`（repo 根） | 專案憲章，每次 session 必讀 |
| `docs/03_research_index.md` | 學術憲法，R01–R19 |
| `docs/04_module_registry.md` | 模組登記冊 |
| `docs/05_integration_risk_audit.md` | 18 條整合風險 |
| `docs/DESIGN_PHILOSOPHY_AUDIT.md` | 設計哲學稽核 + 分層架構（2026-08） |
| `docs/PHASE1_SCOPE_AND_ACCEPTANCE.md` | 當前階段範疇與驗收契約 |
| `docs/manual_test_log.md` | 真實使用回饋，L2/L3 問題的最佳來源 |
| `reports/coOS_審查報告.md` | 5 位審查者的同儕審查，裁決 Major Revision |

## 已知的痛點（來自實際使用）

- Persona 首次問候太長（121 字）、語氣急迫催促、沒有溫度
- 氣泡分割太長、延遲太短（應該 = f(字數, WPM)）
- 每回合都產生 project 偵測標記，缺去重
- 返回聊天室後氣泡合併、標記消失
- Project board 新標籤擠掉舊的

## 未解的技術缺口

| 編號 | 問題 |
| --- | --- |
| `GAP-C2` | Gemma `generate_json` 語意錯位，本地承諾萃取空轉——擋住 `DEVIATION-09` 的隱私回退方案 |
| `GAP-C3` | M4.4 套問缺 telemetry confidence 檢查 |
| `GAP-C8` | Elicitation turn counter 語意錯（算注入次數非對話輪數） |
| `DEVIATION-09` | 逐字稿直送 Gemini，回退方案已拍板但 0 行程式碼 |
| — | 反 KPI（mood_score 等）無任何計算實作 |
| — | 零使用者數據、零效能實測（審查報告 P0） |
