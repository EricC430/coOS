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
| (無直接 RISK-xx) | Observer 超時或崩潰阻塞主對話 | Observer 與 Persona 並行執行；Observer 設 30s timeout，超時靜默失敗不影響對話 |

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m4_6/test_observer_agent.py

import pytest
import asyncio

class TestObserverExtraction:
    def test_project_detected_in_30_seconds(self, db, user, role_csie):
        """[決策] 對話含「我想做 X 專案」→ 30 秒內 role_projects 出現對應紀錄"""
        result = run_observer(
            thread_id="t_001",
            user_msg="我想開始做微積分的期末專案",
            role_id=role_csie.id,
        )
        assert result.elapsed_seconds <= 30
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

    def test_emotion_extraction(self, db):
        """[決策] 萃取使用者情緒"""
        result = run_observer(user_msg="這份作業我寫了三天都寫不出來，真的很想放棄")
        assert result.emotion_detected is not None
        assert result.emotion_detected in ["frustrated", "anxious", "sad"]

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
    # v1.2 新增：承諾萃取與目標確立
    promises_detected: List[dict] = field(default_factory=list)
    goal_established: Optional[dict] = None
    session_intention: Optional[str] = None  # Session 結束時 LLM 抽取
    emotion_detected: Optional[str] = None   # [決策] 偵測到的當下情緒標籤 (如 anxious, frustrated)
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
    [決策] 30s timeout — 超時靜默失敗以適應本地端推論。
    """
    import asyncio
    try:
        result = await asyncio.wait_for(
            _do_extraction(task), timeout=30.0
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

    # [決策] 專案本質是標籤，提高匹配閾值至 0.85 防止過度合併 (例如 微積分作業 vs 微積分練習方法)
    match = fuzzy_match(candidate, [p.name for p in existing_projects], threshold=0.85)
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

### 7.4 承諾萃取 (v1.2 新增)

```python
# services/m4_6_observer/promise_extractor.py
# [v1.2] 從對話中偵測口頭承諾並寫入 promises 表

async def extract_promises(
    user_msg: str, thread_id: str, role_id: str, persona_id: str
) -> list[dict]:
    """
    使用 LLM (本地 Gemma) 從使用者訊息中抽取口頭承諾。
    純 Regex 無法涵蓋「我這週末應該可以搞定」等模糊承諾語句，
    因此使用 LLM 做語意理解 + 時間 NER。

    回傳格式: [{"text": "週五前做完報告", "deadline": "2026-06-06T23:59:00"}]
    """
    prompt = (
        "從以下使用者訊息中抽取任何口頭承諾或時間約定。"
        "回傳 JSON 陣列，每個元素包含 text（承諾原文）和 deadline（ISO 格式，若無法確定則為 null）。"
        "若無承諾則回傳空陣列 []。\n"
        f"使用者訊息：{user_msg}"
    )
    result = await gemma_edge.generate_json(prompt)
    
    # 寫入 promises 表
    for promise in result:
        promise_text = await eguard_filter_pii(promise["text"])
        await db.execute(
            "INSERT INTO promises (id, role_id, persona_id, source_thread_id, text, deadline) "
            "VALUES (gen_random_uuid(), :rid, :pid, :tid, :text, :deadline)",
            {"rid": role_id, "pid": persona_id, "tid": thread_id,
             "text": promise_text, "deadline": promise.get("deadline")}
        )
        await emit_sse("PROMISE_RECORDED", {
            "text": promise_text, "deadline": promise.get("deadline"),
            "persona_id": persona_id,
        })
    
    return result
```

### 7.5 Session 結束時 Intention 抽取 (v1.2 新增)

```python
# services/m4_6_observer/intention_extractor.py
# [v1.2] 每個 Session (thread) 結束時由 LLM 抽取使用者核心 intention

async def extract_session_intention(
    thread_id: str, role_id: str, persona_id: str
) -> Optional[str]:
    """
    Session 結束時觸發（由 M4.1 的 session_end 回調呼叫）。
    從整段對話歷史中抽取使用者進行此對話的核心 intention。
    寫入 chat_transcripts 的 session metadata，供 M3.4 前端歷史時間軸的 intention 欄顯示。
    """
    transcripts = await db.fetch_all(
        "SELECT content, role FROM chat_transcripts "
        "WHERE thread_id = :tid ORDER BY created_at ASC",
        {"tid": thread_id}
    )
    if not transcripts:
        return None
    
    conversation = "\n".join(
        f"{'使用者' if t['role'] == 'user' else '專家'}: {t['content']}"
        for t in transcripts
    )
    
    prompt = (
        "請用一句話摘要此對話中使用者的核心意圖/目的是什麼。"
        "回傳純文字，不要 JSON。\n"
        f"對話內容：\n{conversation[:2000]}"
    )
    intention = await gemma_edge.generate_text(prompt)
    
    # 更新 session metadata
    await db.execute(
        "UPDATE chat_transcripts SET session_intention = :intention "
        "WHERE thread_id = :tid AND turn_number = 1",
        {"intention": intention.strip(), "tid": thread_id}
    )
    
    return intention.strip()
```

### 7.6 目標確立偵測 (v1.2 新增)

```python
# services/m4_6_observer/goal_detector.py
# [v1.2] 偵測對話中是否確立了新的核心目標

async def detect_goal_establishment(
    user_msg: str, assistant_msg: str,
    thread_id: str, role_id: str, persona_id: str,
    existing_goals: list
) -> Optional[dict]:
    """
    使用 LLM 判斷對話中是否確立了新的最高階目標。
    觸發條件：
    - 專家引導使用者明確說出目的 (如「所以你找我最主要是想...」)
    - 使用者主動聲明目標 (如「我希望能...」「我的目標是...」)
    
    若偵測到新目標且不與既有 active goals 重複 → 寫入 goals 表。
    觸發 GOAL_CONFIRMED SSE 事件（區別於單純的 GOAL_INFERRED）。
    """
    prompt = (
        "以下對話中，使用者是否與專家確立了一個明確的核心目標或最高階目的？"
        "若有，回傳 JSON: {\"title\": \"目標標題\", \"description\": \"詳細描述\"}。"
        "若無明確目標確立，回傳 null。\n"
        f"專家：{assistant_msg[:500]}\n使用者：{user_msg[:500]}"
    )
    result = await gemma_edge.generate_json(prompt)
    
    if result and result.get("title"):
        # 去重：模糊匹配既有目標
        title = await eguard_filter_pii(result["title"])
        if not fuzzy_match(title, [g["title"] for g in existing_goals], threshold=0.7):
            await db.execute(
                "INSERT INTO goals (id, role_id, persona_id, title, description) "
                "VALUES (gen_random_uuid(), :rid, :pid, :title, :desc)",
                {"rid": role_id, "pid": persona_id,
                 "title": title, "desc": result.get("description", "")}
            )
            await emit_sse("GOAL_CONFIRMED", {
                "title": title, "persona_id": persona_id,
            })
            return result
    
    return None
```

### 7.7 異常處理

- **Observer 超時 (>30s)** → 靜默失敗，記錄 `observer_timeout` 日誌；不影響主對話流
- **Eguard 過濾後 project_name 為空** → 放棄此次萃取，記錄 `extraction_filtered_empty`
- **`role_projects` UNIQUE 約束衝突** → 視為已存在，匹配而非失敗
- **SSE 推送失敗 (前端斷線)** → 靜默忽略，System Event 非關鍵路徑
- **承諾萃取 LLM 回傳格式錯誤** → 靜默忽略，記錄 `promise_extraction_parse_error`
- **Intention 抽取失敗** → 記錄 `intention_extraction_failed`，前端 intention 欄顯示「(未抽取)」

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

❌ **不要讓承諾萃取繞過 Eguard 直接寫入 promises 表**
   理由：RISK-12。承諾原文可能包含 PII（如「幫陳小明做 OpenStack 報告」），必須先泛化。

## 9. Open Questions (已拍板決策)

- [x] **Observer 的萃取是用 Regex 還是 LLM?**
  * **決策**：**LLM（本地 Gemma）**。承諾萃取與目標確立偵測需要語意理解，純 Regex 無法涵蓋「我這週末應該可以搞定」等模糊語句。專案偵測保留 Regex 作為快速路徑，LLM 作為回退。
- **[決策] 專案模糊匹配的閾值與定義**：
  * **決策**：專案在系統中實質上是**「議題/討論標籤 (Topic Tag)」**而非限定於嚴格定義的專案實體。若角色本身的專業領域較為集中（例如「微積分助教」），過度寬鬆的匹配會將各種微積分話題合併。因此，將模糊匹配閾值提高至 **`0.85`**（高嚴格度），且專案定義為標籤（例如將討論「微積分怎麼練習比較好」標記為「微積分的練習方法」標籤），以防將不同話題錯誤合併。
- **[決策] Observer 是否應萃取「情緒」**：
  * **決策**：**是，進行情緒萃取**。除了原有的 project/intent/deadline/promise/goal 外，Observer 將同時偵測使用者在對話中所流露的當下情緒（如：焦慮、受挫、自信、迷茫等），並寫入 `chat_transcripts` 中的 metadata，以供 Persona 動態調整回應語氣或觸發反思套問。
- **[決策] System Event 的 UI 呈現方式**：
  * **決策**：**到時候確認**。暫不於 SPEC 硬性規定具體呈現樣式，待後續與前端 UI 設計實際開發對齊後再行敲定。

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
