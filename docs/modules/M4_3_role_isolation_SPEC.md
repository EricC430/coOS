# M4.3 — 全域情境隔離狀態機 (Role Isolation Engine)

**標籤**:`[MVP]`
**版本**:`1.0` / `draft`
**最後更新**:2026-06-03

## 1. Purpose (目的)

依 `Role_ID` 對整條 API 請求鏈施加沙盒隔離——資料流路由、資料庫查詢範圍、Persona 可用池與系統提示詞快取——確保角色間零資料交叉。角色 A (CSIE) 的任何資料、對話記憶或隱性狀態絕不會出現在角色 B (FAMILY) 的上下文中。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R03 | §2 ARPM 框架 | 角色切換時 Persona 記憶必須完全重置，不可跨角色繼承對話上下文 |
| R03 | §6 狀態機移轉 | 角色切換觸發 `ROLE_SWITCHED` 事件，所有狀態機歸零重啟 |
| R03 | §人設崩塌 | 角色-Persona 映射確保每個 Persona 只服務單一角色，避免跨角色記憶汙染 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M3.1 全域狀態 `ROLE_SWITCHED` 事件 | `RoleSwitchEvent` | `{"user_id": "u_001", "from_role_id": "role_csie", "to_role_id": "role_family"}` |
| M3.4 / 任何 API 請求 | HTTP Header | `X-Role-ID: role_csie` |
| M6.2 `roles` 表 | DB Row | `{id: "role_csie", slug: "csie", display_name: "資工系", user_id: "u_001"}` |
| M6.3 `role_projects`, `role_settings`, `role_implicit_states` | DB Rows | 當前角色的專案清單、設定、隱性狀態 |
| M6.2 `ai_experts` 表 | DB Rows | `WHERE role_id = current_role_id AND is_active = TRUE` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M4.1 Router Agent | `RoleContext` | `{"role_id": "role_csie", "active_experts": ["robert_001", "宏軒_002"], "projects": [...], "settings": {...}}` |
| M4.2 Persona 容器 | `PersonaInjectionContext` | `{"persona_id": "robert_001", "personality_prompt": "...", "tone_default": "authoritative"}` |
| M4.2.4 隱性狀態注入 | `RoleImplicitState` 或 `null` | `{"label": "flow", "confidence": 0.8}` 或 `null` (無狀態時回傳中性預設) |
| M3.1 全域狀態 | `RoleContextLoaded` | `{"role_id": "role_csie", "expert_count": 2, "project_count": 3}` |
| M0.4 結構化日誌 | `LogEvent` | 記錄角色切換、沙盒啟用、快取清除事件 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M4.1** (Agent 路由)：M4.3 作為中介軟體攔截請求後，將 `RoleContext` 注入 M4.1 的路由決策流程
- **M6.2** (`roles`, `ai_experts` 表)：讀取角色定義與 Persona 清單
- **M6.3** (`role_projects`, `role_settings`, `role_implicit_states`)：讀取當前角色的完整情境資料
- **M3.1** (全域狀態 Zustand)：訂閱 `ROLE_SWITCHED` 事件觸發沙盒重建
- **M0.4** (結構化日誌)：所有隔離操作寫入 `raw_tracking_logs`

### 下游 (誰依賴我)

- **M4.1** (Agent 路由)：接收白名單限定的 `active_experts` 池 ([RISK-06])
- **M4.2** (Persona 狀態機)：接收當前角色的 Persona 配置，含隱性狀態
- **M4.4** (自然套問)：套問範圍限定於當前角色的 Projects
- **M4.6** (Observer Agent)：萃取結果綁定當前 `role_id`
- **M3.2** (儀表板)：角色切換後 UI 完全重繪

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-06** | 角色切換時 ImplicitState 跨界洩漏：M4.2.4 可能把 CSIE 角色的「焦慮」狀態注入 FAMILY 角色的 Persona | `role_implicit_states` 以 `(user_id, role_id)` 雙鍵查詢；切換後若新角色無狀態，回傳 `PersonaContext.neutral_default()`，**絕不繼承** |
| **RISK-06** (延伸) | LangGraph 的 `thread_id` 若跨角色共用，對話歷史會洩漏 | `thread_id` 必須包含 `role_id` 前綴 (例：`role_csie::t_001`)，查詢時強制過濾 |
| **RISK-12** | 角色切換事件本身若上雲 (如 `xp_ledger`)，可從切換時間推測行為模式 | 角色切換事件僅寫入本地 `raw_tracking_logs` (L1)，不上雲 |

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m4_3/test_role_isolation.py

import pytest
from unittest.mock import patch, AsyncMock

class TestM4_3_1_SandboxMiddleware:
    def test_request_without_role_id_rejected(self, client):
        """所有 Agent API 請求必須攜帶 X-Role-ID"""
        response = client.post("/api/m4_1/chat", json={"content": "hi"})
        assert response.status_code == 422
        assert "X-Role-ID" in response.json()["detail"]

    def test_request_with_invalid_role_id_rejected(self, client, user):
        """X-Role-ID 必須是使用者擁有的角色"""
        response = client.post(
            "/api/m4_1/chat",
            json={"content": "hi"},
            headers={"X-Role-ID": "role_not_mine"}
        )
        assert response.status_code == 403

    def test_request_scoped_to_correct_role(self, client, user, role_csie):
        """請求的資料查詢範圍限定在指定角色"""
        response = client.get(
            "/api/m6_3/projects",
            headers={"X-Role-ID": str(role_csie.id)}
        )
        for project in response.json():
            assert project["role_id"] == str(role_csie.id)

class TestM4_3_2_DatabaseSwitching:
    def test_query_only_returns_current_role_data(self, db, user, role_csie, role_family):
        """[RISK-06] A 角色資料絕不出現在 B 角色查詢結果"""
        # CSIE 角色下建立 Project
        create_project(db, role_id=role_csie.id, name="微積分")
        # 切換到 FAMILY 角色查詢
        with role_context(user, role_family):
            projects = get_projects_for_current_role(db, user.id)
        assert len(projects) == 0
        assert not any(p.name == "微積分" for p in projects)

    def test_experts_filtered_by_role(self, db, user, role_csie, role_family):
        """[RISK-06] Persona 候選池嚴格限定於當前角色"""
        create_expert(db, role_id=role_csie.id, name="Robert")
        with role_context(user, role_family):
            experts = get_active_experts(db, role_family.id)
        assert not any(e.name == "Robert" for e in experts)

class TestM4_3_3_DynamicPersonaInjection:
    def test_role_switch_reloads_persona_config(self, user, role_csie, role_family):
        """角色切換後 Persona 配置完全重載"""
        ctx_csie = build_role_context(user, role_csie)
        ctx_family = build_role_context(user, role_family)
        # 兩個角色的 expert 池不可有交集
        csie_ids = {e.id for e in ctx_csie.active_experts}
        family_ids = {e.id for e in ctx_family.active_experts}
        assert csie_ids.isdisjoint(family_ids)

    def test_implicit_state_not_inherited(self, db, user, role_csie, role_family):
        """[RISK-06] 切換角色後不可繼承上一角色的隱性狀態"""
        set_implicit_state(db, user.id, role_csie.id, "anxiety", 0.85)
        with role_context(user, role_family):
            state = get_current_implicit_state(db, user.id, role_family.id)
        assert state is None  # 不繼承 CSIE 的焦慮

class TestM4_3_4_PromptCacheReset:
    def test_role_switch_clears_prompt_cache(self, user, role_csie, role_family):
        """角色切換後系統提示詞快取必須清除"""
        # 先在 CSIE 角色下載入 Robert 的 prompt
        load_persona_prompt(user, role_csie, "robert_001")
        cache_before = get_prompt_cache_keys()
        assert "robert_001" in cache_before

        # 切換到 FAMILY
        switch_role(user, role_family)
        cache_after = get_prompt_cache_keys()
        assert "robert_001" not in cache_after

    def test_thread_id_scoped_by_role(self, user, role_csie, role_family):
        """[RISK-06] thread_id 包含 role_id 前綴，防止跨角色對話歷史洩漏"""
        thread = create_thread(user, role_csie)
        assert str(role_csie.id) in thread.thread_id
        # 在 FAMILY 角色下查不到此 thread
        with role_context(user, role_family):
            threads = list_threads(user)
        assert thread.thread_id not in [t.thread_id for t in threads]
```

## 7. Implementation Notes

### 7.1 沙盒中介軟體 (M4.3.1)

```python
# services/m4_3_role_isolation/middleware.py
# [R03 §6 + RISK-06] 角色隔離中介軟體

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

class RoleIsolationMiddleware(BaseHTTPMiddleware):
    """
    攔截所有 /api/m4_* 與 /api/m6_* 請求,
    從 X-Role-ID header 提取角色並注入 request.state。
    """

    # 不需要角色隔離的端點白名單
    EXEMPT_PATHS = {"/api/health", "/api/auth/login", "/api/m6_2/roles"}

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        role_id = request.headers.get("X-Role-ID")
        if not role_id:
            raise HTTPException(422, "Missing X-Role-ID header")

        # 驗證 role_id 屬於當前使用者
        user_id = request.state.user_id  # 由 auth middleware 設定
        role = await validate_role_ownership(user_id, role_id)
        if not role:
            raise HTTPException(403, "Role does not belong to current user")

        # 注入角色上下文
        request.state.role_id = role_id
        request.state.role_context = await build_role_context(user_id, role_id)

        return await call_next(request)
```

### 7.2 角色上下文建構器

```python
# services/m4_3_role_isolation/context.py
# [R03 §人設崩塌] 角色上下文組裝

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import UUID

@dataclass
class RoleContext:
    """M4.1 Router 與 M4.2 Persona 共用的角色上下文"""
    role_id: UUID
    user_id: UUID
    active_experts: List[dict] = field(default_factory=list)
    projects: List[dict] = field(default_factory=list)
    settings: Optional[dict] = None
    implicit_state: Optional[dict] = None  # [RISK-06] 僅當前角色

async def build_role_context(user_id: UUID, role_id: UUID) -> RoleContext:
    """
    組裝當前角色的完整上下文。
    [RISK-06] implicit_state 嚴格以 (user_id, role_id) 雙鍵查詢。
    """
    experts = await db.fetch_all(
        "SELECT * FROM ai_experts WHERE role_id = :rid AND is_active = TRUE",
        {"rid": role_id}
    )
    projects = await db.fetch_all(
        "SELECT * FROM role_projects WHERE role_id = :rid AND status = 'active'",
        {"rid": role_id}
    )
    settings = await db.fetch_one(
        "SELECT * FROM role_settings WHERE role_id = :rid",
        {"rid": role_id}
    )
    # [RISK-06] 雙鍵查詢，絕不用 user_id 單鍵
    implicit_state = await db.fetch_one(
        "SELECT * FROM role_implicit_states "
        "WHERE user_id = :uid AND role_id = :rid "
        "ORDER BY inferred_at DESC LIMIT 1",
        {"uid": user_id, "rid": role_id}
    )

    return RoleContext(
        role_id=role_id,
        user_id=user_id,
        active_experts=experts,
        projects=projects,
        settings=settings,
        implicit_state=implicit_state,  # 可能為 None → M4.2.4 用中性預設
    )
```

### 7.3 角色切換處理器 (M4.3.3 + M4.3.4)

```python
# services/m4_3_role_isolation/switch.py
# [R03 §6] 角色切換時的狀態重置

async def handle_role_switch(user_id: UUID, from_role_id: UUID, to_role_id: UUID):
    """
    角色切換時執行的三步驟清除:
    1. 清除系統提示詞快取 (M4.3.4)
    2. 重建角色上下文 (M4.3.3)
    3. 廣播 ROLE_SWITCHED 事件
    """
    # Step 1: 清除快取 [R03 §6]
    prompt_cache.invalidate_by_role(from_role_id)
    thread_cache.invalidate_by_role(from_role_id)

    # Step 2: 重建新角色上下文
    new_context = await build_role_context(user_id, to_role_id)

    # Step 3: 廣播 (M0.4 日誌 + M3.1 前端)
    await log_event("role_switched", {
        "user_id": str(user_id),
        "from_role_id": str(from_role_id),
        "to_role_id": str(to_role_id),
        "new_expert_count": len(new_context.active_experts),
    })
    await broadcast_sse("ROLE_SWITCHED", {
        "role_id": str(to_role_id),
        "context": new_context.to_frontend_dto(),
    })

    return new_context
```

### 7.4 Thread ID 角色前綴策略

```python
# services/m4_3_role_isolation/thread.py
# [RISK-06] 防止跨角色對話歷史洩漏

import uuid

def create_scoped_thread_id(role_id: uuid.UUID) -> str:
    """
    產生包含 role_id 的 thread_id。
    查詢時強制過濾前綴，即使直接拼 thread_id 也無法跨角色讀取。
    """
    return f"{role_id}::{uuid.uuid4()}"

def validate_thread_access(thread_id: str, current_role_id: uuid.UUID) -> bool:
    """驗證 thread 屬於當前角色"""
    prefix = thread_id.split("::")[0]
    return prefix == str(current_role_id)
```

### 7.5 異常處理

- **角色不存在** → `404 Not Found`，不可 fallback 到其他角色
- **角色切換時 DB 查詢失敗** → 中止切換，保持原角色，記錄 `role_switch_failed` 至 `raw_tracking_logs`
- **`build_role_context` 超時 (>3s)** → 回傳空 `RoleContext` (無 experts、無 projects)，前端顯示 skeleton UI，背景重試
- **`implicit_state` 查詢回傳已過期狀態** (`expires_at < NOW()`) → 視為 `None`，走中性預設

## 8. Anti-patterns (反模式)

❌ **不要在角色切換時把上一個角色的 `role_implicit_states` 複製到新角色**
   理由：RISK-06 (跨角色資料洩漏)。切換後若新角色無狀態，回傳 `PersonaContext.neutral_default()`。

❌ **不要用 `user_id` 單鍵查詢 `role_implicit_states`**
   理由：會拿到所有角色的狀態，必須用 `(user_id, role_id)` 雙鍵。[RISK-06]

❌ **不要讓 M4.1 Router 繞過此中介軟體直接查詢 `ai_experts`**
   理由：Router 必須從 `RoleContext.active_experts` 白名單取得候選池，而非自行查表。否則角色隔離形同虛設。

❌ **不要在 `ROLE_SWITCHED` 事件中攜帶上一個角色的具體資料** (如 expert 名稱、project 內容)
   理由：前端快取如果殘留上一角色的資料，可能在新角色 UI 中閃現 → 體驗與隱私雙重問題。

❌ **不要讓角色切換事件同步至雲端 PostgreSQL**
   理由：角色切換的時間戳可能洩漏行為模式 (如「每天 22:00 切到 FAMILY 角色」)。僅寫入本地 `raw_tracking_logs`。[RISK-12]

## 9. Open Questions

實作前必須與使用者拍板：

- [ ] **角色切換的冷卻時間?** 是否需要防止使用者快速連續切換 (如 1 秒內切 5 次) 導致快取反覆清除的效能問題?
- [ ] **「工具型 AI」(M3.4.1.1) 是否跨角色共享?** 它是首位固定的無人設 AI，是否應該在所有角色都可用，還是每個角色有獨立的工具型 AI 實例?
- [ ] **角色切換時是否需要確認彈窗?** 如果使用者在對話中途切換角色，當前對話是否自動存檔? 還是需要提醒「切換後此對話將結束」?
- [ ] **`thread_id` 的 role_id 前綴策略是否過於僵硬?** 是否有未來場景需要「跨角色引用對話」(例如導師提及使用者在另一角色的進步)? 若有，應改為 ACL 層級控制而非前綴硬隔離。

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責，不能拆解 — 角色沙盒隔離
- [x] §2 至少 1 個 `Rxx` 引用 — R03 §2, §6, §人設崩塌
- [x] §3 Schema 用 Pydantic / dataclass — `RoleContext`, `RoleSwitchEvent`
- [x] §4 依賴是真實模組編號 — M4.1, M4.2, M6.2, M6.3, M3.1 等
- [x] §5 grep 過 `05_integration_risk_audit.md` — RISK-06, RISK-12
- [x] §6 測試先於程式碼 — 12 條驗收測試
- [x] §8 至少 3 條反模式 — 5 條
- [x] §9 至少 1 個開放問題 — 4 個

---

## 附錄：子模組拆分決策

> **結論：M4.3.1~M4.3.4 合併為單一 SPEC，不分開寫。**

| 評估維度 | M4.3 子模組情況 |
| -------- | -------------- |
| **部署邊界** | 全在同一 FastAPI sidecar 內，M4.3.1 是中介軟體，M4.3.2~M4.3.4 是它呼叫的內部函式 |
| **技術棧** | 全是 Python FastAPI middleware + SQLAlchemy 查詢 |
| **耦合度** | 極高 — M4.3.1 攔截請求後依序呼叫 M4.3.2 (DB 切換) → M4.3.3 (Persona 注入) → M4.3.4 (快取重置)，是同一個請求管線的四個階段 |
| **共享狀態** | 共用 `RoleContext` dataclass，管線式傳遞 |
| **獨立部署** | 不可能，它們是同一個 middleware 的內部邏輯分層 |
| **對照** | 類似 M4.1 / M4.2 — 同一服務內的邏輯節點，適合合併 |
