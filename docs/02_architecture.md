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
| **T2 意圖向量** | Gemma 壓縮後的軟提示詞向量 | 本地 SQLite (短暫) | 僅向量本身,不可還原 | `edge_event_buffer.intent_tag` |
| **T3 業務狀態** | XP、徽章、角色、社群貼文 | PostgreSQL (雲端) | 跨裝置同步 | `users`, `ai_experts`, `social_posts` |

任何違反此分類的 PR 必須拒絕。Claude Code 在實作時必須先檢查資料屬於哪一層。

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
| Gemini 3.5 Flash / Gemini 3.1 Flash Lite | 雲端 LLM | Google AI Pro | 限時免費 |
| Gemini 3.5 Pro API | 雲端 LLM | Google Dev Program | $10/月 (尚未開通) |
| Supabase | PostgreSQL | Free tier | 500MB |
| Neo4j AuraDB | 圖譜 DB | Free tier | 20 萬節點 |
| Pollinations.ai | 生圖 (MVP) | 無 | 免費 |
| Leonardo.ai | 生圖 (Beta) | Free tier | 150 點/日 |

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
