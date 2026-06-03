# M4.7 — Markdown 同步至 Obsidian Agent

**標籤**:`[MVP]`
**版本**:`1.0`
**最後更新**:2026-06-03

## 1. Purpose

在對話 Session 結束時，從 M4.6 Observer 已萃取的結構化資訊（專案、意圖、承諾、時間投入）自動歸納成 Markdown 摘要，寫入使用者指定的 Obsidian Vault——讓 coOS 的 AI 洞察成為使用者本地知識庫的持續輸入，無需手動複製貼上。

## 2. References

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R10 | §代理工作流狀態機 | Session 結束觸發器：M4.7 作為 Agent 工作流的終止節點，負責輸出持久化 |
| R10 | §MindScape 反思鷹架 | 摘要格式以結構化鷹架（目標 / 行動 / 感受 / 下一步）組織，而非自由文字 |
| R08 | §五 意圖脫鉤與作者身分設計模式 | 摘要由 AI 生成但寫入本地 Vault 維持使用者「作者身分」——洞察屬於我，不鎖在 app 裡 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M4.6 Session 結束事件 | `SessionEndEvent { thread_id, role_id, ended_at }` | `{ thread_id: "t_001", role_id: "csie_001", ended_at: "2026-06-03T23:00:00" }` |
| M4.6 萃取結構 (via M6.1 `chat_transcripts`) | `ObserverSummary { projects[], intents[], commitments[], time_spent_minutes }` | `{ projects: ["OpenStack 部署"], intents: ["學習 K8s"], time_spent_minutes: 90 }` |
| M6.3 `role_context_aggregates` | `{ role_name, active_goals[] }` | `{ role_name: "資工系大學生", active_goals: ["畢業專題"] }` |
| M3.6 已綁定的 Vault 路徑 (via M0.3 `.env`) | `string` (本機絕對路徑) | `"C:/Users/user/Documents/ObsidianVault"` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| 本機 Vault `.md` 檔案（透過 Tauri `fs` API 寫入） | Markdown 文件 | `coOS/2026-06-03_csie.md` |
| `raw_tracking_logs` (M0.4) | `{ source: "M4.7", event: "vault_write_success", thread_id, file_path }` | 寫入成功後的觀測紀錄 |

### 輸出 Markdown 結構

```markdown
# [角色名稱] Session 摘要 — YYYY-MM-DD

## 本次工作
- 投入時間：N 分鐘
- 專案：{{projects}}

## 意圖與行動
{{intents}}

## 承諾
{{commitments}}

## 下一步（AI 建議）
{{ai_next_step_suggestion}}

---
*由 coOS M4.7 自動生成 | thread: {{thread_id}}*
```

## 4. Dependencies

### 上游 (我依賴誰)

- **M4.6** (Observer 背景萃取 Agent)：提供 Session 內萃取的結構化資訊；M4.7 消費 M4.6 的輸出，不重複做萃取
- **M0.2** (Tauri IPC)：透過 Tauri `fs::write_file` API 存取本機檔案系統（Python sidecar 無法直接寫入 Vault）
- **M0.3** (環境變數管理)：Vault 路徑從 `.env` 讀取（`OBSIDIAN_VAULT_PATH`）
- **M6.3** (角色與情境鏈結)：補充角色名稱與目標資訊至摘要

### 下游 (誰依賴我)

- 無其他模組依賴 M4.7（純輸出端，終止節點）

## 5. Known Risks

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| （無現有 RISK-xx） | Vault 路徑不存在或無寫入權限 → 靜默失敗，使用者不知道沒寫入 | 寫入失敗時必須在 M3.4 對話框末尾顯示警示 Toast：「Obsidian 同步失敗，請檢查 Vault 路徑設定」 |
| （無現有 RISK-xx） | 摘要若含 M4.6 萃取的敏感字串（人名、密碼片段）直接落盤 | M4.6 萃取結果已過 M2.3 Eguard；M4.7 在組裝 Markdown 前再做一次 PII regex 檢查，不依賴上游保證 |
| （隱性 RISK-12 衍生） | 若使用者把 Vault 同步到雲端（iCloud / Dropbox），coOS 寫入的摘要會上雲 | 偵測到常見雲端同步目錄（`iCloudDrive/`、`Dropbox/`）時顯示一次性警告，尊重使用者決定，不阻止 |

## 6. Acceptance Criteria

```python
# tests/m4_7/test_obsidian_sync.py

import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock

class TestM4_7_VaultWrite:
    async def test_markdown_file_created_on_session_end(self, tmp_vault: Path):
        """Session 結束後 Vault 中出現對應日期的 .md 檔案"""
        summary = build_mock_observer_summary(
            thread_id="t_001",
            projects=["OpenStack 部署"],
            time_spent_minutes=90,
        )
        await obsidian_sync_agent.run(
            summary=summary,
            vault_path=str(tmp_vault),
            role_name="資工系大學生",
            date="2026-06-03",
        )
        expected = tmp_vault / "coOS" / "2026-06-03_csie.md"
        assert expected.exists()

    async def test_markdown_contains_required_sections(self, tmp_vault: Path):
        """輸出 Markdown 包含所有必要區塊"""
        summary = build_mock_observer_summary(projects=["K8s 學習"])
        await obsidian_sync_agent.run(summary=summary, vault_path=str(tmp_vault))
        content = (tmp_vault / "coOS" / "2026-06-03_csie.md").read_text(encoding="utf-8")
        assert "## 本次工作" in content
        assert "## 意圖與行動" in content
        assert "## 承諾" in content
        assert "## 下一步" in content

    async def test_pii_stripped_before_write(self, tmp_vault: Path):
        """寫入 Vault 前必須剝離 PII"""
        summary = build_mock_observer_summary(
            intents=["幫 陳小明 準備簡報"]  # 含人名
        )
        await obsidian_sync_agent.run(summary=summary, vault_path=str(tmp_vault))
        content = (tmp_vault / "coOS" / "2026-06-03_csie.md").read_text(encoding="utf-8")
        assert "陳小明" not in content  # PII 已遮蔽

    async def test_write_failure_triggers_toast_notification(self):
        """Vault 路徑不存在時，前端收到錯誤通知"""
        with patch("tauri_fs.write_file", side_effect=FileNotFoundError):
            event = await obsidian_sync_agent.run(
                summary=build_mock_observer_summary(),
                vault_path="/nonexistent/path",
            )
        assert event.error_type == "vault_write_failed"
        # 前端 Toast 由 M0.2 Tauri 事件派發觸發，此處只驗證事件發出
        assert event.notify_frontend is True

    async def test_empty_session_no_file_written(self, tmp_vault: Path):
        """無任何萃取結果的 Session 不應寫入空白 .md 檔案"""
        summary = build_mock_observer_summary(projects=[], intents=[], commitments=[])
        await obsidian_sync_agent.run(summary=summary, vault_path=str(tmp_vault))
        vault_dir = tmp_vault / "coOS"
        md_files = list(vault_dir.glob("*.md")) if vault_dir.exists() else []
        assert len(md_files) == 0

    async def test_idempotent_write_same_session(self, tmp_vault: Path):
        """同一 thread_id 重複觸發只覆寫，不產生多個檔案"""
        summary = build_mock_observer_summary(thread_id="t_dup")
        await obsidian_sync_agent.run(summary=summary, vault_path=str(tmp_vault))
        await obsidian_sync_agent.run(summary=summary, vault_path=str(tmp_vault))
        md_files = list((tmp_vault / "coOS").glob("*.md"))
        assert len(md_files) == 1  # 只有一個檔案
```

## 7. Implementation Notes

### 7.1 LangGraph 節點定位

M4.7 是 Session 結束時的**終止節點**，由 M4.1 的 Graph `END` 邊觸發：

```python
# services/m4_7_obsidian_sync/agent.py

from langgraph.graph import StateGraph, END

def build_session_end_graph():
    graph = StateGraph(SessionState)
    # ...其他節點（M4.2, M4.6 等）...
    graph.add_node("obsidian_sync", obsidian_sync_node)  # M4.7
    graph.add_edge("obsidian_sync", END)
    return graph.compile()

async def obsidian_sync_node(state: SessionState) -> SessionState:
    summary = state.observer_summary  # 由 M4.6 填入
    if not summary.has_content():
        # [R10 §代理工作流] 無內容不寫，避免空白 .md 污染 Vault
        return state
    md_content = render_markdown(summary, state.role_context)
    await write_to_vault(md_content, state.vault_path, state.session_date)
    return state
```

### 7.2 Markdown 渲染器

```python
# services/m4_7_obsidian_sync/renderer.py

# [R10 §MindScape 反思鷹架] 輸出格式遵循結構化鷹架
def render_markdown(summary: ObserverSummary, role: RoleContext) -> str:
    sections = []
    sections.append(f"# [{role.name}] Session 摘要 — {summary.date}")
    sections.append(f"\n## 本次工作\n- 投入時間：{summary.time_spent_minutes} 分鐘")
    if summary.projects:
        sections.append("- 專案：" + "、".join(summary.projects))
    if summary.intents:
        sections.append("\n## 意圖與行動\n" + "\n".join(f"- {i}" for i in summary.intents))
    if summary.commitments:
        sections.append("\n## 承諾\n" + "\n".join(f"- [ ] {c}" for c in summary.commitments))
    if summary.ai_next_step:
        sections.append(f"\n## 下一步（AI 建議）\n{summary.ai_next_step}")
    sections.append(f"\n---\n*由 coOS M4.7 自動生成 | thread: {summary.thread_id}*")
    return "\n".join(sections)
```

### 7.3 Vault 寫入（Tauri fs API）

```python
# services/m4_7_obsidian_sync/vault_writer.py

import os
from pathlib import Path

async def write_to_vault(content: str, vault_path: str, date: str, role_slug: str) -> None:
    target_dir = Path(vault_path) / "coOS"
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / f"{date}_{role_slug}.md"
    # 同 thread 覆寫，不重複建檔（idempotent）
    file_path.write_text(content, encoding="utf-8")

    # 寫入 raw_tracking_logs（M0.4）
    await log_event("vault_write_success", {
        "file_path": str(file_path),
        "content_length": len(content),
    })
```

### 7.4 PII 清理（寫入前最後一道）

```python
# [RISK-12 衍生] M4.7 自身的 PII 二次防線
import re

PII_PATTERNS = [
    r'\b[A-Z][a-z]+\s[A-Z][a-z]+\b',   # 英文全名
    r'[一-鿿]{2,3}(?:小|大|老)\w',  # 中文姓名模式
]

def strip_pii(text: str) -> str:
    for pattern in PII_PATTERNS:
        text = re.sub(pattern, "[姓名已遮蔽]", text)
    return text
```

### 7.5 異常處理

| 情境 | 處理方式 |
| ---- | -------- |
| Vault 路徑未設定 (`OBSIDIAN_VAULT_PATH` 為空) | 跳過寫入，在 `raw_tracking_logs` 記錄 `vault_path_not_configured`，不報錯 |
| 路徑不存在或無寫入權限 | 透過 Tauri 事件發送 `OBSIDIAN_SYNC_FAILED`，M3.4 顯示 Toast 提示 |
| M4.6 萃取結果為空（使用者只閒聊，無結構化資訊） | 不寫入，不通知，靜默跳過 |
| Vault 同步至雲端目錄 | 偵測路徑包含 `iCloudDrive`、`Dropbox`、`OneDrive` → 顯示一次性警告 |

## 8. Anti-patterns

- ❌ **不要讓 M4.7 自行萃取對話內容**。萃取職責屬 M4.6；M4.7 只負責消費 M4.6 的 `ObserverSummary` 並渲染輸出。重複萃取會造成雙重 LLM 呼叫與結果不一致
- ❌ **不要把 Vault 路徑硬編碼在程式碼中**。路徑由 `.env` 的 `OBSIDIAN_VAULT_PATH` 管理（M0.3）；不同使用者的 Vault 位置不同
- ❌ **不要在 Session 中途（對話未結束時）寫入 Vault**。M4.7 只在 Session 結束時觸發；中途寫入會產生不完整的摘要，污染 Vault
- ❌ **不要把 `chat_transcripts` 原文貼入 Markdown**。原始對話逐字稿是 L1 明文（不可落盤到 Vault 此類可能雲同步的位置）；只能寫入 M4.6 已萃取、Eguard 已過濾的結構化摘要

## 9. Open Questions

- [ ] **`ai_next_step` 建議的生成方式？** 由 M4.6 已有的萃取結果延伸，還是額外呼叫一次 LLM？後者成本較高，需決策
- [ ] **每個 Session 對應一個 .md 檔，還是按日期合併到同一個檔？** 如果使用者一天開 5 個 Session，Vault 目錄會快速增長
- [ ] **若使用者刪除了 Vault 中的 .md 檔，coOS 是否需要感知並停止同步？** 還是每次都重新生成覆寫？
- [ ] **Markdown 格式是否需要使用者自訂範本（Template）？** 部分 Obsidian 重度使用者有自己的 note 格式

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責：渲染 + 寫入，不萃取
- [x] §2 至少 3 個 `Rxx §章節` 引用
- [x] §3 Schema 含輸出 Markdown 結構定義
- [x] §4 依賴是真實模組編號
- [x] §5 三條自定義風險（無現有 RISK-xx 直接對應，但均交叉參照）
- [x] §6 測試含 PII、冪等性、空 Session 三個邊界案例
- [x] §8 至少 4 條反模式含隱私層級原則
- [x] §9 至少 4 個開放問題
