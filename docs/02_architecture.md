# coOS 系統架構 (Architecture)

**版本**:1.0

## 0. 架構哲學

兩個核心原則,違反任一即重新設計:

1. **邊緣-雲端協同 (PRISM)** — 隱私敏感資料絕不離開使用者裝置
2. **混合式本地優先 (Hybrid Local-First)** — MVP 階段大腦跑在本機,跨裝置同步是進階功能

## 1. 四層分散式架構

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: 端側感知與介面層 (Ambient Tracking & UI)    │
│   - 載體: 筆電 (i5, 16GB RAM)                        │
│   - 技術: Tauri 2.x (Rust) + React + Vite           │
│   - 職責: 收集 + 展示                                 │
└─────────────────────────────────────────────────────┘
              │ Tauri IPC (WebSocket/SSE, 0ms)
              ▼
┌─────────────────────────────────────────────────────┐
│ Layer 2: 邊緣推論與隱私層 (Edge Inference)           │
│   - 載體: iPad Air M1 (8GB RAM) 區網伺服器           │
│   - 技術: Gemma 4 E4B (4-bit MLX 量化), ai.local    │
│   - 職責: 將明文壓縮為意圖向量                       │
│   - 隱私守門員: 此層之後絕無明文                     │
└─────────────────────────────────────────────────────┘
              │ Intent Vectors (JSON, 經 Eguard 過濾)
              ▼
┌─────────────────────────────────────────────────────┐
│ Layer 3: 混合式多智能體層 (Hybrid Agentic Layer)     │
│   - MVP: 本地 FastAPI (Tauri Sidecar localhost:8000)│
│   - 進階: 雲端 PaaS (Render/AWS) 跨裝置同步         │
│   - 技術: Python 3.11 + FastAPI + LangGraph         │
│   - 職責: 業務邏輯 + Persona 對話 + 排程            │
└─────────────────────────────────────────────────────┘
              │ Gemini API (僅在 PRISM 路由放行時)
              ▼
┌─────────────────────────────────────────────────────┐
│ Layer 4: 深層認知與動態圖譜層 (GraphRAG)             │
│   - 載體: Neo4j AuraDB Free + Cloud LLM             │
│   - 職責: 薩提爾冰山圖譜 + NSVIF 幻覺防禦           │
└─────────────────────────────────────────────────────┘
```

## 2. 資料流四階段 (單向淨化原則)

```
[擷取] 最敏感明文 → 鎖在本地 SQLite (raw_tracking_logs)
   ↓
[淨化] iPad M1 邊緣 AI → 壓縮為意圖標籤 → 暫存本地 (edge_event_buffer)
   ↓
[固化] 雲端 Gemini + NSVIF 驗證 → 薩提爾冰山圖譜節點/邊 → Neo4j
   ↓
[業務] XP / 徽章 / 角色配置 → PostgreSQL (跨裝置同步)
```

**鐵律**:資料只能由左向右流。Layer 4 的雲端服務絕對不能反向讀取 Layer 1 的明文。

## 3. 隱私三層分類 (Privacy Tier)

| Tier | 內容 | 儲存 | 上雲規則 | 範例 |
| ---- | ---- | ---- | -------- | ---- |
| **T1 明文** | 原始程式碼、對話逐字稿、瀏覽器內容 | 本地 SQLite (永久) | **絕對禁止** | `raw_tracking_logs.raw_text` |
| **T1 Opt-in 內文** | 視窗標題、應用程式內文、Local LLM 摘要 (須使用者主動開啟) | 本地 SQLite (永久) | **絕對禁止** `[RISK-15]` | `raw_tracking_logs.payload.window_title`, `.content_raw`, `.content_summary` |
| **T2 意圖向量** | Gemma 壓縮後的軟提示詞向量 | 本地 SQLite (短暫) | 僅向量本身,不可還原 | `edge_event_buffer.intent_tag` |
| **T3 業務狀態** | XP、徽章、角色、社群貼文 | PostgreSQL (雲端) | 跨裝置同步 | `users`, `ai_experts`, `social_posts` |

任何違反此分類的 PR 必須拒絕。Claude Code 在實作時必須先檢查資料屬於哪一層。

> **v1.1 新增**:T1 Opt-in 內文為使用者主動同意後才會採集的應用程式內文與 Local LLM 摘要。預設關閉 (`CaptureMode::Off`)。詳見 `M1_1_os_telemetry_daemon_SPEC.md` §7.3。

## 4. 核心模組實作路線決策

### 決策 A: 短期記憶管理

**選擇**:**A1 SQLite/PostgreSQL 共用**
- MVP:本地 SQLite 儲存 LangGraph 對話樹狀態
- 進階:無縫轉移至雲端 PostgreSQL
- **不選**:A2 Redis 記憶體快取 (留至進階階段升級)

### 決策 B: 路由觸發機制

**選擇**:**B1 Rule-based**
- 0 延遲的 Python 邏輯規則 (例:`if implicit_state == "anxiety": route_to("comforter")`)
- **不選**:B2 LLM-as-a-Judge (留至進階)

### 決策 C: 心理幻覺防禦 (NSVIF)

**選擇**:**C2 符號邏輯攔截**
- Gemini 推論出的薩提爾洞察 → Python 腳本對照 SQLite 行為日誌 → 不合邏輯丟棄
- **不選**:C1 純機率信心過濾 (易產生 false negative)

### 決策 D: ZPD 盲盒生成

**選擇**:**D2 預生成池**
- FastAPI 排程批次計算難度適中任務 → 0ms 抽卡
- **不選**:D1 即時生成 (延遲不可接受)

## 5. 技術棧固定清單

### 前端 (Tauri 2.x)

```toml
# Cargo.toml
[dependencies]
tauri = { version = "2.x" }
tokio = "1.x"
sqlx = { version = "0.7", features = ["sqlite"] }
```

```json
// package.json
{
  "dependencies": {
    "react": "^18",
    "react-dom": "^18",
    "zustand": "^4",
    "framer-motion": "^11",
    "tailwindcss": "^3"
  }
}
```

### 後端 (FastAPI)

```python
# requirements.txt
fastapi==0.110.*
uvicorn[standard]==0.27.*
langgraph==0.0.40
pydantic==2.6.*
sqlalchemy==2.0.*
alembic==1.13.*
httpx==0.27.*  # 呼叫 Gemini / ai.local
arq==0.25.*    # 排程
```

### 邊緣 (iPad M1)

- `ai.local` (Ollama-style 區網 API) [Documentation](https://ai-local.brunowernimont.me/docs/)
- Model: `mlx-community/gemma-4-e4b-it-4bit`
- 模型載入後 RAM 佔用約 2.8GB
- Inference latency target: < 6s for 2K token input

### 雲端服務

| 服務 | 用途 | 方案 | 額度 |
| ---- | ---- | ---- | ---- |
| Gemini 3.5 Flash / Gemini 3 Flash / Gemini 2.5 Flash / Lite | 雲端 LLM (高複雜度，用量緊繃) | Google AI Studio Free Tier | RPD 10 (免費) |
| Gemini 3.1 Flash Lite | 雲端 LLM (中複雜度) | Google AI Studio Free Tier | RPD 500 (免費) |
| Gemma 4 (31B/26B) | 雲端 LLM (輕量級，無感延遲) | Google AI Studio Free Tier | RPD 1500 (免費) |
| Gemini 3.5 Pro API | 核心深層認知 | Google Dev Program | $10/月 (尚未開通) |
| Supabase | PostgreSQL | Free tier | 500MB |
| Neo4j AuraDB | 圖譜 DB | Free tier | 20 萬節點 |
| Pollinations.ai | 生圖 (MVP) | 無 | 免費 |
| Leonardo.ai | 生圖 (Beta) | Free tier | 150 點/日 |

 **Gemini Free Tier Limits:**
   | Model | RPM | TPM | RPD |
   |-------|-----|-----|-----|
   | `gemini-2.0-flash` | 0 | 0 | 0 |
   | `gemini-2.0-flash-lite` | 0 | 0 | 0 |
   | `gemini-3.5-flash` | 5 | 250,000 | 20 |
   | `gemini-3.0-flash` | 5 | 250,000 | 20 |
   | `gemini-3.1-flash-lite` | 15 | 250,000 | 500 |
   | `gemini-2.5-flash-lite` | 10 | 250,000 | 20 |
   | `gemini-2.5-flash` | 5 | 250,000 | 20 |
   | `gemini-2.5-pro` | 0 | 0 | 0 |
   | `Gemma 4 26B` | 15 | unlimited | 1500 |
   | `Gemma 4 26B` | 31 | unlimited | 1500 |

### 5.1 任務難度分層與 LLM 路由策略 (LLM Tiering & Fallback)

為防範 Google AI Studio Free Tier 的每日用量上限 (Quota Limits) 以及本地端運作延遲 (iPad 12秒延遲)，系統將推理任務依複雜度與日配額限制分為四個層級，動態選用最適模型：

| 層級 (Tier) | 適用任務 | 優先推薦模型 (首選) | 備用/降級模型 (Fallback) | 用量配額 (RPD) |
| --- | --- | --- | --- | --- |
| **Tier 1 (最輕量級)** | 基礎關鍵字抽取、PII 過濾、本地遙測資料壓縮、高頻率重複請求 | 雲端 `Gemma 4 31B/26B` (API Studio, 無延遲) | 本地正則與句法特徵提取 (Rule-based) | RPD 1500 |
| **Tier 2 (中低複雜度)** | 背景路由驗證 (`llm_verify_and_learn`)、初步意圖分類、通知卡片生成 | 雲端 `Gemini 3.1 Flash Lite` | 雲端 `Gemma 4 31B/26B` | RPD 500 |
| **Tier 3 (中度複雜度)** | Persona Agent 擬真人設對話、主要路由補判 (`llm_route`) | 雲端 `Gemini 3.5 Flash` / `Gemini 3 Flash` / `Gemini 2.5 Flash` / `Gemini 2.5 Flash Lite` | 雲端 `Gemini 3.1 Flash Lite` | RPD 10 |
| **Tier 4 (深度複雜/關鍵)** | 每日深度反思總結 (M4.4)、薩提爾冰山圖譜 GraphRAG 寫入與驗證 (M5.2) | 雲端 `Gemini 3.5 Pro` | 雲端 `Gemini 3.5 Flash` | 視付費帳戶額度而定 |

**故障轉移 (Fallback) 邏輯**：
當任何 API 請求遭遇 `429 Too Many Requests` (Rate Limit) 或 `503 Service Unavailable` 時，系統客戶端應捕捉該異常，並自動向下一層級 (或較輕量且配額較多的備用模型) 進行 Fallback 重新請求，以保障系統高可用性。



## 6. 開發環境

### 本機開發

```bash
# 啟動三層
pnpm dev          # 前端 + Tauri (Layer 1)
# iPad M1 開機後自動跑 ai.local (Layer 2)
uvicorn main:app  # FastAPI sidecar (Layer 3)
# Neo4j AuraDB 雲端,無需本地啟動 (Layer 4)
```

### 環境變數

```bash
# .env (絕不 commit)
GEMINI_API_KEY=...
NEO4J_URI=...
NEO4J_USER=...
NEO4J_PASSWORD=...
SUPABASE_DB_URL=...
SUPABASE_SECRET_KEY=...
IPAD_AI_LOCAL_HOST=192.168.0.42:11434
```

### 資料庫遷移

```bash
# 本地 SQLite
alembic -c alembic_local.ini upgrade head

# 雲端 PostgreSQL
alembic -c alembic_cloud.ini upgrade head
```

## 7. 部署架構 (MVP 階段)

```
┌──────────────┐
│ 使用者筆電   │
│ ┌──────────┐ │
│ │ Tauri    │ │ ← 唯一可執行檔
│ │  ├ Front │ │
│ │  ├ FastAPI sidecar (跑在 localhost:8000)
│ │  └ SQLite │ │
│ └──────────┘ │
└──────┬───────┘
       │ LAN
       ▼
┌──────────────┐
│ iPad M1      │
│ ai.local     │ ← Gemma 4 E4B 邊緣推論
└──────────────┘

雲端 (按需呼叫):
- Gemini API (語意草圖生成)
- Supabase PostgreSQL (XP/徽章)
- Neo4j AuraDB (薩提爾圖譜)
```

## 8. 風險預留

以下風險已在架構層面預留緩解空間,實作模組時不要再重新發明輪子:

| 風險 | 架構層緩解 |
| ---- | ---------- |
| AI 幻覺 | NSVIF (M5.2) + ARPM (M4.9) 雙層 |
| 紀錄疲勞 | 草稿與核准 (M3.3.3) + 斷點偵測 (M1.2) |
| Prompt Injection | DRIFT 框架 (M2.3.2) 強制隔離 |
| 非同步狀態不一致 | DLQ + Optimistic UI |
| 前端渲染瓶頸 | 列表虛擬化 + GPU 加速動畫 |
| Gamification 倦怠 | 後期動機從 XP 轉移到知識圖譜 |
| 系統崩潰任務放棄 | α-DPO + ABC 信用分配 (M4.13) |

## 9. 未來進階藍圖

當 MVP 跑通且數據量變大時,以下升級路徑已預留:

1. **本地 SQLite → 本地 PostgreSQL** (16GB RAM 下需調 `shared_buffers`)
2. **本地 FastAPI → 雲端 Render 雙軌大腦** (跨裝置同步)
3. **Neo4j AuraDB → 自建 Neo4j Community on VPS** (突破 20 萬節點上限)
4. **Rule-based 路由 → LLM-as-a-Judge** (動態同理心)
5. **本地 SQLite Session → Redis 記憶體快取** (極低延遲對話)
6. **Pollinations.ai → Leonardo.ai 統一風格**

升級時必須保持 `Mx.y` 模組編號與 API 介面不變,僅替換實作。
