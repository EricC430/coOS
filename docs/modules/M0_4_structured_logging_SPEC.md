# M0.4 — 結構化日誌 (Structured Logging)

**標籤**:`[MVP]`
**版本**:`1.0` / `draft`
**最後更新**:2026-05-30

## 1. Purpose (目的)

提供統一的結構化事件日誌框架,使所有跨模組互動 (IPC 呼叫、邊緣推論、資料庫寫入、Agent 決策) 都寫入可查詢的 `raw_tracking_logs` 表,確保除錯時「先 grep log 再猜」。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| (無) | 架構文件 §2 資料流四階段 | 日誌作為第一階段「擷取」的落地點 |
| (無) | CLAUDE.md §觀測性 | 「所有跨模組互動必須寫入 raw_tracking_logs」 |

> 本模組屬基礎設施,無直接學術研究引用。日誌設計決策來自 `02_architecture.md` 與 `CLAUDE.md`。

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| 任意模組的事件呼叫 | `LogEvent` (見 §7.2) | `LogEvent(module="M4.2", action="echo_mode_transition", ...)` |
| M0.3 Settings | `config.LOG_LEVEL` | `"INFO"` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| 本地 SQLite `raw_tracking_logs` | 見 §7.2 `LogEvent` | 一行 JSON 結構化記錄 |
| stdout / stderr (開發模式) | 人類可讀格式化文字 | `[2026-05-30 14:00:00] INFO M4.2 echo_mode_transition {...}` |
| 後續可選：檔案日誌 | `.log` 檔案 (rotate) | `data/logs/coos_2026-05-30.log` |

## 4. Dependencies

### 上游 (我依賴誰)

- **M0.1** (Monorepo):依賴 `services/m0_4_logging/` 目錄結構
- **M0.3** (.env + Alembic):依賴 `config.LOG_LEVEL` 環境變數與 SQLite 資料庫連線

### 下游 (誰依賴我)

- **所有模組**：任何跨模組事件必須呼叫 M0.4 寫入日誌
- **M4.6** (Observer Agent)：從 `raw_tracking_logs` 讀取事件以推論使用者意圖
- **M4.8** (隱性狀態推論)：從日誌中萃取行為特徵向量
- **M5.2** (NSVIF)：反溯因驗證時需對照 `raw_tracking_logs` 的原始事件

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| (無直接 RISK-xx) | 日誌寫入阻塞主執行緒 → 對話延遲 | 使用非同步寫入 (async queue),主執行緒 fire-and-forget |
| (無直接 RISK-xx) | 日誌中意外記錄 L1 明文後被上游模組讀取上雲 | `LogEvent` 的 `payload` 欄位嚴格遵循隱私三層分類; 日誌表永遠留在本地 SQLite |
| (無直接 RISK-xx) | 日誌量膨脹導致 SQLite 檔案過大 | 預設保留 30 天; 超過自動歸檔壓縮; 搭配 `VACUUM` |

> 已 grep `05_integration_risk_audit.md`，無 RISK-xx 與 M0.4 直接相關。

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m0_4/test_structured_logging.py

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class TestLogEventSchema:
    def test_log_event_has_required_fields(self):
        """驗收條件 1: LogEvent 必須包含 module, action, timestamp, level"""
        from services.m0_4_logging.schema import LogEvent

        event = LogEvent(
            module="M4.2",
            action="echo_mode_transition",
            level="INFO",
            payload={"from_agency": 0.85, "to_agency": 0.70},
        )
        assert event.module == "M4.2"
        assert event.action == "echo_mode_transition"
        assert event.level == "INFO"
        assert event.timestamp is not None

    def test_log_event_rejects_invalid_module_id(self):
        """驗收條件 2: 模組 ID 必須符合 Mx.y 格式"""
        from services.m0_4_logging.schema import LogEvent
        import pytest

        with pytest.raises(ValueError):
            LogEvent(module="random_name", action="test", level="INFO")


class TestLogWriter:
    def test_log_writes_to_sqlite(self, tmp_path):
        """驗收條件 3: 日誌事件成功寫入 SQLite raw_tracking_logs"""
        from services.m0_4_logging.writer import LogWriter

        db_path = tmp_path / "test.db"
        writer = LogWriter(db_path=str(db_path))
        writer.init_table()
        writer.write(
            module="M0.4",
            action="test_write",
            level="INFO",
            payload={"key": "value"},
        )
        rows = writer.query_all()
        assert len(rows) == 1
        assert rows[0]["module"] == "M0.4"

    def test_log_async_does_not_block(self):
        """驗收條件 4: 非同步寫入不阻塞呼叫方 (< 5ms 回傳)"""
        import time
        from services.m0_4_logging.writer import AsyncLogWriter

        writer = AsyncLogWriter()
        start = time.monotonic()
        asyncio.get_event_loop().run_until_complete(
            writer.emit(module="M0.4", action="perf_test", level="DEBUG")
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 50  # fire-and-forget 應極快


class TestLogPrivacy:
    def test_raw_tracking_logs_table_is_local_only(self):
        """驗收條件 5: raw_tracking_logs 僅存在於本地 SQLite, 不在雲端 schema"""
        local_migrations = PROJECT_ROOT / "services" / "alembic" / "versions"
        cloud_migrations = PROJECT_ROOT / "services" / "alembic" / "versions"
        # raw_tracking_logs 應出現在 local migration
        # 不應出現在 cloud migration 的 CREATE TABLE
        # (此測試需搭配 M6.1 / M6.2 的 migration 實作)

    def test_payload_does_not_contain_raw_text_marker(self):
        """驗收條件 6: payload 中不可包含標記為 L1 明文的欄位"""
        from services.m0_4_logging.schema import LogEvent

        event = LogEvent(
            module="M1.1",
            action="keystroke_captured",
            level="DEBUG",
            payload={"event_type": "keypress", "count": 42},
        )
        # payload 不應有 raw_text, raw_code, transcript 等明文欄位
        forbidden_keys = {"raw_text", "raw_code", "transcript", "browsing_content"}
        assert not forbidden_keys.intersection(event.payload.keys())
```

## 7. Implementation Notes

### 7.1 日誌等級定義

| Level | 用途 | 範例 |
| ----- | ---- | ---- |
| `DEBUG` | 開發除錯用 (不進生產 DB) | `echo_mode step 3/5 agency=0.55` |
| `INFO` | 正常跨模組事件 (預設) | `M4.2 echo_mode_transition completed` |
| `WARNING` | 非致命但異常 | `M2.2 iPad ai.local 不可達, 退化至本地` |
| `ERROR` | 致命錯誤 | `M0.3 GEMINI_API_KEY 為空, 啟動中止` |
| `AUDIT` | 安全與隱私事件 (永不刪除) | `M2.3 PII 遮蔽觸發: email detected` |

### 7.2 LogEvent Schema

```python
# services/m0_4_logging/schema.py

from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import Any
import re
import uuid


class LogEvent(BaseModel):
    """coOS 統一結構化日誌事件"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    module: str = Field(..., description="模組 ID, 格式 Mx.y")
    action: str = Field(..., description="事件動作名稱")
    level: str = Field(default="INFO")
    payload: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = Field(default=None)
    role_id: str | None = Field(default=None)
    correlation_id: str | None = Field(
        default=None,
        description="跨模組追蹤 ID, 同一業務流程共用"
    )

    @field_validator("module")
    @classmethod
    def validate_module_format(cls, v: str) -> str:
        if not re.match(r"^M\d+\.\d+", v):
            raise ValueError(f"模組 ID 必須符合 Mx.y 格式, 收到: {v}")
        return v

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "AUDIT"}
        if v.upper() not in allowed:
            raise ValueError(f"日誌等級必須是 {allowed} 之一")
        return v.upper()
```

### 7.3 SQLite 表結構

```sql
-- raw_tracking_logs (本地 SQLite 專屬, 絕不上雲)
CREATE TABLE IF NOT EXISTS raw_tracking_logs (
    id             TEXT PRIMARY KEY,
    timestamp      TEXT NOT NULL,       -- ISO 8601 UTC
    module         TEXT NOT NULL,       -- 'M4.2', 'M0.3', ...
    action         TEXT NOT NULL,       -- 'echo_mode_transition', ...
    level          TEXT NOT NULL DEFAULT 'INFO',
    payload        TEXT NOT NULL,       -- JSON string
    user_id        TEXT,
    role_id        TEXT,
    correlation_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_rtl_module ON raw_tracking_logs(module);
CREATE INDEX IF NOT EXISTS idx_rtl_timestamp ON raw_tracking_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_rtl_correlation ON raw_tracking_logs(correlation_id);
```

### 7.4 非同步寫入器

```python
# services/m0_4_logging/writer.py

import asyncio
import json
from collections import deque
from services.m0_4_logging.schema import LogEvent


class AsyncLogWriter:
    """
    非同步 fire-and-forget 日誌寫入器。
    主執行緒呼叫 emit() 後立即返回,
    背景 worker 批次寫入 SQLite。
    """

    def __init__(self, db_session, batch_size: int = 50, flush_interval_s: float = 2.0):
        self._queue: asyncio.Queue[LogEvent] = asyncio.Queue(maxsize=10000)
        self._db = db_session
        self._batch_size = batch_size
        self._flush_interval = flush_interval_s

    async def emit(self, **kwargs) -> None:
        """Fire-and-forget: 放入佇列後立即返回"""
        event = LogEvent(**kwargs)
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            # 佇列滿 → 丟棄最舊的 DEBUG 事件, 保留 ERROR/AUDIT
            pass  # TODO: 實作 priority drop

    async def _flush_worker(self):
        """背景 worker: 批次寫入"""
        while True:
            batch: list[LogEvent] = []
            try:
                while len(batch) < self._batch_size:
                    event = await asyncio.wait_for(
                        self._queue.get(), timeout=self._flush_interval
                    )
                    batch.append(event)
            except asyncio.TimeoutError:
                pass
            if batch:
                await self._write_batch(batch)

    async def _write_batch(self, batch: list[LogEvent]):
        """將一批事件寫入 SQLite"""
        values = [
            (e.id, e.timestamp.isoformat(), e.module, e.action,
             e.level, json.dumps(e.payload, ensure_ascii=False),
             e.user_id, e.role_id, e.correlation_id)
            for e in batch
        ]
        await self._db.executemany(
            """INSERT INTO raw_tracking_logs
               (id, timestamp, module, action, level, payload, user_id, role_id, correlation_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            values,
        )
        await self._db.commit()
```

### 7.5 使用範例 (其他模組如何呼叫)

```python
# 在任何模組中
from services.m0_4_logging.writer import get_logger

logger = get_logger()

# 跨模組事件
await logger.emit(
    module="M4.2",
    action="echo_mode_transition",
    level="INFO",
    payload={"from_state": "Authoritative", "to_state": "Empathetic", "step": 3},
    user_id="user_abc",
    role_id="csie_001",
    correlation_id="conv_xyz",
)
```

### 7.6 異常處理

- SQLite 寫入失敗 (檔案鎖定) → 重試 3 次, 間隔 200ms; 超過則 fallback 至 stderr
- 佇列溢出 → 丟棄 `DEBUG` 等級事件, `ERROR` 和 `AUDIT` 永不丟棄
- `payload` 超過 64KB → 截斷並加 `_truncated: true` 標記
- 日誌檔案 > 500MB → 自動歸檔為 `.gz`, 僅保留最近 30 天

## 8. Anti-patterns (反模式)

- ❌ **不要在 `payload` 中放入 L1 明文** (原始程式碼、對話逐字稿、瀏覽器內容)。日誌可記錄事件的「摘要」或「統計量」,但絕不可記錄明文內容本身。
  理由:CLAUDE.md 隱私三層原則; `raw_tracking_logs` 留在本地但仍可能被 Observer Agent 讀取並生成洞察上雲。

- ❌ **不要用同步阻塞式寫入**。所有日誌寫入必須走非同步佇列,否則會拖慢 Persona 對話的回應時間。
  理由:R05 治療同盟要求對話延遲 < 2s; 同步寫入在 SQLite WAL 鎖等待時可能卡 50-200ms。

- ❌ **不要用 `print()` 或 `logging.info()` 替代 `LogEvent`**。所有跨模組事件必須走 M0.4 的結構化 schema,否則 `grep` 和 Observer Agent 無法解析。
  理由:CLAUDE.md 觀測性原則。

- ❌ **不要跳過 `module` 欄位的格式驗證**。每個日誌事件都必須帶合法的 `Mx.y` 模組 ID,否則事後分析時無法歸因。
  理由:模組可追蹤性是整個系統的基石。

## 9. Open Questions

實作前必須與使用者拍板的問題:

- [x] **日誌保留策略**: (決策：MVP 階段採用 30 天自動清理，`AUDIT` 等級與 `daily_reflections` 等核心反思數據設為永久保留。後續進階階段（Phase 6）實作 Wrapped 報告時，再重構為雙層保留策略（Raw Logs 保留 14~30 天，Summary Metrics 表永久保留），以兼顧資料庫大小與長期行為分析的需求。)
- [x] **開發模式下是否同時輸出至 stdout?** (決策：採用雙寫策略。在開發模式下 (`debug = True`)，日誌除背景非同步寫入 SQLite 外，同時透過 Python Logger 格式化且著色輸出至 stdout。這能顯著提升開發時的即時狀態觀測性與 Debug 效率。)
- [x] **correlation_id 的生成策略**: (決策：採用全鏈路追蹤（Distributed Tracing）策略。由 Tauri IPC 層在前端發起請求時生成 correlation_id (UUID)，並透過 Headers 傳入後端；FastAPI Middleware 自動捕獲並放入 Request context，使同一業務流程的所有日誌（包含 LLM 呼叫、SQL 寫入）能共享相同的追蹤 ID。背景自發性任務（如 Cron）則在啟動時自行生成並綁定。)


---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責,不能拆解
- [x] §2 無學術研究引用,已明確標註屬基礎設施
- [x] §3 Schema 用 Pydantic / SQL / 範例描述
- [x] §4 依賴是真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`,無直接對應 RISK
- [x] §6 測試先於程式碼
- [x] §8 列出 4 條反模式
- [x] §9 列出 3 個開放問題
