# M0.2 — Tauri IPC 通訊橋 (Tauri IPC Communication Bridge)

**標籤**:`[MVP]`
**版本**:`1.0`
**最後更新**:2026-05-30

## 1. Purpose (目的)

建立 Tauri 2.x 前端 (React/WebView) 與後端 (Rust core + FastAPI sidecar) 之間的雙向通訊橋,使前端能透過統一介面呼叫 Rust 命令與 FastAPI HTTP API,並接收 Server-Sent Events (SSE) 串流回應。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| (無) | 架構文件 §1 四層分散式架構 | Layer 1 端側感知層的技術選型: Tauri 2.x |
| (無) | 架構文件 §7 部署架構 | Tauri 唯一可執行檔 + FastAPI sidecar localhost:8000 |

> 本模組屬基礎設施,無直接學術研究引用。所有決策來自 `02_architecture.md`。

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| React 前端 (M3.x 系列) | Tauri `invoke` 呼叫 | `invoke('get_system_health')` → Rust |
| React 前端 (M3.x 系列) | `fetch` / SSE | `fetch('http://localhost:8000/api/m4_4/draft')` → FastAPI |
| FastAPI sidecar | SSE 串流 | `data: {"type":"persona_chunk","content":"嗯..."}` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| React 前端 | Tauri `invoke` 回傳 | `{ status: "ok", uptime: 3600 }` |
| React 前端 | SSE 事件流 | `EventSource('/api/m3_4/chat/stream')` |
| Rust → FastAPI | HTTP Proxy | Tauri Rust 層代理 `/api/*` 至 `localhost:8000` |

### 通訊協定概覽

```
React (WebView)
  │
  ├── invoke('cmd_name', payload)  ──→  Rust (Tauri Core)
  │                                       │
  │                                       ├── 直接回應 (低延遲, <1ms)
  │                                       └── Proxy → FastAPI sidecar (:8000)
  │
  ├── fetch('/api/...')  ──→  FastAPI sidecar (:8000)
  │                            └── JSON 回應
  │
  └── EventSource('/api/.../stream')  ──→  FastAPI SSE
                                            └── 串流文字片段
```

## 4. Dependencies

### 上游 (我依賴誰)

- **M0.1** (Monorepo):依賴 `apps/desktop/src-tauri/` 與 `services/` 目錄結構的存在

### 下游 (誰依賴我)

- **M3.x 所有 UI 模組**:透過 IPC 呼叫後端 API
- **M4.x Agent 模組**:透過 SSE 推送對話串流至前端
- **M1.1** (OS 級遙測):透過 Tauri Rust 層存取系統 API (剪貼簿、視窗焦點)
- **M0.4** (結構化日誌):前端錯誤透過 IPC 傳至後端統一日誌

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| (無直接 RISK-xx) | FastAPI sidecar 未啟動時前端所有 API 呼叫失敗 | Rust 層負責 spawn sidecar 進程; 前端實作健康檢查 `/api/health` 輪詢 + 錯誤提示 UI |
| (無直接 RISK-xx) | SSE 連線在筆電休眠/恢復後斷裂 | 前端 SSE client 實作自動重連 (exponential backoff, max 5 retries) |
| (無直接 RISK-xx) | Tauri WebView CSP 阻擋 localhost 呼叫 | `tauri.conf.json` 的 `security.csp` 須明確允許 `http://localhost:8000` |

> 已 grep `05_integration_risk_audit.md`,無 RISK-xx 與 M0.2 直接相關。

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m0_2/test_tauri_ipc.py

import httpx
import pytest

SIDECAR_URL = "http://localhost:8000"

class TestSidecarHealth:
    @pytest.mark.asyncio
    async def test_fastapi_sidecar_reachable():
        """驗收條件 1: FastAPI sidecar 可透過 localhost:8000 存取"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{SIDECAR_URL}/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_health_returns_version():
        """驗收條件 2: 健康檢查回傳應用程式版本"""
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{SIDECAR_URL}/api/health")
        data = resp.json()
        assert "version" in data
        assert "uptime_seconds" in data

class TestSSEStream:
    @pytest.mark.asyncio
    async def test_sse_endpoint_streams_events():
        """驗收條件 3: SSE 端點能持續推送事件"""
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", f"{SIDECAR_URL}/api/m0_2/test_stream") as resp:
                assert resp.status_code == 200
                assert "text/event-stream" in resp.headers["content-type"]
                events = []
                async for line in resp.aiter_lines():
                    if line.startswith("data:"):
                        events.append(line)
                    if len(events) >= 3:
                        break
                assert len(events) >= 3

class TestCORS:
    @pytest.mark.asyncio
    async def test_cors_allows_tauri_origin():
        """驗收條件 4: CORS 允許 Tauri WebView 的 origin"""
        async with httpx.AsyncClient() as client:
            resp = await client.options(
                f"{SIDECAR_URL}/api/health",
                headers={"Origin": "tauri://localhost"}
            )
        assert resp.status_code in (200, 204)
        assert "tauri://localhost" in resp.headers.get("access-control-allow-origin", "")
```

```typescript
// tests/m0_2/test_tauri_invoke.spec.ts (Vitest)

import { describe, it, expect } from 'vitest';

describe('M0.2 Tauri IPC', () => {
  it('驗收條件 5: Rust invoke 命令可被前端呼叫', async () => {
    // 此測試需在 Tauri 環境中執行
    const { invoke } = await import('@tauri-apps/api/core');
    const result = await invoke('get_system_health');
    expect(result).toHaveProperty('status', 'ok');
  });

  it('驗收條件 6: 不存在的命令應回傳明確錯誤', async () => {
    const { invoke } = await import('@tauri-apps/api/core');
    await expect(invoke('nonexistent_command')).rejects.toThrow();
  });
});
```

## 7. Implementation Notes

### 7.1 Tauri Rust 層命令設計

```rust
// apps/desktop/src-tauri/src/commands/mod.rs

use tauri::command;

/// [架構文件 §7] 系統健康檢查,前端定期輪詢
#[command]
async fn get_system_health() -> Result<serde_json::Value, String> {
    let uptime = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|e| e.to_string())?;
    Ok(serde_json::json!({
        "status": "ok",
        "uptime_seconds": uptime.as_secs(),
        "sidecar_reachable": check_sidecar_health().await
    }))
}

/// 檢查 FastAPI sidecar 是否存活
async fn check_sidecar_health() -> bool {
    reqwest::get("http://localhost:8000/api/health")
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}
```

### 7.2 FastAPI Sidecar 生命週期管理

Tauri Rust 層在應用啟動時 spawn FastAPI 進程:

```rust
// apps/desktop/src-tauri/src/sidecar.rs

use std::process::{Command, Child};

pub fn spawn_sidecar() -> Result<Child, std::io::Error> {
    Command::new("uv")
        .args(["run", "--directory", "../../services", "uvicorn", "main:app",
               "--host", "127.0.0.1", "--port", "8000"])
        .spawn()
}
```

### 7.3 前端 IPC 抽象層

```typescript
// apps/desktop/src/lib/ipc.ts

import { invoke } from '@tauri-apps/api/core';

const SIDECAR_BASE = 'http://localhost:8000';

/** Tauri Rust 命令呼叫 (低延遲 <1ms) */
export async function rustInvoke<T>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  return invoke<T>(cmd, args);
}

/** FastAPI HTTP 呼叫 */
export async function apiCall<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${SIDECAR_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  });
  if (!resp.ok) throw new Error(`API Error: ${resp.status}`);
  return resp.json();
}

/** SSE 串流連線 (自動重連) */
export function createSSE(path: string, onMessage: (data: string) => void): EventSource {
  const es = new EventSource(`${SIDECAR_BASE}${path}`);
  es.onmessage = (e) => onMessage(e.data);
  es.onerror = () => {
    // 指數退避重連,由 EventSource 原生處理
    console.warn('[M0.2] SSE 連線中斷,等待重連...');
  };
  return es;
}
```

### 7.4 FastAPI CORS 與健康檢查

```python
# services/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time

app = FastAPI(title="coOS Sidecar", version="0.1.0")

# [架構文件 §7] 僅允許 Tauri 與本地開發 origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["tauri://localhost", "http://localhost:1420"],  # Vite dev
    allow_methods=["*"],
    allow_headers=["*"],
)

_start_time = time.time()

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "0.1.0",
        "uptime_seconds": int(time.time() - _start_time),
    }
```

### 7.5 異常處理

- FastAPI sidecar crash → Rust 層偵測子進程退出碼 ≠ 0 → 自動重啟 (max 3 次) → 超過則前端顯示「後端離線」橫幅
- Tauri `invoke` 失敗 → 前端 catch 並寫入 M0.4 結構化日誌 (`raw_tracking_logs`)
- SSE 斷線 → `EventSource` 原生 auto-reconnect + 前端 UI 顯示 "重連中..." 指示器

## 8. Anti-patterns (反模式)

- ❌ **不要讓 React 直接呼叫 Gemini/Supabase/Neo4j 等外部 API**。所有外部呼叫必須經 FastAPI sidecar 代理。
  理由:前端 (Layer 1) 直接呼叫雲端違反四層架構原則,且 API key 會暴露在 WebView。

- ❌ **不要在 Tauri `invoke` 命令中做重量級計算** (如 DB query、AI 推論)。Rust 層只做轉發與系統 API 呼叫。
  理由:Rust 層阻塞會導致 Tauri 主執行緒凍結,前端 UI 卡頓。

- ❌ **不要用 WebSocket 替代 SSE 做單向資料推送**。
  理由:SSE 更簡單、自動重連、且 FastAPI 原生支援 `StreamingResponse`。除非未來需要雙向通訊 (目前不需要) 才考慮 WS。

- ❌ **不要讓 FastAPI sidecar 監聽 `0.0.0.0`**。必須綁定 `127.0.0.1`。
  理由:sidecar 只服務本機前端,綁定所有介面會暴露 API 給區網內其他裝置。

## 9. Open Questions

實作前必須與使用者拍板的問題:

- [x] **Tauri sidecar 是否使用 Tauri 內建的 sidecar 機制 (`tauri.conf.json` externalBin)?** (決策：MVP 階段使用 Rust `Command::new` 手動 spawn 本地虛擬環境的 `uv` 執行 `uvicorn`，以獲得極佳的開發熱重載體驗與輕量體積。Rust 層將負責綁定 OS 級 Job Object/Process Group 以確保 lifecycle 的生命週期管理與埠口釋放。)
- [x] **前端 SSE 重連失敗超過 max retries 後,是否彈出 modal 強制使用者手動重啟?** (決策：採用混合策略。在重連期間（前 5 次，約 15 秒）在 UI 邊角顯示狀態指示器背景重試，不干擾用戶流；若超過限制仍失敗則彈出 Modal 提示連線中斷並提供「重新連線」按鈕以維護狀態明確性。)
- [x] **是否需要在 Rust 層做 API 請求的認證 (JWT/session)?** (決策：採用本地 Secret Token 認證。Tauri 啟動 sidecar 時產生 UUID 作為環境變數傳入，前端發送請求時在 Header 中帶上 `X-API-Token`。這能建立深度防禦，防範本機其他程式惡意存取 sidecar，同時為將來跨裝置架構預留空間。)


---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責,不能拆解
- [x] §2 無學術研究引用,已明確標註屬基礎設施
- [x] §3 Schema 用 TypeScript / Python / 通訊協定圖描述
- [x] §4 依賴是真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`,無直接對應 RISK
- [x] §6 測試先於程式碼
- [x] §8 列出 4 條反模式
- [x] §9 列出 3 個開放問題
