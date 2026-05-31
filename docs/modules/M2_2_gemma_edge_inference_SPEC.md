# M2.2 — Gemma 邊緣推論管線 (ai.local)

**標籤**: `[MVP]`
**版本**: `1.1`
**最後更新**: 2026-06-01

## 1. Purpose (目的)

作為隱私過濾海關，在本地端載入 4-bit 量化的輕量語言模型（Gemma 4 E4B），將原始程式碼明文與高頻感知數據（M2.1 批次事件）進行語意理解與降維壓縮，輸出「去識別化意圖向量（Intent Vectors）」。
確保所有敏感的原始文字與程式碼邏輯只保留在本地端，絕不上雲，從根本上消除隱私洩漏風險。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R07 | §1.1 SLM 架構演進 | 本地加載 Gemma 4 E4B 量化模型（iPad M1, <3GB RAM 預算） |
| R07 | §4.3 POST 框架 | 意圖向量（Intent Vectors）與 PII 剝離設計 |
| R07 | §4.4 意圖向量演進 | 語意壓縮演算法以保留足夠圖譜分析精度 |
| R06 | §7.4 差分隱私保護 | 意圖向量去識別化特徵 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M2.1 打包的事件批次 | `EventBatch` | `{"batch_id": "...", "events": [...]}` (高頻遙測資料) |
| M1.3.1 原始代碼 Diff | string | 暫存的程式碼變更文字 (大體積，事件/存檔觸發) |
| M3.4 對話輸入明文 | string | 使用者即時輸入的對話明文 (即時觸發，高優先級) |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M2.3 (Eguard) / M4.6 (Observer) | `IntentVector` (見 §7.2) | 供安全過濾與 Agent 邏輯監聽 |
| 寫入資料表 `m6_1_intent_logs` (M6.1) | SQLite 欄位 | 本地落盤儲存，供日後反思分析 |
| M5.1 (薩提爾圖譜寫入器) | `IntentVector` | 去識別化後同步至雲端 Neo4j |
| M0.4 結構化日誌 | `LogEvent` | 記錄推論狀態、耗時與首字延遲指標 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M2.1** (事件防抖與排隊): 提供穩定的批次原始事件，防止模型被頻繁喚醒。
- **M0.3** (.env & Alembic): 提供本地模型路徑（如 `GEMMA_MODEL_PATH`）。

### 下游 (誰依賴我)

- **M2.3** (Eguard 基礎過濾): 接收推論結果進行二度敏感詞與注入檢查。
- **M4.1/M4.6** (Agent 核心/Observer): 接收去識別化意圖進行專案分析與對話生成。
- **M5.1** (薩提爾圖譜寫入器): 在雲端/圖資料庫基於意圖向量與 ID 建立關係邊。
- **M6.1** (本地 SQLite): 將推理出的意圖日誌與向量數據持久化。
- **M0.4** (結構化日誌): 記錄本地推理的性能指標（如首字延遲、總時間）。

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-05** | 語意壓縮丟失具體變數或錯誤，導致雲端 GraphRAG (M5.1) 與反溯因驗證 (M5.2) 因果邊精度崩潰。 | **反溯因驗證必須走本地 raw_log 路徑**。M5.1 在 Neo4j 寫入邊時必須記錄本地 `source_log_id`，後續驗證在本地用小模型比對 SQLite 內的原始明文，不從雲端意圖向量回推。 |
| **RISK-11** | 本地加載模型佔用 RAM 導致系統卡頓或 OOM。 | 實作三級降級策略：當系統 RAM 可用量 < 1.5GB 時，自動拒絕加載 Gemma 4，改用極輕量的本地 Regex/NLP 特徵抽取器，或在使用者同意下排隊至斷點處理。 |
| **RISK-12** | 意圖推論出的成就發布至社群（M3.7），造成隱私側通道洩漏。 | Observer 自動推論出的成就與意圖預設為 **`visibility="private"`（僅自己可見）**，且發布至社群必須經過手動核准。 |

## 6. Acceptance Criteria (驗收標準)

實作完成的定義。**先寫測試,後寫程式碼**。

```python
# tests/m2_2/test_gemma_inference.py

import pytest
from unittest.mock import MagicMock
from services.m2_2_gemma.pipeline import GemmaInferencePipeline
from services.m2_2_gemma.schema import IntentVector

class TestGemmaInferencePipeline:
    @pytest.fixture
    def pipeline(self):
        # 初始化管線，載入 mock 或者是測試用的輕量量化模型
        return GemmaInferencePipeline(model_path="mock_path")

    def test_compress_to_intent_vector_schema(self, pipeline):
        """驗收條件 1: 原始明文輸入應成功壓縮，且符合 IntentVector Pydantic Schema"""
        raw_code = "def check_user(user_id): return db.query(User).filter_by(id=user_id)"
        result = pipeline.compress(raw_code)
        
        assert isinstance(result, IntentVector)
        assert result.intent_label is not None
        # 意圖標籤不應該包含敏感變數名稱
        assert "check_user" not in result.intent_label
        assert "db.query" not in result.context_summary

    def test_inference_latency_limit(self, pipeline):
        """驗收條件 2: 單次意圖限制在一般硬體上（iPad M1）在 2K token 限制下小於 6 秒"""
        import time
        start_time = time.monotonic()
        pipeline.compress("I am working on calculus assignment")
        latency = (time.monotonic() - start_time)
        assert latency < 6.0  # 6.0s

    def test_risk_05_local_source_log_binding(self, pipeline):
        """驗收條件 3: 生成的 IntentVector 必須包含 source_log_id 以便本地反溯因"""
        result = pipeline.compress("Some work logs", source_log_id="local_sqlite_123")
        assert result.source_log_id == "local_sqlite_123"

    def test_priority_inference_queueing(self):
        """驗收條件 4: 優先權佇列測試，對話明文（High）必須能插隊在遙測 Batch（Low）之前執行"""
        import asyncio
        from services.m2_2_gemma.queue import InferencePriorityQueue, InferenceTask

        queue = InferencePriorityQueue()
        execution_order = []

        async def run():
            # 先入隊低優先級遙測批次
            await queue.put(InferenceTask(priority=3, payload="telemetry_batch", tag="low"))
            await queue.put(InferenceTask(priority=3, payload="telemetry_batch_2", tag="low2"))
            # 後入隊高優先級對話
            await queue.put(InferenceTask(priority=1, payload="chat_input", tag="high"))

            for _ in range(3):
                task = await queue.get()
                execution_order.append(task.tag)

        asyncio.run(run())
        # 對話任務（priority=1）必須第一個被取出
        assert execution_order[0] == "high", f"期望 high 最先執行，實際順序: {execution_order}"

    def test_role_id_present_in_intent_vector(self, pipeline):
        """驗收條件 5: IntentVector 必須攜帶 role_id，供 M5.1 建立角色維度邊"""
        result = pipeline.compress(
            "Working on homework",
            source_log_id="local_sqlite_456",
            role_id="role_csie_001"
        )
        assert result.role_id == "role_csie_001"

    def test_fallback_mode_preserves_source_log_id(self, pipeline):
        """驗收條件 6 (RISK-05): 降級為 Rule-based 時，source_log_id 仍須有效，不可為空"""
        # 模擬 iPad ai.local 不可達，觸發降級
        pipeline.simulate_edge_offline()
        result = pipeline.compress("debug session", source_log_id="local_sqlite_789", role_id="role_csie_001")
        assert result.inference_mode == "rule_based_fallback"
        assert result.source_log_id == "local_sqlite_789", "降級模式下 source_log_id 不可為空（RISK-05）"

    def test_valence_arousal_bounds(self, pipeline):
        """驗收條件 7: valence 與 arousal 必須在合法範圍內，超界應觸發 ValidationError"""
        from pydantic import ValidationError
        from services.m2_2_gemma.schema import IntentVector

        with pytest.raises(ValidationError):
            IntentVector(
                source_log_id="x", role_id="r", intent_label="l",
                context_summary="s", semantic_embedding=[0.0] * 2048,
                stripped_entities_count=0, valence=2.0, arousal=0.5
            )
```

## 7. Implementation Notes

### 7.1 模型與量化選擇

- **模型**：`mlx-community/gemma-4-e4b-it-4bit` (4B 稠密參數，Per-Layer Embeddings 架構，適合語意嵌入與意圖分類)。
- **平台與加速**：部署於 **iPad Air M1 (8GB RAM)** 上，利用 Apple Silicon 的統一記憶體進行 GPU 加速推理。
- **運行方式**：iPad 開機後自動運行作為獨立的區域網絡服務，提供 **Ollama-style 區網 API**。本機筆電透過區域網路（LAN）的 HTTP 協定呼叫該服務，埠號為 `11434`。
- **資源佔用**：模型載入後 iPad RAM 佔用約 2.8GB。

### 7.2 POST 框架提示詞與 JSON Schema

> [!NOTE]
> **與原論文 [R07: POST §4.3] 的工程偏離說明**：
> 原論文採用連續向量空間的「軟提示詞微調與傳輸（Soft-prompt Transfer）」。
> 因雲端商業大模型（Gemini API）不支援直接注入 Embedding 層的 Tensor，coOS 於工程實作上將其適配為**「基於本地 SLM 硬提示詞的語意轉譯（Hard-prompted Semantic Translation）」**。
> 本地 iPad M1 上的 Gemma 4B 透過此 System Prompt 將敏感明文轉譯為去識別化的 Intent Label 與 Context Summary 文字，並輸出相應的 Embedding 向量，以滿足商業 API 的對接限制。

```markdown
# 系統角色 (POST System Prompt)
你是一個隱私保護與語意壓縮海關。你的任務是讀取使用者的原始活動日誌或代碼，並輸出一個 JSON 格式的去識別化意圖標籤。
你必須：
1. 移除所有個人識別資訊 (PII)，如具體檔名、變數名稱、IP、網址與資料庫欄位名稱。
2. 將具體的動作抽像化（例如：「在 VSCode 裡編輯 db.py 寫 SQL 語句」 -> 抽象意圖：「資料庫寫入開發」）。
3. 提取情感與挫折狀態（如：遭遇 Bug 長時間重試 -> 挫折；順利編譯 -> 心流）。
```

> [!NOTE]
> **與原論文 [R07: 意圖向量 §4.4] 的工程偏離說明**：
> 在學術論文中，意圖向量（Intent Vector）是以連續的 Transformer 軟提示啟動張量（Soft-prompt Activation Tensor）形式存在。
> coOS 為了兼容向量資料庫（Neo4j/SQLite）的**語意檢索（Cosine Similarity Search）**以及**商業雲端 API（Gemini）僅接受文字 Prompt 的限制**，將其適配為「結構化 JSON (Pydantic) + 扁平句子嵌入向量（2048維）」。
> 此處的 `semantic_embedding` 是對去識別化後的抽象意圖文本進行 sentence embedding 編碼所得，而非模型內部的 Soft-prompt tensor。

```python
# services/m2_2_gemma/schema.py

from pydantic import BaseModel, Field
from typing import List, Optional

class IntentVector(BaseModel):
    """去識別化意圖向量"""
    source_log_id: str = Field(..., description="本地 SQLite raw_tracking_logs 的 ID，供本地反溯因驗證 (RISK-05)")
    role_id: str = Field(..., description="產生此向量當下的角色 ID，對應 M6.3 role_contexts.id，供 M5.1 建立角色維度邊")
    intent_label: str = Field(..., description="去識別化抽象意圖標籤 (例如: calculus_homework_probing)")
    context_summary: str = Field(..., description="抽象上下文摘要，剝離具體命名")
    semantic_embedding: List[float] = Field(..., description="去識別化的 2048 維語意嵌入向量")
    frustration_level: float = Field(default=0.0, ge=0.0, le=1.0, description="估計的挫折指數 0.0 ~ 1.0")
    valence: float = Field(default=0.0, ge=-1.0, le=1.0, description="情感效價 -1.0(負面) ~ 1.0(正面)，對齊 M6.4 VA 模型")
    arousal: float = Field(default=0.0, ge=0.0, le=1.0, description="情感激活度 0.0(平靜) ~ 1.0(高度激動)，對齊 M6.4 VA 模型")
    stripped_entities_count: int = Field(..., description="被剝離的具體實體與變數數量")
    inference_mode: str = Field(default="gemma_edge", description="推論來源: 'gemma_edge' | 'rule_based_fallback'，降級時標記")
```

### 7.3 優先權推論佇列 (Priority Inference Queue)

為防範 iPad 併發多重推理任務導致顯存溢出 (OOM) 或 CPU 飽和，**在筆電端 (localhost:8000) 的 Python FastAPI Sidecar 中實作優先權佇列**，對 iPad端進行單一併發序列化呼叫：

- **佇列管理**：筆電端 FastAPI 採用 `asyncio.PriorityQueue` 進行任務調度，保證向 iPad 發送的 HTTP 請求為單一通道序列化執行。
- **優先權分級 (Priority Levels)**：
  - **優先權 1 (High)**：`M3.4` 對話輸入明文。使用者即時聊天等待回覆，採**插隊機制**最優先執行。
  - **優先權 2 (Medium)**：`M1.3.1` 原始代碼 Diff。儲存/提交時觸發，背景排隊執行。
  - **優先權 3 (Low)**：`M2.1` 遙測事件 Batch。定期打包上報，資源閒置時背景低速處理。
- **防止飢餓**：對低優先權任務設定 Max Wait Time (如 5 分鐘)，超過時間則強制調升其優先級，避免長期被對話任務淹沒。

### 7.4 硬體資源限制與降級路徑

1. **常態運作（區網連線正常）**：iPad 正常提供服務，筆電透過 LAN 傳送 Batch/Diff，排隊進行推理，延遲目標在 2K token 輸入下小於 6 秒。
2. **連線中斷（iPad 不可達）**：筆電端 FastAPI 捕獲連線超時後，自動進入**降級模式**：關閉深度學習推論，降級為以關鍵字字典與句法樹結構（AST Features）為主的 Rule-based 抽取器，事件暫存於本地 SQLite 不發送。**降級模式下 `source_log_id` 與 `role_id` 仍為必填**（不可為空），且 `inference_mode` 必須設為 `"rule_based_fallback"` 以供下游 M5.1 判斷可信度；否則觸發 RISK-05。

### 7.5 異常處理

- **推論超時（> 6 秒）**：自動熔斷（Circuit Breaker），將當前批次退回 M2.1 佇列，並以中性意圖（`unknown_ambient_activity`）記錄日誌，避免卡死筆電端。
- **模型文件損毀**：若 iPad 端載入模型失敗，`ai.local` 回傳載入錯誤，筆電端觸發系統通知引導使用者檢查 iPad 狀態，並自動轉為 Rule-based 降級模式。

## 8. Anti-patterns (反模式)

- ❌ **絕對不可在 iPad 端執行優先權佇列管理。**
  理由：iPad 端應保持為無狀態的極簡 Ollama-style 模型推理 API 服務，複雜的排程與重試控制交由筆電端 FastAPI 主控。
- ❌ **不要在筆電端併行發送複數 HTTP 請求給 iPad `ai.local`。**
  理由：iPad M1 資源受限，併行推理可能導致顯存崩潰或極度卡頓，必須在筆電端序列化。
- ❌ **絕對不可將未經壓縮的原始代碼明文或對話全文儲存在 IntentVector 內上傳至雲端。**
  理由：嚴重違反 L1 明文不上雲的隱私憲法。
- ❌ **不要將意圖向量的 `source_log_id` 設為可選或為空。**
  理由：觸發 RISK-05。沒有本地 ID 對照，雲端圖譜反溯因將徹底癱瘓。

## 9. Open Questions

- [x] **是否引進 WebGPU (WebLLM) 封裝為 iPad App**：`[已決議]` 目前無開發 iOS App 規劃。iPad M1 端維持執行原生預裝好的 Ollama-style 區網伺服器。
- [x] **Embedding 的維度對齊**：`[已決議]` 向量維度直接對齊。資料庫向量維度與 Gemma 本地模型的原生 Embedding 輸出維度（例如 2048 維）保持一致，不採用額外的 Dense projection 投影層，以避免複雜度增加與精度損失。
