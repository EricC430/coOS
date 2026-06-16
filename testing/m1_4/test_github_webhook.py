"""
M1.4 -- Git & Workflow Telemetry acceptance tests

SPEC: docs/modules/M1_4_git_workflow_telemetry_SPEC.md
Research:
  [R06: 版本控制紀錄 §2.1] Git commit 歷史作為認知狀態感測器
  [R02: 時間動力學 §1.2] commit 間距的爆發性特徵

No integration RISK-xx triggered (M1.4 SPEC §5 確認).
"""
import hashlib
import hmac
import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, patch as mock_patch

import pytest
from fastapi.testclient import TestClient
from config import Settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "test_webhook_secret_32chars_fixed"


@pytest.fixture
def mock_settings():
    """Return a Settings instance with the test webhook secret (bypasses .env cache)."""
    return Settings(github_webhook_secret=WEBHOOK_SECRET, _env_file=None)


@pytest.fixture
def client(mock_settings):
    """FastAPI TestClient with M1.4 router registered and settings patched."""
    from services.main import app
    with patch("m1_4_github.webhooks.get_settings", return_value=mock_settings):
        yield TestClient(app)


@pytest.fixture
def webhook_secret():
    return WEBHOOK_SECRET


def _sign(secret: str, body: bytes) -> str:
    """Compute HMAC-SHA256 signature matching GitHub format."""
    return "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()


def _push_payload(
    repo_name: str = "coOS",
    commit_message: str = "feat: add user login",
    files: list[str] | None = None,
    commit_count: int = 1,
) -> dict:
    files = files or ["src/main.rs"]
    return {
        "ref": "refs/heads/main",
        "repository": {"name": repo_name, "full_name": f"EricC430/{repo_name}"},
        "commits": [
            {
                "id": "abc1234567890",
                "message": commit_message,
                "timestamp": "2026-06-03T10:00:00Z",
                "added": files[:1],
                "removed": [],
                "modified": files[1:] if len(files) > 1 else [],
            }
        ] * commit_count,
    }


def _pr_payload(action: str = "opened", changed_files: int = 3) -> dict:
    return {
        "action": action,
        "repository": {"name": "coOS", "full_name": "EricC430/coOS"},
        "pull_request": {
            "title": "feat: telemetry daemon",
            "body": "adds M1.1",
            "changed_files": changed_files,
            "number": 42,
        },
    }


# ---------------------------------------------------------------------------
# AC-1 & AC-2: Webhook Signature Verification
# ---------------------------------------------------------------------------

class TestWebhookSignatureVerification:
    def test_valid_signature_accepted(self, client, webhook_secret):
        """AC-1: 正確 HMAC-SHA256 簽名的 Webhook 回傳 200。"""
        body = json.dumps(_push_payload()).encode()
        sig = _sign(webhook_secret, body)
        resp = client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "push",
                "X-Hub-Signature-256": sig,
            },
        )
        assert resp.status_code == 200

    def test_invalid_signature_rejected(self, client):
        """AC-2: 錯誤簽名回傳 403。"""
        body = json.dumps(_push_payload()).encode()
        resp = client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "push",
                "X-Hub-Signature-256": "sha256=invalid",
            },
        )
        assert resp.status_code == 403

    def test_missing_signature_rejected(self, client):
        """AC-2b: 無簽名標頭回傳 403。"""
        body = json.dumps(_push_payload()).encode()
        resp = client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={"Content-Type": "application/json", "X-GitHub-Event": "push"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# AC-3: Push Event Processing
# ---------------------------------------------------------------------------

class TestPushEventProcessing:
    def test_push_event_creates_log(self, client):
        """AC-3: [R06 §2.1] commit push 事件寫入 raw_tracking_logs。"""
        payload = _push_payload(commit_count=3)
        body = json.dumps(payload).encode()
        sig = _sign(WEBHOOK_SECRET, body)

        with patch("m1_4_github.webhooks.emit_log", new_callable=AsyncMock) as mock_emit:
            mock_emit.return_value = None
            resp = client.post(
                "/api/v1/webhooks/github",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Event": "push",
                    "X-Hub-Signature-256": sig,
                },
            )
        assert resp.status_code == 200
        mock_emit.assert_called_once()

    def test_pr_event_creates_log(self, client):
        """AC-3b: [R06 §2.1] PR 事件寫入 raw_tracking_logs。"""
        payload = _pr_payload()
        body = json.dumps(payload).encode()
        sig = _sign(WEBHOOK_SECRET, body)

        with patch("m1_4_github.webhooks.emit_log", new_callable=AsyncMock) as mock_emit:
            mock_emit.return_value = None
            resp = client.post(
                "/api/v1/webhooks/github",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Event": "pull_request",
                    "X-Hub-Signature-256": sig,
                },
            )
        assert resp.status_code == 200
        mock_emit.assert_called_once()

    def test_unknown_event_returns_204(self, client):
        """AC-3c: 未知 event type 回傳 204 No Content (不處理但不報錯)。"""
        body = json.dumps({"action": "starred"}).encode()
        sig = _sign(WEBHOOK_SECRET, body)

        resp = client.post(
            "/api/v1/webhooks/github",
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "star",
                "X-Hub-Signature-256": sig,
            },
        )
        assert resp.status_code == 204


# ---------------------------------------------------------------------------
# AC-4 & AC-5: Privacy Constraints
# ---------------------------------------------------------------------------

class TestWebhookPrivacy:
    def test_commit_message_preserved_in_log(self, client):
        """AC-4: [R06 §2.1] commit message 保留於本地 L1 日誌 (不被丟棄)。"""
        payload = _push_payload(commit_message="feat: add user login functionality")
        body = json.dumps(payload).encode()
        sig = _sign(WEBHOOK_SECRET, body)

        captured = {}

        async def capture_emit(*args, **kwargs):
            captured.update(kwargs)

        with patch("m1_4_github.webhooks.emit_log", side_effect=capture_emit):
            client.post(
                "/api/v1/webhooks/github",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Event": "push",
                    "X-Hub-Signature-256": sig,
                },
            )
        payload_data = captured.get("payload", {})
        commits = payload_data.get("commits", [])
        assert any("user login" in c.get("message", "") for c in commits)

    def test_relative_file_paths_only(self, client):
        """AC-5: 修改檔案列表僅儲存相對路徑，不含絕對目錄結構。"""
        payload = _push_payload(files=["src/secrets/api_keys.py"])
        body = json.dumps(payload).encode()
        sig = _sign(WEBHOOK_SECRET, body)

        captured = {}

        async def capture_emit(*args, **kwargs):
            captured.update(kwargs)

        with patch("m1_4_github.webhooks.emit_log", side_effect=capture_emit):
            client.post(
                "/api/v1/webhooks/github",
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Event": "push",
                    "X-Hub-Signature-256": sig,
                },
            )
        files = captured.get("payload", {}).get("files", [])
        assert any("api_keys.py" in f for f in files)
        assert not any(f.startswith("C:") or "/Users/" in f or "\\Users\\" in f for f in files)


# ---------------------------------------------------------------------------
# AC-6: OAuth Flow
# ---------------------------------------------------------------------------

class TestOAuthFlow:
    def test_oauth_callback_returns_200(self, client):
        """AC-6: OAuth callback endpoint 存在且回應 200。"""
        with patch("m1_4_github.oauth.exchange_code_for_token") as mock_exchange:
            mock_exchange.return_value = "encrypted_token_abc"
            resp = client.get("/api/v1/auth/github/callback?code=test_code")
        assert resp.status_code == 200

    def test_oauth_callback_missing_code_returns_422(self, client):
        """AC-6b: callback 缺少 code 參數回傳 422。"""
        resp = client.get("/api/v1/auth/github/callback")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# AC-6 Local Git Monitor (M1.4.3)
# ---------------------------------------------------------------------------

class TestLocalGitMonitor:
    def _make_monitor(self, tmp_path, emitted):
        """Helper: create LocalGitMonitor with new API (dict paths + async callbacks)."""
        from services.m1_4_github.local_git_monitor import LocalGitMonitor
        path_str = str(tmp_path)
        emit_fn = AsyncMock(side_effect=lambda event: emitted.append(event))
        update_hash_fn = AsyncMock()
        monitor = LocalGitMonitor(
            watched_paths=[{"path": path_str, "last_hash": None}],
            emit_fn=emit_fn,
            update_hash_fn=update_hash_fn,
        )
        return monitor

    def test_detects_new_commit_in_repo(self, tmp_path):
        """AC (M1.4.3): [R06 §2.1] 本地 Git 掃描偵測到新 commit after baseline."""
        # Init repo with one commit
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True, capture_output=True)
        (tmp_path / "README.md").write_text("hello")
        subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "init: first commit"], check=True, capture_output=True)

        emitted = []
        monitor = self._make_monitor(tmp_path, emitted)

        import asyncio
        # First scan: establishes baseline (no emit)
        asyncio.run(monitor._check_repo(str(tmp_path)))
        assert len(emitted) == 0, "baseline scan should not emit"

        # Add a second commit
        (tmp_path / "file2.py").write_text("x = 2")
        subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "feat: second commit"], check=True, capture_output=True)

        # Second scan: detects new commit
        asyncio.run(monitor._check_repo(str(tmp_path)))
        assert len(emitted) == 1
        event = emitted[0]
        assert event["action"] == "local_commit"
        assert event["payload"]["repo_name"] == tmp_path.name
        assert "second commit" in str(event["payload"]["commits"])

    def test_no_duplicate_emit_on_rescan(self, tmp_path):
        """AC (M1.4.3): [R02 §1.2] 同一 commit 不重複 emit。"""
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True, capture_output=True)
        (tmp_path / "file.py").write_text("x = 1")
        subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "feat: x"], check=True, capture_output=True)

        emitted = []
        monitor = self._make_monitor(tmp_path, emitted)

        import asyncio
        asyncio.run(monitor._check_repo(str(tmp_path)))  # baseline
        asyncio.run(monitor._check_repo(str(tmp_path)))  # second scan, same HEAD

        assert len(emitted) == 0  # baseline only, no new commits

    def test_repo_path_stored_in_payload(self, tmp_path):
        """AC (M1.4.3): repo_path 絕對路徑存入 payload (本地識別用)。"""
        subprocess.run(["git", "init", str(tmp_path)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "config", "user.email", "test@test.com"], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True, capture_output=True)
        (tmp_path / "a.py").write_text("a = 1")
        subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "chore: init"], check=True, capture_output=True)

        emitted = []
        monitor = self._make_monitor(tmp_path, emitted)

        import asyncio
        asyncio.run(monitor._check_repo(str(tmp_path)))  # baseline

        # Add a second commit to trigger an emit
        (tmp_path / "b.py").write_text("b = 2")
        subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "chore: b"], check=True, capture_output=True)
        asyncio.run(monitor._check_repo(str(tmp_path)))

        assert len(emitted) == 1
        assert emitted[0]["payload"]["repo_path"] == str(tmp_path)

    def test_nonexistent_repo_does_not_crash(self):
        """AC (M1.4.3): 不存在的路徑靜默跳過，不拋例外。"""
        from services.m1_4_github.local_git_monitor import LocalGitMonitor

        emitted = []
        emit_fn = AsyncMock(side_effect=lambda event: emitted.append(event))
        monitor = LocalGitMonitor(
            watched_paths=[{"path": "/nonexistent/path", "last_hash": None}],
            emit_fn=emit_fn,
            update_hash_fn=AsyncMock(),
        )

        import asyncio
        asyncio.run(monitor._check_repo("/nonexistent/path"))
        assert len(emitted) == 0
