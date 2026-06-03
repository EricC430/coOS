# M4.6 — Observer 背景萃取 Agent

**標籤**:`[MVP]`
**版本**:`1.0` / `draft`
**最後更新**:2026-06-03

## 1. Purpose (目的)

作為 LangGraph 中的平行背景節點，在 Persona 回應使用者的同時，非同步監聽對話內容，萃取「意圖」「專案」「時間承諾」等結構化資訊，透過 Function Calling 寫入 DB，並觸發前端 System Event 隱形提示。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R02 | §動態狀態解碼 HMM | Observer 從對話序列推斷使用者隱含意圖的狀態轉移模型 |
| R10 | §結構化 代理工作流 | Observer 作為 Agent 工作流中的平行監聽節點設計 |
| R09 | §6.2 BDI | Observer 推論出的 desire 需經 BDI Reconciler 整合，不可直接注入 Persona |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M4.1 路由容器派發 | `ObserverTask` | `{"thread_id": "t_001", "user_msg": "我想開始做微積分的期末專案", "extract_targets": ["project", "intent"]}` |
| M6.1 `chat_transcripts` | DB Rows | 當前 thread 的對話歷史 |
| M4.3 `RoleContext` | 角色上下文 | 當前角色的 `role_id` 與既有專案清單 |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M6.2 `role_projects` (via M6.3) | Insert / Match | `{role_id: "role_csie", name: "微積分期末專案", inferred_by_ai: true}` |
| M6.1 `chat_transcripts` 標記 | Update | 標記 `elicitation_tag = "project_detected"` |
| M3.4 前端 SSE System Event | `SystemEvent` | `{type: "project_created", project_name: "微積分期末專案", visibility: "private"}` |
| M4.4 套問觸發 | `ElicitationHint` | `{context: "new_project_detected", project_name: "微積分期末專案"}` |
| M0.4 結構化日誌 | `LogEvent` | 記錄萃取結果、耗時、信心度 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M4.1** (Agent 路由)：M4.1.3 Observer 容器派發任務至本模組
- **M4.3** (角色隔離)：萃取範圍限定於當前 `role_id` 的專案清單
- **M2.3** (Eguard 過濾)：萃取結果寫入前必須經 Eguard 二次過濾 ([RISK-12])
- **M6.1** (SQLite)：讀取 `chat_transcripts` 對話歷史
- **M6.2 / M6.3** (`role_projects` 表)：寫入偵測到的新專案

### 下游 (誰依賴我)

- **M3.4** (AI 幫手)：接收 System Event 在對話下方顯示隱形提示
- **M4.4** (自然套問)：接收專案偵測結果觸發耗時套問
- **M4.7** (Obsidian 同步)：Session 結束時從 Observer 萃取的結構化資訊生成摘要
- **M3.2** (儀表板)：顯示 Observer 自動建立的專案

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-08** | Observer 推論的 desire 與 ToM belief 矛盾 → 衝突路由 | Observer 不直接注入 Persona，萃取結果走 BDI Reconciler 整合為 `intention` 後才供 M4.2 使用 |
| **RISK-12** | 推論出的 Project 名稱含敏感資訊 (如「OpenStack 畢業專題 by 陳XX」) 經 M6.2 同步上雲 → 側通道洩漏 | 萃取結果必須經 M2.3 Eguard 過濾 PII；Observer 自動建立的成就預設 `visibility="private"` |
| (無直接 RISK-xx) | Observer 超時或崩潰阻塞主對話 | Observer 與 Persona 並行執行；Observer 設 5s timeout，超時靜默失敗不影響對話 |

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m4_6/test_observer_agent.py

import pytest
import asyncio

class TestObserverExtraction:
    def test_project_detected_in_5_seconds(self, db, user, role_csie):
        """對話含「我想做 X 專案」→ 5 秒內 role_projects 出現對應紀錄"""
        result = run_observer(
            thread_id="t_001",
            user_msg="我想開始做微積分的期末專案",
            role_id=role_csie.id,
        )
        assert result.elapsed_seconds <= 5
        project = db.query_one(
            "SELECT * FROM role_projects WHERE role_id = :rid AND name LIKE '%微積分%'",
            {"rid": role_csie.id}
        )
        assert project is not None
        assert project.inferred_by_ai is True

    def test_existing_project_matched_not_duplicated(self, db, user, role_csie):
        """提及已存在的專案 → 匹配而非重複建立"""
        create_project(db, role_id=role_csie.id, name="微積分")
        run_observer(user_msg="微積分作業好難", role_id=role_csie.id)
        projects = db.query_all(
            "SELECT * FROM role_projects WHERE role_id = :rid AND name LIKE '%微積分%'",
            {"rid": role_csie.id}
        )
        assert len(projects) == 1  # 不重複

    def test_intent_extraction(self, db):
        """萃取使用者意圖"""
        result = run_observer(user_msg="我明天要交作業，今晚得趕完")
        assert result.extracted_intent is not None
        assert "deadline" in result.extracted_intent.lower() or "urgent" in result.extracted_intent.lower()

class TestObserverPrivacy:
    def test_extraction_passes_eguard(self):
        """[RISK-12] 萃取結果必須經 Eguard 過濾 PII"""
        result = run_observer(user_msg="幫我看陳小明的 OpenStack 部署")
        assert "陳小明" not in result.project_name
        assert "陳" not in str(result.extraction)

    def test_inferred_achievement_default_private(self, db):
        """[RISK-12] Observer 自動偵測的成就預設不公開"""
        result = run_observer(user_msg="我連續寫了 30 天程式")
        if result.achievement:
            assert result.achievement.default_visibility == "private"

    def test_extraction_scoped_by_role(self, db, role_csie, role_family):
        """[RISK-06] 萃取結果綁定當前 role_id"""
        result = run_observer(user_msg="微積分專案", role_id=role_csie.id)
        assert result.role_id == role_csie.id
        # FAMILY 角色查不到
        family_projects = db.query_all(
            "SELECT * FROM role_projects WHERE role_id = :rid",
            {"rid": role_family.id}
        )
        assert not any(p.name == result.project_name for p in family_projects)

class TestObserverResilience:
    def test_observer_does_not_block_persona(self):
        """Observer 超時不阻塞 Persona 回應"""
        async def run():
            persona_task = asyncio.create_task(mock_persona_respond(timeout=2))
            observer_task = asyncio.create_task(mock_observer_slow(timeout=10))
            # Persona 應先完成
            done, pending = await asyncio.wait(
                [persona_task, observer_task],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=3
            )
            assert persona_task in done
        asyncio.run(run())

    def test_observer_timeout_silent_failure(self):
        """Observer 超時 → 靜默失敗，記錄日誌"""
        with capture_logs() as logs:
            result = run_observer(user_msg="test", force_timeout=True)
        assert result is None or result.timed_out is True
        assert any(log["event_type"] == "observer_timeout" for log in logs)

    def test_system_event_emitted_on_success(self):
        """萃取成功 → 發送 SSE System Event 至前端"""
        events = capture_sse_events()
        run_observer(user_msg="我想做機器學習專案")
        assert any(e["type"] == "project_created" for e in events)
```

## 7. Implementation Notes

### 7.1 LangGraph 節點結構

```python
# services/m4_6_observer/agent.py
# [R10: §代理工作流 + R02: §動態狀態解碼]

from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class ObserverResult:
    project_name: Optional[str] = None
    extracted_intent: Optional[str] = None
    time_commitment: Optional[str] = None
    achievement: Optional[dict] = None
    role_id: str = ""
    timed_out: bool = False
    elapsed_seconds: float = 0.0

EXTRACT_PATTERNS = {
    "project": [
        r"(?:我想做|開始做|要做|在做)\s*(.{2,20}?)(?:的|專案|作業|報告)",
        r"(.{2,20}?)(?:專案|project)\s*(?:開始|啟動|建立)",
    ],
    "deadline": [
        r"(?:明天|後天|下週|月底).*(?:要交|截止|deadline)",
    ],
}

async def observer_extract(task: dict) -> ObserverResult:
    """
    [R10 §代理工作流] 非同步萃取，不阻塞 Persona。
    5s timeout — 超時靜默失敗。
    """
    import asyncio
    try:
        result = await asyncio.wait_for(
            _do_extraction(task), timeout=5.0
        )
        return result
    except asyncio.TimeoutError:
        await log_event("observer_timeout", {"thread_id": task["thread_id"]})
        return ObserverResult(timed_out=True)
```

### 7.2 專案偵測與去重

```python
# services/m4_6_observer/project_detector.py

async def detect_and_upsert_project(
    user_msg: str, role_id: str, existing_projects: list
) -> Optional[str]:
    """
    1. Regex 偵測專案提及
    2. 模糊匹配既有專案 (防重複)
    3. [RISK-12] Eguard 過濾 PII
    4. 不存在 → 寫入 role_projects (inferred_by_ai=true)
    """
    candidate = regex_extract_project(user_msg)
    if not candidate:
        return None

    # Eguard 過濾 [RISK-12]
    candidate = await eguard_filter_pii(candidate)

    # 模糊匹配
    match = fuzzy_match(candidate, [p.name for p in existing_projects], threshold=0.7)
    if match:
        return match  # 已存在，不新建

    # 新建 [R10 §代理工作流]
    await db.execute(
        "INSERT INTO role_projects (id, role_id, name, inferred_by_ai) "
        "VALUES (:id, :rid, :name, TRUE)",
        {"id": uuid4(), "rid": role_id, "name": candidate}
    )
    await emit_sse("project_created", {"project_name": candidate, "role_id": role_id})
    return candidate
```

### 7.3 BDI 整合介面

```python
# services/m4_6_observer/bdi_bridge.py
# [R09 §6.2 + RISK-08] Observer 推論結果不可直接注入 Persona

async def submit_to_bdi_reconciler(
    desire: str,           # Observer 推論的表面意圖
    thread_id: str,
    role_id: str,
):
    """
    [RISK-08] Observer 的 desire 必須經 BDI Reconciler 整合。
    不可直接把 desire 欄位丟給 M4.2 Persona。
    """
    await bdi_queue.put({
        "source": "M4.6",
        "desire": desire,
        "thread_id": thread_id,
        "role_id": role_id,
    })
    # M4.2 的 BDI Reconciler 會從此佇列取出並整合 belief
```

### 7.4 異常處理

- **Observer 超時 (>5s)** → 靜默失敗，記錄 `observer_timeout` 日誌；不影響主對話流
- **Eguard 過濾後 project_name 為空** → 放棄此次萃取，記錄 `extraction_filtered_empty`
- **`role_projects` UNIQUE 約束衝突** → 視為已存在，匹配而非失敗
- **SSE 推送失敗 (前端斷線)** → 靜默忽略，System Event 非關鍵路徑

## 8. Anti-patterns (反模式)

❌ **不要讓 Observer 阻塞 Persona 回應**
   理由：Observer 是背景萃取，使用者等的是對話回覆。超時靜默失敗即可。

❌ **不要讓 Observer 的推論結果直接注入 Persona Prompt**
   理由：RISK-08。desire 必須經 BDI Reconciler 與 belief 整合後才能供 M4.2 使用，否則產生矛盾建議。

❌ **不要在 Observer 萃取的 project_name 中保留 PII**
   理由：RISK-12。`role_projects` 存在雲端 PostgreSQL，含 PII 的 project 名稱上雲等於側通道洩漏。

❌ **不要讓 Observer 跨角色寫入 project**
   理由：RISK-06。萃取結果必須綁定當前 `role_id`，由 M4.3 RoleContext 限定。

❌ **不要在 Observer 偵測到專案時自動建立完整的 Kanban/Task**
   理由：MVP 階段 Project 僅是標籤概念 (M6.3 Open Questions)，進階功能留待未來。

## 9. Open Questions

- [ ] **Observer 的萃取是用 Regex 還是 LLM?** MVP 用 Regex pattern matching 足夠，但複雜語境 (如「我上週提到的那個東西」) 需要 LLM。是否 MVP 階段就呼叫 Gemini 做 Function Calling?
- [ ] **專案模糊匹配的閾值?** 目前設 0.7，「微積分作業」vs「微積分」是否應匹配? 「OS Lab」vs「Operating System 實驗」呢?
- [ ] **Observer 是否應萃取「情緒」?** 目前只萃取 project/intent/deadline，情緒偵測屬 M4.8 (進階)。但若 MVP 對話中明確說「我很焦慮」，Observer 是否應記錄?
- [ ] **System Event 的 UI 呈現方式?** M3.4.4.1 定義了隱形提示，但具體樣式 (Toast? 對話氣泡? 底部 bar?) 需與前端設計對齊。

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責，不能拆解 — 背景萃取
- [x] §2 至少 1 個 `Rxx` 引用 — R02, R10, R09
- [x] §3 Schema 用 dataclass — `ObserverResult`, `ObserverTask`
- [x] §4 依賴是真實模組編號 — M4.1, M4.3, M2.3, M6.1, M6.2/M6.3
- [x] §5 grep 過 `05_integration_risk_audit.md` — RISK-08, RISK-12
- [x] §6 測試先於程式碼 — 9 條驗收測試
- [x] §8 至少 3 條反模式 — 5 條
- [x] §9 至少 1 個開放問題 — 4 個

---

## 附錄：子模組拆分決策

> **結論：M4.6 無子模組，不需要拆分。**

Module Registry 明確記載「**子模組：無 (單一 LangGraph 節點)**」。Observer 是一個自包含的 LangGraph 節點，內部邏輯 (專案偵測、意圖萃取、BDI 橋接) 雖可分層，但不構成獨立子模組，無需拆分 SPEC。
