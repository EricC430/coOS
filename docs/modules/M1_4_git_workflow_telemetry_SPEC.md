# M1.4 — Git 與工作流遙測接收器 (Git & Workflow Telemetry)

**標籤**: `[MVP]`
**版本**: `1.1`
**最後更新**: 2026-06-02

---

## 子模組 SPEC 決策說明

M1.4 包含三個子模組 (M1.4.1~M1.4.3),**合併為單一 SPEC** 的理由:

1. **強耦合**:M1.4.2 的 Webhook 簽名驗證與事件查詢需要 M1.4.1 提供的 Access Token 與 Webhook Secret,兩者無法獨立運作。
2. **同一 FastAPI Router**:兩個子模組都在 FastAPI sidecar 內,共享同一個 `api/v1/webhooks/` 路由前綴。
3. **共同資料流**: M1.4.3 (本地 Git) 與 M1.4.2 (GitHub Webhook) 產出相同的 `GitActivityEvent` 結構化日誌,下游消費者無需區分來源。

**v1.1 變動** (相較 v1.0):

| 項目 | v1.0 | v1.1 | v1.2 |
|------|------|------|------|
| 模組名稱 | 外部自動化工作流接收器 (GitHub Webhook) | **Git 與工作流遙測接收器** | 同 v1.1 |
| 子模組 | M1.4.1~M1.4.2 | 新增 **M1.4.3 本地 Git 偵測器** | 同 v1.1 |
| Webhook 連通 | 未決議 | Cloudflare Tunnel Sidecar | **MVP 改用 `gh webhook forward`；Cloudflare 方案移至 Phase 6+** |
| Open Questions | Q1~Q3 未決議 | Q1~Q3 已結案 | Q3 方案更新 |

---

## 1. Purpose (目的)

採用「本地 Git 掃描（即時且離線）」+「GitHub Webhook（即時雲端推送）」的雙軌模式,全面感知使用者的開發活動:

- **本地 Git 掃描 (M1.4.3)**: 監控本機硬碟上任何 `.git` 專案的 commit 活動,100% 離線運作,不需網路。
- **GitHub Webhook (M1.4.2)**: 接收 GitHub 雲端推送的 Push / PR / Issues 事件,感知協作與管理活動。

> 一句話:「**無論離線或在線,技術人的開發活動都被完整感知**」。

> **MVP Webhook 連通方案**: 開發期間使用 `gh webhook forward` (GitHub CLI) 將 GitHub 事件轉發至本地 `localhost:8000`，不需要 Cloudflare Tunnel 或公開域名。`gh webhook forward` 在開發者手動執行後保持連線，FastAPI sidecar 正常接收事件。Cloudflare Tunnel 方案保留為 Phase 6+ 生產部署選項。

---

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R06 | §版本控制紀錄 §2.1 | Git commit 歷史作為認知狀態感測器:commit 頻率、commit 訊息語意、PR review 活動 |
| R02 | §時間動力學 §1.2 | commit 間距的爆發性特徵:密集 commit = 衝刺;長間距後突然 commit = 突破 |

---

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| GitHub Webhook `push` event | `PushPayload` | `{ ref: "refs/heads/main", commits: [{id, message, timestamp, added, removed, modified}] }` |
| GitHub Webhook `pull_request` event | `PRPayload` | `{ action: "opened", pull_request: {title, body, changed_files} }` |
| GitHub Webhook `issues` event | `IssuesPayload` | `{ action: "closed", issue: {title, labels} }` |
| GitHub OAuth callback | `code` query param | `GET /api/v1/auth/github/callback?code=xxx` |
| 本地 `.git` 目錄 (M1.4.3) | `git log` / `git diff --stat` | 本機硬碟上任何有 `.git` 的專案目錄 |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M0.4 → `raw_tracking_logs` (L1) | `GitActivityEvent` | `{ module: "M1.4.2", action: "commit_push", payload: { repo_name: "coOS", repo_path: "c:\\User\\coOS", files: ["src/main.rs"], commits: [{"hash": "abc12", "message": "feat: add user login"}], files_changed: 1, additions: 120, deletions: 30, commit_count: 1 } }` |
| M0.4 → `raw_tracking_logs` (L1) | `GitActivityEvent` | `{ module: "M1.4.2", action: "pr_opened", payload: { repo_name: "coOS", changed_files: 12 } }` |
| M0.4 → `raw_tracking_logs` (L1) | `GitActivityEvent` | `{ module: "M1.4.3", action: "local_commit", payload: { repo_name: "coOS", repo_path: "c:\\User\\coOS", branch: "main", files: ["src/main.rs"], commits: [{"hash": "abc12", "message": "feat: add user login"}], files_changed: 1, additions: 45, deletions: 10, commit_count: 1 } }` |

---

## 4. Dependencies

### 上游 (我依賴誰)

- **M0.2** (Tauri IPC): FastAPI sidecar 由 Tauri Rust 層管理生命週期；MVP 不再需要 Cloudflare Tunnel sidecar
- **M0.3** (環境變數): `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_WEBHOOK_SECRET` 從 `.env` 讀取；`CF_TUNNEL_TOKEN` 已移除（Phase 6+ 才需要）
- **M0.4** (結構化日誌): 所有事件經 M0.4 管線寫入 `raw_tracking_logs`
- **M6.1** (SQLite): 儲存 GitHub Access Token (加密) 與 Webhook 配置;儲存本地 Git 監控路徑清單

### 下游 (誰依賴我)

- **M4.8** (隱性狀態推論): commit 頻率與間距作為認知狀態特徵 `[R02 §1.2]`
- **M4.4** (深夜草稿): 統計「今日在哪些 repo 做了多少 commit」並讀取 commit message/相對路徑生成日報
- **M3.6** (Workflow Modal): 提供 GitHub Repo 綁定的管理介面

---

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| (無直接 RISK-xx) | Webhook/Local commit payload 含 commit message 與檔案資訊 → 可能含敏感資訊 | commit message 與修改檔案列表**限於本地 L1 儲存**且絕不上雲;在 L2 邊緣推論消費後即時降維;本地提供 PII 敏感詞過濾器自動遮蔽金鑰或密碼 |
| (無直接 RISK-xx) | GitHub Access Token 洩漏 → 攻擊者可讀取私有 repo | Token 以 AES-256 加密存入本地 SQLite;不上雲;Token scope 限制為 `repo:status` + `read:org` 最小權限 |
| (無直接 RISK-xx) | Webhook 簽名驗證失敗 → 偽造事件注入 | 使用 `GITHUB_WEBHOOK_SECRET` 進行 HMAC-SHA256 簽名驗證;失敗回傳 403 |

---

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m1_4/test_github_webhook.py

class TestWebhookSignatureVerification:
    def test_valid_signature_accepted(self, client, webhook_secret):
        """驗收條件 1: 正確簽名的 Webhook 回傳 200"""
        payload = {"ref": "refs/heads/main", "commits": []}
        sig = compute_hmac_sha256(webhook_secret, json.dumps(payload))
        resp = client.post("/api/v1/webhooks/github",
                           json=payload,
                           headers={"X-Hub-Signature-256": f"sha256={sig}"})
        assert resp.status_code == 200

    def test_invalid_signature_rejected(self, client):
        """驗收條件 2: 錯誤簽名回傳 403"""
        resp = client.post("/api/v1/webhooks/github",
                           json={"ref": "refs/heads/main"},
                           headers={"X-Hub-Signature-256": "sha256=invalid"})
        assert resp.status_code == 403

class TestPushEventProcessing:
    def test_push_event_creates_log_within_5s(self, client, mock_db):
        """驗收條件 3: commit push 後 5 秒內出現在 raw_tracking_logs"""
        send_push_webhook(client, commits=3, files_changed=5)
        events = mock_db.query_by_module("M1.4.2")
        assert len(events) >= 1
        assert events[0].action == "commit_push"
        assert events[0].payload["commit_count"] == 3

class TestPrivacy:
    def test_commit_message_stored_locally(self, client, mock_db):
        """驗收條件 4: commit message 正確儲存於本地日誌 (不被完全丟棄)"""
        send_push_webhook(client, commit_message="feat: add user login functionality")
        events = mock_db.query_by_module("M1.4.2")
        assert len(events) >= 1
        assert events[0].payload["commits"][0]["message"] == "feat: add user login functionality"

    def test_relative_file_paths_stored_but_absolute_scrubbed(self, client, mock_db):
        """驗收條件 5: 修改檔案列表僅儲存相對路徑,不得包含本機使用者家目錄結構"""
        send_push_webhook(client, files=["src/secrets/api_keys.py"])
        events = mock_db.query_by_module("M1.4.2")
        assert len(events) >= 1
        assert "src/secrets/api_keys.py" in events[0].payload["files"]
        # 確保不會記錄包含使用者家目錄的絕對目錄路徑
        assert "Users" not in str(events[0].payload["files"])
        assert "C:" not in str(events[0].payload["files"])

    def test_absolute_repo_path_stored_locally(self, client, mock_db):
        """驗收條件 6: 本地專案路徑 repo_path 正確儲存於本地 L1,供識別工作區"""
        send_push_webhook(client, repo_path="C:\\Users\\username\\coOS")
        events = mock_db.query_by_module("M1.4.2")
        assert len(events) >= 1
        assert events[0].payload["repo_path"] == "C:\\Users\\username\\coOS"

class TestOAuthFlow:
    def test_oauth_callback_stores_token(self, client, mock_github_api):
        """驗收條件 6: OAuth callback 正確儲存加密 Token"""
        resp = client.get("/api/v1/auth/github/callback?code=test_code")
        assert resp.status_code == 200
        stored = get_github_token_from_db()
        assert stored is not None
        assert stored != "raw_token"  # 已加密
```

---

## 7. Implementation Notes

### 7.1 子模組職責邊界

| 子模組 | 檔案路徑 | 核心職責 |
| ------ | -------- | -------- |
| M1.4.1 | `services/m1_4_github/oauth.py` | GitHub OAuth 2.0 授權流程;Token 加密存儲;Token refresh |
| M1.4.2 | `services/m1_4_github/webhooks.py` | Webhook Router;HMAC-SHA256 簽名驗證;Payload 解析 → 結構化日誌 |
| M1.4.3 | `services/m1_4_github/local_git_monitor.py` | 本地 Git 偵測器:定期掃描 `.git` 目錄;`git log` 解析;離線 commit 事件產出 |

### 7.2 FastAPI Router

```python
# services/m1_4_github/router.py
from fastapi import APIRouter, Request, HTTPException
import hmac, hashlib

router = APIRouter(prefix="/api/v1/webhooks")

@router.post("/github")
async def github_webhook(request: Request):
    # [M1.4.2] HMAC-SHA256 簽名驗證
    signature = request.headers.get("X-Hub-Signature-256", "")
    body = await request.body()
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(403, "Invalid signature")

    payload = await request.json()
    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "push":
        await process_push(payload)
    elif event_type == "pull_request":
        await process_pr(payload)
    return {"status": "ok"}
```

### 7.3 本地 Git 偵測器 (M1.4.3) — v1.1 新增

```python
# services/m1_4_github/local_git_monitor.py
import subprocess
import asyncio
from pathlib import Path
from datetime import datetime, timezone

class LocalGitMonitor:
    """
    定期掃描使用者註冊的本地 Git 專案目錄,
    偵測新的 commit 並產出 GitActivityEvent。
    100% 離線運作,不需網路。
    """
    
    SCAN_INTERVAL_S = 60  # 每 60 秒掃描一次
    
    def __init__(self, watched_paths: list[str], logger):
        self._watched_paths = watched_paths  # 從 SQLite 讀取
        self._last_seen_commits: dict[str, str] = {}  # repo_path -> last_commit_hash
        self._logger = logger
    
    async def scan_loop(self):
        """背景循環:定期掃描所有註冊的 Git 專案"""
        while True:
            for repo_path in self._watched_paths:
                await self._check_repo(repo_path)
            await asyncio.sleep(self.SCAN_INTERVAL_S)
    
    async def _check_repo(self, repo_path: str):
        """[R06 §2.1] 檢查單一 repo 是否有新 commit"""
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-1", "--format=%H"],
                cwd=repo_path, capture_output=True, text=True, timeout=5
            )
            latest_hash = result.stdout.strip()
            
            if not latest_hash:
                return
            
            last_seen = self._last_seen_commits.get(repo_path)
            if last_seen == latest_hash:
                return  # 無新 commit
            
            # 取得自上次以來的所有新 commit 統計
            new_commits = self._get_new_commits_stats(repo_path, last_seen)
            
            if new_commits:
                repo_name = Path(repo_path).name
                branch = self._get_current_branch(repo_path)
                await self._logger.emit(
                    module="M1.4.3",
                    action="local_commit",
                    level="INFO",
                    payload={
                        "repo_name": repo_name,
                        "repo_path": repo_path,  # v1.1: 記錄本機絕對路徑以辨識工作區
                        "branch": branch,
                        "commit_count": new_commits["count"],
                        "files_changed": new_commits["files_changed"],
                        "files": new_commits["files"],  # v1.1: 相對專案根目錄之相對路徑列表
                        "additions": new_commits["additions"],
                        "deletions": new_commits["deletions"],
                        "commits": new_commits["commits"],  # v1.1: 包含 commit message 列表供反思草稿使用
                    }
                )
            
            self._last_seen_commits[repo_path] = latest_hash
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # repo 不存在或 git 未安裝,靜默跳過
    
    def _get_new_commits_stats(self, repo_path: str, since_hash: str | None) -> dict:
        """[R02 §1.2] 取得 diff stat 統計值"""
        cmd = ["git", "diff", "--stat", "--numstat"]
        if since_hash:
            cmd.append(f"{since_hash}..HEAD")
        else:
            cmd.extend(["HEAD~1..HEAD"])  # 首次掃描只看最新一筆
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True, timeout=5)
        # 解析 numstat 統計值...
        return {"count": 1, "files_changed": 0, "additions": 0, "deletions": 0}  # 簡化示意
    
    def _get_current_branch(self, repo_path: str) -> str:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_path, capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or "detached"
```

### 7.4 MVP Webhook 連通：`gh webhook forward`

MVP 開發期間不使用 Cloudflare Tunnel。開發者在終端機手動執行以下指令，將 GitHub 事件轉發至本地 FastAPI：

```powershell
# 開發前執行一次，保持終端機視窗開啟
gh webhook forward `
  --repo=你的帳號/repo名稱 `
  --events=push,pull_request `
  --url=http://localhost:8000/api/v1/webhooks/github `
  --secret=$env:GITHUB_WEBHOOK_SECRET
```

**運作方式**：`gh webhook forward` 在 GitHub 上暫時建立一個 Webhook，將事件透過 GitHub CLI 的長連線轉發至本地端點。終端機關閉後 Webhook 自動失效，不會殘留在 GitHub 設定中。

**限制**：
- 需要開發者手動執行，不會隨 Tauri app 自動啟動
- 每次開發 session 重新執行即可
- 不影響 M1.4.3 本地 Git 掃描（完全離線，無需此步驟）

**Phase 6+ 生產方案**：屆時改用 Cloudflare Tunnel 作為 Tauri sidecar 自動啟動（需公開域名），`CF_TUNNEL_TOKEN` 環境變數屆時才加入。

### 7.5 異常處理

| 例外情況 | 處理方式 |
| -------- | -------- |
| GitHub OAuth Token 過期 | 自動使用 refresh_token 更新;若失敗,通知使用者重新授權 |
| Webhook payload 格式異常 | 記錄 `level: "WARN"` log,回傳 400,不寫入 `raw_tracking_logs` |
| M0.4 寫入管線不可用 | 本地 buffer 暫存 (max 50 events);恢復後批次回傳 |
| `gh webhook forward` 未執行 | M1.4.2 Webhook 無法收到事件;M1.4.3 本地 Git 不受影響;記錄 `level: "INFO"` 提示開發者啟動指令 |
| 本地 `.git` 目錄不存在或不可讀 | 靜默跳過;下次掃描再試 |
| `git` 未安裝 (系統無 git CLI) | M1.4.3 整體停用,記錄 `level: "ERROR"` log |

---

## 8. Anti-patterns (反模式)

- ❌ **不要將 commit message 上傳至雲端 L3 儲存** — 限制儲存於本地 L1 資料庫，僅供 L2 本地推論與深夜反思生成使用，以防止語意敏感資訊外流。
- ❌ **不要記錄含有使用者家目錄或系統敏感結構的絕對檔案路徑** — 專案內的檔案變更僅能記錄相對於專案根目錄的**相對路徑**（如 `src/main.rs`）。
- ❌ **不要將本機專案絕對路徑（repo_path）同步至 L3 雲端** — 本地路徑（如 `c:\User\coOS`）僅限本地處理，禁止上傳。
- ❌ **不要將 GitHub Access Token 明文儲存** — 必須 AES-256 加密後存入本地 SQLite。
- ❌ **不要將 Webhook 事件轉發至雲端** — 所有 GitHub 事件僅存本地 `raw_tracking_logs` (L1)。

---

## 9. Open Questions

- [x] ~~**Q1: 是否支援 GitHub App 模式?**~~ → MVP 階段先用 **OAuth App**（開發簡單）。未來商業化或有細緻權限控制需求時再重構為 GitHub App。
- [x] ~~**Q2: 是否支援多個 GitHub 帳號/組織?**~~ → MVP 僅支援**單一帳號**。進階可擴充多帳號/組織支援。
- [x] ~~**Q3: Webhook endpoint 如何從外部可達?**~~ → **MVP 採用 `gh webhook forward`** (§7.4)。開發者手動在終端執行一次，GitHub CLI 建立臨時 Webhook 並長連線轉發至 `localhost:8000`，終端關閉後自動失效，零基礎設施成本。Cloudflare Tunnel 方案保留至 Phase 6+ 生產部署。

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責 (雙軌 Git 遙測)
- [x] §2 至少 1 個 `Rxx` 引用 (R06 §2.1, R02 §1.2)
- [x] §3 Schema 定義完整 (含 M1.4.3 本地 Git 輸出)
- [x] §4 依賴是真實模組編號 (M0.2 FastAPI sidecar; MVP 無 Cloudflare sidecar)
- [x] §5 已 grep `05_integration_risk_audit.md`
- [x] §6 測試先於程式碼,覆蓋 6 個驗收條件
- [x] §8 至少 5 條反模式
- [x] §9 3 個開放問題已結案
