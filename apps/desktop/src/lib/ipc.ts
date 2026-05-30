/**
 * M0.2 — Tauri IPC 抽象層
 *
 * 實作 SPEC: docs/modules/M0_2_tauri_ipc_SPEC.md §7.3
 * 三種通訊通道:
 *   1. rustInvoke  — Tauri Rust 命令 (<1ms, 系統 API 用)
 *   2. apiCall     — FastAPI HTTP JSON 呼叫
 *   3. createSSE   — FastAPI SSE 串流 (自動重連)
 */

const SIDECAR_BASE = "http://127.0.0.1:8000";
const MAX_SSE_RETRIES = 5;

// ---------------------------------------------------------------------------
// 1. Rust invoke — Tauri Core 低延遲命令
// ---------------------------------------------------------------------------

/** Tauri Rust 命令呼叫。只在 Tauri 環境中有效，瀏覽器開發環境會 throw。 */
export async function rustInvoke<T>(
  cmd: string,
  args?: Record<string, unknown>
): Promise<T> {
  const { invoke } = await import("@tauri-apps/api/core");
  return invoke<T>(cmd, args);
}

// ---------------------------------------------------------------------------
// 2. FastAPI HTTP 呼叫
// ---------------------------------------------------------------------------

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** FastAPI HTTP 呼叫。回傳 JSON，失敗時 throw ApiError。 */
export async function apiCall<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const resp = await fetch(`${SIDECAR_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  if (!resp.ok) {
    throw new ApiError(resp.status, `API Error ${resp.status}: ${path}`);
  }
  return resp.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// 3. SSE 串流 — 自動重連
// ---------------------------------------------------------------------------

export interface SSEConnection {
  close: () => void;
}

/**
 * 建立 SSE 連線，自動指數退避重連 (最多 MAX_SSE_RETRIES 次)。
 * 超過重試上限後呼叫 onMaxRetries。
 */
export function createSSE(
  path: string,
  onMessage: (data: string) => void,
  onMaxRetries?: () => void
): SSEConnection {
  let retries = 0;
  let es: EventSource | null = null;
  let closed = false;

  function connect() {
    if (closed) return;
    es = new EventSource(`${SIDECAR_BASE}${path}`);

    es.onmessage = (e) => {
      retries = 0; // 成功收到訊息，重置重試計數
      onMessage(e.data);
    };

    es.onerror = () => {
      es?.close();
      if (closed) return;

      retries++;
      if (retries >= MAX_SSE_RETRIES) {
        onMaxRetries?.();
        return;
      }

      // 指數退避：500ms、1s、2s、4s...
      const delay = Math.min(500 * Math.pow(2, retries - 1), 16000);
      console.warn(`[M0.2] SSE 連線中斷，${delay}ms 後重試 (${retries}/${MAX_SSE_RETRIES})`);
      setTimeout(connect, delay);
    };
  }

  connect();

  return {
    close: () => {
      closed = true;
      es?.close();
    },
  };
}
